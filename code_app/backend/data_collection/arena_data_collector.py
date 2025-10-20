#!/usr/bin/env python3
"""
Arena Human Preference Data Collector

This script collects human preference data from Hugging Face's LMArena Arena dataset
and prepares it for analysis. This dataset contains user votes comparing different LLM models.

Data Source: https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k
"""

import pandas as pd
import requests
import logging
import ast
from datetime import datetime
import os
import json
from datasets import load_dataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# CONFIGURATION SECTION
# ===============================
# Data collection settings
COLLECT_ALL_DATA = True  # Set to True to collect all available data, False to collect limited rows
LIMIT_ROWS = 10000         # Number of rows to collect when COLLECT_ALL_DATA is False
#
# Usage examples:
# - For exploration: COLLECT_ALL_DATA = False, LIMIT_ROWS = 1000
# - For full analysis: COLLECT_ALL_DATA = True (may take longer)
# ===============================

class ArenaDataCollector:
    """Collector for human preference data from LMArena Arena dataset"""

    def __init__(self):
        self.dataset_name = "lmarena-ai/arena-human-preference-140k"
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_arena', 'data_collection')
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_arena_data(self, limit_rows=None):
        """Fetch the latest arena preference data from Hugging Face"""
        try:
            logger.info(f"Trying to load dataset '{self.dataset_name}' from Hugging Face Hub...")
            dataset = load_dataset(self.dataset_name, split="train")

            # Convert to pandas DataFrame
            df = dataset.to_pandas()

            # Limit rows if specified (for exploration)
            if limit_rows:
                df = df.head(limit_rows)
                logger.info(f"Limited to first {limit_rows} rows for exploration")

            logger.info(f"Successfully loaded {len(df)} records from arena dataset using Hugging Face datasets library.")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch arena data using Hugging Face datasets library: {str(e)}")
            return None

    def explore_data_structure(self, df):
        """Explore and analyze the data structure"""
        if df is None or df.empty:
            return None

        try:
            analysis = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': list(df.columns),
                'column_types': {},
                'missing_values': {},
                'unique_models_a': None,
                'unique_models_b': None,
                'winner_distribution': None,
            }

            # Safely get column types and missing values
            for col in df.columns:
                analysis['column_types'][col] = str(df[col].dtype)
                analysis['missing_values'][col] = int(df[col].isnull().sum())

            # Safely get model counts
            if 'model_a' in df.columns:
                analysis['unique_models_a'] = int(df['model_a'].nunique())
            if 'model_b' in df.columns:
                analysis['unique_models_b'] = int(df['model_b'].nunique())

            # Safely get winner distribution
            if 'winner' in df.columns:
                analysis['winner_distribution'] = df['winner'].value_counts().to_dict()

            # Sample first few rows for inspection
            try:
                analysis['sample_rows'] = df.head(5).to_dict('records')
            except:
                analysis['sample_rows'] = "Unable to convert sample rows"

            # Check for conversation data
            if 'conversation_a' in df.columns:
                first_conv = df['conversation_a'].iloc[0] if len(df) > 0 else ""
                if isinstance(first_conv, str) and len(first_conv) > 500:
                    analysis['conversation_sample'] = first_conv[:500] + "..."
                else:
                    analysis['conversation_sample'] = str(first_conv)

            logger.info("Data structure analysis completed")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze data structure: {str(e)}")
            logger.error(f"DataFrame info: shape={df.shape}, columns={list(df.columns)}")
            return None

    def save_exploration_data(self, df, analysis, filename=None):
        """Save the exploration data to CSV and metadata"""
        if df is None:
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'arena_human_preference_exploration_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Save the raw data
            df.to_csv(filepath, index=False)
            logger.info(f"Exploration data saved to: {filepath}")

            # Save metadata with analysis
            if COLLECT_ALL_DATA:
                description = 'Arena Human Preference Dataset - Full dataset'
            else:
                description = f'Arena Human Preference Dataset - First {LIMIT_ROWS} rows for exploration'

            metadata = {
                'timestamp': datetime.now().isoformat(),
                'source_dataset': self.dataset_name,
                'total_rows': len(df),
                'data_analysis': analysis,
                'description': description,
                'collection_config': {
                    'collect_all_data': COLLECT_ALL_DATA,
                    'limit_rows': LIMIT_ROWS
                }
            }

            metadata_filepath = filepath.replace('.csv', '_metadata.json')
            with open(metadata_filepath, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)  # default=str to handle datetime

            return filepath

        except Exception as e:
            logger.error(f"Failed to save exploration data: {str(e)}")
            return None


def main():
    """Main function to collect and explore arena data"""
    collector = ArenaDataCollector()

    # Determine collection parameters based on configuration
    if COLLECT_ALL_DATA:
        limit_rows = None
        logger.info("Starting Arena Human Preference data collection...")
        logger.info("Collecting ALL available data...")
    else:
        limit_rows = LIMIT_ROWS
        logger.info("Starting Arena Human Preference data collection...")
        logger.info(f"Collecting first {LIMIT_ROWS} rows for data exploration...")

    raw_df = collector.fetch_arena_data(limit_rows=limit_rows)
    if raw_df is None:
        logger.error("Failed to fetch data")
        return

    # Analyze data structure
    analysis = collector.explore_data_structure(raw_df)
    if analysis is None:
        logger.error("Failed to analyze data")
        return

    # Save exploration data
    if COLLECT_ALL_DATA:
        filename = 'arena_human_preference_full.csv'
    else:
        filename = f'arena_human_preference_sample_{LIMIT_ROWS}.csv'

    saved_path = collector.save_exploration_data(raw_df, analysis, filename)
    if saved_path:
        logger.info(f"Successfully saved exploration data to {saved_path}")

        # Display summary
        print("\n" + "="*80)
        print("ARENA HUMAN PREFERENCE DATASET - EXPLORATION SUMMARY")
        print("="*80)
        print(f"Dataset: {collector.dataset_name}")
        print(f"Rows collected: {len(raw_df)}")
        print(f"Columns: {len(raw_df.columns)}")
        print(f"Columns: {', '.join(raw_df.columns.tolist())}")

        print("\nData Analysis:")
        print(f"- Total rows: {analysis['total_rows']}")
        print(f"- Unique models in column A: {analysis.get('unique_models_a', 'N/A')}")
        print(f"- Unique models in column B: {analysis.get('unique_models_b', 'N/A')}")

        if analysis.get('winner_distribution'):
            print(f"- Winner distribution: {analysis['winner_distribution']}")

        print("\nSample Data Preview:")
        for i, row in enumerate(analysis['sample_rows'][:3]):
            print(f"Row {i+1}: model_a='{row.get('model_a', 'N/A')}', model_b='{row.get('model_b', 'N/A')}', winner='{row.get('winner', 'N/A')}'")

        print(f"\nFull data saved to: {saved_path}")
        print("Metadata saved to: " + saved_path.replace('.csv', '_metadata.json'))


if __name__ == "__main__":
    main()