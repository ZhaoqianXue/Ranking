#!/usr/bin/env python3

import json
import pandas as pd
from pathlib import Path

def load_results(json_path):
    with open(json_path) as f:
        return json.load(f)

def compare_datasets():
    datasets = ['simulated', 'aou', 'ukbb']

    for dataset in datasets:
        print(f"\n=== {dataset.upper()} Dataset Comparison ===")

        py_results = load_results(f'output_{dataset}_py/ranking_results.json')
        r_results = load_results(f'output_{dataset}_r/ranking_results.json')

        # Create comparison DataFrame
        comparison_data = []

        for py_method, r_method in zip(py_results['methods'], r_results['methods']):
            comparison_data.append({
                'method': py_method['name'],
                'py_theta': round(py_method['theta_hat'], 4),
                'r_theta': round(r_method['theta_hat'], 4),
                'theta_diff': round(abs(py_method['theta_hat'] - r_method['theta_hat']), 4),
                'py_rank': py_method['rank'],
                'r_rank': r_method['rank'],
                'rank_diff': abs(py_method['rank'] - r_method['rank']),
                'py_runtime': round(py_results['metadata']['runtime_sec'], 3),
                'r_runtime': round(r_results['metadata']['runtime_sec'], 3)
            })

        df = pd.DataFrame(comparison_data)
        print(df.to_string(index=False))

        # Summary stats
        print("\nSummary:")
        print(f"  Max theta difference: {df['theta_diff'].max():.4f}")
        print(f"  Mean theta difference: {df['theta_diff'].mean():.4f}")
        print(f"  Max rank difference: {df['rank_diff'].max()}")
        print(f"  Python runtime: {df['py_runtime'].iloc[0]:.3f}s")
        print(f"  R runtime: {df['r_runtime'].iloc[0]:.3f}s")

if __name__ == "__main__":
    compare_datasets()
