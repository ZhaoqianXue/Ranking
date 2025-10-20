#!/usr/bin/env python3
"""
Update Dashboard Ranking Data for Arena Human Preferences

This script updates the LLM ranking data for the dashboard by running the spectral ranking algorithm
on Arena human preference data. It replaces static ranking data with results from actual ranking computation.

Usage:
    python arena_ranking.py [--top-n 21] [--bigbetter 1] [--B 2000] [--seed 42]

The script will:
1. Prepare ranking data using arena_data_process.py
2. Run spectral ranking algorithm via ranking_cli.R
3. Process and format the results
4. Update arena_ranking_top21.csv with the new rankings
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

class ArenaDashboardRankingUpdater:
    """Updates dashboard ranking data with Arena spectral ranking results"""

    def __init__(self):
        # Get absolute paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.data_llm_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_processing')
        self.data_ranking_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_ranking')
        self.demo_r_dir = os.path.join(self.project_root, 'demo_r')
        self.backend_dir = os.path.join(self.project_root, 'code_app', 'backend')

        # Scripts and data paths
        self.prepare_script = os.path.join(self.backend_dir, 'data_processing', 'arena_data_process.py')
        self.ranking_script = os.path.join(self.demo_r_dir, 'ranking_cli.R')
        self.output_file = os.path.join(self.project_root, 'data_llm', 'data_arena', 'arena_ranking_top21.csv')
        self.full_output_file = os.path.join(self.project_root, 'data_llm', 'data_arena', 'arena_ranking_full.csv')

        # Ensure ranking directory exists
        os.makedirs(self.data_ranking_dir, exist_ok=True)

    def prepare_ranking_data(self, top_n: int = None, use_full_data: bool = True) -> str:
        """Prepare ranking data for spectral analysis"""
        if use_full_data:
            # Use existing full dataset directly
            input_file = os.path.join(self.data_llm_dir, 'arena_ranking_full.csv')
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Full data file not found: {input_file}")
            logger.info(f"Using existing Arena full ranking data: {input_file}")
        else:
            # Run arena_data_process.py to generate the input file
            logger.info(f"Preparing Arena ranking data for top {top_n} models...")
            cmd = [sys.executable, self.prepare_script]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            if result.returncode != 0:
                logger.error(f"Failed to prepare ranking data: {result.stderr}")
                raise RuntimeError(f"Data preparation failed: {result.stderr}")

            # Check if the target file was created
            input_file = os.path.join(self.data_llm_dir, f'arena_ranking_top{top_n}.csv')
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Expected input file not found: {input_file}")

            logger.info(f"Arena ranking data prepared: {input_file}")

        return input_file

    def run_spectral_ranking(self, input_file: str, bigbetter: int = 1, B: int = 2000, seed: int = 42) -> Tuple[str, str]:
        """Run spectral ranking algorithm via R script"""
        logger.info(f"Running spectral ranking on Arena data: {input_file}...")

        # Create output directory (use fixed name for dashboard access)
        temp_output_dir = os.path.join(self.data_ranking_dir, 'current')

        # Ensure the directory exists
        os.makedirs(temp_output_dir, exist_ok=True)

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

    def process_ranking_results(self, results_file: str, input_file: str) -> Tuple[pd.DataFrame, dict]:
        """Process ranking results and create dashboard-compatible format"""
        logger.info("Processing Arena ranking results...")

        # Load ranking results
        with open(results_file, 'r') as f:
            ranking_data = json.load(f)

        # Load original input data to get model names
        input_df = pd.read_csv(input_file, index_col=0)  # First column is virtual benchmark names

        # Extract methods information from ranking results
        methods_data = ranking_data.get('methods', [])

        if not methods_data:
            raise ValueError("Invalid ranking results: missing methods data")

        # Create mapping from ranking result names to original CSV column names
        ranking_to_csv_mapping = {}
        for method_info in methods_data:
            r_name = method_info['name']
            # Find the corresponding original CSV column name
            original_csv_name = self._find_original_csv_name(r_name, input_df.columns.tolist())
            ranking_to_csv_mapping[r_name] = original_csv_name

        # Create results DataFrame
        results = []
        for i, method_info in enumerate(methods_data):
            r_model_name = method_info['name']  # Name as stored by R
            original_model_name = ranking_to_csv_mapping.get(r_model_name, r_model_name)

            theta_hat = method_info['theta_hat']
            rank = method_info['rank']

            row = {
                'model': original_model_name,
                'ranking_score': theta_hat,
                'rank': int(rank),
                'data_source': 'arena_human_preference'
            }

            results.append(row)

        # Sort by ranking score (descending, higher is better)
        results_df = pd.DataFrame(results).sort_values('ranking_score', ascending=False)

        logger.info(f"Processed {len(results_df)} Arena model rankings")
        return results_df, ranking_to_csv_mapping

    def _save_enhanced_results(self, results_df: pd.DataFrame, name_mapping: dict, temp_dir: str):
        """Save enhanced results with mapping for dashboard access"""
        enhanced_results_file = os.path.join(temp_dir, 'arena_ranking_result_enhanced.json')

        # Load original ranking results
        ranking_results_file = os.path.join(temp_dir, 'ranking_results.json')
        with open(ranking_results_file, 'r') as f:
            original_data = json.load(f)

        # Add mapping and enhanced data
        enhanced_data = original_data.copy()
        enhanced_data['name_mapping'] = name_mapping

        # Add enhanced method data
        enhanced_methods = []
        for method in original_data.get('methods', []):
            method_name = method['name']
            # For arena data, name_mapping is a simple dict with string values
            original_name = name_mapping.get(method_name, method_name)

            enhanced_method = method.copy()
            enhanced_method['original_name'] = original_name

            enhanced_methods.append(enhanced_method)

        enhanced_data['methods'] = enhanced_methods

        # Save enhanced results
        with open(enhanced_results_file, 'w') as f:
            json.dump(enhanced_data, f, indent=2)

        logger.info(f"Saved enhanced Arena ranking results: {enhanced_results_file}")

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

    def format_for_dashboard(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Format results for dashboard compatibility"""
        logger.info("Formatting Arena data for dashboard...")

        # Dashboard expects: benchmark columns with model names as rows
        # Current format: model rows with benchmark columns
        # Need to transpose and reorganize

        # For Arena data, we'll create a simple format with ranking info
        # Since we don't have traditional benchmarks, we'll show ranking metrics
        dashboard_data = {
            'model': results_df['model'].tolist(),
            'arena_rank': results_df['rank'].tolist(),
            'arena_theta_score': results_df['ranking_score'].tolist(),
        }

        dashboard_df = pd.DataFrame(dashboard_data)

        logger.info(f"Arena dashboard data formatted: {dashboard_df.shape[0]} models")
        return dashboard_df

    def update_dashboard_file(self, dashboard_df: pd.DataFrame, output_file: str = None):
        """Update the dashboard CSV file"""
        if output_file is None:
            output_file = self.output_file

        logger.info(f"Updating Arena dashboard file: {output_file}")

        # Backup existing file
        if os.path.exists(output_file):
            backup_file = output_file + '.backup'
            os.rename(output_file, backup_file)
            logger.info(f"Backup created: {backup_file}")

        # Save new data
        dashboard_df.to_csv(output_file, index=False)
        logger.info(f"Arena dashboard file updated successfully")

    def _find_original_csv_name(self, r_name: str, csv_columns: list) -> str:
        """Find the original CSV column name that corresponds to R's modified name"""
        # Handle R's truncation (e.g., "Linkbricks-Horizon-AI-Ave...11" -> "Linkbricks-Horizon-AI-Ave.1")
        if '...' in r_name:
            base_name = r_name.split('...')[0]
            suffix_num = r_name.split('...')[1]
            try:
                suffix_int = int(suffix_num)
                # Try to find the closest match
                candidates = [col for col in csv_columns if col.startswith(base_name)]
                if candidates:
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

        # Return the R name as fallback
        return r_name

    def update_ranking(self, top_n: int = None, bigbetter: int = 1, B: int = 2000, seed: int = 42, use_full_data: bool = True):
        """Main method to update dashboard ranking data"""
        logger.info("="*60)
        logger.info("STARTING ARENA DASHBOARD RANKING UPDATE")
        logger.info("="*60)

        try:
            # Step 1: Prepare ranking data
            input_file = self.prepare_ranking_data(top_n=top_n, use_full_data=use_full_data)

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
            output_file = self.full_output_file if use_full_data else self.output_file
            self.update_dashboard_file(dashboard_df, output_file)

            # Step 6: Save enhanced results with mapping
            self._save_enhanced_results(results_df, name_mapping, temp_dir)

            # Step 7: Cleanup
            self.cleanup_temp_files(temp_dir)

            logger.info("="*60)
            logger.info("ARENA DASHBOARD RANKING UPDATE COMPLETED SUCCESSFULLY")
            logger.info("="*60)

            # Print summary
            print("\n" + "="*60)
            print("ARENA DASHBOARD RANKING UPDATE SUMMARY")
            print("="*60)
            print(f"Input models: {len(dashboard_df)}")
            print(f"Bootstrap iterations: {B}")
            print(f"Random seed: {seed}")
            print(f"Output file: {output_file}")

            # Show top 5 rankings
            results_df_head = results_df.head(5)
            print("\nTOP 5 ARENA MODELS (SPECTRAL RANKING):")
            for i, (_, row) in enumerate(results_df_head.iterrows(), 1):
                print("2d")

        except Exception as e:
            logger.error(f"Arena dashboard ranking update failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Update dashboard ranking data with Arena spectral ranking results")
    parser.add_argument('--top-n', type=int,
                       help='Number of top models to rank (if not specified, uses full dataset)')
    parser.add_argument('--bigbetter', type=int, default=1,
                       help='Higher scores are better (1) or lower scores are better (0) (default: 1)')
    parser.add_argument('--B', type=int, default=2000,
                       help='Number of bootstrap iterations (default: 2000)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--use-full-data', action='store_true', default=True,
                       help='Use existing full dataset instead of generating top-n subset (default: True)')

    args = parser.parse_args()

    # Validate arguments
    if not args.use_full_data and args.top_n is not None and args.top_n <= 0:
        parser.error("top-n must be positive when not using full data")
    if args.B <= 0:
        parser.error("B must be positive")
    if args.bigbetter not in [0, 1]:
        parser.error("bigbetter must be 0 or 1")

    # Run update
    updater = ArenaDashboardRankingUpdater()
    updater.update_ranking(
        top_n=args.top_n,
        bigbetter=args.bigbetter,
        B=args.B,
        seed=args.seed,
        use_full_data=args.use_full_data
    )


if __name__ == "__main__":
    main()
