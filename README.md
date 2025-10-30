# 鲁棒排序框架 (Robust Ranking Framework)

本项目提供了一个统计框架，旨在根据多个方法（例如，机器学习模型、治疗方案）在一系列样本或评估案例上的表现进行鲁棒排序，并量化该排序结果的不确定性。该框架的核心是 **Vanilla Spectral Method**，它不仅能提供最终排名，还能通过置信区间来评估排名的可靠性。

## 0. Spectral Ranking Inferences based on General Multiway Comparisons: https://arxiv.org/html/2308.02918

Spectral Ranking Inferences based on General Multiway Comparisons 这篇论文是该项目理论基础，该项目在
## 1. 核心方法论

排序过程基于对每个样本中方法之间的成对比较分析。

### 1.1. 数据预处理 ( `process_data` 函数)

输入数据首先被转换为图的表示形式。

-   **输入**: 一个数据矩阵，其中行代表样本，列代表方法。
-   **过程**: 对于每个样本，所有可用的方法对都会被进行比较。根据它们的性能得分（比较的方向由 `bigbetter` 参数控制），确定“胜者”和“败者”。
-   **输出**: 所有样本的成对比较结果被汇总为矩阵（`aa` 和 `ww`），这些矩阵构成了谱排序算法的基础。

### 1.2. Vanilla Spectral Method ( `vanilla_spectrum_method` 函数)

这是用于排序和不确定性估计的核心算法。

-   **排序**: 算法根据比较数据构建一个转移矩阵 `P`。然后，计算由 `P` 所代表的马尔可夫链的平稳分布。该分布的元素作为每种方法的“能力得分” (`theta.hat`)。最终排名由这些得分导出。
-   **不确定性量化**: 为了评估排名的稳定性，该框架使用了 **加权自助法 (Weighted Bootstrap)**。通过重复重采样并重新计算排名（例如，2000次），它为每种方法的排名构建了经验分布。从这些分布中，它计算出几种类型的置信区间。

## 2. 输出结果解读

最终输出是一个总结排序结果的矩阵。该矩阵的行代表：

-   `theta.hat`: 通过谱方法计算出的原始能力得分。得分越高，表示性能越好。
-   `Ranking`: 每种方法的最终排名，从第1名（最好）到第k名（最差）。
-   `two-sided CI`: 排名的95%双边置信区间。例如，`[1, 3]` 的区间表示我们有95%的信心认为该方法的真实排名在第1到第3名之间。
-   `left-sided CI`: 排名的95%单边置信区间（下限）。这提供了一个关于最佳可能排名的保守估计。例如，值为2意味着我们有95%的信心认为该方法的真实排名不会好于第2名（即排名可能是2, 3, 4, ...）。
-   `uniform left-sided CI`: 一个更保守的、统一的单边置信区间，它以95%的置信度同时对所有方法成立。

## 3. 如何使用

项目中包含一个演示 R 脚本文件 `demo_r/demo.25.9.27.R`，它展示了完整的工作流程。

### 3.1. 输入数据

输入应为一个 CSV 文件，其中：
-   每一行代表一个样本、案例或试验。
-   每一列代表一个待排序的方法。
-   单元格中的值是每种方法在每个样本上的性能指标。
-   缺失值 (`NA`) 会被自动处理。

### 3.2. 运行演示

-   `demo_r/demo.25.9.27.R` 脚本展示了三个示例：
1.  **模拟数据**: 它首先生成一个 `demo_r/simulated_data.csv` 文件，其中包含已知的真实排名，用于验证算法的正确性。
2.  **真实世界机器学习模型比较 (AoU)**: 它根据 `demo_r/top2000childrencode_report_aou.csv` 数据集对几种机器学习模型的性能进行排名。
3.  **真实世界机器学习模型比较 (UKBB)**: 它使用 `demo_r/top2000childrencode_report_ukbb.csv` 数据集执行类似的排名。

