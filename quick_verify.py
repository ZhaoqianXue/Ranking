#!/usr/bin/env python3
"""
Quick test to verify the optimized dataset improvements
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001"

def create_and_test(file_path, indicators, name):
    """Create job and get results"""
    # Create job
    url = f"{BASE_URL}/api/ranking/jobs"
    with open(file_path, 'rb') as f:
        files = {'file': ('data.csv', f, 'text/csv')}
        data = {
            'bigbetter': 'true',
            'B': '2000',
            'seed': '42',
            'indicator_column': 'Task',
            'selected_indicators': json.dumps(indicators)
        }
        response = requests.post(url, files=files, data=data)
        job = response.json()
    
    job_id = job['job_id']
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Job ID: {job_id}")
    print(f"{'='*70}")
    
    # Poll until complete
    status_url = f"{BASE_URL}/api/ranking/jobs/{job_id}/status"
    while True:
        status = requests.get(status_url).json()
        if status['status'] == 'succeeded':
            break
        elif status['status'] == 'failed':
            print(f"Failed: {status.get('message')}")
            return None
        time.sleep(2)
    
    # Get results
    results_url = f"{BASE_URL}/api/ranking/jobs/{job_id}/results"
    results = requests.get(results_url).json()
    
    # Display
    methods = sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))
    metadata = results.get('metadata', {})
    
    print(f"Samples: {metadata.get('n_samples')}, Runtime: {metadata.get('runtime_sec')}s")
    print(f"\n{'Rank':<6} {'Method':<15} {'θ-hat':<12} {'95% CI':<25}")
    print("-" * 70)
    
    theta_values = []
    for method in methods:
        rank = method.get('rank')
        name = method.get('name')
        theta = method.get('theta_hat')
        ci = method.get('ci_95', [])
        
        theta_values.append((name, theta))
        
        theta_str = f"{theta:.4f}" if theta else "N/A"
        ci_str = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if len(ci) == 2 else "[]"
        ci_width = ci[1] - ci[0] if len(ci) == 2 else 0
        
        print(f"{rank:<6} {name:<15} {theta_str:<12} {ci_str:<25} (width: {ci_width:.3f})")
    
    # Calculate theta range
    theta_vals = [t for _, t in theta_values if t is not None]
    if theta_vals:
        theta_range = max(theta_vals) - min(theta_vals)
        print(f"\n📊 θ-hat range: {theta_range:.4f} (max: {max(theta_vals):.4f}, min: {min(theta_vals):.4f})")
    
    # Check top 3
    top3 = [m.get('name') for m in methods[:3]]
    top_tier = {'ChatGPT', 'Gemini', 'Claude'}
    if set(top3).issubset(top_tier):
        print(f"✅ Top 3 are from top tier: {', '.join(top3)}")
    else:
        print(f"⚠️  Top 3 include lower tier: {', '.join(top3)}")
    
    return results

# Test with all three tasks
data_file = "demo_r/example_arena_style.csv"
create_and_test(data_file, ['code', 'math', 'writing'], "All three tasks")
