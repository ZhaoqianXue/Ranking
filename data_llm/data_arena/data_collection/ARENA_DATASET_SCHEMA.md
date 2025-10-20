# Arena Human Preference Dataset Schema Documentation

## Dataset Overview

**Dataset Name**: `lmarena-ai/arena-human-preference-140k`
**Source**: Hugging Face Datasets
**Purpose**: Human preference voting data comparing different LLM models in conversational scenarios
**Total Records**: 136,634 (sampled 100 for exploration)
**Data Format**: Parquet/CSV

## Schema Structure

### Core Fields (14 columns)

| Field Name | Data Type | Description | Example | Null Count | Notes |
|------------|-----------|-------------|---------|------------|-------|
| `id` | `string` | Unique identifier for each preference vote | `c4b9710c-8d64-4bee-a0b0-94637ae4cc65` | 0 | UUID format |
| `model_a` | `string` | First model being compared | `gemini-2.5-pro` | 0 | Model identifier |
| `model_b` | `string` | Second model being compared | `claude-3-7-sonnet-20250219-thinking-32k` | 0 | Model identifier |
| `winner` | `string` | Voting result | `model_a` | 0 | Values: `model_a`, `model_b`, `tie`, `both_bad` |
| `evaluation_session_id` | `string` | Session identifier for evaluation batch | `a333a685-37f9-474d-b703-f079d8329552` | 0 | UUID format |
| `evaluation_order` | `int64` | Order within the evaluation session | `1` | 0 | Integer, typically 1-3 |
| `conversation_a` | `object` | Complete conversation with model_a's responses | `[{'role': 'user', 'content': [{'type': 'text', 'text': '...'}` | 0 | JSON array of conversation turns |
| `conversation_b` | `object` | Complete conversation with model_b's responses | `[{'role': 'user', 'content': [{'type': 'text', 'text': '...'}` | 0 | JSON array of conversation turns |
| `full_conversation` | `object` | Combined conversation history | `[{'user': {...}, 'model_side_a': {...}, 'model_side_b': {...}}]` | 0 | JSON array with full context |
| `conv_metadata` | `object` | Conversation metadata and statistics | `{'sum_assistant_a_tokens': 1854, 'header_count_a': {...}}` | 0 | Token counts, formatting stats |
| `category_tag` | `object` | Content category annotation | `{'creative_writing_v0.1': {'creative_writing': False, 'score': 'no'}}` | 0 | JSON object with category scores |
| `language` | `string` | Primary language of conversation | `en` | 0 | Language code (en, pl, de, etc.) |
| `is_code` | `bool` | Whether conversation involves code | `False` | 0 | Boolean flag |
| `timestamp` | `string` | Evaluation timestamp | `2025-05-29T14:48:41.602925` | 0 | ISO format datetime |

## Data Types and Constraints

### String Fields
- **UUID Fields**: `id`, `evaluation_session_id` - Standard UUID format
- **Model Names**: `model_a`, `model_b` - Various formats (e.g., `gemini-2.5-pro`, `claude-3-5-haiku-20241022`)
- **Winner Values**: `winner` - Categorical: `['model_a', 'model_b', 'tie', 'both_bad']`
- **Language Codes**: `language` - ISO language codes (primarily `en`, but includes `pl`, `de`, etc.)

### Integer Fields
- **Evaluation Order**: `evaluation_order` - Range: 1-3 (typical), but can be higher

### Boolean Fields
- **Is Code**: `is_code` - `True`/`False` indicating code-related conversations

### JSON Object Fields

#### conversation_a / conversation_b Structure
```json
[
  {
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "User message content...",
        "image": null,
        "mimeType": null
      }
    ]
  },
  {
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "Assistant response content...",
        "image": null,
        "mimeType": null
      }
    ]
  }
]
```

#### full_conversation Structure
```json
[
  {
    "user": {
      "role": "user",
      "content": [...]
    },
    "model_side_a": {
      "role": "assistant",
      "content": [...]
    },
    "model_side_b": {
      "role": "assistant",
      "content": [...]
    }
  }
]
```

