#!/usr/bin/env python3
"""
LLM Data Collector for Open LLM Leaderboard

This script collects LLM performance data from Hugging Face's Open LLM Leaderboard
and prepares it for spectral ranking analysis.

Data Source: https://huggingface.co/datasets/open-llm-leaderboard/contents
"""

import pandas as pd
import requests
import logging
from datetime import datetime
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMDataCollector:
    """Collector for LLM performance data from Open LLM Leaderboard"""

    def __init__(self):
        self.dataset_name = "open-llm-leaderboard/contents"
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_collection')
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_leaderboard_data(self):
        """Fetch the latest leaderboard data from Hugging Face using direct download"""
        try:
            # Direct download URL for the parquet file
            parquet_url = "https://huggingface.co/datasets/open-llm-leaderboard/contents/resolve/main/data/train-00000-of-00001.parquet"

            logger.info(f"Downloading data from: {parquet_url}")

            # Download the parquet file
            response = requests.get(parquet_url, timeout=60)
            response.raise_for_status()

            # Save temporarily and read with pandas
            temp_file = os.path.join(self.output_dir, 'temp_leaderboard.parquet')
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            # Read parquet file
            df = pd.read_parquet(temp_file)

            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

            logger.info(f"Loaded {len(df)} records from leaderboard")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch leaderboard data: {str(e)}")
            return None

    def clean_and_prepare_data(self, df):
        """Clean and prepare the data for spectral ranking"""
        if df is None or df.empty:
            return None

        try:
            # Select relevant benchmark columns
            benchmark_columns = [
                'IFEval', 'BBH', 'MATH Lvl 5', 'GPQA', 'MUSR', 'MMLU-PRO'
            ]

            # Filter out rows with missing benchmark data
            df_clean = df.dropna(subset=benchmark_columns, how='all').copy()

            # Create a simplified dataframe with essential columns
            result_df = pd.DataFrame({
                'model': df_clean['fullname'],
                'model_link': df_clean['Model'],  # Keep HTML link for reference
                'ifeval': df_clean['IFEval'],
                'bbh': df_clean['BBH'],
                'math': df_clean['MATH Lvl 5'],
                'gpqa': df_clean['GPQA'],
                'musr': df_clean['MUSR'],
                'mmlu_pro': df_clean['MMLU-PRO'],
                'average_score': df_clean['Average ⬆️'],
                'params_b': df_clean['#Params (B)'],
                'architecture': df_clean['Architecture'],
                'precision': df_clean['Precision'],
                'type': df_clean['Type'],
                'submission_date': df_clean['Submission Date'],
                'base_model': df_clean['Base Model']
            })

            # Remove rows with all NaN benchmark scores
            result_df = result_df.dropna(subset=['ifeval', 'bbh', 'math', 'gpqa', 'musr', 'mmlu_pro'], how='all')

            # Sort by average score (descending)
            result_df = result_df.sort_values('average_score', ascending=False)

            logger.info(f"Prepared {len(result_df)} models with benchmark data")
            return result_df

        except Exception as e:
            logger.error(f"Failed to clean data: {str(e)}")
            return None

    def save_data(self, df, filename=None):
        """Save the prepared data to CSV"""
        if df is None:
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'llm_leaderboard_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Data saved to: {filepath}")

            # Also save metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'total_models': len(df),
                'benchmarks': ['ifeval', 'bbh', 'math', 'gpqa', 'musr', 'mmlu_pro'],
                'source': 'https://huggingface.co/datasets/open-llm-leaderboard/contents'
            }

            metadata_filepath = filepath.replace('.csv', '_metadata.json')
            with open(metadata_filepath, 'w') as f:
                json.dump(metadata, f, indent=2)

            return filepath

        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            return None

    def get_top_models_data(self, top_n=50):
        """Get data for top N models formatted for spectral ranking"""
        df = self.fetch_leaderboard_data()
        if df is None:
            return None

        df_clean = self.clean_and_prepare_data(df)
        if df_clean is None:
            return None

        # Select top N models
        top_df = df_clean.head(top_n).copy()

        # Create benchmark-only dataframe for ranking
        benchmark_df = top_df[['ifeval', 'bbh', 'math', 'gpqa', 'musr', 'mmlu_pro']].copy()

        # Add model names as index
        benchmark_df.index = top_df['model']

        return benchmark_df

def main():
    """Main function to collect and save LLM data"""
    collector = LLMDataCollector()

    # Fetch raw data
    raw_df = collector.fetch_leaderboard_data()
    if raw_df is None:
        logger.error("Failed to fetch data")
        return

    # Clean and prepare data for analysis
    clean_df = collector.clean_and_prepare_data(raw_df)
    if clean_df is None:
        logger.error("Failed to clean data")
        return

    # Save cleaned data
    clean_filepath = collector.save_data(clean_df, 'llm_leaderboard_cleaned.csv')
    if clean_filepath:
        logger.info(f"Successfully saved cleaned LLM data to {clean_filepath}")

        # Display cleaned data summary
        print(f"\n=== CLEANED DATA SUMMARY ===")
        print(f"Total models: {len(clean_df)}")
        print(f"Date range: {clean_df['submission_date'].min()} to {clean_df['submission_date'].max()}")
        print(f"Top model: {clean_df.iloc[0]['model']}")
        print(".2f")

if __name__ == "__main__":
    main()
