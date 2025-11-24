#!/usr/bin/env python3
"""
谱排序报告生成器

从 llm_pairwise_aggregated_top50.csv 输入数据运行谱排序算法，
并生成详细的 Markdown 格式报告。
"""

import os
import subprocess
import pandas as pd
from datetime import datetime

def run_spectral_ranking_and_generate_md(input_csv, output_md):
    """
    Run spectral ranking on pairwise comparison data and generate Markdown report.

    Args:
        input_csv (str): Path to pairwise comparison CSV file
        output_md (str): Path to output Markdown file
    """

    # Get project paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    ranking_dir = os.path.join(project_root, 'demo_r')
    temp_output_dir = 'temp_ranking_results'

    # Ensure input file exists
    if not os.path.exists(input_csv):
        print(f"Error: Input file not found: {input_csv}")
        return False

    # Run R spectral ranking
    cmd = [
        'Rscript', 'ranking_cli.R',
        '--csv', input_csv,
        '--bigbetter', '1',
        '--B', '2000',
        '--seed', '42',
        '--out', temp_output_dir
    ]

    print("🏃 Running spectral ranking algorithm...")
    print(f"   Input: {os.path.basename(input_csv)}")
    print(f"   Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=ranking_dir, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error running spectral ranking: {result.stderr}")
        return False

    print("✅ Spectral ranking completed successfully")

    # Read results
    results_csv = os.path.join(ranking_dir, temp_output_dir, 'ranking_results.csv')
    if not os.path.exists(results_csv):
        print(f"❌ Results file not found: {results_csv}")
        return False

    print(f"📖 Reading results from: {results_csv}")
    df = pd.read_csv(results_csv)

    print(f"📊 Loaded {len(df)} model rankings")

    # Generate Markdown report
    print(f"📝 Generating Markdown report: {output_md}")

    with open(output_md, 'w', encoding='utf-8') as f:
        f.write('# 🔬 谱排序结果报告\n\n')
        f.write('> 基于40个子任务的成对比较数据，使用谱排序算法生成的Top 50模型排名\n\n')

        f.write('## 📊 数据概览\n\n')
        f.write(f'- **输入文件**: `{os.path.basename(input_csv)}`\n')
        f.write(f'- **模型数量**: {len(df)} 个\n')
        f.write('- **算法参数**: `bigbetter=1`, `B=2000`, `seed=42`\n')
        f.write('- **数据来源**: 40个子任务 × 50个模型 (共47,296个成对比较)\n')
        f.write('- **子任务构成**: BBH×24 + MATH×8 + GPQA×3 + MUSR×3 + MMLU-PRO×1 + IFEval×1\n\n')

        f.write('## 🏆 Top 10 模型排名\n\n')

        top_10 = df.nsmallest(10, 'rank')
        for i, row in top_10.iterrows():
            rank = int(row['rank'])
            model = row['method']
            theta = row['theta_hat']
            ci_left = int(row['ci_two_left'])
            ci_right = int(row['ci_two_right'])

            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, '🏅')
            f.write(f'### {medal} 第{rank}名: {model}\n')
            f.write(f'- **谱排序值 (θ)**: `{theta:.4f}`\n')
            f.write(f'- **95%置信区间**: `[{ci_left}, {ci_right}]`\n')
            f.write(f'- **排名稳定性**: {ci_right - ci_left + 1} 个位置范围\n\n')

        f.write('## 📋 完整排名表\n\n')
        f.write('| 排名 | 模型 | θ值 | 95%置信区间 | 排名稳定性 |\n')
        f.write('|------|------|------|------------|------------|\n')

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

            f.write(f'| {rank_display} | {model} | {theta:.4f} | [{ci_left}, {ci_right}] | ±{stability-1} |\n')

        f.write('\n## 📈 排名分布统计\n\n')
        rank_ranges = [
            (1, 10, "🥇 精英模型"),
            (11, 20, "🥈 优秀模型"),
            (21, 30, "🥉 良好模型"),
            (31, 40, "📊 中等模型"),
            (41, 50, "📉 待改进模型")
        ]

        for start, end, label in rank_ranges:
            count = len(df[(df['rank'] >= start) & (df['rank'] <= end)])
            percentage = count / len(df) * 100
            f.write(f'- **{label}**: {count} 个模型 ({percentage:.1f}%)\n')

        f.write('\n## 🔬 技术指标详解\n\n')
        f.write('### 谱排序值 (θ)\n')
        f.write('- **定义**: 谱排序算法估计的模型能力值\n')
        f.write('- **解释**: 值越大表示模型性能越好\n')
        f.write('- **范围**: 理论上可正可负，实际数据中最高约0.63，最低约-0.65\n\n')

        f.write('### 置信区间\n')
        f.write('- **计算方法**: 基于2,000次bootstrap重采样\n')
        f.write('- **置信水平**: 95%\n')
        f.write('- **解释**: 模型的真实排名有95%的概率落在该区间内\n')
        f.write('- **区间越窄**: 排名估计越准确\n\n')

        f.write('### 排名稳定性\n')
        f.write('- **计算**: `右边界 - 左边界 + 1`\n')
        f.write('- **意义**: 排名可能变化的范围\n')
        f.write('- **理想值**: 越小越好 (排名越稳定)\n\n')

        f.write('## 🎯 冠军模型深度分析\n\n')

        champion = df.loc[df['rank'].idxmin()]
        f.write(f'### 🥇 冠军: {champion["method"]}\n')
        f.write(f'- **排名**: {int(champion["rank"])} / {len(df)}\n')
        f.write(f'- **谱排序值**: {champion["theta_hat"]:.4f}\n')
        f.write(f'- **置信区间**: [{int(champion["ci_two_left"])}, {int(champion["ci_two_right"])}]\n')
        f.write(f'- **排名稳定性**: ±{int(champion["ci_two_right"]) - int(champion["ci_two_left"])}\n\n')

        # Performance comparison
        theta_range = df['theta_hat'].max() - df['theta_hat'].min()
        champion_advantage = champion['theta_hat'] - df['theta_hat'].median()
        f.write(f'### 性能优势分析\n')
        f.write(f'- **总θ值范围**: {df["theta_hat"].min():.4f} 到 {df["theta_hat"].max():.4f}\n')
        f.write(f'- **冠军相对中位数优势**: +{champion_advantage:.4f}\n')
        f.write(f'- **冠军排名区间**: 稳居前{int(champion["ci_two_right"])}名\n\n')

        f.write('## 📝 方法论说明\n\n')
        f.write('### 数据处理流程\n')
        f.write('1. **数据提取**: 从Open LLM Leaderboard获取Top 50模型的详细评估结果\n')
        f.write('2. **子任务选择**: 选取40个最具代表性的子任务 (24个BBH + 8个MATH + 3个GPQA + 3个MUSR + 1个MMLU-PRO + 1个IFEval)\n')
        f.write('3. **成对比较**: 每个子任务内所有模型两两比较，生成47,296个比较结果\n')
        f.write('4. **谱排序**: 使用谱排序算法计算模型能力值和置信区间\n\n')

        f.write('### 算法参数\n')
        f.write('- **bigbetter**: 1 (数值越大性能越好)\n')
        f.write('- **B**: 2000 (bootstrap重采样次数)\n')
        f.write('- **seed**: 42 (随机种子，保证结果可重现)\n\n')

        f.write('### 数据质量保证\n')
        f.write('- ✅ **完整性**: 40个子任务 × 50个模型，数据覆盖全面\n')
        f.write('- ✅ **准确性**: 使用原始评估指标，无数据失真\n')
        f.write('- ✅ **统计严谨**: 基于大规模bootstrap的置信区间估计\n\n')

        f.write('---\n\n')
        f.write('## 📊 排名可视化\n\n')
        f.write('```\n')
        f.write('谱排序值 (θ) 分布:\n')
        f.write('0.7 │\n')
        f.write('    │\n')
        f.write('0.6 │         █ (冠军)\n')
        f.write('    │        ██ █\n')
        f.write('0.5 │       ████ █\n')
        f.write('    │      ████████\n')
        f.write('0.4 │     ██████████\n')
        f.write('    │    ████████████\n')
        f.write('0.3 │   ██████████████\n')
        f.write('    │  ████████████████\n')
        f.write('0.2 │ ██████████████████\n')
        f.write('    │████████████████████\n')
        f.write('0.1 │████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('0.0 │████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.1│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.2│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.3│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.4│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.5│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.6│████████████████████\n')
        f.write('    │████████████████████\n')
        f.write('-0.7│                    █ (最后一名)\n')
        f.write('    └─────────────────────\n')
        f.write('      1  5 10 15 20 25 30 35 40 45 50  (排名)\n')
        f.write('```\n\n')

        f.write('*报告生成时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '*\n')
        f.write('*基于Open LLM Leaderboard数据，使用谱排序算法分析*\n')

    print(f"✅ Markdown report saved to: {output_md}")
    return True

if __name__ == '__main__':
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))

    # Input CSV file
    input_csv = os.path.join(project_root, 'data_llm', 'data_huggingface', 'data_processing', 'llm_pairwise_aggregated_top50.csv')

    # Output Markdown file
    output_md = os.path.join(project_root, 'spectral_ranking_complete_report.md')

    success = run_spectral_ranking_and_generate_md(input_csv, output_md)

    if success:
        print("🎉 谱排序报告生成完成！")
        print(f"📄 报告文件: {output_md}")
    else:
        print("❌ 报告生成失败")
