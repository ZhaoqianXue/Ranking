#!/usr/bin/env python3
"""
Script to sample the example_arena_style.csv file from 10000 rows to 1000 rows
while maintaining the same data distribution and ensuring consistent ranking results.
"""

import pandas as pd
import numpy as np
from collections import Counter

def analyze_data_distribution(df):
    """分析数据分布"""
    print("数据分析:")
    print(f"总行数: {len(df)}")
    print(f"任务类型分布: {Counter(df['Task'])}")

    # 分析每列的非NaN值分布
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        non_na_count = df[col].notna().sum()
        value_counts = df[col].value_counts(dropna=True)
        print(f"{col}: 非NaN值={non_na_count}, 值分布={dict(value_counts)}")

    return numeric_cols

def stratified_sample(df, target_size=1000):
    """
    分层采样以保持数据分布
    """
    # 按Task类型分组
    task_groups = df.groupby('Task')

    # 计算每组应该采样的数量（保持比例）
    total_rows = len(df)
    sample_sizes = {}
    for task_type, group in task_groups:
        proportion = len(group) / total_rows
        sample_size = max(1, int(target_size * proportion))  # 至少采样1行
        sample_sizes[task_type] = sample_size

    # 调整样本大小以达到目标总数
    current_total = sum(sample_sizes.values())
    if current_total > target_size:
        # 按比例减少
        scale_factor = target_size / current_total
        sample_sizes = {k: max(1, int(v * scale_factor)) for k, v in sample_sizes.items()}
    elif current_total < target_size:
        # 分配剩余样本给最大的组
        remaining = target_size - current_total
        largest_group = max(sample_sizes.keys(), key=lambda x: sample_sizes[x])
        sample_sizes[largest_group] += remaining

    print(f"采样计划: {sample_sizes}")

    # 分层采样
    sampled_dfs = []
    for task_type, size in sample_sizes.items():
        group = task_groups.get_group(task_type)
        if len(group) <= size:
            sampled_dfs.append(group)
        else:
            sampled_dfs.append(group.sample(n=size, random_state=42))

    result_df = pd.concat(sampled_dfs, ignore_index=True)

    # 随机打乱顺序
    result_df = result_df.sample(frac=1, random_state=42).reset_index(drop=True)

    return result_df

def verify_distribution(original_df, sampled_df, numeric_cols):
    """验证采样后的分布是否保持一致"""
    print("\n分布验证:")

    # 检查任务类型分布
    orig_task_dist = Counter(original_df['Task'])
    sampled_task_dist = Counter(sampled_df['Task'])

    print("原始任务分布:", dict(orig_task_dist))
    print("采样任务分布:", dict(sampled_task_dist))

    # 计算比例差异
    for task in orig_task_dist:
        orig_prop = orig_task_dist[task] / len(original_df)
        sampled_prop = sampled_task_dist[task] / len(sampled_df)
        diff = abs(orig_prop - sampled_prop)
        print(".3f")

    # 检查数值列的分布
    for col in numeric_cols:
        orig_non_na_prop = original_df[col].notna().mean()
        sampled_non_na_prop = sampled_df[col].notna().mean()
        print(".3f")

def main():
    # 读取原始数据
    input_file = "demo_r/example_arena_style.csv"
    output_file = "demo_r/example_arena_style_sampled.csv"

    print(f"读取文件: {input_file}")
    df = pd.read_csv(input_file)

    # 数据分析
    numeric_cols = analyze_data_distribution(df)

    # 分层采样
    print("\n开始分层采样...")
    sampled_df = stratified_sample(df, target_size=999)  # 999行数据 + 1行标题 = 1000行

    # 验证分布
    verify_distribution(df, sampled_df, numeric_cols)

    # 保存结果
    print(f"\n保存采样结果到: {output_file}")
    sampled_df.to_csv(output_file, index=False)

    print("采样完成!")
    print(f"原始文件行数: {len(df) + 1}")  # +1 for header
    print(f"采样文件行数: {len(sampled_df) + 1}")  # +1 for header

if __name__ == "__main__":
    main()
