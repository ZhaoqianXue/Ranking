#!/usr/bin/env python3
"""
Update Dashboard Ranking Data for Arena Human Preferences - All Combinations Version

This script runs SPECTRAL RANKING on ALL POSSIBLE COMBINATIONS of Arena benchmarks,
producing spectral rankings for each combination of 2 to 6 benchmarks (excluding the full 7-benchmark combination).

Usage:
    python arena_ranking_single.py [--bigbetter 1] [--B 2000] [--seed 42] [--max-combinations N]

The script will:
1. Load the full Arena ranking data (7 benchmarks)
2. Generate all combinations of 2-6 benchmarks (119 combinations total, excluding full 7-benchmark combo)
3. For each combination, run spectral ranking on the models
4. Process and format the spectral ranking results
5. Save individual and combined results for all combinations
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import subprocess
import argparse
import logging
from datetime import datetime
from typing import Tuple, Dict, List
import tempfile
import shutil
import itertools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArenaAllCombinationsRankingUpdater:
    """Updates ranking data for all possible combinations of Arena benchmarks"""

    def __init__(self):
        # Get absolute paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.data_llm_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_processing')
        self.data_ranking_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_ranking')
        self.demo_r_dir = os.path.join(self.project_root, 'demo_r')
        self.backend_dir = os.path.join(self.project_root, 'code_app', 'backend')

        # Scripts and data paths
        self.ranking_script = os.path.join(self.demo_r_dir, 'ranking_cli.R')
        self.input_file = os.path.join(self.data_llm_dir, 'arena_ranking_full.csv')

        # Ensure ranking directory exists
        os.makedirs(self.data_ranking_dir, exist_ok=True)

    def load_full_data(self) -> pd.DataFrame:
        """Load the full Arena ranking data"""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        logger.info(f"Loading full Arena data: {self.input_file}")
        df = pd.read_csv(self.input_file)
        logger.info(f"Loaded data with shape: {df.shape}")
        return df

    def get_benchmarks(self, df: pd.DataFrame) -> List[str]:
        """Extract benchmark names from the data"""
        benchmarks = df.iloc[:, 0].tolist()  # First column contains benchmark names
        logger.info(f"Found {len(benchmarks)} benchmarks: {benchmarks}")
        return benchmarks

    def generate_all_combinations(self, benchmarks: List[str]) -> List[List[str]]:
        """Generate all possible combinations of 2 to n-1 benchmarks (excluding full n-benchmark combination)"""
        all_combinations = []
        n = len(benchmarks)

        # Generate combinations for sizes 2 to n-1 (excluding full n-benchmark combination)
        for k in range(2, n):
            combinations_k = list(itertools.combinations(benchmarks, k))
            all_combinations.extend(combinations_k)

        logger.info(f"Generated {len(all_combinations)} combinations from {n} benchmarks (excluding full {n}-benchmark combination)")
        return all_combinations

    def create_single_benchmark_data(self, df: pd.DataFrame, benchmark: str) -> str:
        """Create a CSV file for a single benchmark with original scores for spectral ranking"""
        # Find the row for this benchmark
        benchmark_row = df[df.iloc[:, 0] == benchmark]
        if benchmark_row.empty:
            raise ValueError(f"Benchmark '{benchmark}' not found in data")

        # Extract the scores (skip the first column which is benchmark name)
        scores = benchmark_row.iloc[0, 1:].values  # Skip first column (benchmark name)
        model_names = df.columns[1:].tolist()  # Skip first column

        # Ensure scores are float type
        scores = np.array(scores, dtype=float)

        # Create single-row dataframe with original scores (1 sample, N models)
        single_sample_df = pd.DataFrame([scores], columns=model_names)

        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.csv', prefix=f'arena_{benchmark.replace("_", "_")}_')
        os.close(temp_fd)

        single_sample_df.to_csv(temp_path, index=False)
        logger.info(f"Created single-sample benchmark file for {benchmark}: {temp_path}")
        logger.info(f"Benchmark data shape: {single_sample_df.shape} (1 sample, {len(model_names)} models)")
        logger.info(f"Original scores range: [{scores.min():.4f}, {scores.max():.4f}]")

        return temp_path

    def create_combination_data(self, df: pd.DataFrame, benchmark_combination: List[str]) -> str:
        """Create a CSV file for a combination of benchmarks for spectral ranking"""
        # Extract data for each benchmark in the combination
        combination_data = []

        for benchmark in benchmark_combination:
            benchmark_row = df[df.iloc[:, 0] == benchmark]
            if benchmark_row.empty:
                raise ValueError(f"Benchmark '{benchmark}' not found in data")

            # Extract the scores (skip the first column which is benchmark name)
            scores = benchmark_row.iloc[0, 1:].values  # Skip first column (benchmark name)
            combination_data.append(scores)

        # Convert to numpy array and ensure float type
        combination_data = np.array(combination_data, dtype=float)
        model_names = df.columns[1:].tolist()  # Skip first column

        # Create multi-row dataframe (benchmarks as rows, models as columns)
        combination_df = pd.DataFrame(combination_data, columns=model_names, index=benchmark_combination)

        # Create temporary file
        combination_name = "_".join(benchmark_combination)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.csv', prefix=f'arena_{combination_name}_')
        os.close(temp_fd)

        combination_df.to_csv(temp_path, index=False)
        logger.info(f"Created combination file for {benchmark_combination}: {temp_path}")
        logger.info(f"Combination data shape: {combination_df.shape} ({len(benchmark_combination)} benchmarks, {len(model_names)} models)")

        # Show score ranges for each benchmark
        for i, benchmark in enumerate(benchmark_combination):
            scores = combination_data[i]
            logger.info(f"{benchmark} score range: [{scores.min():.4f}, {scores.max():.4f}]")

        return temp_path

    def run_spectral_ranking(self, input_file: str, combination: List[str], bigbetter: int = 1, B: int = 2000, seed: int = 42) -> Tuple[str, str]:
        """Run spectral ranking algorithm on a benchmark combination"""
        combination_name = "_".join(combination)
        logger.info(f"Running spectral ranking for combination: {combination}")

        # Create output directory for this combination
        combination_output_dir = os.path.join(self.data_ranking_dir, 'current', 'all_combinations', combination_name)
        os.makedirs(combination_output_dir, exist_ok=True)

        # R script command
        cmd = [
            'Rscript', self.ranking_script,
            '--csv', input_file,
            '--bigbetter', str(bigbetter),
            '--B', str(B),
            '--seed', str(seed),
            '--out', combination_output_dir
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        if result.returncode != 0:
            logger.error(f"Spectral ranking failed for combination {combination}: {result.stderr}")
            raise RuntimeError(f"Spectral ranking failed for combination {combination}: {result.stderr}")

        # Check if results were generated
        results_file = os.path.join(combination_output_dir, 'ranking_results.json')
        if not os.path.exists(results_file):
            raise FileNotFoundError(f"Ranking results not found for combination {combination}: {results_file}")

        logger.info(f"Spectral ranking completed for combination {combination}: {results_file}")
        return results_file, combination_output_dir

    def process_combination_results(self, results_file: str, combination: List[str], df: pd.DataFrame) -> Dict:
        """Process ranking results for a benchmark combination using spectral ranking results"""
        combination_name = "_".join(combination)
        logger.info(f"Processing spectral ranking results for combination: {combination}")

        # Load the spectral ranking results from R script
        try:
            with open(results_file, 'r') as f:
                spectral_results = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load spectral ranking results from {results_file}: {e}")
            raise

        # Get model names
        model_names = df.columns[1:].tolist()

        # Process spectral ranking results
        methods_data = []
        for method_data in spectral_results['methods']:
            model_name = method_data['name']

            # Validate that model exists in our data
            if model_name not in model_names:
                logger.warning(f"Model {model_name} from spectral results not found in data")
                continue

            methods_data.append(method_data)

        # Sort methods by spectral ranking
        methods_data.sort(key=lambda x: x['rank'])

        # Create results dictionary for this combination
        combination_results = {
            'combination': combination,
            'combination_name': combination_name,
            'n_benchmarks': len(combination),
            'methods': methods_data,
            'metadata': {
                'note': f'Spectral ranking using combination of {len(combination)} benchmarks',
                'n_samples_used': spectral_results['metadata']['n_samples'],
                'k_methods': spectral_results['metadata']['k_methods'],
                'runtime_sec': spectral_results['metadata']['runtime_sec']
            },
            'params': spectral_results['params']
        }

        logger.info(f"Processed {len(methods_data)} rankings for combination {combination} using spectral ranking")
        logger.info(f"Spectral ranking used {spectral_results['metadata']['n_samples']} samples, {spectral_results['metadata']['k_methods']} methods")
        return combination_results

    def run_all_combinations(self, bigbetter: int = 1, B: int = 2000, seed: int = 42, max_combinations: int = None) -> Dict[str, Dict]:
        """Run spectral ranking on all possible combinations of benchmarks"""
        logger.info("Starting all-combinations ranking for Arena benchmarks...")

        # Load full data
        df = self.load_full_data()
        benchmarks = self.get_benchmarks(df)

        # Generate all combinations
        all_combinations = self.generate_all_combinations(benchmarks)

        # Limit combinations if specified
        if max_combinations is not None and len(all_combinations) > max_combinations:
            all_combinations = all_combinations[:max_combinations]
            logger.info(f"Limited to first {max_combinations} combinations for testing")

        # Display overall progress information
        total_combinations = len(all_combinations)
        print(f"\n🚀 STARTING ARENA ALL-COMBINATIONS SPECTRAL RANKING")
        print(f"📊 Total combinations to process: {total_combinations}")
        print(f"🎯 Benchmarks available: {len(benchmarks)} ({', '.join(benchmarks)})")
        print(f"⚙️  Parameters: B={B}, bigbetter={bigbetter}, seed={seed}")
        print(f"⏱️  Estimated total runtime: ~{total_combinations * 3:.0f}-{total_combinations * 8:.0f} seconds (3-8s per combination)")
        print("=" * 80)

        # Results for all combinations
        all_results = {}
        temp_files = []

        try:
            import time
            start_time = time.time()
            completed_combinations = 0

            for i, combination in enumerate(all_combinations, 1):
                combination_name = "_".join(combination)
                logger.info(f"="*60)
                logger.info(f"PROCESSING COMBINATION {i}/{len(all_combinations)}: {combination}")
                logger.info(f"="*60)

                # Calculate and display progress
                progress_percent = (i - 1) / total_combinations * 100
                elapsed_time = time.time() - start_time
                avg_time_per_combination = elapsed_time / (i - 1) if i > 1 else 0
                estimated_remaining = avg_time_per_combination * (total_combinations - i + 1)

                print(f"\n🔄 Progress: {i}/{total_combinations} combinations ({progress_percent:.1f}%)")
                print(f"⏱️  Elapsed: {elapsed_time:.1f}s")
                print(f"📊 Average time per combination: {avg_time_per_combination:.1f}s")
                print(f"⏳ Estimated remaining: {estimated_remaining:.1f}s")
                print(f"🎯 Current combination: {combination_name}")
                print("-" * 50)

                # Create combination data for spectral ranking
                temp_file = self.create_combination_data(df, combination)
                temp_files.append(temp_file)

                # Run spectral ranking
                results_file, output_dir = self.run_spectral_ranking(
                    input_file=temp_file,
                    combination=combination,
                    bigbetter=bigbetter,
                    B=B,
                    seed=seed
                )

                # Process spectral ranking results
                combination_results = self.process_combination_results(results_file, combination, df)
                all_results[combination_name] = combination_results

                completed_combinations += 1
                current_elapsed = time.time() - start_time
                progress_percent = completed_combinations / total_combinations * 100

                print(f"✅ Completed: {combination_name} ({completed_combinations}/{total_combinations} - {progress_percent:.1f}%)")
                print(f"🏆 Top model: {combination_results['methods'][0]['name'] if combination_results['methods'] else 'N/A'}")
                print(f"⏱️  Combination runtime: {combination_results['metadata']['runtime_sec']:.1f}s")
                print()

                logger.info(f"Completed processing for combination {combination}")

        finally:
            # Final completion summary
            total_runtime = time.time() - start_time
            print(f"\n🎉 COMPLETED ALL {len(all_combinations)} COMBINATIONS!")
            print(f"⏱️  Total runtime: {total_runtime:.1f} seconds")
            print(f"📊 Average time per combination: {total_runtime/len(all_combinations):.1f} seconds")
            print(f"💾 Results saved to: {os.path.join(self.data_ranking_dir, 'current', 'all_combinations')}")
            print("=" * 80)

            # Clean up temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")

        logger.info(f"Completed all-combinations ranking for {len(all_combinations)} combinations")
        return all_results

    def save_combined_results(self, all_results: Dict[str, Dict]):
        """Save combined results for all combinations"""
        # Create output directory
        output_dir = os.path.join(self.data_ranking_dir, 'current', 'all_combinations')
        os.makedirs(output_dir, exist_ok=True)

        # Save combined results for all combinations
        combined_file = os.path.join(output_dir, 'arena_all_combinations_rankings.json')
        with open(combined_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        logger.info(f"Saved combined results for all combinations: {combined_file}")

        # Create summary file with combination statistics
        summary_data = []
        for combination_name, results in all_results.items():
            summary_data.append({
                'combination_name': combination_name,
                'combination': results['combination'],
                'n_benchmarks': results['n_benchmarks'],
                'n_models': len(results['methods']),
                'runtime_sec': results['metadata']['runtime_sec'],
                'top_model': results['methods'][0]['name'] if results['methods'] else None,
                'top_score': results['methods'][0]['theta_hat'] if results['methods'] else None
            })

        summary_df = pd.DataFrame(summary_data)
        summary_file = os.path.join(output_dir, 'arena_combinations_summary.csv')
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"Saved combinations summary: {summary_file}")

        return combined_file

    def create_summary_table(self, all_results: Dict[str, Dict]) -> pd.DataFrame:
        """Create a summary table showing rankings across all benchmarks"""
        logger.info("Creating summary table...")

        # Get all unique model names
        all_models = set()
        for benchmark_results in all_results.values():
            for method in benchmark_results['methods']:
                all_models.add(method['name'])

        all_models = sorted(list(all_models))

        # Create summary data
        summary_data = []
        for model in all_models:
            row = {'model': model}

            # Add ranking for each benchmark
            for benchmark, benchmark_results in all_results.items():
                # Find this model's ranking in this benchmark
                model_ranking = None
                model_theta = None
                for method in benchmark_results['methods']:
                    if method['name'] == model:
                        model_ranking = method['rank']
                        model_theta = method['theta_hat']
                        break

                row[f'{benchmark}_rank'] = model_ranking
                row[f'{benchmark}_theta'] = model_theta

            summary_data.append(row)

        # Convert to DataFrame
        summary_df = pd.DataFrame(summary_data)

        # Sort by average rank across all benchmarks
        rank_columns = [col for col in summary_df.columns if col.endswith('_rank')]
        summary_df['avg_rank'] = summary_df[rank_columns].mean(axis=1)
        summary_df = summary_df.sort_values('avg_rank')

        # Save summary table
        output_dir = os.path.join(self.data_ranking_dir, 'current', 'single_benchmarks')
        summary_file = os.path.join(output_dir, 'arena_single_benchmark_summary.csv')
        summary_df.to_csv(summary_file, index=False)

        logger.info(f"Saved summary table: {summary_file}")
        return summary_df

    def print_summary(self, all_results: Dict[str, Dict], summary_df: pd.DataFrame):
        """Print a summary of the results"""
        print("\n" + "="*80)
        print("ARENA SINGLE-BENCHMARK SPECTRAL RANKING SUMMARY")
        print("="*80)

        print(f"\nProcessed {len(all_results)} benchmarks:")
        for benchmark in all_results.keys():
            print(f"  - {benchmark}")

        print("\nTop 5 models by average rank across all benchmarks:")
        print("-" * 60)
        for i, (_, row) in enumerate(summary_df.head(5).iterrows(), 1):
            print("2d")

        print("\nBenchmark-specific rankings (top 3 for each):")
        print("-" * 60)

        for benchmark, results in all_results.items():
            print(f"\n{benchmark}:")
            for i, method in enumerate(results['methods'][:3], 1):
                print("2d")

    def update_ranking(self, bigbetter: int = 1, B: int = 2000, seed: int = 42, max_combinations: int = None):
        """Main method to update all-combinations ranking data"""
        logger.info("="*80)
        logger.info("STARTING ARENA ALL-COMBINATIONS SPECTRAL RANKING")
        logger.info("="*80)

        try:
            # Step 1: Run ranking on all combinations
            all_results = self.run_all_combinations(
                bigbetter=bigbetter,
                B=B,
                seed=seed,
                max_combinations=max_combinations
            )

            # Step 2: Save results
            combined_file = self.save_combined_results(all_results)

            logger.info("="*80)
            logger.info("ARENA ALL-COMBINATIONS SPECTRAL RANKING COMPLETED SUCCESSFULLY")
            logger.info("="*80)

            return combined_file

        except Exception as e:
            logger.error(f"Arena all-combinations ranking update failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Update Arena ranking data with all-combinations spectral ranking")
    parser.add_argument('--bigbetter', type=int, default=1,
                       help='Higher scores are better (1) or lower scores are better (0) (default: 1)')
    parser.add_argument('--B', type=int, default=2000,
                       help='Number of bootstrap iterations (default: 2000)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--max-combinations', type=int, default=None,
                       help='Maximum number of combinations to process (for testing)')

    args = parser.parse_args()

    # Validate arguments
    if args.B <= 0:
        parser.error("B must be positive")
    if args.bigbetter not in [0, 1]:
        parser.error("bigbetter must be 0 or 1")

    # Run update
    updater = ArenaAllCombinationsRankingUpdater()
    updater.update_ranking(
        bigbetter=args.bigbetter,
        B=args.B,
        seed=args.seed,
        max_combinations=args.max_combinations
    )


if __name__ == "__main__":
    main()
