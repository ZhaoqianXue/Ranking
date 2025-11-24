# 测试数据说明

这个文件夹包含了用于测试LLM-based列分析功能的不同类型的CSV数据文件。每个文件都代表了不同类型的数据结构，用于验证我们的改进是否能正确识别ranking items列。

## 文件列表

### 1. `model_comparison_basic.csv`
- **描述**: 基本的模型比较数据（0-1范围）
- **列类型**: 模型名称列 + 多个性能指标列 + 描述列
- **预期ranking columns**: autogluon, tabpfn, glm, superlearner, unsemble, single
- **预期excluded columns**: model, description

### 2. `mixed_metrics.csv`
- **描述**: 混合数值范围的性能指标（准确率、损失、F1分数等）
- **列类型**: 方法名称 + 多种性能指标 + 描述
- **预期ranking columns**: accuracy, loss, f1_score, precision, recall, mse
- **预期excluded columns**: method, description

### 3. `sparse_data.csv`
- **描述**: 包含缺失值的数据（稀疏矩阵）
- **列类型**: 序号列 + 模型性能列 + 描述列
- **预期ranking columns**: model_1, model_2, model_3, model_4
- **预期excluded columns**: case_num, description

### 4. `id_columns.csv`
- **描述**: 包含ID列的数据
- **列类型**: 样本ID + 序号 + 方法性能 + 描述
- **预期ranking columns**: method_1, method_2, method_3
- **预期excluded columns**: sample_id, case_num, description

### 5. `resource_metrics.csv`
- **描述**: 包含资源使用指标的数据（大数值）
- **列类型**: 算法名称 + 时间/内存消耗 + 性能指标 + 描述
- **预期ranking columns**: time_seconds, memory_mb, f1_macro, precision_micro
- **预期excluded columns**: algorithm, description
- **⚠️ 注意**: 混合了不同优化方向的指标（time_seconds/memory_mb越低越好，f1_macro/precision_micro越高越好），不适合直接输入ranking_cli.R

### 6. `time_metadata.csv`
- **描述**: 包含时间戳和实验元数据
- **列类型**: 时间戳 + 实验ID + 模型名称 + 性能指标 + 描述
- **预期ranking columns**: accuracy, loss, f1
- **预期excluded columns**: timestamp, experiment_id, model_name, description
- **⚠️ 注意**: 混合了不同优化方向的指标（accuracy/f1越高越好，loss越低越好），不适合直接输入ranking_cli.R

### 7. `classification_metrics.csv`
- **描述**: 二分类指标和混淆矩阵计数
- **列类型**: 分类器名称 + 混淆矩阵计数 + 性能指标 + 描述
- **预期ranking columns**: true_positives, false_positives, true_negatives, false_negatives, accuracy, precision, recall, f1
- **预期excluded columns**: classifier, description

### 8. `ukbb_style_data.csv`
- **描述**: 模拟UKBB数据集格式（你遇到问题的原始格式）
- **列类型**: 模型列 + 序号 + 性能指标 + 描述
- **预期ranking columns**: autogluon, tabpfn, glm, superlearner, unsemble, single
- **预期excluded columns**: model, case_num, description

### 9. `negative_values.csv`
- **描述**: 包含负值和不同数值范围的数据
- **列类型**: 模型名称 + 对数损失 + 负分 + AUC + 准确率 + 描述
- **预期ranking columns**: log_loss, negative_score, auc, accuracy
- **预期excluded columns**: model, description
- **⚠️ 注意**: 混合了不同优化方向的指标（log_loss/negative_score数值越大越好，auc/accuracy越高越好），不适合直接输入ranking_cli.R

### 10. `loss_metrics.csv`
- **描述**: 损失函数指标数据（lower is better），格式与 `demo_r/example_data.csv` 类似
- **列类型**: 样本ID + 6个模型损失值 + 描述
- **预期ranking columns**: model_1, model_2, model_3, model_4, model_5, model_6
- **预期excluded columns**: sample_id, description
- **优化方向**: **lower value is better**（损失值，越小越好）
- **数值范围**: 0.15-0.35（典型的损失函数值范围）
- **用途**: 测试方向推断功能是否能正确识别"lower is better"的指标

## 测试目的

这些数据文件用于验证LLM-based列分析功能是否能：

1. ✅ 正确识别ranking items列（数值性能指标）
2. ✅ 正确排除metadata列（ID、描述、时间戳等）
3. ✅ 处理各种数值范围（0-1、负值、大数值）
4. ✅ 处理缺失值和稀疏数据
5. ✅ 区分真正的ID列和数值指标列

## ⚠️ 数据质量测试案例

三个特殊文件（`negative_values.csv`、`resource_metrics.csv`、`time_metadata.csv`）被设计为**不适合直接排序的测试案例**，用于验证系统是否能识别数据结构问题：

- **混合优化方向**: 同一数据集中包含"越高越好"和"越低越好"的指标
- **ranking_cli.R 脚本假设**: 所有数值列都遵循相同优化方向
- **实际应用**: 需要预处理（如取反、标准化）后才能正确排序

这些文件展示了真实世界中常见的数据质量问题，测试系统是否能正确识别ranking columns但同时警示用户数据结构问题。

## 使用方法

运行 `test_comprehensive_llm_analysis.py` 脚本来测试这些数据文件（虽然脚本已删除，但你可以使用相同的逻辑）。

每个文件都会显示：
- LLM识别的ranking columns
- LLM排除的columns
- 预期结果对比
- 通过/失败状态
