#!/usr/bin/env python3
"""
Prepare Arena Human Preference Data for Spectral Ranking Analysis

This script transforms the collected Arena human preference data into the format
expected by ranking_cli.R for spectral ranking analysis.

Input format (from arena_data_collector.py):
- Rows: Individual preference votes
- Columns: model_a, model_b, winner, conversation data, metadata

Output format (for ranking_cli.R):
- Rows: Virtual benchmarks (derived metrics)
- Columns: Models (as "methods")

Virtual Benchmarks Created:
1. win_rate: Overall win rate (wins / total_games)
2. effective_score: Weighted score (win=1, tie=0.5, loss=0)
3. total_games: Total number of comparisons participated in
4. tie_rate: Tie rate (ties / total_games)
"""

import pandas as pd
import numpy as np
import os
import json
import logging
import ast
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# CONFIGURATION SECTION
# ===============================
# Specify which top-N datasets to generate
TOP_DATASETS_TO_GENERATE = [21]
# ===============================
# Virtual benchmarks to create (only category-specific performance)
VIRTUAL_BENCHMARKS = [
    # 7 category dimensions via Bradley–Terry MLE probabilities
    'creative_writing_bt_prob',
    'math_bt_prob',
    'instruction_following_bt_prob',
    'coding_bt_prob',
    'hard_prompt_bt_prob',
    'longer_query_bt_prob',
    'multi_turn_bt_prob',
]
# ===============================
# Configuration switches
LIMIT_MODEL_COUNT = False  # Set to False to include all qualified models
# ===============================
# Minimum games threshold for model inclusion
MIN_GAMES_THRESHOLD = 5
# ===============================