-   `demo_r/simulated_data.csv`: 用于测试目的的人工生成数据。
-   `demo_r/top2000childrencode_report_aou.csv`: 来自 All of Us (AoU) 数据集的真实世界模型性能数据。
-   `demo_r/top2000childrencode_report_ukbb.csv`: 来自 UK Biobank (UKBB) 数据集的真实世界模型性能数据。

## 4. Technical Architecture

### 4.1. 技术栈：
前端界面：NiceGUI；
后端服务：Python FastAPI；
Report_Generator_Agent数据可视化：JavaScript (e.g. D3.js) (用于生成交互式和美观的报告图表)；
R脚本运行环境：使用 rpy2 调用当前 Conda 环境中的 R 来执行 R 脚本。
要运行分析，只需在 R Markdown 文件中执行代码块即可。
LLM Agent：集成OpenAI GPT系列模型，实现智能对话式用户交互，提供自然语言参数配置和实时进度反馈

### 4.2. 前后端架构优化

#### 架构改进：
- **前后端分离**: 前端通过HTTP API调用后端，不再直接导入后端模块
- **依赖解耦**: 前端不再需要安装R环境，后端独立管理R依赖

#### 后端API端点：
- 新增 `/api/ranking/custom` 端点处理自定义模型排名请求
- 支持Form数据格式：`model_name` 和 `scores` (JSON字符串)

#### 前端优化：
- 移除直接导入 `run_custom_ranking` 函数
- 改为使用 `aiohttp` 通过HTTP API调用后端
- 前端启动脚本不再安装R包，启动时间大幅缩短

#### 后端部署优化：
**必需的系统依赖：**
- **R 环境**: `r-base`, `r-base-dev` - 用于谱排序算法执行
- **R 包**: `readr`, `dplyr`, `jsonlite` - R脚本核心依赖
- **编译工具**: `libcurl4-openssl-dev`, `libssl-dev`, `libxml2-dev` - R包编译依赖

**已移除的不必要依赖：**
- `libgomp1` - OpenMP并行库（后端不需要）
- GTK图形界面库（后端是API服务，无GUI）
- X11显示系统（后端不显示界面）
- OpenGL/Vulkan图形库（后端不需要GPU渲染）
- 终端模拟器等

**R包优化：**
- 移除了 `MASS`, `Matrix`, `stats4` 包（与R 4.0.4版本不兼容）
- 只保留实际使用的 `readr`, `dplyr`, `jsonlite` 包

## 5. LLM Performance Dashboard

LLM Performance Dashboard是集成到现有Web界面中的一个新功能模块，用于实时监控和分析LLM模型性能。

### 5.1. 数据收集器 (huggingface_data_collector.py)

`huggingface_data_collector.py` 是一个专门的数据收集和预处理脚本，用于从Hugging Face的Open LLM Leaderboard获取LLM性能数据，并将其转换为适合谱排序分析的格式。

