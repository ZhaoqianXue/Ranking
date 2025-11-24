#!/usr/bin/env python3
"""
Open LLM Leaderboard Results Collector

This script collects the first 7 rows from the open-llm-leaderboard/results dataset
on Hugging Face and saves them for analysis.

Data Source: https://huggingface.co/datasets/open-llm-leaderboard/results
"""

import pandas as pd
import logging
from datetime import datetime
import os
import json
from datasets import load_dataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenLLMResultsCollector:
    """Collector for Open LLM Leaderboard Results dataset (first 7 rows)"""

    def __init__(self):
        self.dataset_name = "open-llm-leaderboard/results"
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        self.output_dir = os.path.join(self.project_root, 'data_llm', 'data_huggingface', 'data_collection')
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_first_7_rows(self):
        """Fetch the first 7 rows from the open-llm-leaderboard/results dataset"""
        try:
            logger.info(f"Loading dataset: {self.dataset_name}")

            # Try to load the dataset - it might have multiple splits or need special handling
            try:
                # First try loading without specifying split
                dataset = load_dataset(self.dataset_name)
                if "train" in dataset:
                    df = dataset["train"].to_pandas()
                elif "default" in dataset:
                    df = dataset["default"].to_pandas()
                else:
                    # If multiple splits, get the first available
                    split_name = list(dataset.keys())[0]
                    df = dataset[split_name].to_pandas()

            except Exception as split_error:
                logger.warning(f"Standard loading failed: {str(split_error)}")
                # Try loading with streaming
                dataset = load_dataset(self.dataset_name, streaming=True)
                if "train" in dataset:
                    # Take first 10 records from stream
                    records = []
                    for i, record in enumerate(dataset["train"]):
                        if i >= 10:
                            break
                        records.append(record)
                    df = pd.DataFrame(records)
                else:
                    split_name = list(dataset.keys())[0]
                    records = []
                    for i, record in enumerate(dataset[split_name]):
                        if i >= 10:
                            break
                        records.append(record)
                    df = pd.DataFrame(records)

            # Get first 10 rows if we have more
            if len(df) > 10:
                first_10_df = df.head(10)
            else:
                first_10_df = df

            logger.info(f"Successfully loaded first {len(first_10_df)} rows from dataset")
            logger.info(f"Total available rows in dataset: {len(df)}")

            return first_10_df

        except Exception as e:
            logger.error(f"Failed to fetch data from {self.dataset_name}: {str(e)}")
            return None

    def save_data(self, df, filename=None):
        """Save the data to CSV and JSON formats"""
        if df is None:
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'open_llm_results_first_7_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Save as CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Data saved to CSV: {filepath}")

            # Also save as JSON for easier reading
            json_filepath = filepath.replace('.csv', '.json')
            df.to_json(json_filepath, orient='records', indent=2)
            logger.info(f"Data saved to JSON: {json_filepath}")

            # Save metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'dataset_name': self.dataset_name,
                'rows_collected': len(df),
                'source': 'https://huggingface.co/datasets/open-llm-leaderboard/results',
                'description': 'First 7 rows from Open LLM Leaderboard Results dataset'
            }

            metadata_filepath = filepath.replace('.csv', '_metadata.json')
            with open(metadata_filepath, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Metadata saved to: {metadata_filepath}")

            return filepath

        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            return None

    def display_data_summary(self, df):
        """Display a summary of the collected data"""
        if df is None or df.empty:
            print("No data to display")
            return

        print(f"\n=== OPEN LLM LEADERBOARD RESULTS - FIRST 10 ROWS ===")
        print(f"Dataset: {self.dataset_name}")
        print(f"Rows collected: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print(f"Collection timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\nFirst 7 rows preview:")
        print(df.head(10).to_string(index=False))

def main():
    """Main function to collect and save the first 7 rows from Open LLM Results dataset"""
    collector = OpenLLMResultsCollector()

    # Fetch first 7 rows
    df = collector.fetch_first_7_rows()
    if df is None:
        logger.error("Failed to fetch data")
        return

    # Save the data
    filepath = collector.save_data(df, 'open_llm_results_first_7.csv')
    if filepath:
        logger.info(f"Successfully saved first 7 rows to {filepath}")

        # Display summary
        collector.display_data_summary(df)

if __name__ == "__main__":
    main()