class ArenaRankingDataPreparer:
    """Prepare Arena human preference data for spectral ranking analysis"""

    @staticmethod
    def _fit_bt_probabilities_from_edges(oriented_edge_wins, max_iter=5000, tol=1e-8, alpha=0.5):
        """
        Fit Bradley–Terry strengths using MM algorithm and return probabilities vs average opponent.

        Args:
            oriented_edge_wins: dict[(winner, loser)] -> float (wins; ties should be split as 0.5)
            max_iter: maximum iterations for MM updates
            tol: convergence tolerance on log-strengths
            alpha: Jeffreys/Laplace-like smoothing applied to wins and denominators

        Returns:
            dict[str, float]: model -> p_i in [0,1], interpreted as Pr(model beats an average opponent)
        """
        # Collect unique models
        models = set()
        for (w, l) in oriented_edge_wins.keys():
            models.add(w)
            models.add(l)

        if len(models) < 2:
            return {m: 0.5 for m in models}

        model_list = sorted(models)
        idx = {m: i for i, m in enumerate(model_list)}
        k = len(model_list)

        # Build directed wins matrix W[i,j] = wins of i over j (already includes 0.5 for ties)
        W = np.zeros((k, k), dtype=float)
        for (w, l), val in oriented_edge_wins.items():
            if w not in idx or l not in idx:
                continue
            W[idx[w], idx[l]] += float(val)

        # Symmetric total comparisons per pair
        N = W + W.T  # N[i,j] = total outcomes between i and j (after tie split)

        # Wins per player (after tie split)
        wins_i = W.sum(axis=1)

        # If everyone has zero comparisons, return 0.5
        if float(N.sum()) <= 0.0:
            return {m: 0.5 for m in model_list}

        # Initialize strengths s_i > 0
        s = np.ones(k, dtype=float)

        # Mask for pairs with any comparisons
        pair_mask = (N > 0)

        # MM iterations
        for _ in range(max_iter):
            # Compute denominators: denom_i = sum_j N_ij / (s_i + s_j)
            denom = np.zeros(k, dtype=float)
            for i in range(k):
                # Only consider j with comparisons
                js = np.where(pair_mask[i])[0]
                if js.size == 0:
                    denom[i] = 0.0
                else:
                    denom[i] = np.sum(N[i, js] / (s[i] + s[js]))

            # Smoothed wins to avoid zero locking
            wins_smoothed = wins_i + alpha
            denom_smoothed = denom + alpha

            # Update strengths
            s_new = wins_smoothed / np.where(denom_smoothed > 0, denom_smoothed, 1.0)

            # Normalize to geometric mean 1 to fix identifiability
            with np.errstate(divide='ignore', invalid='ignore'):
                log_s_new = np.log(np.where(s_new > 0, s_new, 1e-12))
            gm = float(np.exp(np.mean(log_s_new)))
            if gm <= 0:
                gm = 1.0
            s_new = s_new / gm

            # Convergence check on log scale
            with np.errstate(divide='ignore', invalid='ignore'):
                diff = np.max(np.abs(np.log(np.where(s > 0, s, 1e-12)) - np.log(np.where(s_new > 0, s_new, 1e-12))))
            s = s_new
            if diff < tol:
                break

        # After normalization, geometric mean(s) == 1, so average opponent strength is 1
        # Probability vs average opponent: p_i = s_i / (s_i + 1)
        p = s / (s + 1.0)

        return {model_list[i]: float(p[i]) for i in range(k)}

    def classify_task_categories(self, row):
        """
        Classify a task into the 7 categories based on Arena dataset schema

        Args:
            row: pandas Series containing the row data

        Returns:
            dict: Classification results for each of the 7 categories
        """
        categories = {
            'is_creative_writing': False,
            'is_math': False,
            'is_instruction_following': False,
            'is_coding': False,
            'is_hard_prompt': False,
            'is_longer_query': False,
            'is_multi_turn': False
        }

        try:
            # Parse category_tag and conv_metadata
            category_tag = ast.literal_eval(row['category_tag']) if pd.notna(row['category_tag']) else {}
            conv_metadata = ast.literal_eval(row['conv_metadata']) if pd.notna(row['conv_metadata']) else {}

            # 1. Creative Writing
            if category_tag.get('creative_writing_v0.1', {}).get('creative_writing', False):
                categories['is_creative_writing'] = True

            # 2. Math
            if category_tag.get('math_v0.1', {}).get('math', False):
                categories['is_math'] = True

            # 3. Instruction Following
            if category_tag.get('if_v0.1', {}).get('if', False):
                categories['is_instruction_following'] = True

            # 4. Coding
            if row.get('is_code', False):
                categories['is_coding'] = True

            # 5. Hard Prompt (needs >=6 of 7 criteria)
            criteria = category_tag.get('criteria_v0.1', {})
            hard_score = sum([
                criteria.get('specificity', False),
                criteria.get('domain_knowledge', False),
                criteria.get('complexity', False),
                criteria.get('problem_solving', False),
                criteria.get('creativity', False),
                criteria.get('technical_accuracy', False),
                criteria.get('real_world', False)
            ])
            if hard_score >= 6:
                categories['is_hard_prompt'] = True

            # 6. Longer Query
            if conv_metadata.get('sum_user_tokens', 0) > 500:
                categories['is_longer_query'] = True

            # 7. Multi-Turn
            if conv_metadata.get('turns', 1) > 1:
                categories['is_multi_turn'] = True

        except Exception as e:
            logger.warning(f"Error classifying task: {e}")

        return categories

    def __init__(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.input_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_collection')
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_processing')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_raw_data(self):
        """Load the raw Arena preference data"""
        input_file = os.path.join(self.input_dir, 'arena_human_preference_full.csv')
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Raw data file not found: {input_file}")

        logger.info(f"Loading raw Arena data from: {input_file}")
        df = pd.read_csv(input_file)
        logger.info(f"Loaded {len(df)} preference votes with {len(df.columns)} columns")
        return df

    def calculate_model_statistics(self, df):
        """
        Calculate statistics for each model from the preference data
        Now includes performance across the 7 task categories

        Returns a dictionary with model stats and a list of all unique models
        """
        logger.info("Calculating model statistics from preference data...")

        # Initialize tracking dictionaries for each model
        model_stats = defaultdict(lambda: {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'ties': 0,
            'both_bad': 0,
            # Category-specific stats
            'creative_writing_games': 0, 'creative_writing_wins': 0,
            'math_games': 0, 'math_wins': 0,
            'instruction_following_games': 0, 'instruction_following_wins': 0,
            'coding_games': 0, 'coding_wins': 0,
            'hard_prompt_games': 0, 'hard_prompt_wins': 0,
            'longer_query_games': 0, 'longer_query_wins': 0,
            'multi_turn_games': 0, 'multi_turn_wins': 0
        })

        # Prepare per-category oriented edge wins for BT (ties split as 0.5; both_bad ignored)
        bt_edges_by_category = {
            'creative_writing': defaultdict(float),
            'math': defaultdict(float),
            'instruction_following': defaultdict(float),
            'coding': defaultdict(float),
            'hard_prompt': defaultdict(float),
            'longer_query': defaultdict(float),
            'multi_turn': defaultdict(float)
        }

        # Process each preference vote
        for _, row in df.iterrows():
            model_a = row['model_a']
            model_b = row['model_b']
            winner = row['winner']

            # Classify the task into categories
            categories = self.classify_task_categories(row)

            # Count games for both models
            model_stats[model_a]['total_games'] += 1
            model_stats[model_b]['total_games'] += 1

            # Count category-specific games
            for category_key, is_category in categories.items():
                if is_category:
                    game_key = category_key.replace('is_', '') + '_games'
                    model_stats[model_a][game_key] += 1
                    model_stats[model_b][game_key] += 1

            # Record outcomes
            if winner == 'model_a':
                model_stats[model_a]['wins'] += 1
                model_stats[model_b]['losses'] += 1

                # Record category-specific wins
                for category_key, is_category in categories.items():
                    if is_category:
                        win_key = category_key.replace('is_', '') + '_wins'
                        model_stats[model_a][win_key] += 1
                        # BT oriented edge: model_a beats model_b
                        cat = category_key.replace('is_', '')
                        bt_edges_by_category[cat][(model_a, model_b)] += 1.0

            elif winner == 'model_b':
                model_stats[model_b]['wins'] += 1
                model_stats[model_a]['losses'] += 1

                # Record category-specific wins
                for category_key, is_category in categories.items():
                    if is_category:
                        win_key = category_key.replace('is_', '') + '_wins'
                        model_stats[model_b][win_key] += 1
                        # BT oriented edge: model_b beats model_a
                        cat = category_key.replace('is_', '')
                        bt_edges_by_category[cat][(model_b, model_a)] += 1.0

            elif winner == 'tie':
                model_stats[model_a]['ties'] += 1
                model_stats[model_b]['ties'] += 1
                # Split tie as half win to both directions for BT
                for category_key, is_category in categories.items():
                    if is_category:
                        cat = category_key.replace('is_', '')
                        bt_edges_by_category[cat][(model_a, model_b)] += 0.5
                        bt_edges_by_category[cat][(model_b, model_a)] += 0.5
            elif winner == 'both_bad':
                model_stats[model_a]['both_bad'] += 1
                model_stats[model_b]['both_bad'] += 1
                # Do not include both_bad in BT likelihood (treated as missing)

        # Fit BT per category to obtain probabilities vs average opponent
        category_bt_prob = {}
        for cat in ['creative_writing', 'math', 'instruction_following',
                    'coding', 'hard_prompt', 'longer_query', 'multi_turn']:
            edges = bt_edges_by_category[cat]
            if len(edges) == 0:
                category_bt_prob[cat] = {}
            else:
                category_bt_prob[cat] = self._fit_bt_probabilities_from_edges(edges)

        # Calculate derived metrics for each model
        model_metrics = {}
        all_models = []

        for model, stats in model_stats.items():
            total_games = stats['total_games']

            if total_games >= MIN_GAMES_THRESHOLD:
                # Calculate overall virtual benchmark scores
                win_rate = stats['wins'] / total_games if total_games > 0 else 0
                effective_score = (stats['wins'] + 0.5 * stats['ties']) / total_games if total_games > 0 else 0
                tie_rate = stats['ties'] / total_games if total_games > 0 else 0

                # Calculate category-specific BT probabilities and (for reference) win rates
                category_metrics = {}
                for category in ['creative_writing', 'math', 'instruction_following',
                                 'coding', 'hard_prompt', 'longer_query', 'multi_turn']:
                    games_key = f'{category}_games'
                    wins_key = f'{category}_wins'
                    category_games = stats[games_key]
                    category_wins = stats[wins_key]

                    # Win rate reference (not used in ranking rows anymore)
                    if category_games >= 3:
                        category_metrics[f'{category}_win_rate'] = category_wins / category_games
                    else:
                        category_metrics[f'{category}_win_rate'] = None

                    # BT probability vs average opponent
                    if category_games >= 3 and model in category_bt_prob.get(category, {}):
                        category_metrics[f'{category}_bt_prob'] = category_bt_prob[category][model]
                    else:
                        category_metrics[f'{category}_bt_prob'] = None

                model_metrics[model] = {
                    'model': model,
                    'win_rate': win_rate,
                    'effective_score': effective_score,
                    'total_games': total_games,
                    'tie_rate': tie_rate,
                    # Raw counts for reference
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'ties': stats['ties'],
                    'both_bad': stats['both_bad'],
                    # Category-specific metrics (win rates and BT probabilities)
                    **category_metrics
                }
                all_models.append(model)

        logger.info(f"Calculated metrics for {len(model_metrics)} models (min {MIN_GAMES_THRESHOLD} games)")
        logger.info(f"Included category-specific performance for 7 task dimensions")
        return model_metrics, all_models

    def prepare_ranking_data(self, model_metrics, all_models, top_n=None):
        """
        Prepare data in the format expected by ranking_cli.R
        Now includes only 7 category-specific virtual benchmarks

        ranking_cli.R expects:
        - Rows: Different samples/cases (virtual benchmarks in our case)
        - Columns: Different methods (models in our case)
        """
        if LIMIT_MODEL_COUNT and top_n and len(all_models) >= top_n:
            # Sort models by effective_score and select top N
            sorted_models = sorted(all_models,
                                 key=lambda m: model_metrics[m]['effective_score'],
                                 reverse=True)[:top_n]
            logger.info(f"Selected top {top_n} models by effective score")
        else:
            # Sort by effective_score for consistent ordering (or include all)
            sorted_models = sorted(all_models,
                                 key=lambda m: model_metrics[m]['effective_score'],
                                 reverse=True)
            if LIMIT_MODEL_COUNT:
                top_n = len(sorted_models)
            else:
                logger.info(f"Including all {len(sorted_models)} qualified models (LIMIT_MODEL_COUNT=False)")

        # Create ranking dataframe
        ranking_data = {}

        # For each virtual benchmark, create a row with model scores
        for benchmark in VIRTUAL_BENCHMARKS:
            benchmark_scores = []
            for model in sorted_models:
                score = model_metrics[model].get(benchmark)
                # Handle None values (when model doesn't have enough data for a category)
                if score is None:
                    # For category-specific benchmarks, use 0.5 as neutral fallback
                    # (since we can't use overall win_rate when only categories are included)
                    score = 0.5
                benchmark_scores.append(score)
            ranking_data[benchmark] = benchmark_scores

        # Create DataFrame
        ranking_df = pd.DataFrame(ranking_data, index=sorted_models).T
        ranking_df.index.name = 'virtual_benchmark'

        # Clean model names for column headers (similar to huggingface processing)
        def clean_model_name(name):
            """Clean model name for CSV column header"""
            # Take the last part after '/' and limit length
            name = name.split('/')[-1] if '/' in name else name
            return name[:25] if len(name) > 25 else name

        ranking_df.columns = [clean_model_name(model) for model in sorted_models]

        logger.info(f"Prepared ranking data: {ranking_df.shape[0]} virtual benchmarks × {ranking_df.shape[1]} models")
        logger.info(f"Includes only 7 category-specific BT-MLE probability metrics")
        return ranking_df, sorted_models

    def create_comprehensive_stats(self, model_metrics, all_models):
        """
        Create a comprehensive statistics DataFrame for analysis
        This includes all calculated metrics for dashboard display
        """
        stats_data = []
        for model in all_models:
            metrics = model_metrics[model]
            stats_data.append({
                'model': metrics['model'],
                'effective_score': metrics['effective_score'],
                'win_rate': metrics['win_rate'],
                'total_games': metrics['total_games'],
                'tie_rate': metrics['tie_rate'],
                'wins': metrics['wins'],
                'losses': metrics['losses'],
                'ties': metrics['ties'],
                'both_bad': metrics['both_bad'],
                'rank_by_score': None,  # Will be filled after ranking
                'rank_by_winrate': None  # Will be filled after ranking
            })

        stats_df = pd.DataFrame(stats_data)

        # Calculate ranks
        stats_df = stats_df.sort_values('effective_score', ascending=False)
        stats_df['rank_by_score'] = range(1, len(stats_df) + 1)

        stats_df = stats_df.sort_values('win_rate', ascending=False)
        stats_df['rank_by_winrate'] = range(1, len(stats_df) + 1)

        # Sort back by effective score for final output
        stats_df = stats_df.sort_values('effective_score', ascending=False)

        return stats_df

    def save_ranking_data(self, df, filename=None):
        """Save the prepared ranking data"""
        if df is None:
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'arena_ranking_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        # Save without index (virtual benchmarks become rows without explicit index column)
        df.to_csv(filepath, index=True)

        logger.info(f"Ranking data saved to: {filepath}")

        # Also save metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'total_models': len(df.columns),
            'virtual_benchmarks': list(df.index),
            'models': list(df.columns),
            'shape': df.shape,
            'source': 'Arena Human Preference Dataset via arena_data_collector.py',
            'prepared_for': 'ranking_cli.R spectral ranking analysis',
            'min_games_threshold': MIN_GAMES_THRESHOLD,
            'category_min_games_threshold': 3,  # For category-specific metrics
            'virtual_benchmarks_explanation': {
                # Overall performance metrics
                'win_rate': 'Overall win rate (wins / total_games)',
                'effective_score': 'Weighted score (win=1, tie=0.5, loss=0)',
                'total_games': 'Total number of comparisons participated in',
                'tie_rate': 'Tie rate (ties / total_games)',

                # Category-specific BT probabilities (vs average opponent)
                'creative_writing_bt_prob': 'BT-MLE probability in creative writing tasks',
                'math_bt_prob': 'BT-MLE probability in mathematics reasoning tasks',
                'instruction_following_bt_prob': 'BT-MLE probability in instruction following tasks',
                'coding_bt_prob': 'BT-MLE probability in programming/coding tasks',
                'hard_prompt_bt_prob': 'BT-MLE probability in hard/complex prompt tasks',
                'longer_query_bt_prob': 'BT-MLE probability in longer query tasks (>500 tokens)',
                'multi_turn_bt_prob': 'BT-MLE probability in multi-turn conversation tasks'
            },
            'task_categories': {
                'Creative Writing': 'Tasks requiring originality and imagination',
                'Math': 'Mathematics and logical reasoning tasks',
                'Instruction Following': 'Tasks requiring precise instruction execution',
                'Coding': 'Programming and code-related tasks',
                'Hard Prompt': 'Complex tasks meeting ≥6 difficulty criteria',
                'Longer Query': 'Queries with >500 tokens',
                'Multi-Turn': 'Conversations with >1 turns'
            }
        }

        metadata_filepath = filepath.replace('.csv', '_metadata.json')
        with open(metadata_filepath, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        return filepath


def main():
    """Main function to prepare Arena ranking data"""
    preparer = ArenaRankingDataPreparer()

    print("\n" + "="*80)
    print("ARENA HUMAN PREFERENCE DATA PROCESSING")
    print("="*80)

    # Load raw data
    try:
        raw_df = preparer.load_raw_data()
        print(f"✓ Loaded {len(raw_df)} preference votes")
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        return

    # Calculate model statistics
    try:
        model_metrics, all_models = preparer.calculate_model_statistics(raw_df)
        print(f"✓ Calculated metrics for {len(model_metrics)} models")
        print(f"  (Filtered models with ≥{MIN_GAMES_THRESHOLD} games)")
    except Exception as e:
        print(f"✗ Failed to calculate statistics: {e}")
        return

    # Create comprehensive stats
    try:
        stats_df = preparer.create_comprehensive_stats(model_metrics, list(model_metrics.keys()))
        print(f"✓ Created comprehensive statistics")
    except Exception as e:
        print(f"✗ Failed to create statistics: {e}")
        return

    print("\n" + "="*60)
    print("MODEL STATISTICS SUMMARY")
    print("="*60)

    # Show top models by effective score
    top_models = stats_df.head(10)
    print("\nTOP 10 MODELS BY EFFECTIVE SCORE:")
    print("-" * 80)
    for i, (_, row) in enumerate(top_models.iterrows(), 1):
        print("<10")
    print("-" * 80)

    # Show model distribution
    print("\nMODEL PARTICIPATION DISTRIBUTION:")
    print("-" * 40)
    games_bins = [0, 5, 10, 20, 50, float('inf')]
    games_labels = ['1-5', '6-10', '11-20', '21-50', '50+']
    stats_df['games_category'] = pd.cut(stats_df['total_games'], bins=games_bins,
                                       labels=games_labels, include_lowest=True)
    games_dist = stats_df['games_category'].value_counts().sort_index()
    for category, count in games_dist.items():
        print("<8")

    print(f"\nTOTAL MODELS: {len(stats_df)}")
    print(f"AVERAGE GAMES PER MODEL: {stats_df['total_games'].mean():.1f}")
    print(f"MEDIAN GAMES PER MODEL: {stats_df['total_games'].median():.0f}")

    # Generate ranking dataset based on configuration
    generated_datasets = []

    print("\n" + "="*60)
    if LIMIT_MODEL_COUNT:
        print("GENERATING TOP-N RANKING DATASETS")
    else:
        print("GENERATING FULL MODEL RANKING DATASET")
    print("="*60)

    if LIMIT_MODEL_COUNT:
        # Generate top-N datasets as before
        for top_n in TOP_DATASETS_TO_GENERATE:
            if len(model_metrics) >= top_n:
                print(f"\nGenerating top {top_n} dataset...")
                ranking_df_top, top_models = preparer.prepare_ranking_data(model_metrics,
                                                                         list(model_metrics.keys()),
                                                                         top_n=top_n)
                top_filepath = preparer.save_ranking_data(ranking_df_top, f'arena_ranking_top{top_n}.csv')

                generated_datasets.append({
                    'top_n': top_n,
                    'filepath': top_filepath,
                    'shape': ranking_df_top.shape
                })

                print(f"  ✓ Top {top_n}: {ranking_df_top.shape[0]} virtual benchmarks × {ranking_df_top.shape[1]} models saved")
            else:
                print(f"  ⚠ Skipping top {top_n}: insufficient data ({len(model_metrics)} available)")
    else:
        # Generate single dataset with all qualified models
        print("\nGenerating full dataset with all qualified models...")
        ranking_df_full, all_models_sorted = preparer.prepare_ranking_data(model_metrics,
                                                                          list(model_metrics.keys()),
                                                                          top_n=None)
        full_filepath = preparer.save_ranking_data(ranking_df_full, 'arena_ranking_full.csv')

        generated_datasets.append({
            'type': 'full',
            'filepath': full_filepath,
            'shape': ranking_df_full.shape,
            'model_count': len(all_models_sorted)
        })

        print(f"  ✓ Full dataset: {ranking_df_full.shape[0]} virtual benchmarks × {ranking_df_full.shape[1]} models saved")

    print("\n" + "="*60)
    print("GENERATED DATASETS SUMMARY")
    print("="*60)

    for dataset in generated_datasets:
        if 'type' in dataset and dataset['type'] == 'full':
            print(f"Full dataset: {dataset['filepath']}")
            print(f"  Shape: {dataset['shape'][0]} virtual benchmarks × {dataset['shape'][1]} models")
            print(f"  Models included: {dataset['model_count']}")
        else:
            print(f"Top {dataset['top_n']} dataset: {dataset['filepath']}")
            print(f"  Shape: {dataset['shape'][0]} virtual benchmarks × {dataset['shape'][1]} models")

    print("\n" + "="*60)
    print("VIRTUAL BENCHMARKS EXPLANATION")
    print("="*60)

    print("🎯 Category-Specific Performance Metrics (7 dimensions, BT-MLE probabilities):")
    category_explanations = {
        'creative_writing_bt_prob': 'BT-MLE probability in creative writing tasks',
        'math_bt_prob': 'BT-MLE probability in mathematics reasoning tasks',
        'instruction_following_bt_prob': 'BT-MLE probability in instruction following tasks',
        'coding_bt_prob': 'BT-MLE probability in programming/coding tasks',
        'hard_prompt_bt_prob': 'BT-MLE probability in hard/complex prompt tasks (≥6 difficulty criteria)',
        'longer_query_bt_prob': 'BT-MLE probability in longer query tasks (>500 tokens)',
        'multi_turn_bt_prob': 'BT-MLE probability in multi-turn conversation tasks'
    }

    for benchmark, explanation in category_explanations.items():
        print(f"  • {benchmark}: {explanation}")

    print("\n📋 Task Categories Definition:")
    task_categories = {
        'Creative Writing': 'Tasks requiring originality and imagination',
        'Math': 'Mathematics and logical reasoning tasks',
        'Instruction Following': 'Tasks requiring precise instruction execution',
        'Coding': 'Programming and code-related tasks',
        'Hard Prompt': 'Complex tasks meeting ≥6 difficulty criteria',
        'Longer Query': 'Queries with >500 tokens',
        'Multi-Turn': 'Conversations with >1 turns'
    }

    for category, description in task_categories.items():
        print(f"  • {category}: {description}")

    print("\n" + "="*60)
    print("USAGE EXAMPLES")
    print("="*60)

    print("# Use generated datasets for spectral ranking:")
    for dataset in generated_datasets:
        if 'type' in dataset and dataset['type'] == 'full':
            print(f"\n# Full dataset ({dataset['model_count']} models):")
            print("Rscript demo_r/ranking_cli.R \\")
            print("  --csv data_llm/data_arena/data_processing/arena_ranking_full.csv \\")
            print("  --bigbetter 1 --B 2000 --seed 42 \\")
            print("  --out data_llm/data_arena/data_ranking/arena_ranking_full")
        else:
            print(f"\n# Top {dataset['top_n']} models:")
            print("Rscript demo_r/ranking_cli.R \\")
            print(f"  --csv data_llm/data_arena/data_processing/arena_ranking_top{dataset['top_n']}.csv \\")
            print("  --bigbetter 1 --B 2000 --seed 42 \\")
            print(f"  --out data_llm/data_arena/data_ranking/arena_ranking_top{dataset['top_n']}")


if __name__ == "__main__":
    main()
