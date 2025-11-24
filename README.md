# 鲁棒排序框架 (Robust Ranking Framework)

本项目提供了一个统计框架，旨在根据多个方法（例如，机器学习模型、治疗方案）在一系列样本或评估案例上的表现进行鲁棒排序，并量化该排序结果的不确定性。该框架的核心是 **Vanilla Spectral Method**，它不仅能提供最终排名，还能通过置信区间来评估排名的可靠性。

## 0. Spectral Ranking Inferences based on General Multiway Comparisons: https://arxiv.org/html/2308.02918

Spectral Ranking Inferences based on General Multiway Comparisons（https://arxiv.org/html/2308.02918）这篇论文是该项目理论基础，该项目在论文的理论基础以及代码基础上将 Spectral Ranking Inferences 制作成了有LLM Agent加持的网页应用，以便于更多人可以简单轻易地使用 Spectral Ranking Inferences 而不需要花费大量的时间阅读文章并且复现代码。

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

#### 5.2.1. 数据处理策略：综合基准 vs. 子任务拆分

为了将Hugging Face的得分数据应用于谱排序，核心任务是将其转换为一个 **“评估案例 × 模型”** 的矩阵。这个转换过程遵循“成对比较”的原则，具体步骤如下：
1.  **将每个基准测试（行）视为一场独立的“比赛”**。
2.  在这场比赛中，**将所有模型两两配对进行比较**。
3.  **根据分数判定胜负**：如果在一个基准上 `score_A > score_B`，则记录为“A胜B”一次。
4.  最终，**所有基准上的所有胜负记录被汇总起来**，形成算法所需的完整比较数据。

我们主要有两种策略来定义“比赛”（即评估案例），它们的区别在于粒度：

**策略一：使用综合基准**

此方法将6个核心的综合性基准作为评估案例。

*   **评估案例 (行)**: 6个 (IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO)
*   **数据点计算 (以Top 50模型为例)**:
    *   每个基准产生 `50 * 49 / 2 = 1,225` 个成对比较。
    *   总数据点: `6 (基准) × 1,225 = 7,350` 条。

**策略二：使用子任务拆分 (推荐)**

此方法将综合性基准展开为其所有独立的子任务，以增加评估案例的数量，从而提升排名的鲁棒性。这被视为更优的数据处理方法。

*   **评估案例 (行)**: **40个** 独立的子任务。其构成为：
    *   **BBH**: 24个子任务
    *   **MATH**: 8个子任务
    *   **GPQA**: 3个子任务
    *   **MUSR**: 3个子任务
    *   **MMLU-PRO**: 1个任务
    *   **IFEval**: 1个任务
*   **数据点计算 (以Top 50模型为例)**:
    *   总数据点: `40 (子任务) × 1,225 = 49,000` 条。

**结论与建议**

| 数据处理方式 | 任务数量 | 总比较数据条数 (Top 50) | 优势 |
| :--- | :---: | :---: | :--- |
| 1. 综合基准 | 6 | 7,350 | 速度快，计算量小 |
| **2. 子任务拆分** | **40** | **49,000** | **统计鲁棒性高，结果更可靠** |

我们**强烈推荐使用“子任务拆分”策略**。通过将数据量扩大近6.5倍，该方法能显著减少因单个任务得分波动对整体排名的影响，从而生成更稳定、更可信的排序结果和置信区间。

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

#### 5.7. 谱排序数据处理结果

经过多类别展开处理的Arena数据，用于谱排序分析：

**处理脚本**: `code_app/backend/data_processing/arena_spectral_process.py`

**输出文件**:
```
data_llm/data_arena/data_processing/
├── arena_spectral_full.csv          # 谱排序完整数据 (117,947行 × 53列)
└── arena_spectral_full_metadata.json # 谱排序元数据
```

**数据集规模**:
- **总行数**: 117,947行（比原始98,348行有效比较增加约20%）
- **总列数**: 53列（52个模型列 + 1个类别列）
- **实际参赛模型**: 52个（有实际比较数据的模型）
- **处理方式**: 自动过滤全为NaN的模型列 + 多类别展开 + 流式处理避免内存溢出

**7基准类别分布统计**:

| 类别 | 行数 | 占比 | 说明 |
|------|------|------|------|
| `hard_prompt` | 36,829 | 31.3% | 复杂提示处理能力 |
| `coding` | 28,287 | 24.0% | 编程相关任务 |
| `instruction_following` | 17,556 | 14.9% | 指令跟随能力 |
| `multi_turn` | 13,834 | 11.7% | 多轮对话交互 |
| `creative_writing` | 8,424 | 7.1% | 创意写作任务 |
| `math` | 7,341 | 6.2% | 数学推理能力 |
| `longer_query` | 5,676 | 4.8% | 长查询处理 |

