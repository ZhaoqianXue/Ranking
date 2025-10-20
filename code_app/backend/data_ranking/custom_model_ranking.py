#!/usr/bin/env python3
"""
Custom Model Ranking Logic
This module handles on-the-fly spectral ranking for a user-submitted model
against the existing top 100 Hugging Face LLMs.
"""
import os
import sys
import json
import pandas as pd
import subprocess
import asyncio
import uuid
import shutil
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project root to locate necessary files and scripts
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))

async def _enrich_ranking_results(
    ranking_data: Dict,
    sanitized_user_model_name: str,
    original_user_model_name: str,
    user_scores: Dict,
    combined_input_df: pd.DataFrame
) -> Dict:
    """
    Enriches the raw ranking results from the R script with full benchmark data and model info.
    Avoid external leaderboard matching by deriving benchmark scores directly from
    the combined input dataframe used for ranking. This eliminates N/A values and
    ensures names map correctly via column order.
    """
    # Build mapping from R-returned (mangled) names to original CSV column names
    # The order of methods in the JSON equals the numeric columns' order in the CSV
    if 'benchmark' in combined_input_df.columns:
        original_model_names = combined_input_df.columns[1:].tolist()
    else:
        original_model_names = combined_input_df.columns.tolist()
    r_mangled_names = [method['name'] for method in ranking_data.get('methods', [])]
    r_to_original_name_map = dict(zip(r_mangled_names, original_model_names))

    # Prepare quick access to benchmark rows (lowercased)
    if 'benchmark' not in combined_input_df.columns:
        raise ValueError("Combined input dataframe must contain a 'benchmark' column")

    benchmarks_series = combined_input_df['benchmark'].astype(str).str.lower()
    # Accept both 'average' or 'average_score'
    benchmark_keys = {
        'ifeval': 'ifeval',
        'bbh': 'bbh',
        'math': 'math',
        'gpqa': 'gpqa',
        'musr': 'musr',
        'mmlu_pro': 'mmlu_pro',
        'average_score': 'average_score',
        'average': 'average'
    }

    def get_benchmark_value(col_name: str, key: str) -> float | None:
        row_mask = benchmarks_series == key
        if not row_mask.any():
            return None
        try:
            val = combined_input_df.loc[row_mask, col_name].values[0]
            return None if pd.isna(val) else float(val)
        except Exception:
            return None

    enhanced_methods = []

    for method in ranking_data.get('methods', []):
        r_model_name = method['name']
        original_model_name = r_to_original_name_map.get(r_model_name, r_model_name)
        is_user_model = (original_model_name == sanitized_user_model_name)

        display_name = original_user_model_name if is_user_model else original_model_name
        model_url = None

        if is_user_model:
            # User-provided scores (keys are title-cased in UI); normalize
            avg_user = sum(user_scores.values()) / len(user_scores) if user_scores else 0.0
            benchmark_scores_payload = {
                'ifeval': float(user_scores.get('IFEval')) if user_scores.get('IFEval') is not None else None,
                'bbh': float(user_scores.get('BBH')) if user_scores.get('BBH') is not None else None,
                'math': float(user_scores.get('MATH')) if user_scores.get('MATH') is not None else None,
                'gpqa': float(user_scores.get('GPQA')) if user_scores.get('GPQA') is not None else None,
                'musr': float(user_scores.get('MUSR')) if user_scores.get('MUSR') is not None else None,
                'mmlu_pro': float(user_scores.get('MMLU-Pro')) if user_scores.get('MMLU-Pro') is not None else None,
                'average_score': float(avg_user)
            }
        else:
            # Derive from combined_input_df directly
            col = original_model_name
            if col not in combined_input_df.columns:
                # Defensive: try to find by simple suffix match
                candidates = [c for c in combined_input_df.columns if c.endswith('/' + col) or col.endswith('/' + c)]
                if candidates:
                    col = candidates[0]
            # Fetch benchmark values
            ifeval_v = get_benchmark_value(col, benchmark_keys['ifeval'])
            bbh_v = get_benchmark_value(col, benchmark_keys['bbh'])
            math_v = get_benchmark_value(col, benchmark_keys['math'])
            gpqa_v = get_benchmark_value(col, benchmark_keys['gpqa'])
            musr_v = get_benchmark_value(col, benchmark_keys['musr'])
            mmlu_v = get_benchmark_value(col, benchmark_keys['mmlu_pro'])
            avg_v = get_benchmark_value(col, benchmark_keys['average_score'])
            if avg_v is None:
                avg_v = get_benchmark_value(col, benchmark_keys['average'])
            if avg_v is None:
                # Compute average if not present
                vals = [v for v in [ifeval_v, bbh_v, math_v, gpqa_v, musr_v, mmlu_v] if v is not None]
                avg_v = float(sum(vals) / len(vals)) if vals else None

            benchmark_scores_payload = {
                'ifeval': ifeval_v,
                'bbh': bbh_v,
                'math': math_v,
                'gpqa': gpqa_v,
                'musr': musr_v,
                'mmlu_pro': mmlu_v,
                'average_score': avg_v
            }

            # Construct a simple model URL if it resembles hf path
            if '/' in original_model_name:
                model_url = f"https://huggingface.co/{original_model_name}"

        enhanced_method = method.copy()
        enhanced_method['name'] = display_name
        enhanced_method['benchmark_scores'] = benchmark_scores_payload
        enhanced_method['model_url'] = model_url
        enhanced_methods.append(enhanced_method)

    ranking_data['methods'] = enhanced_methods
    return ranking_data