#### conv_metadata Structure
```json
{
  "sum_assistant_a_tokens": 1854,
  "header_count_a": {
    "h1": 0,
    "h2": 0,
    "h3": 8,
    "h4": 0,
    "h5": 0,
    "h6": 0
  },
  "list_count_a": {
    "ordered": 0,
    "unordered": 39
  },
  "bold_count_a": {
    "**": 65,
    "__": 0
  },
  "context_a_tokens": 11,
  "sum_assistant_b_tokens": 264,
  "header_count_b": {...},
  "turns": 1
}
```

#### category_tag Structure
```json
{
  "creative_writing_v0.1": {
    "creative_writing": false,
    "score": "no"
  },
  "criteria_v0.1": {
    "complexity": false,
    "creativity": true,
    "domain_knowledge": true,
    "problem_solving": true,
    "real_world": true,
    "specificity": true,
    "technical_accuracy": true
  },
  "if_v0.1": {
    "if": false,
    "score": 3
  },
  "math_v0.1": {
    "math": false
  }
}
```

## Data Quality Statistics

### Sample Analysis (100 records)
- **Total Records**: 100
- **Unique Models in A**: 38
- **Unique Models in B**: 42
- **Winner Distribution**:
  - `model_a`: 38 (38%)
  - `model_b`: 33 (33%)
  - `tie`: 19 (19%)
  - `both_bad`: 10 (10%)
- **Language Distribution**: Primarily English (`en`) with some Polish (`pl`) and German (`de`)
- **Evaluation Sessions**: Multiple sessions with varying lengths
- **No Missing Values**: All fields are complete

## Usage Scenarios

### 1. Model Performance Analysis
- Compare win rates between different model pairs
- Analyze performance by conversation type/category
- Study temporal performance trends

### 2. Conversation Quality Assessment
- Extract conversation metadata for quality metrics
- Analyze response characteristics (token counts, formatting)
- Study conversation complexity indicators

### 3. Preference Learning
- Train reward models for RLHF
- Analyze human preference patterns
- Study bias in human evaluations

## Integration with Existing Framework

### Relationship to Open LLM Leaderboard
- **Arena**: Human preference voting on conversations
- **Leaderboard**: Automated benchmark scores
- **Complementary**: Together provide comprehensive evaluation

### Potential Analysis Dimensions
1. **Cross-validation**: Compare Arena preferences with Leaderboard scores
2. **Category Analysis**: Study preferences by conversation type
3. **Model Evolution**: Track performance changes over time
4. **Bias Analysis**: Study evaluator preferences and consistency

## Data Processing Pipeline

### 1. Raw Data Collection
- Source: Hugging Face `lmarena-ai/arena-human-preference-140k`
- Format: Parquet with JSON fields
- Method: Direct download or datasets library

### 2. Data Cleaning & Transformation
- Parse JSON conversation fields
- Extract metadata features
- Normalize model names
- Handle language encoding

### 3. Feature Engineering
- Conversation length metrics
- Response quality indicators
- Category-based aggregations
- Temporal analysis features

### 4. Integration with Ranking Framework
- Convert to pairwise comparison format
- Generate Bradley-Terry model inputs
- Create spectral ranking matrices
- Validate against existing benchmarks

## File Structure

```
data_llm/data_huggingface/data_collection/
├── arena_human_preference_sample_100.csv          # Sample data (100 rows)
├── arena_human_preference_sample_100_metadata.json # Data analysis metadata
└── ARENA_DATASET_SCHEMA.md                        # This schema documentation
```

## Future Extensions

1. **Full Dataset Processing**: Scale to complete 136K records
2. **Real-time Updates**: Integrate with Arena platform for live data
3. **Multi-language Support**: Expand beyond English conversations
4. **Advanced Analytics**: Machine learning on preference patterns
5. **Dashboard Integration**: Add Arena visualizations to LLM dashboard

---

**Last Updated**: October 12, 2025
**Data Version**: Sample 100 records
**Source URL**: https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k
