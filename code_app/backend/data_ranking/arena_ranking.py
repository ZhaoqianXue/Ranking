#!/usr/bin/env python3
"""
Run Spectral Ranking on All Category Combinations for Arena Human Preferences

This script runs the spectral ranking algorithm on all 120 category combinations (2-7 categories)
or optionally on only the 7 individual category files from the Arena human preference data.
It processes each combination/single category file and generates ranking results.

Usage:
    python arena_ranking.py [--bigbetter 1] [--B 2000] [--seed 42] [--max-combinations N] [--single-only]

The script will:
1. Discover all category combination files (or single category files) in all_combinations directory
2. Run spectral ranking algorithm via ranking_cli.R for each combination/single category
3. Process and save ranking results for each combination/single category
4. Generate summary of all combination/single category rankings
"""

import os
import sys
import json
import pandas as pd
import subprocess
import argparse
import logging
from typing import Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_single_combination_worker(combination_file: str, project_root: str, bigbetter: int = 1, B: int = 2000, seed: int = 42):
    """
    Worker function for processing a single combination in parallel.
    This function is designed to be called from a process pool.
    """
    try:
        # Re-import necessary modules in the worker process
        import os
        import json
        import pandas as pd
        import subprocess
        import logging

        # Setup logging for worker
        logging.basicConfig(level=logging.INFO)
        worker_logger = logging.getLogger(f"worker_{os.getpid()}")

        # Extract combination name
        filename = os.path.basename(combination_file)
        combination_name = filename.replace('arena_spectral_', '').replace('.csv', '')

        worker_logger.info(f"Worker {os.getpid()} processing: {combination_name}")

        # Setup paths
        data_ranking_dir = os.path.join(project_root, 'data_llm', 'data_arena', 'data_ranking')
        demo_r_dir = os.path.join(project_root, 'demo_r')
        ranking_script = os.path.join(demo_r_dir, 'ranking_cli.R')

        # Create output directory for this combination
        combinations_ranking_dir = os.path.join(data_ranking_dir, 'current', 'all_combinations')
        output_dir = os.path.join(combinations_ranking_dir, combination_name)
        os.makedirs(output_dir, exist_ok=True)

        # Run spectral ranking
        cmd = [
            'Rscript', ranking_script,
            '--csv', combination_file,
            '--bigbetter', str(bigbetter),
            '--B', str(B),
            '--seed', str(seed),
            '--out', output_dir
        ]

        worker_logger.info(f"Running R command for {combination_name}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        if result.returncode != 0:
            error_msg = f"R script failed for {combination_name}: {result.stderr}"
            worker_logger.error(error_msg)
            return {
                'combination_name': combination_name,
                'success': False,
                'error': error_msg,
                'input_file': combination_file
            }

        # Check if results were generated
        results_file = os.path.join(output_dir, 'ranking_results.json')
        if not os.path.exists(results_file):
            error_msg = f"Results file not found for {combination_name}: {results_file}"
            worker_logger.error(error_msg)
            return {
                'combination_name': combination_name,
                'success': False,
                'error': error_msg,
                'input_file': combination_file
            }

        # Process results
        with open(results_file, 'r') as f:
            ranking_data = json.load(f)

        # Load original input data to get model names
        input_df = pd.read_csv(combination_file, index_col=0)

        # Extract methods information
        methods_data = ranking_data.get('methods', [])
        ranking_to_csv_mapping = {}

        # Get all columns (R script automatically filters numeric columns)
        all_columns = input_df.columns.tolist()

        for method_info in methods_data:
            r_name = method_info['name']
            original_csv_name = _find_original_csv_name_worker(r_name, all_columns)
            ranking_to_csv_mapping[r_name] = original_csv_name

        # Create results DataFrame
        results = []
        for method_info in methods_data:
            r_model_name = method_info['name']
            original_model_name = ranking_to_csv_mapping.get(r_model_name, r_model_name)
            theta_hat = method_info['theta_hat']
            rank = method_info['rank']

            # Extract confidence intervals
            ci_two_sided = method_info.get('ci_two_sided', [None, None])
            ci_two_left = ci_two_sided[0] if len(ci_two_sided) > 0 else None
            ci_two_right = ci_two_sided[1] if len(ci_two_sided) > 1 else None
            ci_left = method_info.get('ci_left', None)
            ci_uniform_left = method_info.get('ci_uniform_left', None)

            row = {
                'model': original_model_name,
                'theta_hat': theta_hat,
                'rank': int(rank),
                'ci_two_left': ci_two_left,
                'ci_two_right': ci_two_right,
                'ci_left': ci_left,
                'ci_uniform_left': ci_uniform_left
            }
            results.append(row)

        # Sort by ranking score
        results_df = pd.DataFrame(results).sort_values('theta_hat', ascending=False)

        # Save processed results
        csv_file = os.path.join(output_dir, 'ranking_results.csv')
        results_df.to_csv(csv_file, index=False)

        json_file = os.path.join(output_dir, 'ranking_results.json')
        with open(json_file, 'w') as f:
            json.dump(results_df.to_dict('records'), f, indent=2)

        worker_logger.info(f"Successfully processed {combination_name}: {len(results_df)} models")

        return {
            'combination_name': combination_name,
            'success': True,
            'input_file': combination_file,
            'output_dir': output_dir,
            'results_file': results_file,
            'num_models': len(results_df),
            'top_model': results_df.iloc[0]['model'] if len(results_df) > 0 else None,
            'top_score': results_df.iloc[0]['theta_hat'] if len(results_df) > 0 else None
        }

    except Exception as e:
        import traceback
        error_msg = f"Worker failed for {combination_file}: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {
            'combination_name': os.path.basename(combination_file).replace('arena_spectral_', '').replace('.csv', ''),
            'success': False,
            'error': error_msg,
            'input_file': combination_file
        }

