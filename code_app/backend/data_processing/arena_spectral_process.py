#!/usr/bin/env python3
"""
Prepare Arena Human Preference Data for Spectral Analysis (Polars Version)

This script transforms the collected Arena human preference data into the format
for spectral analysis, using Polars for high-performance data processing.

Input format:
- Rows: Individual preference votes (136K+ records)
- Columns: model_a, model_b, winner, conversation data, metadata

Output format:
- Rows: Individual comparison instances
- Columns: Models
- Values: 1.0 (winner), 0.0 (loser), NaN (not involved)
- Filtered out: ties, both_bad cases, and general category

Key Features:
- Uses Polars for high-performance data processing
- Filters out ambiguous comparisons (ties, both_bad)
- Excludes general category, keeps only 7 benchmark categories
- Generates arena_spectral_full.csv and arena_spectral_full_metadata.json
- Ready for spectral ranking analysis
"""

import polars as pl
import numpy as np
import os
import json
import logging
import ast
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# CONFIGURATION SECTION
# ===============================
# Only generate the full dataset (filtered to exclude general category)
# ===============================

class ArenaSpectralPreparer:
    """Prepare Arena data for spectral ranking with preserved pairwise comparisons"""

    def __init__(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.input_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_collection')
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_processing')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_arena_data(self, sample_size=None, use_full_data=True):
        """Load Arena human preference data"""
        if use_full_data:
            input_file = os.path.join(self.input_dir, 'arena_human_preference_full.csv')
        else:
            input_file = os.path.join(self.input_dir, 'arena_human_preference_sample_10000.csv')

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Arena data file not found: {input_file}")

        logger.info(f"Loading Arena data from: {input_file}")
        df = pl.read_csv(input_file)

        if sample_size and len(df) > sample_size:
            logger.info(f"Sampling {sample_size} records from {len(df)} total")
            df = df.sample(n=sample_size, seed=42)

        logger.info(f"Loaded {len(df)} Arena comparison records")
        return df

    def get_all_models(self, df):
        """Extract all unique models from the dataset"""
        models_a = set(df['model_a'].unique().to_list())
        models_b = set(df['model_b'].unique().to_list())
        all_models = sorted(list(models_a.union(models_b)))
        logger.info(f"Found {len(all_models)} unique models")
        return all_models


    def create_spectral_dataset(self, df, all_models, dataset_name="full", chunk_size=10000):
        """
        Create spectral ranking dataset from Arena comparisons using streaming processing.
        Each comparison that belongs to multiple categories will be duplicated for each category.

        Args:
            df: Arena dataframe
            all_models: List of all models
            dataset_name: Name for the dataset
            chunk_size: Size of chunks to process at once

        Returns:
            pl.DataFrame: Spectral ranking format with expanded categories
        """
        logger.info(f"Creating spectral dataset '{dataset_name}' with {len(df)} comparisons using streaming processing")

        # First, filter out invalid winner types
        valid_winners = ['model_a', 'model_b']
        filtered_df = df.filter(pl.col('winner').is_in(valid_winners))

        filtered_count = len(df) - len(filtered_df)
        logger.info(f"Filtered out {filtered_count} comparisons (ties, both_bad, or unknown winners)")

        if len(filtered_df) == 0:
            raise ValueError("No valid comparisons remaining after filtering")

        # Process in chunks to avoid memory overflow
        expanded_rows = []
        total_processed = 0
        benchmark_categories = ['creative_writing', 'math', 'instruction_following',
                               'coding', 'hard_prompt', 'longer_query', 'multi_turn']

        for start_idx in range(0, len(filtered_df), chunk_size):
            end_idx = min(start_idx + chunk_size, len(filtered_df))
            chunk = filtered_df.slice(start_idx, end_idx - start_idx)

            logger.info(f"Processing chunk {start_idx//chunk_size + 1}: rows {start_idx} to {end_idx-1}")

            # Create spectral columns for this chunk
            def create_model_column(model):
                return (
                    pl.when((pl.col('winner') == 'model_a') & (pl.col('model_a') == model))
                    .then(1.0)
                    .when((pl.col('winner') == 'model_a') & (pl.col('model_b') == model))
                    .then(0.0)
                    .when((pl.col('winner') == 'model_b') & (pl.col('model_b') == model))
                    .then(1.0)
                    .when((pl.col('winner') == 'model_b') & (pl.col('model_a') == model))
                    .then(0.0)
                    .otherwise(float('nan'))
                )

            spectral_data = {model: create_model_column(model) for model in all_models}
            spectral_chunk = chunk.with_columns(**spectral_data)

            # Extract categories and expand for this chunk
            categories_list = self.extract_all_categories_vectorized(chunk)

            for i, row in enumerate(spectral_chunk.to_dicts()):
                categories = categories_list[i]
                valid_categories = [cat for cat in categories if cat in benchmark_categories]

                if not valid_categories:
                    continue

                # Create one row for each valid category
                for category in valid_categories:
                    new_row = row.copy()
                    new_row['_category'] = category
                    expanded_rows.append(new_row)

            total_processed += len(chunk)

            # Clear memory by processing accumulated rows if they get too large
            if len(expanded_rows) > 50000:  # Process in batches of 50k expanded rows
                logger.info(f"Processing accumulated {len(expanded_rows)} expanded rows...")
                if expanded_rows:
                    temp_df = pl.DataFrame(expanded_rows[:50000])
                    keep_columns = all_models + ['_category']
                    temp_df = temp_df.select(keep_columns)

                    # Save to temporary file and clear memory
                    temp_file = f"/tmp/spectral_chunk_{start_idx//chunk_size}.parquet"
                    temp_df.write_parquet(temp_file)
                    expanded_rows = expanded_rows[50000:]

        # Process any remaining rows
        if expanded_rows:
            logger.info(f"Processing final {len(expanded_rows)} expanded rows...")
            temp_df = pl.DataFrame(expanded_rows)
            keep_columns = all_models + ['_category']
            temp_df = temp_df.select(keep_columns)

            temp_file = f"/tmp/spectral_final.parquet"
            temp_df.write_parquet(temp_file)

        # Combine all chunks
        logger.info("Combining all processed chunks...")
        import glob
        chunk_files = glob.glob("/tmp/spectral_chunk_*.parquet") + ["/tmp/spectral_final.parquet"]

        if not chunk_files:
            raise ValueError("No data chunks were created")

        # Read and combine all chunks
        dfs = []
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file):
                dfs.append(pl.read_parquet(chunk_file))
                os.remove(chunk_file)  # Clean up

        if not dfs:
            raise ValueError("No valid data chunks found")

        expanded_df = pl.concat(dfs, how='vertical')

        logger.info(f"Expanded data to include all category memberships")
        logger.info(f"Created spectral dataset: {expanded_df.shape[0]} rows x {expanded_df.shape[1]} columns")
        return expanded_df

    def extract_all_categories_vectorized(self, df):
        """
        Extract ALL categories that each comparison belongs to.
        Returns a list of category lists, where each inner list contains all categories for that row.
        Supports all 7 Arena benchmark categories.
        """
        def extract_categories(row):
            try:
                # Parse category_tag
                category_tag_str = row['category_tag']
                if isinstance(category_tag_str, str):
                    import ast
                    category_tag = ast.literal_eval(category_tag_str)
                else:
                    category_tag = category_tag_str

                # Parse conv_metadata
                conv_metadata_str = row['conv_metadata']
                if isinstance(conv_metadata_str, str):
                    conv_metadata = ast.literal_eval(conv_metadata_str)
                else:
                    conv_metadata = conv_metadata_str

                is_code = row['is_code']

                # Check all categories (no priority order - collect all that match)
                matching_categories = []

                # 1. Coding
                if is_code:
                    matching_categories.append('coding')

                # 2. Creative Writing
                try:
                    if category_tag.get('creative_writing_v0.1', {}).get('creative_writing', False):
                        matching_categories.append('creative_writing')
                except:
                    pass

                # 3. Math
                try:
                    if category_tag.get('math_v0.1', {}).get('math', False):
                        matching_categories.append('math')
                except:
                    pass

                # 4. Instruction Following
                try:
                    if category_tag.get('if_v0.1', {}).get('if', False):
                        matching_categories.append('instruction_following')
                except:
                    pass

                # 5. Hard Prompt
                try:
                    if self._is_hard_prompt(category_tag):
                        matching_categories.append('hard_prompt')
                except:
                    pass

                # 6. Longer Query
                try:
                    if conv_metadata.get('sum_user_tokens', 0) > 500:
                        matching_categories.append('longer_query')
                except:
                    pass

                # 7. Multi-Turn
                try:
                    if conv_metadata.get('turns', 1) > 1:
                        matching_categories.append('multi_turn')
                except:
                    pass

                # If no categories matched, assign 'general'
                if not matching_categories:
                    matching_categories.append('general')

                return matching_categories
            except Exception as e:
                return ['general']

        # Apply the function to each row
        all_categories = []
        for row in df.to_dicts():
            categories = extract_categories(row)
            all_categories.append(categories)

        return all_categories

    def _is_hard_prompt(self, category_tag):
        """Check if this is a hard prompt (satisfies >=6 criteria)"""
        try:
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
            return hard_score >= 6
        except:
            return False


    def save_dataset(self, spectral_df, dataset_name, metadata):
        """Save spectral dataset and metadata"""
        # Save CSV
        csv_file = os.path.join(self.output_dir, f'arena_spectral_{dataset_name}.csv')
        spectral_df.write_csv(csv_file)
        logger.info(f"Saved spectral dataset to: {csv_file}")

        # Save metadata
        metadata_file = os.path.join(self.output_dir, f'arena_spectral_{dataset_name}_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved metadata to: {metadata_file}")

        return csv_file, metadata_file

    def prepare_all_datasets(self):
        """Prepare all configured datasets"""
        logger.info("Starting Arena spectral data preparation")

        # Load full dataset
        df = self.load_arena_data()
        all_models = self.get_all_models(df)

        # Create full spectral dataset
        spectral_df = self.create_spectral_dataset(df, all_models, 'full')

        # Calculate model counts by stacking model_a and model_b columns
        all_models_series = pl.concat([
            df.select('model_a').rename({'model_a': 'model'}),
            df.select('model_b').rename({'model_b': 'model'})
        ])
        all_model_counts = all_models_series.group_by('model').len().sort('len', descending=True)
        model_counts_dict = dict(zip(all_model_counts['model'].to_list()[:10], all_model_counts['len'].to_list()[:10]))

        metadata = {
            'dataset_type': 'full',
            'n_comparisons': len(df),
            'n_models': len(all_models),
            'matrix_shape': spectral_df.shape,
            'created_at': datetime.now(),
            'winner_distribution': {'total_comparisons': len(df)},
            'model_counts': model_counts_dict
        }

        csv_file, metadata_file = self.save_dataset(spectral_df, 'full', metadata)

        logger.info("Arena spectral data preparation completed")

        return {
            'csv': csv_file,
            'metadata': metadata_file,
            'shape': spectral_df.shape
        }

def main():
    """Main execution function"""
    try:
        preparer = ArenaSpectralPreparer()
        summary = preparer.prepare_all_datasets()

        print("\n" + "="*60)
        print("ARENA SPECTRAL DATA PREPARATION COMPLETED")
        print("="*60)
        print(json.dumps(summary, indent=2, default=str))

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise

if __name__ == "__main__":
    main()
