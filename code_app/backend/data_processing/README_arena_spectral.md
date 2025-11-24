# Arena Spectral Processing Script

## Overview

`arena_spectral_process.py` is a new script that properly processes Arena human preference data for spectral ranking analysis. Unlike previous approaches that aggregated data into win rates, this script preserves all original pairwise comparisons.

## Key Features

- **Preserves Raw Comparisons**: Converts each Arena record into a spectral ranking row
- **Supports Heterogeneous Graphs**: Leverages spectral ranking's native support for pairwise comparisons
- **Complete Category Support**: Implements all 7 Arena benchmark categories for fine-grained analysis
- **Multiple Dataset Sizes**: Generates full, top50, and top100 model datasets
- **Statistical Integrity**: Maintains all 10,000+ comparison instances

## Input Format

The script reads from:
```
data_llm/data_arena/data_collection/arena_human_preference_sample_10000.csv
```

Expected columns:
- `model_a`, `model_b`: Models being compared
- `winner`: Result ('model_a', 'model_b', 'tie', 'both_bad')
- `id`, `timestamp`: Metadata for tracking
- `category_tag`: For future category-specific analysis

## Supported Benchmark Categories

The script implements all 7 Arena benchmark categories for fine-grained performance analysis:

| Category | Description | Detection Logic |
|----------|-------------|----------------|
| **Creative Writing** | Original content creation with imagination | `category_tag['creative_writing_v0.1']['creative_writing'] == True` |
| **Math** | Mathematical reasoning and problem solving | `category_tag['math_v0.1']['math'] == True` |
| **Instruction Following** | Precise adherence to given instructions | `category_tag['if_v0.1']['if'] == True` |
| **Coding** | Code understanding, generation, and debugging | `is_code == True` |
| **Hard Prompt** | Complex prompts requiring multiple skills | ≥6 criteria from specificity, domain knowledge, complexity, etc. |
| **Longer Query** | Extended queries (>500 tokens) | `conv_metadata['sum_user_tokens'] > 500` |
| **Multi-Turn** | Multi-round conversations | `conv_metadata['turns'] > 1` |

### Category Distribution Example (10K sample)

Based on the processed data, here's the typical distribution of categories:

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **General** | 3,669 | 36.7% | Unclassified comparisons |
| **Coding** | 1,975 | 19.8% | Code-related tasks |
| **Instruction Following** | 1,398 | 14.0% | Following specific instructions |
| **Hard Prompt** | 867 | 8.7% | Complex multi-skill prompts |
| **Creative Writing** | 855 | 8.6% | Creative content generation |
| **Math** | 805 | 8.1% | Mathematical reasoning |
| **Multi-Turn** | 369 | 3.7% | Multi-round conversations |
| **Longer Query** | 62 | 0.6% | Extended queries (>500 tokens) |

## Output Format

Generates spectral ranking compatible CSV files:

### Row Structure
- **Columns 1-52**: Model scores (1.0 = winner, 0.0 = loser, 0.5 = tie, NaN = not involved)
- **Column 53**: `_category` - Primary category (supports all 7 Arena benchmark categories)

### Example Row
```csv
claude-opus-4-20250514,gemini-2.5-flash,...,NaN,NaN,...,1.0,0.0,...,math
```
This represents: claude-opus-4-20250514 won against gemini-2.5-flash in a math-related comparison.

## Generated Datasets

1. **arena_spectral_full.csv**: All 10,000 comparisons, all 52 models
   - Shape: 10,000 rows × 53 columns (52 models + 1 category)
   - Best for comprehensive analysis

2. **arena_spectral_top50.csv**: Top 50 most active models
   - Shape: ~9,941 rows × 51 columns (50 models + 1 category)
   - Balanced performance and speed

3. **arena_spectral_top100.csv**: Top 100 most active models
   - Shape: 10,000 rows × 53 columns (52 models + 1 category)
   - Maximum coverage

## Usage

### Basic Usage
```bash
cd code_app/backend/data_processing
python3 arena_spectral_process.py
```

### Integration with Spectral Ranking
```bash
# Run spectral ranking on the processed data
Rscript demo_r/ranking_cli.R \
  --csv data_llm/data_arena/data_spectral/arena_spectral_top50.csv \
  --bigbetter 1 \
  --B 2000 \
  --seed 42 \
  --out results/arena_spectral_top50/
```

## Advantages Over Win Rate Aggregation

| Aspect | Win Rate Aggregation | Spectral Direct Processing |
|--------|---------------------|---------------------------|
| **Information Loss** | High (loses specific comparisons) | None (preserves all comparisons) |
| **Statistical Power** | Reduced | Full (10K+ observations) |
| **Algorithm Fit** | Poor (not designed for aggregated data) | Excellent (designed for comparison graphs) |
| **Category Analysis** | Limited | Possible (metadata preserved) |
| **Bootstrap Stability** | Lower | Higher (more observations) |

## Configuration

Edit the script to customize:

```python
# Specify which datasets to generate
DATASETS_TO_GENERATE = ['full', 'top50', 'top100']
```

## Output Files

All outputs are saved to:
```
data_llm/data_arena/data_spectral/
├── arena_spectral_full.csv & _metadata.json
├── arena_spectral_top50.csv & _metadata.json
├── arena_spectral_top100.csv & _metadata.json
└── arena_spectral_summary.json
```

## Expected Performance

Based on testing with 10,000 comparisons:

| Dataset | Matrix Size | Spectral Ranking Time |
|---------|-------------|----------------------|
| Full | 10,000 × 55 | ~2-3 minutes (B=2000) |
| Top 50 | 9,941 × 53 | ~1-2 minutes (B=2000) |
| Top 100 | 10,000 × 55 | ~2-3 minutes (B=2000) |

## Next Steps

1. **Run Spectral Analysis**: Use the generated CSV files with `ranking_cli.R`
2. **Compare Results**: Compare with win rate based rankings
3. **Category Analysis**: Implement category-specific filtering
4. **Scale Up**: Process full 136K Arena dataset when needed

## Technical Notes

- Uses NaN for uninvolved models (spectral ranking handles sparse matrices)
- Winner encoding: 1.0/0.0 for clear wins, 0.5/0.5 for ties
- Metadata columns help with result interpretation and filtering
- Bootstrap iterations (B) can be adjusted based on desired precision
