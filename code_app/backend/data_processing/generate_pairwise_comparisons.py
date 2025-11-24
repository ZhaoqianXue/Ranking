import pandas as pd
import itertools
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_pairwise_matrix(input_file, output_file):
    """
    Converts a benchmark-vs-model score matrix into a wide-format pairwise
    comparison matrix suitable for ranking_cli.R, similar to arena_spectral_full.csv.

    Args:
        input_file (str): Path to the input CSV where rows are benchmarks
                          and columns are models.
        output_file (str): Path to save the resulting matrix CSV file.
    """
    try:
        logger.info(f"Loading data from {input_file}...")
        df = pd.read_csv(input_file, index_col=0)
        logger.info(f"Loaded data with shape: {df.shape}")
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        return

    models = df.columns.tolist()
    benchmarks = df.index.tolist()
    
    all_pairwise_rows = []

    logger.info("Generating wide-format pairwise comparison matrix...")
    # 1. Iterate through each benchmark (row), treating it as a context for comparisons.
    for benchmark in benchmarks:
        scores = df.loc[benchmark]
        
        # 2. Generate all unique pairs of models for comparison.
        for model_a, model_b in itertools.combinations(models, 2):
            score_a = scores.get(model_a)
            score_b = scores.get(model_b)

            # Skip if either score is missing or if it's a tie.
            if pd.isna(score_a) or pd.isna(score_b) or score_a == score_b:
                continue

            # Create a new row representing this single pairwise comparison.
            new_row = {'benchmark': benchmark}

            # Initialize all model columns to NaN.
            for model in models:
                new_row[model] = pd.NA

            # 3. Assign 1 for winner, 0 for loser.
            if score_a > score_b:
                new_row[model_a] = 1  # Winner
                new_row[model_b] = 0  # Loser
            else:  # score_b > score_a
                new_row[model_a] = 0  # Loser
                new_row[model_b] = 1  # Winner
            
            all_pairwise_rows.append(new_row)

    # 4. Create the final DataFrame from the list of rows.
    if not all_pairwise_rows:
        logger.warning("No pairwise comparisons were generated. The output file will be empty.")
        # Create an empty df with correct columns to avoid errors
        pairwise_df = pd.DataFrame(columns=['benchmark'] + models)
    else:
        pairwise_df = pd.DataFrame(all_pairwise_rows)

    # Ensure column order is consistent: benchmark column first, then model columns.
    cols = ['benchmark'] + models
    pairwise_df = pairwise_df[cols]

    logger.info(f"Generated a total of {len(pairwise_df)} pairwise comparison rows.")
    
    # Save the file. The R script will treat each row as a sample.
    pairwise_df.to_csv(output_file, index=False, na_rep='NaN')
    logger.info(f"Processing complete. Output saved to {output_file}")

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    data_processing_dir = os.path.join(project_root, 'data_llm', 'data_huggingface', 'data_processing')
    
    input_csv = os.path.join(data_processing_dir, 'llm_ranking_top50.csv')
    output_csv = os.path.join(data_processing_dir, 'llm_pairwise_aggregated_top50.csv')
    
    generate_pairwise_matrix(input_csv, output_csv)
