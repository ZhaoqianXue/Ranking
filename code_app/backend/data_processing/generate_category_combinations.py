#!/usr/bin/env python3
"""
Generate Category Combinations Script

Reads arena_spectral_full.csv, filters out inactive model columns (all NaN),
and generates all 120 combinations of 2-7 categories from the 7 available categories,
or optionally generates only the 7 individual category files.

Usage:
    python generate_category_combinations.py                    # Generate all combinations (2-7 categories)
    python generate_category_combinations.py --single-only     # Generate only single categories
"""

import os
import itertools
import polars as pl
from pathlib import Path
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_combinations_directory(base_dir: str) -> Path:
    """Create the all_combinations directory if it doesn't exist."""
    combinations_dir = Path(base_dir) / "all_combinations"
    combinations_dir.mkdir(parents=True, exist_ok=True)
    return combinations_dir

def get_category_combinations(categories: list, min_size: int = 2, max_size: int = 7) -> list:
    """Generate all combinations of categories from min_size to max_size."""
    all_combinations = []
    for k in range(min_size, max_size + 1):
        combinations = list(itertools.combinations(sorted(categories), k))
        all_combinations.extend(combinations)
    return all_combinations

def filter_data_by_categories(df: pl.DataFrame, category_list: tuple) -> pl.DataFrame:
    """Filter the dataframe to include only rows where _category is in category_list."""
    return df.filter(pl.col('_category').is_in(category_list))

def save_combination_data(df: pl.DataFrame, combination: tuple, output_dir: Path) -> int:
    """Save a specific category combination to CSV. Returns the number of rows saved."""
    # Create combination name
    combo_name = '_'.join(sorted(combination))

    # Filter data for this combination
    filtered_df = filter_data_by_categories(df, combination)

    if len(filtered_df) == 0:
        logger.warning(f"No data found for combination: {combo_name}")
        return 0

    # Save to CSV
    output_file = output_dir / f"arena_spectral_{combo_name}.csv"
    filtered_df.write_csv(output_file)

    row_count = len(filtered_df)
    logger.info(f"Saved {combo_name}: {row_count} rows")

    return row_count

def save_single_category_data(df: pl.DataFrame, category: str, output_dir: Path) -> int:
    """Save a single category to CSV. Returns the number of rows saved."""
    # Filter data for this single category
    filtered_df = df.filter(pl.col('_category') == category)

    if len(filtered_df) == 0:
        logger.warning(f"No data found for category: {category}")
        return 0

    # Save to CSV (single category uses just the category name)
    output_file = output_dir / f"arena_spectral_{category}.csv"
    filtered_df.write_csv(output_file)

    row_count = len(filtered_df)
    logger.info(f"Saved {category}: {row_count} rows")

    return row_count

def filter_active_model_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Filter out columns that are entirely NaN (inactive models)."""
    # Get all columns except _category
    model_columns = [col for col in df.columns if col != '_category']

    # Find columns that have at least one non-null and non-NaN value
    active_columns = ['_category']  # Always keep _category
    removed_columns = []

    for col in model_columns:
        # Check if column has any finite (non-null, non-NaN) values
        has_finite_data = df.select(pl.col(col).is_finite().any()).to_series()[0]
        if has_finite_data:
            active_columns.append(col)
        else:
            removed_columns.append(col)

    if removed_columns:
        logger.info(f"Removed inactive model columns: {removed_columns}")

    logger.info(f"Kept {len(active_columns)-1} active model columns out of {len(model_columns)} total model columns")

    return df.select(active_columns)

def main():
    """Main function to generate category combinations or single categories."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate category combinations or single categories from arena spectral data.')
    parser.add_argument('--single-only', action='store_true',
                        help='Generate only single category files instead of all combinations')
    args = parser.parse_args()

    # Define paths
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent.parent.parent / "data_llm" / "data_arena" / "data_processing"
    input_file = data_dir / "arena_spectral_full.csv"

    # Create output directory
    output_dir = create_combinations_directory(data_dir)

    # Load data
    logger.info(f"Loading data from {input_file}")
    df = pl.read_csv(input_file)

    # Filter out inactive model columns (all NaN)
    df = filter_active_model_columns(df)

    # Get unique categories
    categories = df['_category'].unique().sort().to_list()
    logger.info(f"Found {len(categories)} categories: {categories}")

    total_rows = 0

    if args.single_only:
        # Generate only single category files
        logger.info("Generating single category files...")

        for category in categories:
            rows_saved = save_single_category_data(df, category, output_dir)
            total_rows += rows_saved

        # Final summary for single categories
        logger.info("\n=== Single Category Generation Complete ===")
        logger.info(f"Total single categories generated: {len(categories)}")
        logger.info(f"Total rows across all files: {total_rows}")
        logger.info(f"Output directory: {output_dir}")
    else:
        # Generate all combinations (2-7 categories)
        combinations = get_category_combinations(categories, min_size=2, max_size=7)
        logger.info(f"Generating {len(combinations)} combinations (2-7 categories)")

        # Process each combination
        for i, combination in enumerate(combinations, 1):
            if i % 20 == 0 or i == len(combinations):
                logger.info(f"Processing combination {i}/{len(combinations)}")

            rows_saved = save_combination_data(df, combination, output_dir)
            total_rows += rows_saved

        # Final summary
        logger.info("\n=== Generation Complete ===")
        logger.info(f"Total combinations generated: {len(combinations)}")
        logger.info(f"Total rows across all files: {total_rows}")
        logger.info(f"Output directory: {output_dir}")

if __name__ == "__main__":
    main()