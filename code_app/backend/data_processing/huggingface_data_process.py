#!/usr/bin/env python3
"""
Prepare LLM Data for Spectral Ranking Analysis

This script transforms the collected LLM benchmark data into the format
expected by ranking_cli.R for spectral ranking analysis.

Input format (from huggingface_data_collector.py):
- Rows: Models
- Columns: Benchmarks + metadata

Output format (for ranking_cli.R):
- Rows: Benchmarks (as "samples")
- Columns: Models (as "methods")
"""

import pandas as pd
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# CONFIGURATION SECTION
# ===============================
# Specify which top-N datasets to generate
TOP_DATASETS_TO_GENERATE = [100]
# ===============================

class RankingDataPreparer:
    """Prepare LLM data for spectral ranking analysis"""

    def __init__(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.input_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_collection')
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_processing')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_cleaned_data(self):
        """Load the cleaned LLM data"""
        input_file = os.path.join(self.input_dir, 'huggingface_cleaned.csv')
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Cleaned data file not found: {input_file}")

        logger.info(f"Loading cleaned data from: {input_file}")
        df = pd.read_csv(input_file)
        logger.info(f"Loaded {len(df)} models with {len(df.columns)} columns")
        return df

    def prepare_ranking_data(self, df, top_n=None):
        """
        Prepare data in the format expected by ranking_cli.R

        ranking_cli.R expects:
        - Rows: Different samples/cases (benchmarks in our case)
        - Columns: Different methods (models in our case)
        """
        # Select benchmark columns
        benchmark_columns = ['ifeval', 'bbh', 'math', 'gpqa', 'musr', 'mmlu_pro']

        if top_n and len(df) >= top_n:
            # Select top N models by average score
            df_selected = df.head(top_n).copy()
            selected_models = df_selected['model'].tolist()
            logger.info(f"Selected top {top_n} models for ranking")
        else:
            # Use all models
            df_selected = df.copy()
            selected_models = df['model'].tolist()

        # Extract benchmark data
        benchmark_data = df_selected[benchmark_columns].copy()

        # Transpose for ranking format (benchmarks as rows, models as columns)
        ranking_df = benchmark_data.T
        ranking_df.index.name = 'benchmark'

        # Clean model names for column headers
        def clean_model_name(name):
            """Clean model name for CSV column header"""
            name = name.split('/')[-1]  # Take the last part after '/'
            return name[:25] if len(name) > 25 else name  # Shorter limit for readability

        ranking_df.columns = [clean_model_name(model) for model in selected_models]

        logger.info(f"Prepared ranking data: {ranking_df.shape[0]} benchmarks × {ranking_df.shape[1]} models")
        return ranking_df, selected_models

    def save_ranking_data(self, df, filename=None):
        """Save the prepared ranking data"""
        if df is None:
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'llm_ranking_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        # Save without index (benchmarks become rows without explicit index column)
        df.to_csv(filepath, index=True)

        logger.info(f"Ranking data saved to: {filepath}")

        # Also save metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'total_models': len(df.columns),
            'benchmarks': list(df.index),
            'models': list(df.columns),
            'shape': df.shape,
            'source': 'Open LLM Leaderboard via huggingface_data_collector.py',
            'prepared_for': 'ranking_cli.R spectral ranking analysis'
        }

        metadata_filepath = filepath.replace('.csv', '_metadata.json')
        with open(metadata_filepath, 'w') as f:
            json.dump(metadata, f, indent=2)

        return filepath

def main():
    """Main function to prepare ranking data"""
    preparer = RankingDataPreparer()

    # Load cleaned data
    df = preparer.load_cleaned_data()

    print("\n=== DATA PREPARATION SUMMARY ===")
    print(f"Input: {len(df)} models × {len(df.columns)} columns")
    print(f"Configured top datasets: {TOP_DATASETS_TO_GENERATE}")

    # Skip full ranking dataset generation - only generate top-N datasets
    # ranking_df_full, all_models = preparer.prepare_ranking_data(df)
    # main_filepath = preparer.save_ranking_data(ranking_df_full, 'llm_ranking_full.csv')

    # Create top-N ranking datasets based on configuration
    generated_datasets = []

    print("\n=== GENERATING TOP-N DATASETS ===")
    for top_n in TOP_DATASETS_TO_GENERATE:
        if len(df) >= top_n:
            print(f"Generating top {top_n} dataset...")
            ranking_df_top, top_models = preparer.prepare_ranking_data(df, top_n=top_n)
            top_filepath = preparer.save_ranking_data(ranking_df_top, f'llm_ranking_top{top_n}.csv')

            generated_datasets.append({
                'top_n': top_n,
                'filepath': top_filepath,
                'shape': ranking_df_top.shape
            })

            print(f"  ✓ Top {top_n}: {ranking_df_top.shape[0]}×{ranking_df_top.shape[1]} saved")
        else:
            print(f"  ⚠ Skipping top {top_n}: insufficient data ({len(df)} available)")

    print("\n=== GENERATED DATASETS SUMMARY ===")
    # Full dataset generation skipped

    for dataset in generated_datasets:
        print(f"Top {dataset['top_n']} dataset: {dataset['filepath']}")
        print(f"  Shape: {dataset['shape'][0]} benchmarks × {dataset['shape'][1]} models")

    print("\n=== TOP 5 MODELS BY AVERAGE SCORE ===")
    for i, (model, score) in enumerate(zip(df['model'][:5], df['average_score'][:5])):
        print(f"{i+1}. {model}: {score:.3f}")

    print("\n=== USAGE EXAMPLES ===")
    print("# Use configured top-N datasets:")
    for dataset in generated_datasets:
        print(f"\n# Top {dataset['top_n']} models:")
        print("Rscript demo_r/ranking_cli.R \\")
        print(f"  --csv data_llm/llm_ranking_top{dataset['top_n']}.csv \\")
        print("  --bigbetter 1 --B 2000 --seed 42 \\")
        print(f"  --out jobs/llm_ranking_top{dataset['top_n']}")


if __name__ == "__main__":
    main()
