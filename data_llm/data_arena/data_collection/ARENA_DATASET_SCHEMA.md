# Arena Human Preference Dataset Schema Documentation

## Dataset Overview

**Dataset Name**: `lmarena-ai/arena-human-preference-140k`
**Source**: Hugging Face Datasets
**Purpose**: Human preference voting data comparing different LLM models in conversational scenarios
**Total Records**: 136,634 (sampled 10000 for exploration)
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

### Sample Analysis (10000 records)
- **Total Records**: 10000
- **Unique Models in A**: 52
- **Unique Models in B**: 52
- **Winner Distribution**:
  - `model_a`: 3621 (36.21%)
  - `model_b`: 3642 (36.42%)
  - `tie`: 1615 (16.15%)
  - `both_bad`: 1122 (11.22%)
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
data_llm/data_arena/data_collection/
├── arena_human_preference_sample_10000.csv        # Sample data (10000 rows)
├── arena_human_preference_sample_10000_metadata.json # Data analysis metadata (10000 rows)
└── ARENA_DATASET_SCHEMA.md                        # This schema documentation
```

## Future Extensions

1. **Full Dataset Processing**: Scale to complete 136K records
2. **Real-time Updates**: Integrate with Arena platform for live data
3. **Multi-language Support**: Expand beyond English conversations
4. **Advanced Analytics**: Machine learning on preference patterns
5. **Dashboard Integration**: Add Arena visualizations to LLM dashboard

---

**Last Updated**: October 14, 2025
**Data Version**: Sample 10000 records
**Source URL**: https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k


## Arena数据集7个任务分类维度的判定标准
基于Chatbot Arena官方定义，Arena数据集支持7个任务分类维度，用于更细粒度的模型性能分析：
**参考资料**: [Chatbot Arena Categories: Definitions, Methods, and Insights](https://news.lmarena.ai/arena-category/)

### **1. Creative Writing (创意写作)**
- **判定字段**: `category_tag['creative_writing_v0.1']['creative_writing'] == True`
- **定义**: 评估模型创作原创、有想象力和情感共鸣内容的能力
- **判定标准**:
  - 需要原创性和想象力
  - 涉及情感或艺术表达
  - 请求独特视角或解释性响应
  - 超越事实报告或分析的写作

### **2. Math (数学推理)**
- **判定字段**: `category_tag['math_v0.1']['math'] == True`
- **定义**: 评估模型应用数学推理和问题解决技能的能力
- **判定标准**:
  - 需要主动应用数学概念
  - 涉及数值计算、代数运算或几何推理
  - 包含清晰、明确的问题
  - 测试一个或多个数学能力

### **3. Instruction Following (指令跟随)**
- **判定字段**: `category_tag['if_v0.1']['if'] == True`
- **定义**: 评估模型精确遵循给定指令的能力
- **判定标准**:
  - 清晰、可操作的用户指令
  - 特定的格式或结构要求
  - 独特或具有挑战性的方面

### **4. Coding (编程)**
- **判定字段**: `is_code == True`
- **定义**: 评估模型理解、生成和调试代码的能力
- **判定标准**: 启发式算法检测代码相关内容
  - 代码块标记
  - 编程语言关键词
  - 代码命令和相关术语

### **5. Hard Prompt (困难提示)**
**Reference**: [Introducing Hard Prompts Category in Chatbot Arena](https://lmsys.org/blog/2024-05-17-category-hard/)
- **判定逻辑**: 满足至少6个以下7个核心维度的要求
- **定义**: 处理复杂、严格、精心设计的提示
- **7个核心维度**:
  1. **Specificity**: 是否要求特定输出？
  2. **Domain Knowledge**: 是否涉及一个或多个特定领域？
  3. **Complexity**: 是否具有多个推理层次、组件或变量？
  4. **Problem-Solving**: 是否需要主动问题解决技能？
  5. **Creativity**: 是否需要创造性解决问题？
  6. **Technical Accuracy**: 是否需要技术准确性？
  7. **Real-world Application**: 是否涉及现实应用？

```python
# Hard Prompt判定代码
def is_hard_prompt(category_tag):
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
```

### **6. Longer Query (长查询)**
- **判定逻辑**: `conv_metadata['sum_user_tokens'] > 500`
- **定义**: 查询长度超过500 tokens（约占全部提示的10%）
- **判定标准**: 基于用户输入的token数量阈值

### **7. Multi-Turn (多轮对话)**
- **判定逻辑**: `conv_metadata['turns'] > 1`
- **定义**: 多轮对话交互
- **判定标准**: 对话轮数超过1轮

### **分类部署说明**
- **前4个维度**: 基于预定义的分类标签字段直接判断
- **后3个维度**: 通过元数据统计和内容特征推断判断
- **Hard Prompt**: 需要满足至少6个评估维度的组合判断
- **数据来源**: 所有判定信息均来自`category_tag`和`conv_metadata`字段