**核心功能**：
- 从 [Open LLM Leaderboard Dataset](https://huggingface.co/datasets/open-llm-leaderboard/contents) 自动下载最新数据
- 筛选和清洗数据，只保留对谱排序有用的列
- 生成标准化的CSV格式数据供后续分析

Output File: `llm_leaderboard_cleaned.csv` Schema：

**核心Benchmark分数（6列）**：
- `ifeval` (float): **IFEval指令遵循评估分数** - 测试模型对复杂、精确指令的遵循能力，包括条件执行、多步骤任务和格式要求等。衡量模型是否能准确理解和执行详细的指令。
- `bbh` (float): **BBH (Big Bench Hard) 大型基准测试分数** - 来自Google BIG-Bench项目的困难任务集合，涵盖逻辑推理、数学、常识推理等多种挑战性任务。代表模型在复杂推理任务上的表现。
- `math` (float): **MATH Lvl 5数学推理分数** - 五级难度的数学问题求解能力测试，涵盖代数、几何、微积分等高级数学概念。反映模型在严谨数学推理方面的实力。
- `gpqa` (float): **GPQA研究生级问题回答分数** - Graduate-level Google-Proof Q&A，专门设计用于区分人类专家和AI模型的问题。测试模型在专业领域知识和推理上的深度。
- `musr` (float): **MUSR多步推理任务分数** - Multi-Step Unified Reasoning，测试模型进行多步骤逻辑推理和问题分解的能力。要求模型能进行连贯的推理链并得出正确结论。
- `mmlu_pro` (float): **MMLU-PRO专业级知识测试分数** - MMLU的增强版本，使用更具挑战性的问题和更严格的评估标准。测试模型在57个学科的专业知识掌握程度。

**模型元数据（9列）**：
- `model` (string): 模型全名（主要标识符）
- `model_link` (string): HuggingFace模型页面HTML链接
- `average_score` (float): 平均综合得分
- `params_b` (float): 参数数量
- `architecture` (string): 模型架构类型
- `precision` (string): **模型权重的数据类型** - 决定模型参数的数值表示精度。常见类型包括：`float32`（标准32位浮点）、`float16`（半精度，可减少内存使用）、`bfloat16`（Google设计的16位格式）、`int8/int4`（量化格式，压缩模型大小）等。影响模型大小、推理速度和内存占用。
- `type` (string): 模型类型（预训练/微调/聊天模型等）
- `submission_date` (string): 提交日期
- `base_model` (string): 基础模型名称

**数据质量保证**：
- 所有benchmark分数为**准确率百分比（0.0-100.0）** - 直接表示模型在相应任务上的正确率，例如82.5表示82.5%的准确率
- 自动过滤缺失benchmark数据的模型
- 按平均得分降序排序，最优模型排在前面
- 包含约4,576个经过验证的LLM模型记录

### 5.2. 数据处理流程 (huggingface_data_process.py)

`huggingface_data_process.py` 脚本将收集到的LLM数据转换为`ranking_cli.R`期望的格式：

**输入格式**（来自`huggingface_data_collector.py`）：
- 行：LLM模型（4,576个）
- 列：Benchmark分数 + 元数据（15列）

**输出格式**（供谱排序分析）：
- 行：Benchmark任务（6个：IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO）
- 列：LLM模型（Top N个，按平均得分排序）

**自动生成的数据集**：
- `llm_ranking_full.csv`: 全量数据（6×4,576）
- `llm_ranking_top25.csv`: Top 25模型（6×25）- 快速测试
- `llm_ranking_top50.csv`: Top 50模型（6×50）- 中等规模
- `llm_ranking_top100.csv`: Top 100模型（6×100）- 推荐用于谱排序分析

基于B=2000次bootstrap重采样的谱排序分析运行时间：

| 数据集规模 | 矩阵维度 | 运行时间 | 相对时间 |
|-----------|---------|---------|---------|
| **Top 25** | 6×25 | **1.01秒** | 1x |
| **Top 50** | 6×50 | **5.09秒** | 5.0x |
| **Top 100** | 6×100 | **33.0秒** | 32.7x |

### 5.3. Dashboard数据更新脚本 (huggingface_ranking.py)

`huggingface_ranking.py` 是一个专门的脚本，用于运行谱排序算法并更新dashboard的数据文件。它将静态的LLM性能数据转换为基于谱排序算法的动态排名。

**核心功能**：
- 自动调用谱排序算法对LLM数据进行排名
- 处理R脚本输出格式并转换为dashboard兼容格式
- 更新 `llm_ranking_top100.csv` 文件，实现实时排名更新

**使用方法**：

```bash
# 更新top 100模型的排名（推荐用于完整分析）
python code_app/backend/data_ranking/huggingface_ranking.py --top-n 100 --B 2000

# 快速测试使用top 25模型
python code_app/backend/data_ranking/huggingface_ranking.py --top-n 25 --B 100

# 自定义参数
python code_app/backend/data_ranking/huggingface_ranking.py \
  --top-n 50 \
  --bigbetter 1 \
  --B 1000 \
  --seed 123
```

**参数说明**：
- `--top-n`: 要排名的模型数量 (默认: 100)
- `--bigbetter`: 更高分数是否更好 (1=是, 0=否) (默认: 1)
- `--B`: Bootstrap迭代次数 (默认: 2000)
- `--seed`: 随机种子 (默认: 42)

**输出**：
- 更新 `data_llm/llm_ranking_top100.csv` 文件
- 自动备份原有文件为 `.backup` 后缀
- 显示排名前5的模型及其评分

**性能参考**（基于Top 100模型）：
- Bootstrap 500次: ~25秒
- Bootstrap 2000次: ~1.5-2分钟
- Bootstrap 5000次: ~5-6分钟

### 5.4. ranking_cli.R算法时间复杂度分析（基于实测数据）

基于详细的时间测量脚本(`ranking_cli_timing.R`)，对不同规模数据集进行精确的时间复杂度分析：

##### 实测时间分布对比

| 数据集规模         |   总时间   |  IO时间  |   预处理   |  矩阵构建  |   SVD分解   |  Bootstrap | Uniform CI |谱排序占比|
|-------------------|-----------|---------|---------|-----------|-----------|-----------|-----------|-----------|
| **Top 25** (n=25) | **1.01秒** | 0.18秒  | 0.07秒  | **0.07秒** | **0.003秒** | **0.35秒** | **0.26秒** | 69.4%  |
| **Top 50** (n=50) | **5.09秒** | 0.26秒  | 0.42秒  | **1.40秒** | **0.017秒** | **1.59秒** | **1.19秒** | 82.4%  |
| **Top 100** (n=100)| **33.0秒**| 0.23秒  | 0.92秒  | **17.7秒** | **0.041秒** | **7.13秒** | **6.41秒** | 94.9%  |

##### 详细性能特征分析

**1. SVD分解性能特征**：
- **实际复杂度**: 近似O(1) - 从Top 25(0.003秒)到Top 100(0.041秒)，仅增加13.7倍
- **理论vs实际**: 远低于理论O(n³)复杂度（应增加64倍）
- **原因**: 现代BLAS库高度优化，小矩阵完全在CPU缓存中处理
- **结论**: SVD不是性能瓶颈，库优化使其接近常数时间

**2. 矩阵构建性能特征**：
- **实际复杂度**: O(n²) - 从Top 25(0.07秒)到Top 100(17.7秒)，增加253倍
- **理论验证**: Top 25→50→100，倍数关系为1:20:253，符合O(n²)特征
- **性能占比**: 在大矩阵下成为主要瓶颈（Top 100占53.6%）
- **结论**: 实际增长略高于理论，可能是内存访问模式影响

**3. Bootstrap重采样性能特征**：
- **实际复杂度**: O(n²) - 从Top 25(0.35秒)到Top 100(7.13秒)，增加20.4倍
- **理论验证**: 符合O(n²)特征，但增长相对较慢
- **性能占比**: 始终占谱排序时间的40-50%
- **结论**: 主要计算负载，具备并行优化潜力

**4. Uniform CI计算性能特征**：
- **实际复杂度**: O(n²) - 从Top 25(0.26秒)到Top 100(6.41秒)，增加24.7倍
- **性能占比**: 在大矩阵下显著增加（Top 100占19.4%）
- **结论**: 统计计算开销随矩阵规模快速增长

##### 复杂度理论vs实际对比

**理论复杂度预期**：
- **SVD**: O(n³) - 应随n³快速增长
- **矩阵构建**: O(n²) - 应随n²增长
- **Bootstrap**: O(B×n²) - 应随n²增长
- **Uniform CI**: O(n²) - 应随n²增长

**实际测量结果**：
- **SVD实际复杂度**: 近似O(1)，远低于理论O(n³)
- **矩阵构建实际复杂度**: O(n²)，符合理论预期
- **Bootstrap实际复杂度**: O(n²)，符合理论预期
- **Uniform CI实际复杂度**: O(n²)，符合理论预期

**Optimization Opportunities**：
1.  **矩阵构建优化 (首要任务)**:
    *   **向量化计算 (Vectorized Computation)**: 这是最直接且最有效的优化手段。当前 `O(n²)` 的瓶颈主要来自矩阵构建过程。通过使用 R 语言内置的向量和矩阵操作，替代显式 `for` 循环，可以利用底层高度优化的 C/Fortran 代码执行计算，从而大幅减少 R 解释器的开销。这是解决性能问题的首选方案。
    *   **GPU 加速**: 对于更大规模的数据集，可以考虑使用支持 GPU 的库（如 `gpuR`）将矩阵运算 offload 到 GPU 上执行，但这需要额外的硬件和依赖配置。
2.  **Bootstrap 并行化**:
    *   Bootstrap 过程占用了约 40-50% 的计算时间，且每次迭代都是独立的。因此，使用 `parallel` 或 `future` 包将 `B=2000` 次重采样分配到多个 CPU 核心上并行执行，可以几乎线性地减少这部分所需的时间。

### 5.5. Arena Human Preference Dataset (新增数据源)

Arena数据集提供了基于人类偏好的LLM模型比较数据，与传统基准测试形成互补。

#### 数据源
- **Dataset**: `lmarena-ai/arena-human-preference-140k`
- **来源**: Hugging Face Datasets
- **数据规模**: 136,634条完整记录
- **采集样本**: 136,634条完整记录

#### Schema结构 (14列)

**核心比较字段**：
- `id` (string): 唯一投票标识符，UUID格式
- `model_a` (string): 第一个被比较的模型（如：`gemini-2.5-pro`）
- `model_b` (string): 第二个被比较的模型（如：`claude-3-7-sonnet-20250219-thinking-32k`）
- `winner` (string): 投票结果，可选值：`model_a`、`model_b`、`tie`、`both_bad`

**会话管理字段**：
- `evaluation_session_id` (string): 评估批次标识符
- `evaluation_order` (int64): 会话内的评估顺序

**对话内容字段**：
- `conversation_a` (JSON): model_a的完整对话历史
- `conversation_b` (JSON): model_b的完整对话历史
- `full_conversation` (JSON): 合并的用户问题和双模型回答

**元数据字段**：
- `conv_metadata` (JSON): 对话统计信息（Token数、格式统计等）
- `category_tag` (JSON): 内容分类标签（如创意写作、数学推理等）
- `language` (string): 对话主要语言（主要`en`，也包含`pl`、`de`等）
- `is_code` (bool): 是否涉及编程代码
- `timestamp` (string): 评估时间戳（ISO格式）

#### 数据特点
- **多语言支持**: 英语、波兰语、德语等多语言对话
- **丰富元数据**: Token统计、内容分类、格式分析等
- **对话质量评估**: 基于人类偏好的主观质量判断
- **时间序列**: 支持模型性能趋势分析

#### 分析价值
Arena数据集与Open LLM Leaderboard形成互补：
- **Leaderboard**: 客观基准测试分数（IFEval、BBH、MATH等）
- **Arena**: 主观人类偏好投票（对话质量、用户体验）

#### 数据文件位置
```
data_llm/data_arena/data_collection/
├── arena_human_preference_sample_100.csv          # 样本数据
├── arena_human_preference_sample_100_metadata.json # 分析元数据
└── ARENA_DATASET_SCHEMA.md                        # 详细schema文档
```

#### 未来集成计划
1. **数据处理脚本**: `arena_data_process.py` - 转换为谱排序格式
2. **排名分析脚本**: `arena_ranking.py` - 执行谱排序算法
3. **Dashboard集成**: 在Web界面中添加Arena数据可视化
4. **联合分析**: 探索Leaderboard分数与Arena偏好的相关性

### 5.6. Arena数据集7个任务分类维度的判定标准
基于Chatbot Arena官方定义，Arena数据集支持7个任务分类维度，用于更细粒度的模型性能分析：
**参考资料**: [Chatbot Arena Categories: Definitions, Methods, and Insights](https://news.lmarena.ai/arena-category/)

#### **1. Creative Writing (创意写作)**
- **判定字段**: `category_tag['creative_writing_v0.1']['creative_writing'] == True`
- **定义**: 评估模型创作原创、有想象力和情感共鸣内容的能力
- **判定标准**:
  - 需要原创性和想象力
  - 涉及情感或艺术表达
  - 请求独特视角或解释性响应
  - 超越事实报告或分析的写作

#### **2. Math (数学推理)**
- **判定字段**: `category_tag['math_v0.1']['math'] == True`
- **定义**: 评估模型应用数学推理和问题解决技能的能力
- **判定标准**:
  - 需要主动应用数学概念
  - 涉及数值计算、代数运算或几何推理
  - 包含清晰、明确的问题
  - 测试一个或多个数学能力

#### **3. Instruction Following (指令跟随)**
- **判定字段**: `category_tag['if_v0.1']['if'] == True`
- **定义**: 评估模型精确遵循给定指令的能力
- **判定标准**:
  - 清晰、可操作的用户指令
  - 特定的格式或结构要求
  - 独特或具有挑战性的方面

#### **4. Coding (编程)**
- **判定字段**: `is_code == True`
- **定义**: 评估模型理解、生成和调试代码的能力
- **判定标准**: 启发式算法检测代码相关内容
  - 代码块标记
  - 编程语言关键词
  - 代码命令和相关术语

#### **5. Hard Prompt (困难提示)**
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

#### **6. Longer Query (长查询)**
- **判定逻辑**: `conv_metadata['sum_user_tokens'] > 500`
- **定义**: 查询长度超过500 tokens（约占全部提示的10%）
- **判定标准**: 基于用户输入的token数量阈值

#### **7. Multi-Turn (多轮对话)**
- **判定逻辑**: `conv_metadata['turns'] > 1`
- **定义**: 多轮对话交互
- **判定标准**: 对话轮数超过1轮

#### **分类部署说明**
- **前4个维度**: 基于预定义的分类标签字段直接判断
- **后3个维度**: 通过元数据统计和内容特征推断判断
- **Hard Prompt**: 需要满足至少6个评估维度的组合判断
- **数据来源**: 所有判定信息均来自`category_tag`和`conv_metadata`字段


### 5.7. Arena 数据的 BT-MLE 建模与谱排序集成（替代 win_rate）

为提升严格性与稳健性，本项目在 `arena_data_process.py` 中采用 Bradley–Terry（BT）模型对 Arena 的人类偏好投票进行类别级建模，并将每个类别的 BT 概率作为谱排序输入（7 行“虚拟基准”）。核心要点如下：

- 为什么不用简单 win_rate：
  - **对手强度校正**：BT 在成对比较层面统一估计每个模型的能力，能够自然校正“遇到强/弱对手”带来的偏差。
  - **小样本更稳健**：可以引入轻量先验/平滑，避免稀疏类别下的极端比值；比原始胜率更稳定。
  - **平局处理一致**：与 Arena 做法一致，将平局计作“各 0.5 胜”。

- 模型公式（Logit 形式）：
  - 任意两模型 \(i, j\) 的胜率为
    \[\Pr(i > j) = \sigma(\theta_i - \theta_j) = \frac{\exp(\theta_i)}{\exp(\theta_i)+\exp(\theta_j)}.\]
  - 可辨识性通过约束（如 \(\sum_i \theta_i = 0\)）或几何均值归一化解决。
  - 平局处理：将 tie 按 0.5/0.5 分摊到双方的胜场；`both_bad` 视作缺失（不进入似然）。
  - 本实现采用 MM（Minorize–Maximize）迭代进行极大似然估计，并加入轻量平滑（默认为 \(\alpha=0.5\)）。

- 类别级建模与输出：
  - 对 7 个任务类别分别拟合 BT，输出对“平均对手”的胜率刻度 \(p_i = s_i/(s_i+1)\)。
  - 生成的 7 行虚拟基准为：
    - `creative_writing_bt_prob`
    - `math_bt_prob`
    - `instruction_following_bt_prob`
    - `coding_bt_prob`
    - `hard_prompt_bt_prob`
    - `longer_query_bt_prob`
    - `multi_turn_bt_prob`
  - 门槛与回退：整体最少对局数 `MIN_GAMES_THRESHOLD=5`；类别内最少对局数为 3。若类别对局不足或无法估计，则在导出矩阵时以 0.5 作为“中性值”回退。

- 与谱排序的关系（不会重复）：
  - BT 解决“类别内：投票→能力刻度”的问题；谱排序解决“跨类别：多行样本→总体稳健排名与区间”的问题，层级不同，不是重复建模。
  - 若只需要一个“全局”偏好评分，可直接用“全局 BT”；但本项目的目标是利用 7 类信息进行稳健聚合与不确定性量化，因此采用“类别 BT → 谱排序”。

- 与 LMSYS 的做法一致且可映射到 Elo 刻度：
  - LMSYS 已从在线 Elo 迁移到集中式 BT-MLE，并将平局按 0.5 计入；展示上仍用 Elo 刻度以保持连续性。
  - 两种刻度等价：\( \Pr(i>j) = 1/(1+10^{(R_j-R_i)/400}) \) 与上式线性对应，\( \theta_i = (\ln 10/400)\,R_i + c \)。
  - 参考： [Chatbot Arena: New models & Elo system update](https://lmsys.org/blog/2023-12-07-leaderboard/)

- 实践参数（当前实现）：
  - 平滑：\(\alpha=0.5\)（Jeffreys/Laplace 风格，避免零锁死）
  - 收敛：MM 最大迭代 5000，容差 \(1e{-8}\)
  - 归一化：几何均值为 1（平均对手强度为 1）

#### 5.7.1. 数据产物与路径

- 处理脚本：`code_app/backend/data_processing/arena_data_process.py`
- 输出 CSV：`data_llm/data_arena/data_processing/arena_ranking_full.csv`
  - 行：上述 7 个 `*_bt_prob`
  - 列：清洗后的模型名
- 元数据：同路径下 `_metadata.json`，记录阈值与字段说明。

#### 5.7.2. 模型参赛统计

基于 135,634 场比赛的数据统计，总共有 53 种独特模型参与比赛。

| 排名 | 模型名称 | model_a次数 | model_b次数 | 总比赛次数 |
|------|---------|-------------|-------------|------------|
| 1 | claude-opus-4-20250514 | 4957 | 5135 | 10092 |
| 2 | gemini-2.5-flash | 4911 | 4757 | 9668 |
| 3 | gemini-2.5-pro | 4576 | 4643 | 9219 |
| 4 | mistral-medium-2505 | 4599 | 4536 | 9135 |
| 5 | qwen3-235b-a22b-no-thinking | 4561 | 4515 | 9076 |
| 6 | o3-2025-04-16 | 4272 | 4257 | 8529 |
| 7 | claude-sonnet-4-20250514 | 4130 | 4165 | 8295 |
| 8 | chatgpt-4o-latest-20250326 | 3816 | 3834 | 7650 |
| 9 | gemma-3-27b-it | 3675 | 3651 | 7326 |
| 10 | claude-3-7-sonnet-20250219-thinking-32k | 3530 | 3619 | 7149 |
| 11 | claude-3-7-sonnet-20250219 | 3409 | 3443 | 6852 |
| 12 | command-a-03-2025 | 3463 | 3375 | 6838 |
| 13 | claude-3-5-sonnet-20241022 | 3316 | 3501 | 6817 |
| 14 | o3-mini | 3279 | 3345 | 6624 |
| 15 | deepseek-r1-0528 | 3290 | 3264 | 6554 |
| 16 | gpt-4.1-2025-04-14 | 3254 | 3286 | 6540 |
| 17 | o4-mini-2025-04-16 | 3250 | 3227 | 6477 |
| 18 | claude-3-5-haiku-20241022 | 3210 | 3256 | 6466 |
| 19 | amazon.nova-pro-v1:0 | 3218 | 3165 | 6383 |
| 20 | claude-opus-4-20250514-thinking-16k | 3149 | 3008 | 6157 |
| 21 | gpt-4.1-mini-2025-04-14 | 3061 | 3060 | 6121 |
| 22 | deepseek-v3-0324 | 3020 | 3097 | 6117 |
| 23 | gemini-2.0-flash-001 | 3137 | 2937 | 6074 |
| 24 | grok-3-preview-02-24 | 3021 | 3019 | 6040 |
| 25 | grok-3-mini-beta | 2992 | 2999 | 5991 |
| 26 | llama-4-maverick-03-26-experimental | 2844 | 2962 | 5806 |
| 27 | claude-sonnet-4-20250514-thinking-32k | 2838 | 2775 | 5613 |
| 28 | qwen3-30b-a3b | 2807 | 2691 | 5498 |
| 29 | minimax-m1 | 2726 | 2743 | 5469 |
| 30 | llama-4-maverick-17b-128e-instruct | 2614 | 2718 | 5332 |
| 31 | gemini-2.5-flash-lite-preview-06-17-thinking | 2583 | 2649 | 5232 |
| 32 | qwen3-235b-a22b | 2593 | 2522 | 5115 |
| 33 | gemini-2.5-flash-preview-04-17 | 2571 | 2479 | 5050 |
| 34 | llama-3.3-70b-instruct | 2457 | 2448 | 4905 |
| 35 | qwen-max-2025-01-25 | 2153 | 2226 | 4379 |
| 36 | qwq-32b | 2112 | 2147 | 4259 |
| 37 | mistral-small-3.1-24b-instruct-2503 | 1636 | 1635 | 3271 |
| 38 | amazon-nova-experimental-chat-05-14 | 1658 | 1609 | 3267 |
| 39 | gemini-2.5-pro-preview-05-06 | 1648 | 1607 | 3255 |
| 40 | llama-4-scout-17b-16e-instruct | 1370 | 1435 | 2805 |
| 41 | grok-3-mini-high | 1427 | 1374 | 2801 |
| 42 | kimi-k2-0711-preview | 1364 | 1379 | 2743 |
| 43 | gemma-3n-e4b-it | 1271 | 1340 | 2611 |
| 44 | magistral-medium-2506 | 1307 | 1299 | 2606 |
| 45 | mistral-small-2506 | 1201 | 1172 | 2373 |
| 46 | hunyuan-turbos-20250416 | 817 | 768 | 1585 |
| 47 | grok-4-0709 | 802 | 759 | 1561 |
| 48 | gemini-2.5-pro-preview-03-25 | 635 | 754 | 1389 |
| 49 | qwen3-235b-a22b-instruct-2507 | 306 | 316 | 622 |
| 50 | gpt-4o-mini-2024-07-18 | 319 | 271 | 590 |
| 51 | gpt-4o-2024-11-20 | 286 | 287 | 573 |
| 52 | gemini-2.0-flash-thinking-exp-01-21 | 192 | 174 | 366 |
| 53 | qwen3-coder-480b-a35b-instruct | 1 | 1 | 2 |

**统计说明：**
- **model_a次数**: 该模型作为第一个候选模型出现的次数
- **model_b次数**: 该模型作为第二个候选模型出现的次数
- **总比赛次数**: 该模型参与的总比赛场次
- 排名按总比赛次数降序排列

**数据洞察：**
- 最活跃的模型 `claude-opus-4-20250514` 参加了 10,092 场比赛
- 大多数主流模型（如Gemini、Claude、GPT系列）都有数千场参赛记录
- 参赛次数分布呈现明显的长尾效应，前10名模型占据了大部分比赛