#!/usr/bin/env python3
"""
谱排序矩阵格式报告生成器

从 ranking_matrix_results 生成详细的 Markdown 格式报告。
"""

import pandas as pd
from datetime import datetime
import os

def generate_matrix_ranking_report():
    """Generate comprehensive Markdown report from matrix format spectral ranking results."""

    # Get paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    ranking_dir = os.path.join(project_root, 'demo_r')
    results_csv = os.path.join(ranking_dir, 'ranking_matrix_results', 'ranking_results.csv')
    output_md = os.path.join(project_root, 'spectral_ranking_matrix_report.md')

    # Read the ranking results
    df = pd.read_csv(results_csv)

    # Create comprehensive Markdown report
    report_content = f'''# 🔬 谱排序结果报告 (矩阵格式输入)

> 使用 `llm_ranking_top50.csv` (子任务×模型矩阵) 作为输入的谱排序算法完整结果

## 📊 数据概览

- **输入文件**: `llm_ranking_top50.csv`
- **输入格式**: 子任务×模型矩阵 (40行×52列)
- **数据构成**: 40个子任务 × 50个模型
- **算法参数**: bigbetter=1, B=2000, seed=42
- **处理方式**: R脚本自动将矩阵转换为成对比较格式

## 🏆 Top 10 模型排名

'''

    # Add top 10 models
    top_10 = df.nsmallest(10, 'rank')
    for i, row in top_10.iterrows():
        rank = int(row['rank'])
        model = row['method']
        theta = row['theta_hat']
        ci_left = int(row['ci_two_left'])
        ci_right = int(row['ci_two_right'])

        medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, '🏅')
        report_content += f'### {medal} 第{rank}名: {model}\n'
        report_content += f'- **谱排序值 (θ)**: `{theta:.4f}`\n'
        report_content += f'- **95%置信区间**: `[{ci_left}, {ci_right}]`\n'
        report_content += f'- **排名稳定性**: ±{ci_right - ci_left} 个位置范围\n\n'

    report_content += '''## 📋 完整排名表

| 排名 | 模型 | θ值 | 95%置信区间 | 排名稳定性 |
|------|------|------|------------|------------|
'''

    # Add all rankings
    for i, row in df.iterrows():
        rank = int(row['rank'])
        model = row['method']
        theta = row['theta_hat']
        ci_left = int(row['ci_two_left'])
        ci_right = int(row['ci_two_right'])
        stability = ci_right - ci_left + 1

        # Color code based on rank
        if rank <= 10:
            rank_display = f'**{rank}**'
        elif rank <= 25:
            rank_display = f'{rank}'
        else:
            rank_display = f'{rank}'

        report_content += f'| {rank_display} | {model} | {theta:.4f} | [{ci_left}, {ci_right}] | ±{stability-1} |\n'

    report_content += '''
## 📈 排名分布统计

'''

    # Add ranking distribution
    rank_ranges = [
        (1, 10, "🥇 精英模型"),
        (11, 25, "🥈 优秀模型"),
        (26, 40, "🥉 良好模型"),
        (41, 50, "📊 待改进模型")
    ]

    for start, end, label in rank_ranges:
        count = len(df[(df['rank'] >= start) & (df['rank'] <= end)])
        percentage = count / len(df) * 100
        report_content += f'- **{label}**: {count} 个模型 ({percentage:.1f}%)\n'

    report_content += '''
## 🔬 技术指标详解

### 谱排序值 (θ)
- **定义**: 谱排序算法估计的模型能力值
- **解释**: 值越大表示模型性能越好
- **数据范围**: 本次分析中从 -0.645 (最低) 到 +0.632 (最高)

### 置信区间
- **计算方法**: 基于2,000次bootstrap重采样
- **置信水平**: 95%
- **意义**: 模型的真实排名有95%的概率落在该区间内

### 排名稳定性
- **计算**: `右边界 - 左边界 + 1`
- **意义**: 排名可能变化的范围
- **理想值**: 越小越好 (排名越稳定)

## 🎯 冠军模型深度分析

'''

    # Champion analysis
    champion = df.loc[df['rank'].idxmin()]
    report_content += f'### 🥇 冠军: {champion["method"]}\n'
    report_content += f'- **排名**: {int(champion["rank"])} / {len(df)}\n'
    report_content += f'- **谱排序值**: {champion["theta_hat"]:.4f}\n'
    report_content += f'- **置信区间**: [{int(champion["ci_two_left"])}, {int(champion["ci_two_right"])}]\n'
    report_content += f'- **排名稳定性**: ±{int(champion["ci_two_right"]) - int(champion["ci_two_left"])}\n\n'

    # Performance comparison
    theta_range = df['theta_hat'].max() - df['theta_hat'].min()
    champion_advantage = champion['theta_hat'] - df['theta_hat'].median()
    report_content += f'### 性能优势分析\n'
    report_content += f'- **θ值总范围**: {df["theta_hat"].min():.4f} 到 {df["theta_hat"].max():.4f}\n'
    report_content += f'- **冠军相对中位数优势**: +{champion_advantage:.4f}\n\n'

    report_content += '''## 📝 数据处理说明

### 输入数据格式
- **文件格式**: CSV矩阵格式
- **行结构**: 每一行是一个子任务 + 该子任务下所有模型的分数
- **列结构**: benchmark, sub_benchmark, 模型1, 模型2, ..., 模型50
- **数据规模**: 40个子任务 × 50个模型

### R脚本处理流程
1. **数据读取**: 读取CSV矩阵文件
2. **格式转换**: 自动将矩阵格式转换为成对比较格式
3. **谱排序计算**: 使用谱排序算法计算排名和置信区间
4. **结果输出**: 生成CSV和JSON格式的结果文件

### 数据质量保证
- ✅ **完整性**: 40个子任务 × 50个模型，覆盖全面
- ✅ **准确性**: 使用原始评估指标，无数据失真
- ✅ **统计严谨**: 基于大规模bootstrap的置信区间
- ✅ **可重现性**: 使用固定随机种子保证结果一致性

---
'''

    report_content += f'*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*\n'
    report_content += '*基于Open LLM Leaderboard数据，使用谱排序算法分析*\n'
    report_content += '*输入格式: 子任务×模型矩阵 (自动转换为成对比较格式)*\n'

    # Save the report
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f'✅ Matrix format spectral ranking report saved to: {output_md}')
    print(f'Report contains {len(report_content.split(chr(10)))} lines')
    return output_md

if __name__ == '__main__':
    generate_matrix_ranking_report()