def _find_original_csv_name_worker(r_name: str, csv_columns: list) -> str:
    """Worker version of _find_original_csv_name for parallel processing"""
    # Handle R's truncation
    if '...' in r_name:
        base_name = r_name.split('...')[0]
        suffix_num = r_name.split('...')[1]
        try:
            suffix_int = int(suffix_num)
            candidates = [col for col in csv_columns if col.startswith(base_name)]
            if candidates:
                return candidates[0]
        except ValueError:
            pass

    # Exact match
    if r_name in csv_columns:
        return r_name

    # Remove prefix
    if '/' in r_name:
        simple_name = r_name.split('/')[-1]
        if simple_name in csv_columns:
            return simple_name

    return r_name

class ArenaCombinationsRankingProcessor:
    """Processes all category combinations with spectral ranking"""

    def __init__(self):
        # Get absolute paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.data_processing_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_processing')
        self.data_ranking_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_ranking')
        self.demo_r_dir = os.path.join(self.project_root, 'demo_r')

        # Scripts and data paths
        self.ranking_script = os.path.join(self.demo_r_dir, 'ranking_cli.R')
        self.combinations_dir = os.path.join(self.data_processing_dir, 'all_combinations')
        self.combinations_ranking_dir = os.path.join(self.data_ranking_dir, 'current', 'all_combinations')

        # Ensure directories exist
        os.makedirs(self.combinations_ranking_dir, exist_ok=True)

    def discover_combination_files(self, max_combinations: int = None, single_only: bool = False) -> list:
        """Discover all category combination files or single category files"""
        if not os.path.exists(self.combinations_dir):
            raise FileNotFoundError(f"Combinations directory not found: {self.combinations_dir}")

        # Known single categories (these are the 7 individual category files)
        known_single_categories = {
            'coding', 'creative_writing', 'hard_prompt',
            'instruction_following', 'longer_query', 'math', 'multi_turn'
        }

        # Find all CSV files in combinations directory
        combination_files = []
        for filename in os.listdir(self.combinations_dir):
            if filename.startswith('arena_spectral_') and filename.endswith('.csv'):
                # Extract the category part from filename
                category_part = filename.replace('arena_spectral_', '').replace('.csv', '')

                if single_only:
                    # Only include known single category files
                    if category_part in known_single_categories:
                        filepath = os.path.join(self.combinations_dir, filename)
                        combination_files.append(filepath)
                else:
                    # Include all combination files (exclude single category files)
                    if category_part not in known_single_categories:
                filepath = os.path.join(self.combinations_dir, filename)
                combination_files.append(filepath)

        # Sort by filename for consistent processing
        combination_files.sort()

        if max_combinations:
            combination_files = combination_files[:max_combinations]

        file_type = "single category" if single_only else "combination"
        logger.info(f"Found {len(combination_files)} {file_type} files")
        return combination_files

    def extract_combination_name(self, filepath: str) -> str:
        """Extract combination name from file path"""
        filename = os.path.basename(filepath)
        # Remove 'arena_spectral_' prefix and '.csv' suffix
        combination_name = filename.replace('arena_spectral_', '').replace('.csv', '')
        return combination_name

    def process_single_combination(self, combination_file: str, bigbetter: int = 1, B: int = 2000, seed: int = 42) -> dict:
        """Process a single category combination"""
        combination_name = self.extract_combination_name(combination_file)
        logger.info(f"Processing combination: {combination_name}")

        # Create output directory for this combination
        output_dir = os.path.join(self.combinations_ranking_dir, combination_name)
        os.makedirs(output_dir, exist_ok=True)

        # Run spectral ranking
        results_file, _ = self.run_spectral_ranking(
            input_file=combination_file,
            bigbetter=bigbetter,
            B=B,
            seed=seed,
            output_dir=output_dir
        )

        # Process results
        results_df, name_mapping = self.process_ranking_results(results_file, combination_file)

        # Save processed results
        self.save_combination_results(results_df, combination_name, output_dir)

        # Return summary
        return {
            'combination_name': combination_name,
            'input_file': combination_file,
            'output_dir': output_dir,
            'results_file': results_file,
            'num_models': len(results_df),
            'top_model': results_df.iloc[0]['model'] if len(results_df) > 0 else None,
            'top_score': results_df.iloc[0]['theta_hat'] if len(results_df) > 0 else None
        }

    def save_combination_results(self, results_df: pd.DataFrame, combination_name: str, output_dir: str):
        """Save processed results for a combination"""
        # Save as CSV
        csv_file = os.path.join(output_dir, 'ranking_results.csv')
        results_df.to_csv(csv_file, index=False)

        # Save as JSON
        json_file = os.path.join(output_dir, 'ranking_results.json')
        with open(json_file, 'w') as f:
            json.dump(results_df.to_dict('records'), f, indent=2)

        logger.info(f"Saved results for {combination_name}: {csv_file}")


    def run_spectral_ranking(self, input_file: str, bigbetter: int = 1, B: int = 2000, seed: int = 42, output_dir: str = None) -> Tuple[str, str]:
        """Run spectral ranking algorithm via R script"""
        logger.info(f"Running spectral ranking on Arena data: {input_file}...")

        # Use provided output directory or create default
        if output_dir is None:
            temp_output_dir = os.path.join(self.data_ranking_dir, 'current')
        else:
            temp_output_dir = output_dir

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

        # Get all columns (R script automatically filters numeric columns)
        all_columns = input_df.columns.tolist()

        # Create mapping from ranking result names to original CSV column names
        ranking_to_csv_mapping = {}
        for method_info in methods_data:
            r_name = method_info['name']
            # Find the corresponding original CSV column name
            original_csv_name = self._find_original_csv_name(r_name, all_columns)
            ranking_to_csv_mapping[r_name] = original_csv_name

        # Create results DataFrame
        results = []
        for i, method_info in enumerate(methods_data):
            r_model_name = method_info['name']  # Name as stored by R
            original_model_name = ranking_to_csv_mapping.get(r_model_name, r_model_name)

            theta_hat = method_info['theta_hat']
            rank = method_info['rank']

            # Extract confidence intervals
            ci_two_sided = method_info.get('ci_two_sided', [None, None])
            ci_two_left = ci_two_sided[0] if len(ci_two_sided) > 0 else None
            ci_two_right = ci_two_sided[1] if len(ci_two_sided) > 1 else None
            ci_left = method_info.get('ci_left', None)
            ci_uniform_left = method_info.get('ci_uniform_left', None)

            row = {
                'model': original_model_name,
                'theta_hat': theta_hat,
                'rank': int(rank),
                'ci_two_left': ci_two_left,
                'ci_two_right': ci_two_right,
                'ci_left': ci_left,
                'ci_uniform_left': ci_uniform_left
            }

            results.append(row)

        # Sort by ranking score (descending, higher is better)
        results_df = pd.DataFrame(results).sort_values('theta_hat', ascending=False)

        logger.info(f"Processed {len(results_df)} Arena model rankings")
        return results_df, ranking_to_csv_mapping



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

    def process_all_combinations(self, bigbetter: int = 1, B: int = 2000, seed: int = 42, max_combinations: int = None, max_workers: int = 120, single_only: bool = False):
        """Main method to process all category combinations or single categories in parallel"""
        processing_type = "SINGLE CATEGORIES" if single_only else "COMBINATIONS"
        logger.info("="*60)
        logger.info(f"STARTING ARENA {processing_type} SPECTRAL RANKING (PARALLEL)")
        logger.info(f"Using {max_workers} parallel workers")
        logger.info("="*60)

        try:
            # Step 1: Discover all combination files
            combination_files = self.discover_combination_files(max_combinations, single_only)

            if not combination_files:
                raise FileNotFoundError("No combination files found")

            total_combinations = len(combination_files)
            logger.info(f"Found {total_combinations} combinations to process")

            # Step 2: Process combinations in parallel
            all_summaries = []
            successful_combinations = 0
            failed_combinations = 0

            logger.info("\n🚀 STARTING PARALLEL PROCESSING")
            logger.info(f"📊 Total combinations: {total_combinations}")
            logger.info(f"⚡ Parallel workers: {max_workers}")
            logger.info(f"🎯 Bootstrap iterations: {B}")
            logger.info("=" * 80)

            # Use ProcessPoolExecutor for parallel processing
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        process_single_combination_worker,
                        combination_file,
                        self.project_root,
                        bigbetter,
                        B,
                        seed
                    ): combination_file for combination_file in combination_files
                }

                # Process completed tasks
                completed_count = 0
                for future in as_completed(future_to_file):
                    combination_file = future_to_file[future]
                    combination_name = self.extract_combination_name(combination_file)
                    completed_count += 1

                    # Debug: Print every completion
                    if completed_count <= 5 or completed_count % 10 == 0:
                        print(f"DEBUG: Completed {completed_count}/{total_combinations} combinations")

                    try:
                        summary = future.result()
                        if summary['success']:
                            all_summaries.append(summary)
                            successful_combinations += 1

                            # Detailed success info
                            logger.info("2d"                                       f"   📁 Combination: {combination_name}")
                            logger.info(f"   👥 Models: {summary['num_models']}")
                            logger.info(f"   🏆 Top model: {summary.get('top_model', 'N/A')}")
                            logger.info(f"   📊 Top score: {summary.get('top_score', 'N/A'):.4f}")
                            logger.info(f"   📂 Output: {summary['output_dir']}")
                            logger.info(f"   {'='*60}")

                        else:
                            failed_combinations += 1
                            # Detailed failure info
                            logger.error("2d"                                        f"   📁 Combination: {combination_name}")
                            logger.error(f"   ❌ Error: {summary.get('error', 'Unknown error')}")
                            logger.error(f"   📂 Input: {summary.get('input_file', 'N/A')}")
                            logger.error(f"   {'='*60}")

                    except Exception as e:
                        failed_combinations += 1
                        logger.error("2d")
                        logger.error(f"   📁 Combination: {combination_name}")
                        logger.error(f"   💥 Exception: {e}")
                        logger.error(f"   {'='*60}")

                    # Progress summary every 5 completions or at key milestones
                    if completed_count % 5 == 0 or completed_count == total_combinations or completed_count == 1:
                        progress_percent = (completed_count / total_combinations) * 100
                        print("\n" + "="*80, flush=True)
                        print("🚀 ARENA COMBINATIONS PROCESSING PROGRESS", flush=True)
                        print("="*80, flush=True)
                        print(f"📊 Progress: {completed_count}/{total_combinations} ({progress_percent:.1f}%)", flush=True)
                        print(f"✅ Successful: {successful_combinations}", flush=True)
                        print(f"❌ Failed: {failed_combinations}", flush=True)
                        print(f"⏳ Remaining: {total_combinations - completed_count}", flush=True)
                        print(f"⚡ Workers: {max_workers}", flush=True)
                        print(f"🎯 Bootstrap: {B}", flush=True)
                        print("="*80, flush=True)

            # Step 3: Generate overall summary
            self.generate_overall_summary(all_summaries, single_only)

            processing_type_display = "SINGLE CATEGORIES" if single_only else "COMBINATIONS"
            logger.info("="*60)
            logger.info(f"ARENA {processing_type_display} SPECTRAL RANKING COMPLETED")
            logger.info("="*60)

            # Print summary
            print("\n" + "="*60)
            print(f"ARENA {processing_type_display} RANKING SUMMARY")
            print("="*60)
            print(f"Total combinations found: {total_combinations}")
            print(f"Successfully processed: {successful_combinations}")
            print(f"Failed combinations: {failed_combinations}")
            print(f"Parallel workers used: {max_workers}")
            print(f"Bootstrap iterations: {B}")
            print(f"Random seed: {seed}")
            print(f"Output directory: {self.combinations_ranking_dir}")

            # Show sample results
            successful_summaries = [s for s in all_summaries if s['success']]
            if successful_summaries:
                print("\nSAMPLE RESULTS (first 3 successful combinations):")
                for summary in successful_summaries[:3]:
                    print(f"  {summary['combination_name']}: {summary['num_models']} models, top: {summary['top_model']}")

        except Exception as e:
            logger.error(f"Arena combinations ranking failed: {e}")
            raise

    def generate_overall_summary(self, all_summaries: list, single_only: bool = False):
        """Generate overall summary of all combinations or single categories processing"""
        file_type = "single_categories" if single_only else "combinations"
        summary_filename = f"{file_type}_ranking_summary.json"
        summary_file = os.path.join(self.combinations_ranking_dir, summary_filename)

        summary_data = {
            'processing_timestamp': pd.Timestamp.now().isoformat(),
            'processing_type': 'single_categories' if single_only else 'combinations',
            'total_items': len(all_summaries),
            'items': all_summaries
        }

        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)

        logger.info(f"Overall summary saved: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="Run spectral ranking on all Arena category combinations or single categories")
    parser.add_argument('--bigbetter', type=int, default=1,
                       help='Higher scores are better (1) or lower scores are better (0) (default: 1)')
    parser.add_argument('--B', type=int, default=2000,
                       help='Number of bootstrap iterations (default: 2000)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--max-combinations', type=int,
                       help='Maximum number of combinations/categories to process (for testing)')
    parser.add_argument('--max-workers', type=int, default=120,
                       help='Maximum number of parallel workers (default: 120)')
    parser.add_argument('--single-only', action='store_true',
                       help='Process only single category files instead of all combinations')

    args = parser.parse_args()

    # Validate arguments
    if args.B <= 0:
        parser.error("B must be positive")
    if args.bigbetter not in [0, 1]:
        parser.error("bigbetter must be 0 or 1")
    if args.max_combinations is not None and args.max_combinations <= 0:
        parser.error("max-combinations must be positive")
    if args.max_workers <= 0:
        parser.error("max-workers must be positive")

    # Run processing
    processor = ArenaCombinationsRankingProcessor()
    processor.process_all_combinations(
        bigbetter=args.bigbetter,
        B=args.B,
        seed=args.seed,
        max_combinations=args.max_combinations,
        max_workers=args.max_workers,
        single_only=args.single_only
    )


if __name__ == "__main__":
    main()
