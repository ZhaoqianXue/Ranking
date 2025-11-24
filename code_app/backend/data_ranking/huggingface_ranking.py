#!/usr/bin/env python3
"""
Update Dashboard Ranking Data

This script updates the LLM ranking data for the dashboard by running the spectral ranking algorithm.
It replaces the static llm_ranking_top100.csv with results from the actual ranking computation.

Usage:
    python huggingface_ranking.py [--top-n 100] [--bigbetter 1] [--B 2000] [--seed 42]

The script will:
1. Prepare ranking data using huggingface_data_process.py
2. Run spectral ranking algorithm via ranking_cli.R
3. Process and format the results
4. Update llm_ranking_top100.csv with the new rankings
"""

import os
import sys
import json
import pandas as pd
import subprocess
import argparse
import logging
from datetime import datetime
from typing import Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DashboardRankingUpdater:
    """Updates dashboard ranking data with spectral ranking results"""

    def __init__(self):
        # Get absolute paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.data_llm_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_processing')
        self.data_ranking_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_ranking')
        self.demo_r_dir = os.path.join(self.project_root, 'demo_r')
        self.backend_dir = os.path.join(self.project_root, 'code_app', 'backend')

        # Scripts and data paths
        self.prepare_script = os.path.join(self.backend_dir, 'data_processing', 'huggingface_data_process.py')
        self.ranking_script = os.path.join(self.demo_r_dir, 'ranking_cli.R')
        self.output_file = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'llm_ranking_top100.csv')

    def prepare_ranking_data(self, top_n: int = 100) -> str:
        """Prepare ranking data for spectral analysis"""
        logger.info(f"Preparing ranking data for top {top_n} models...")

        # Run huggingface_data_process.py to generate the input file
        cmd = [sys.executable, self.prepare_script]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        if result.returncode != 0:
            logger.error(f"Failed to prepare ranking data: {result.stderr}")
            raise RuntimeError(f"Data preparation failed: {result.stderr}")

        # Check if the target file was created
        input_file = os.path.join(self.data_llm_dir, f'llm_ranking_top{top_n}.csv')
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Expected input file not found: {input_file}")

        logger.info(f"Ranking data prepared: {input_file}")
        return input_file

    def run_spectral_ranking(self, input_file: str, bigbetter: int = 1, B: int = 2000, seed: int = 42) -> str:
        """Run spectral ranking algorithm via R script"""
        logger.info(f"Running spectral ranking on {input_file}...")

        # Create temporary output directory (use fixed name for dashboard access)
        temp_output_dir = os.path.join(self.data_ranking_dir, 'current')

        # R script command
        cmd = [
            'Rscript', self.ranking_script,
            '--csv', input_file,
            '--bigbetter', str(bigbetter),
            '--B', str(B),
            '--seed', str(seed),
            '--out', temp_output_dir
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        if result.returncode != 0:
            logger.error(f"Spectral ranking failed: {result.stderr}")
            raise RuntimeError(f"Spectral ranking failed: {result.stderr}")

        # Check if results were generated
        results_file = os.path.join(temp_output_dir, 'ranking_results.json')
        if not os.path.exists(results_file):
            raise FileNotFoundError(f"Ranking results not found: {results_file}")

        logger.info(f"Spectral ranking completed: {results_file}")
        return results_file, temp_output_dir

    def process_ranking_results(self, results_file: str, input_file: str) -> tuple[pd.DataFrame, dict]:
        """Process ranking results and create dashboard-compatible format with leaderboard mapping"""
        logger.info("Processing ranking results...")

        # Load ranking results
        with open(results_file, 'r') as f:
            ranking_data = json.load(f)

        # Load original input data to get model names and scores
        input_df = pd.read_csv(input_file, index_col=0)  # First column is benchmark names

        # Load complete leaderboard data for full benchmark scores
        leaderboard_file = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_collection', 'llm_leaderboard_cleaned.csv')
        leaderboard_df = None
        if os.path.exists(leaderboard_file):
            leaderboard_df = pd.read_csv(leaderboard_file)
            logger.info(f"Loaded leaderboard data: {len(leaderboard_df)} models")

        # Extract methods information from ranking results
        methods_data = ranking_data.get('methods', [])

        if not methods_data:
            raise ValueError("Invalid ranking results: missing methods data")

        # Create mapping from ranking result names to original CSV column names first
        ranking_to_csv_mapping = {}
        for method_info in methods_data:
            r_name = method_info['name']
            # Find the corresponding original CSV column name
            original_csv_name = self._find_original_csv_name(r_name, input_df.columns.tolist())
            ranking_to_csv_mapping[r_name] = original_csv_name

        # Then create mapping from CSV names to leaderboard data
        name_mapping = self._create_model_mapping_from_csv(ranking_to_csv_mapping, leaderboard_df)

        # Create results DataFrame
        results = []
        for i, method_info in enumerate(methods_data):
            r_model_name = method_info['name']  # Name as stored by R
            mapped_info = name_mapping.get(r_model_name, {})
            original_model_name = mapped_info.get('original_name', r_model_name)
            leaderboard_name = mapped_info.get('leaderboard_name')
            benchmark_scores = mapped_info.get('benchmark_scores', {})

            theta_hat = method_info['theta_hat']
            rank = method_info['rank']

            row = {
                'model': original_model_name,
                'ranking_score': theta_hat,
                'rank': int(rank),
                'leaderboard_name': leaderboard_name,
            }

            # Add benchmark scores from leaderboard
            for benchmark in ['ifeval', 'bbh', 'math', 'gpqa', 'musr', 'mmlu_pro', 'average_score']:
                row[benchmark] = benchmark_scores.get(benchmark, 'N/A')

            results.append(row)

        # Sort by ranking score (descending, higher is better)
        results_df = pd.DataFrame(results).sort_values('ranking_score', ascending=False)

        logger.info(f"Processed {len(results_df)} model rankings with leaderboard data")
        return results_df, name_mapping

    def format_for_dashboard(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Format results for dashboard compatibility"""
        logger.info("Formatting data for dashboard...")

        # Dashboard expects: benchmark columns with model names as rows
        # Current format: model rows with benchmark columns
        # Need to transpose and reorganize

        # Extract benchmark columns (exclude model, ranking_score, rank)
        benchmark_cols = [col for col in results_df.columns if col not in ['model', 'ranking_score', 'rank']]

        # Create dashboard format: benchmarks as rows, models as columns
        dashboard_data = {}

        # First row: benchmark names
        dashboard_data['benchmark'] = benchmark_cols

        # Subsequent rows: model scores for each benchmark
        sorted_models = results_df['model'].tolist()

        for model in sorted_models:
            model_scores = []
            for benchmark in benchmark_cols:
                score = results_df[results_df['model'] == model][benchmark].iloc[0]
                model_scores.append(score)
            dashboard_data[model] = model_scores

        dashboard_df = pd.DataFrame(dashboard_data)

        logger.info(f"Dashboard data formatted: {dashboard_df.shape[0]} benchmarks × {dashboard_df.shape[1]-1} models")
        return dashboard_df

    def update_dashboard_file(self, dashboard_df: pd.DataFrame):
        """Update the dashboard CSV file"""
        logger.info(f"Updating dashboard file: {self.output_file}")

        # Backup existing file
        if os.path.exists(self.output_file):
            backup_file = self.output_file + '.backup'
            os.rename(self.output_file, backup_file)
            logger.info(f"Backup created: {backup_file}")

        # Save new data
        dashboard_df.to_csv(self.output_file, index=False)
        logger.info(f"Dashboard file updated successfully")

    def _create_model_mapping(self, methods_data: list, original_names: list, leaderboard_df: pd.DataFrame = None) -> dict:
        """Create mapping from ranking result names to leaderboard full names and scores"""
        name_mapping = {}

        for method_info in methods_data:
            r_model_name = method_info['name']

            # First try exact match with original names
            original_name = None
            if r_model_name in original_names:
                original_name = r_model_name
            else:
                # Try to find the best match for modified names
                best_match = None
                max_overlap = 0

                for orig_name in original_names:
                    # Calculate overlap score
                    overlap = 0
                    min_len = min(len(r_model_name), len(orig_name))
                    for i in range(min_len):
                        if r_model_name[i] == orig_name[i]:
                            overlap += 1
                        else:
                            break

                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_match = orig_name

                if best_match:
                    original_name = best_match

            # Find corresponding leaderboard entry
            leaderboard_name = None
            benchmark_scores = {}

            if leaderboard_df is not None and original_name:
                # Try multiple matching strategies
                candidates = pd.DataFrame()
                simple_name = original_name.split('/')[-1] if '/' in original_name else original_name

                # 1. Exact match
                exact_matches = leaderboard_df[leaderboard_df['model'] == original_name]
                if not exact_matches.empty:
                    candidates = exact_matches

                # 2. Handle R's name truncation FIRST (before other matching)
                if candidates.empty and '...' in original_name:
                    base_name = original_name.split('...')[0]
                    print(f"DEBUG: Attempting truncated name matching for {original_name} with base {base_name}")
                    # Look for models containing the base name
                    for _, row in leaderboard_df.iterrows():
                        full_name = row['model']
                        # Remove prefix for matching
                        clean_full_name = full_name.split('/')[-1] if '/' in full_name else full_name
                        if base_name in clean_full_name and len(clean_full_name) > len(base_name):
                            print(f"DEBUG: Found truncated name match: {full_name} for {original_name}")
                            candidates = pd.DataFrame([row])
                            break

                # 3. Match by removing prefix (username/)
                if candidates.empty:
                    prefix_matches = leaderboard_df[leaderboard_df['model'].str.endswith('/' + simple_name)]
                    if not prefix_matches.empty:
                        print(f"DEBUG: Found prefix match for {original_name}")
                        candidates = prefix_matches

                # 4. Regular fuzzy matching
                if candidates.empty:
                    for _, row in leaderboard_df.iterrows():
                        full_name = row['model']
                        if simple_name in full_name and len(full_name) > len(simple_name):
                            candidates = pd.DataFrame([row])
                            break

                if not candidates.empty:
                    # Use the first match
                    row = candidates.iloc[0]
                    leaderboard_name = row['model']
                    model_link = row['model_link']
                    benchmark_scores = {
                        'ifeval': row['ifeval'],
                        'bbh': row['bbh'],
                        'math': row['math'],
                        'gpqa': row['gpqa'],
                        'musr': row['musr'],
                        'mmlu_pro': row['mmlu_pro'],
                        'average_score': row['average_score']
                    }

            name_mapping[r_model_name] = {
                'original_name': original_name or r_model_name,
                'leaderboard_name': leaderboard_name,
                'model_link': model_link,
                'benchmark_scores': benchmark_scores
            }

        return name_mapping

    def _get_r_column_names(self, column_names: list) -> list:
        """Simulate R's column name cleaning (check.names=TRUE)"""
        import re

        cleaned_names = []
        used_names = set()

        for name in column_names:
            # R's make.names function logic (simplified)
            # Replace non-alphanumeric characters with dots
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '.', str(name))

            # Ensure starts with letter or dot
            if cleaned and not (cleaned[0].isalpha() or cleaned[0] == '.'):
                cleaned = '.' + cleaned

            # Remove trailing dots
            cleaned = cleaned.rstrip('.')

            # Handle empty names
            if not cleaned:
                cleaned = 'X'

            # Handle duplicates by adding suffix
            original_cleaned = cleaned
            counter = 1
            while cleaned in used_names:
                cleaned = f"{original_cleaned}.{counter}"
                counter += 1

            used_names.add(cleaned)
            cleaned_names.append(cleaned)

        return cleaned_names

    def _find_original_csv_name(self, r_name: str, csv_columns: list) -> str:
        """Find the original CSV column name that corresponds to R's modified name"""
        # Handle R's truncation (e.g., "Linkbricks-Horizon-AI-Ave...11" -> "Linkbricks-Horizon-AI-Ave.1")
        if '...' in r_name:
            base_name = r_name.split('...')[0]
            suffix_num = r_name.split('...')[1]
            try:
                suffix_int = int(suffix_num)
                # R uses ...11 for the 11th duplicate, which corresponds to .10 in make.names
                # But let's try a simpler approach: look for the closest match
                candidates = [col for col in csv_columns if col.startswith(base_name)]
                if candidates:
                    # Return the first candidate (should work for most cases)
                    return candidates[0]
            except ValueError:
                pass

        # For non-truncated names, try exact match first
        if r_name in csv_columns:
            return r_name

        # Try removing prefix if present
        if '/' in r_name:
            simple_name = r_name.split('/')[-1]
            if simple_name in csv_columns:
                return simple_name

        # Return the R name as fallback (will be handled by leaderboard matching)
        return r_name

    def _create_model_mapping_from_csv(self, ranking_to_csv_mapping: dict, leaderboard_df: pd.DataFrame = None) -> dict:
        """Create mapping from CSV column names to leaderboard data"""
        name_mapping = {}

        for r_name, csv_name in ranking_to_csv_mapping.items():
            leaderboard_name = None
            benchmark_scores = {}

            if leaderboard_df is not None:
                # Try multiple matching strategies for the CSV column name
                candidates = pd.DataFrame()

                # 1. Exact match
                exact_matches = leaderboard_df[leaderboard_df['model'] == csv_name]
                if not exact_matches.empty:
                    candidates = exact_matches

                # 2. Match by removing prefix (username/)
                if candidates.empty:
                    simple_name = csv_name.split('/')[-1] if '/' in csv_name else csv_name
                    prefix_matches = leaderboard_df[leaderboard_df['model'].str.endswith('/' + simple_name)]
                    if not prefix_matches.empty:
                        candidates = prefix_matches

                # 3. Fuzzy matching
                if candidates.empty:
                    for _, row in leaderboard_df.iterrows():
                        full_name = row['model']
                        if simple_name in full_name and len(full_name) > len(simple_name):
                            candidates = pd.DataFrame([row])
                            break

                if not candidates.empty:
                    # Use the first match
                    row = candidates.iloc[0]
                    leaderboard_name = row['model']
                    model_link = row['model_link']
                    benchmark_scores = {
                        'ifeval': row['ifeval'],
                        'bbh': row['bbh'],
                        'math': row['math'],
                        'gpqa': row['gpqa'],
                        'musr': row['musr'],
                        'mmlu_pro': row['mmlu_pro'],
                        'average_score': row['average_score']
                    }

            name_mapping[r_name] = {
                'original_name': csv_name,
                'leaderboard_name': leaderboard_name,
                'model_link': model_link,
                'benchmark_scores': benchmark_scores
            }

        return name_mapping

    def _save_enhanced_results(self, results_df: pd.DataFrame, name_mapping: dict, temp_dir: str):
        """Save enhanced results with leaderboard mapping for dashboard access"""
        enhanced_results_file = os.path.join(temp_dir, 'huggingface_ranking_result_enhanced.json')

        # Load original ranking results
        ranking_results_file = os.path.join(temp_dir, 'huggingface_ranking_result_basic.json')
        with open(ranking_results_file, 'r') as f:
            original_data = json.load(f)

        # Add leaderboard mapping and enhanced data
        enhanced_data = original_data.copy()
        enhanced_data['leaderboard_mapping'] = name_mapping

        # Add enhanced method data with full benchmark scores
        enhanced_methods = []
        for method in original_data.get('methods', []):
            method_name = method['name']
            mapping_info = name_mapping.get(method_name, {})

            enhanced_method = method.copy()
            enhanced_method['leaderboard_name'] = mapping_info.get('leaderboard_name')

            # Parse HTML links into structured URLs
            model_link_html = mapping_info.get('model_link', '')
            if model_link_html:
                import re
                # Extract all href URLs from the HTML
                url_matches = re.findall(r'href="([^"]*huggingface\.co/[^"]*)"', model_link_html)
                if url_matches:
                    # Usually the first URL is the model page, second is details page
                    enhanced_method['model_url'] = url_matches[0]
                    if len(url_matches) > 1:
                        enhanced_method['details_url'] = url_matches[1]
                else:
                    enhanced_method['model_url'] = None
            else:
                enhanced_method['model_url'] = None

            enhanced_method['benchmark_scores'] = mapping_info.get('benchmark_scores', {})
            enhanced_methods.append(enhanced_method)

        enhanced_data['methods'] = enhanced_methods

        # Save enhanced results
        with open(enhanced_results_file, 'w') as f:
            json.dump(enhanced_data, f, indent=2)

        logger.info(f"Saved enhanced ranking results: {enhanced_results_file}")

    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files (skip fixed results directory)"""
        # Don't clean up the fixed 'current' directory
        # as dashboard.py needs to access it
        if 'current' in temp_dir:
            logger.info(f"Keeping results directory for dashboard access: {temp_dir}")
            return

        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

    def update_ranking(self, top_n: int = 100, bigbetter: int = 1, B: int = 2000, seed: int = 42):
        """Main method to update dashboard ranking data"""
        logger.info("="*60)
        logger.info("STARTING DASHBOARD RANKING UPDATE")
        logger.info("="*60)

        try:
            # Step 1: Prepare ranking data
            input_file = self.prepare_ranking_data(top_n=top_n)

            # Step 2: Run spectral ranking
            results_file, temp_dir = self.run_spectral_ranking(
                input_file=input_file,
                bigbetter=bigbetter,
                B=B,
                seed=seed
            )

            # Step 3: Process results
            results_df, name_mapping = self.process_ranking_results(results_file, input_file)

            # Step 4: Format for dashboard
            dashboard_df = self.format_for_dashboard(results_df)

            # Step 5: Update dashboard file
            self.update_dashboard_file(dashboard_df)

            # Step 6: Save enhanced results with leaderboard mapping
            self._save_enhanced_results(results_df, name_mapping, temp_dir)

            # Step 7: Cleanup
            self.cleanup_temp_files(temp_dir)

            logger.info("="*60)
            logger.info("DASHBOARD RANKING UPDATE COMPLETED SUCCESSFULLY")
            logger.info("="*60)

            # Print summary
            print("\n" + "="*60)
            print("DASHBOARD RANKING UPDATE SUMMARY")
            print("="*60)
            print(f"Input models: {len(dashboard_df.columns) - 1}")
            print(f"Benchmarks: {len(dashboard_df)}")
            print(f"Bootstrap iterations: {B}")
            print(f"Random seed: {seed}")
            print(f"Output file: {self.output_file}")

            # Show top 5 rankings
            results_df_head = results_df.head(5)
            print("\nTOP 5 MODELS (SPECTRAL RANKING):")
            for i, (_, row) in enumerate(results_df_head.iterrows(), 1):
                print("2d")

        except Exception as e:
            logger.error(f"Dashboard ranking update failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Update dashboard ranking data with spectral ranking results")
    parser.add_argument('--top-n', type=int, default=100,
                       help='Number of top models to rank (default: 100)')
    parser.add_argument('--bigbetter', type=int, default=1,
                       help='Higher scores are better (1) or lower scores are better (0) (default: 1)')
    parser.add_argument('--B', type=int, default=2000,
                       help='Number of bootstrap iterations (default: 2000)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')

    args = parser.parse_args()

    # Validate arguments
    if args.top_n <= 0:
        parser.error("top-n must be positive")
    if args.B <= 0:
        parser.error("B must be positive")
    if args.bigbetter not in [0, 1]:
        parser.error("bigbetter must be 0 or 1")

    # Run update
    updater = DashboardRankingUpdater()
    updater.update_ranking(
        top_n=args.top_n,
        bigbetter=args.bigbetter,
        B=args.B,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