#### 5.7.1. 模型参赛统计

基于原始有效比较数据统计（98,348个比较，排除tie和both_bad），总共有52种独特模型实际参与比赛。

| 排名 | 模型名称 | 总比赛次数 |
|------|---------|------------|
| 1 | claude-opus-4-20250514 | 7337 |
| 2 | gemini-2.5-pro | 6954 |
| 3 | gemini-2.5-flash | 6920 |
| 4 | qwen3-235b-a22b-no-thinking | 6497 |
| 5 | mistral-medium-2505 | 6454 |
| 6 | o3-2025-04-16 | 6411 |
| 7 | claude-sonnet-4-20250514 | 6081 |
| 8 | chatgpt-4o-latest-20250326 | 5635 |
| 9 | claude-3-7-sonnet-20250219-thinking-32k | 5344 |
| 10 | gemma-3-27b-it | 5256 |
| 11 | claude-3-7-sonnet-20250219 | 5110 |
| 12 | claude-3-5-sonnet-20241022 | 5054 |
| 13 | o3-mini | 4807 |
| 14 | command-a-03-2025 | 4787 |
| 15 | deepseek-r1-0528 | 4783 |
| 16 | claude-3-5-haiku-20241022 | 4694 |
| 17 | gpt-4.1-2025-04-14 | 4656 |
| 18 | o4-mini-2025-04-16 | 4649 |
| 19 | claude-opus-4-20250514-thinking-16k | 4582 |
| 20 | amazon.nova-pro-v1:0 | 4580 |
| 21 | grok-3-preview-02-24 | 4435 |
| 22 | deepseek-v3-0324 | 4354 |
| 23 | gpt-4.1-mini-2025-04-14 | 4347 |
| 24 | llama-4-maverick-03-26-experimental | 4313 |
| 25 | gemini-2.0-flash-001 | 4305 |
| 26 | grok-3-mini-beta | 4300 |
| 27 | claude-sonnet-4-20250514-thinking-32k | 4124 |
| 28 | minimax-m1 | 3972 |
| 29 | llama-4-maverick-17b-128e-instruct | 3900 |
| 30 | qwen3-30b-a3b | 3862 |
| 31 | gemini-2.5-flash-lite-preview-06-17-thinking | 3738 |
| 32 | gemini-2.5-flash-preview-04-17 | 3665 |
| 33 | qwen3-235b-a22b | 3614 |
| 34 | llama-3.3-70b-instruct | 3604 |
| 35 | qwen-max-2025-01-25 | 3080 |
| 36 | qwq-32b | 3053 |
| 37 | gemini-2.5-pro-preview-05-06 | 2382 |
| 38 | mistral-small-3.1-24b-instruct-2503 | 2331 |
| 39 | amazon-nova-experimental-chat-05-14 | 2313 |
| 40 | llama-4-scout-17b-16e-instruct | 2028 |
| 41 | kimi-k2-0711-preview | 2028 |
| 42 | magistral-medium-2506 | 1993 |
| 43 | grok-3-mini-high | 1982 |
| 44 | gemma-3n-e4b-it | 1893 |
| 45 | mistral-small-2506 | 1669 |
| 46 | grok-4-0709 | 1153 |
| 47 | hunyuan-turbos-20250416 | 1111 |
| 48 | gemini-2.5-pro-preview-03-25 | 1029 |
| 49 | qwen3-235b-a22b-instruct-2507 | 431 |
| 50 | gpt-4o-mini-2024-07-18 | 426 |
| 51 | gpt-4o-2024-11-20 | 410 |
| 52 | gemini-2.0-flash-thinking-exp-01-21 | 260 |

**统计说明：**
- **总比赛次数**: 该模型在有效比较中出现的总次数（作为model_a或model_b）
- 统计基于经过过滤的98,348个有效比较（排除tie和both_bad）
- 排名按总比赛次数降序排列

**数据洞察：**
- 最活跃的模型 `claude-opus-4-20250514` 参加了 7,337 场有效比较
- 大多数主流模型（如Gemini、Claude、GPT系列）都有数千场参赛记录
- 参赛次数分布呈现明显的长尾效应，前10名模型占据了大部分比较
- 数据已过滤掉模糊比较，确保统计的准确性和可靠性