async def run_custom_ranking(model_name: str, scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Main function to execute the on-the-fly ranking.
    """
    # 1. Prepare data by adding the user's model to the base top 100 data
    base_data_path = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_processing', 'huggingface_processed_top100.csv')
    if not os.path.exists(base_data_path):
        raise FileNotFoundError(f"Base ranking data not found at {base_data_path}")
    
    df = pd.read_csv(base_data_path)

    # Sanitize user model name to be a valid R data.frame column name
    # R replaces invalid characters with '.'
    sanitized_model_name = ''.join(c if c.isalnum() else '.' for c in model_name)
    if not sanitized_model_name or not sanitized_model_name[0].isalpha():
        sanitized_model_name = 'X' + sanitized_model_name

    # Check for name collisions and append a suffix if necessary
    original_sanitized_name = sanitized_model_name
    counter = 1
    while sanitized_model_name in df.columns:
        sanitized_model_name = f"{original_sanitized_name}.{counter}"
        counter += 1

    # Normalize score keys to lower case to match benchmark names in the dataframe
    scores_lower = {k.lower(): v for k, v in scores.items()}
    # MMLU-Pro key needs special handling
    if 'mmlu-pro' in scores_lower:
        scores_lower['mmlu_pro'] = scores_lower.pop('mmlu-pro')

    benchmark_order = df['benchmark'].astype(str).str.lower().tolist()
    user_scores_ordered = [float(scores_lower.get(b, 0.0)) if scores_lower.get(b, None) is not None else 0.0 for b in benchmark_order]
    df[sanitized_model_name] = user_scores_ordered

    # 2. Save combined data to a temporary CSV file
    # Use a unique ID for the temporary directory to handle concurrent requests
    job_id = str(uuid.uuid4())
    temp_dir = os.path.join(PROJECT_ROOT, 'temp_ranking_jobs', job_id)
    os.makedirs(temp_dir, exist_ok=True)
    temp_csv_path = os.path.join(temp_dir, 'custom_ranking_input.csv')
    df.to_csv(temp_csv_path, index=False)

    try:
        # 3. Run the spectral ranking R script as a subprocess
        if not shutil.which('Rscript'):
            raise FileNotFoundError("Rscript executable not found. Ensure R is installed in the running environment.")
        ranking_script = os.path.join(PROJECT_ROOT, 'demo_r', 'ranking_cli.R')
        if not os.path.exists(ranking_script):
            raise FileNotFoundError(f"R script not found at {ranking_script}")
        cmd = [
            'Rscript', ranking_script,
            '--csv', temp_csv_path,
            '--bigbetter', '1',
            '--B', '2000',  # Using the standard number of iterations for accuracy
            '--seed', '42',
            '--out', temp_dir
        ]

        logger.info(f"Executing R script for job {job_id}: {' '.join(cmd)}")
        
        # Run the subprocess in a separate thread to avoid blocking the event loop
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_message = stderr.decode() or stdout.decode()
            logger.error(f"Spectral ranking script failed for job {job_id}: {error_message}")
            raise RuntimeError(f"Spectral ranking failed: {error_message}")

        # 4. Process the results JSON
        results_file = os.path.join(temp_dir, 'ranking_results.json')
        if not os.path.exists(results_file):
            raise FileNotFoundError("Ranking script did not produce an output file.")

        with open(results_file, 'r') as f:
            ranking_data = json.load(f)

        # 5. Enrich results with full benchmark data from the combined dataframe
        enriched_results = await _enrich_ranking_results(
            ranking_data,
            sanitized_model_name,
            model_name,
            scores,
            df
        )

        return enriched_results

    finally:
        # 6. Clean up the temporary directory and files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
