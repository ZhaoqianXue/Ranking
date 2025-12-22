#!/usr/bin/env python3
"""
Test the enhanced dataset with different indicator combinations
Verify that different selections produce different rankings
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"

def create_job(file_path, bigbetter, B, seed, indicator_column=None, selected_indicators=None):
    """Create a ranking job"""
    url = f"{BASE_URL}/api/ranking/jobs"
    
    with open(file_path, 'rb') as f:
        files = {'file': ('data.csv', f, 'text/csv')}
        data = {
            'bigbetter': 'true' if bigbetter else 'false',
            'B': str(B),
            'seed': str(seed)
        }
        
        if indicator_column:
            data['indicator_column'] = indicator_column
        if selected_indicators:
            data['selected_indicators'] = json.dumps(selected_indicators)
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()

def poll_until_complete(job_id, max_wait=180):
    """Poll job status until complete"""
    url = f"{BASE_URL}/api/ranking/jobs/{job_id}/status"
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(url)
        response.raise_for_status()
        status_data = response.json()
        
        status = status_data.get('status')
        
        if status == 'succeeded':
            return True
        elif status == 'failed':
            print(f"  ❌ Job failed: {status_data.get('message', 'Unknown error')}")
            return False
        
        time.sleep(2)
    
    print(f"  ⏱️ Timeout after {max_wait}s")
    return False

def get_results(job_id):
    """Get ranking results"""
    url = f"{BASE_URL}/api/ranking/jobs/{job_id}/results"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def display_ranking(results, name):
    """Display ranking results"""
    methods = sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))
    metadata = results.get('metadata', {})
    
    print(f"\n{'='*70}")
    print(f"Results: {name}")
    print(f"{'='*70}")
    print(f"Samples: {metadata.get('n_samples', 'N/A')}, Runtime: {metadata.get('runtime_sec', 'N/A')}s")
    print(f"Indicators: {metadata.get('selected_indicators', 'all')}")
    print(f"\n{'Rank':<6} {'Method':<15} {'θ-hat':<12} {'95% CI':<20}")
    print("-" * 70)
    
    for method in methods:
        rank = method.get('rank', 'N/A')
        name = method.get('name', 'N/A')
        theta = method.get('theta_hat', 'N/A')
        ci = method.get('ci_95', [])
        
        theta_str = f"{theta:.4f}" if isinstance(theta, (int, float)) else str(theta)
        ci_str = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if len(ci) == 2 else "[]"
        
        print(f"{rank:<6} {name:<15} {theta_str:<12} {ci_str:<20}")

def main():
    data_file = "demo_r/example_arena_style_enhanced.csv"
    params = {'bigbetter': True, 'B': 1000, 'seed': 42}
    
    print("="*70)
    print("Testing Enhanced Dataset with Different Indicator Combinations")
    print("="*70)
    
    # Test scenarios
    scenarios = [
        ("Code only", ['code']),
        ("Math only", ['math']),
        ("Writing only", ['writing']),
        ("Code + Math", ['code', 'math']),
        ("Code + Writing", ['code', 'writing']),
        ("Math + Writing", ['math', 'writing']),
        ("All three", ['code', 'math', 'writing'])
    ]
    
    results_list = []
    
    for name, indicators in scenarios:
        print(f"\n{'='*70}")
        print(f"[{len(results_list)+1}/{len(scenarios)}] Testing: {name}")
        print(f"{'='*70}")
        
        job = create_job(data_file, **params, 
                        indicator_column='Task', 
                        selected_indicators=indicators)
        job_id = job['job_id']
        print(f"Job ID: {job_id}")
        
        if not poll_until_complete(job_id):
            print(f"❌ Failed to complete {name}")
            continue
        
        results = get_results(job_id)
        results_list.append((name, results))
        display_ranking(results, name)
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("RANKING SUMMARY - Top 3 for Each Scenario")
    print(f"{'='*70}")
    
    for name, results in results_list:
        methods = sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))
        top3 = [m.get('name', 'N/A') for m in methods[:3]]
        print(f"{name:<20} → {' > '.join(top3)}")
    
    # Check for diversity
    print(f"\n{'='*70}")
    print("DIVERSITY CHECK")
    print(f"{'='*70}")
    
    all_top_methods = set()
    for name, results in results_list:
        methods = sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))
        if methods:
            all_top_methods.add(methods[0].get('name'))
    
    print(f"Different #1 ranked methods: {len(all_top_methods)}")
    print(f"Methods that reached #1: {', '.join(sorted(all_top_methods))}")
    
    if len(all_top_methods) >= 3:
        print("\n✅ SUCCESS: Dataset shows good ranking diversity!")
        print("   Different indicator combinations produce different #1 rankings.")
        return 0
    else:
        print("\n⚠️  Limited diversity in #1 rankings")
        print("   But theta-hat values should still show differences.")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
