#!/usr/bin/env python3
"""
Detailed analysis script to verify data filtering and analyze statistical differences
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def get_results(job_id):
    """Get ranking results for completed job"""
    url = f"{BASE_URL}/api/ranking/jobs/{job_id}/results"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def analyze_results(results, name):
    """Detailed analysis of results"""
    print(f"\n{'='*70}")
    print(f"Analysis: {name}")
    print(f"{'='*70}")
    
    metadata = results.get('metadata', {})
    methods = results.get('methods', [])
    
    print(f"Metadata:")
    print(f"  Samples: {metadata.get('n_samples', 'N/A')}")
    print(f"  Methods: {metadata.get('k_methods', 'N/A')}")
    print(f"  Runtime: {metadata.get('runtime_sec', 'N/A')}s")
    print(f"  Indicators: {metadata.get('selected_indicators', 'N/A')} (column: {metadata.get('indicator_column', 'N/A')})")
    
    print(f"\nRanking Results:")
    print(f"  {'Rank':<6} {'Method':<15} {'θ-hat':<10} {'95% CI':<15} {'Uniform CI'}")
    print(f"  {'-'*60}")
    
    for method in sorted(methods, key=lambda x: x.get('rank', 999)):
        rank = method.get('rank', 'N/A')
        name_str = method.get('name', 'N/A')
        theta = method.get('theta_hat', 'N/A')
        ci_95 = method.get('ci_95', [])
        ci_unif = method.get('uniform_ci', [])
        
        theta_str = f"{theta:.4f}" if isinstance(theta, (int, float)) else str(theta)
        ci_95_str = f"[{ci_95[0]}, {ci_95[1]}]" if len(ci_95) == 2 else str(ci_95)
        ci_unif_str = f"[{ci_unif[0]}, {ci_unif[1]}]" if len(ci_unif) == 2 else str(ci_unif)
        
        print(f"  {rank:<6} {name_str:<15} {theta_str:<10} {ci_95_str:<15} {ci_unif_str}")

def main():
    # Get the three job IDs from the previous test
    # You'll need to update these with the actual job IDs
    jobs = [
        ("5f9d5e9a-6838-4e5d-b3b4-095e76bceb95", "code only"),
        ("64311e9e-5605-4f48-b3cb-49d1f91d618e", "math only"),
        ("f5cbc442-b307-441b-b4c0-b32ea673d64b", "both")
    ]
    
    all_results = []
    for job_id, name in jobs:
        try:
            results = get_results(job_id)
            all_results.append((name, results))
            analyze_results(results, name)
        except Exception as e:
            print(f"Error getting results for {name}: {e}")
    
    # Compare theta-hat values
    print(f"\n{'='*70}")
    print("THETA-HAT COMPARISON")
    print(f"{'='*70}")
    
    if len(all_results) == 3:
        methods_theta = {}
        for name, results in all_results:
            for method in results.get('methods', []):
                method_name = method.get('name')
                theta = method.get('theta_hat')
                if method_name not in methods_theta:
                    methods_theta[method_name] = {}
                methods_theta[method_name][name] = theta
        
        print(f"  {'Method':<15} {'code only':<12} {'math only':<12} {'both':<12} {'Variance'}")
        print(f"  {'-'*70}")
        
        for method_name in sorted(methods_theta.keys()):
            values = methods_theta[method_name]
            code_val = values.get('code only', 'N/A')
            math_val = values.get('math only', 'N/A')
            both_val = values.get('both', 'N/A')
            
            # Calculate variance if all values are numeric
            numeric_values = [v for v in [code_val, math_val, both_val] if isinstance(v, (int, float))]
            if len(numeric_values) == 3:
                mean = sum(numeric_values) / len(numeric_values)
                variance = sum((v - mean) ** 2 for v in numeric_values) / len(numeric_values)
                var_str = f"{variance:.6f}"
            else:
                var_str = "N/A"
            
            code_str = f"{code_val:.4f}" if isinstance(code_val, (int, float)) else str(code_val)
            math_str = f"{math_val:.4f}" if isinstance(math_val, (int, float)) else str(math_val)
            both_str = f"{both_val:.4f}" if isinstance(both_val, (int, float)) else str(both_val)
            
            print(f"  {method_name:<15} {code_str:<12} {math_str:<12} {both_str:<12} {var_str}")
        
        print(f"\nNote: If variance is very small, theta-hat values are nearly identical")
        print(f"      This could explain why rankings are the same despite different data.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
