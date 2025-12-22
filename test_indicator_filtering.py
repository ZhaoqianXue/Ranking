#!/usr/bin/env python3
"""
Test script to verify that different indicator selections produce different ranking results.
Tests three scenarios:
1. Only 'code' indicator selected
2. Only 'math' indicator selected  
3. Both 'code' and 'math' indicators selected
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"

def create_job(file_path, bigbetter, B, seed, indicator_column=None, selected_indicators=None):
    """Create a ranking job with optional indicator filtering"""
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

def poll_until_complete(job_id, max_wait=120):
    """Poll job status until complete or timeout"""
    url = f"{BASE_URL}/api/ranking/jobs/{job_id}/status"
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(url)
        response.raise_for_status()
        status_data = response.json()
        
        status = status_data.get('status')
        print(f"  Status: {status}")
        
        if status == 'succeeded':
            return True
        elif status == 'failed':
            print(f"  Job failed: {status_data.get('message', 'Unknown error')}")
            return False
        
        time.sleep(2)
    
    print(f"  Timeout after {max_wait}s")
    return False

def get_results(job_id):
    """Get ranking results for completed job"""
    url = f"{BASE_URL}/api/ranking/jobs/{job_id}/results"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def compare_results(result1, result2, name1, name2):
    """Compare two ranking results"""
    methods1 = {m['name']: m['rank'] for m in result1.get('methods', [])}
    methods2 = {m['name']: m['rank'] for m in result2.get('methods', [])}
    
    print(f"\n{'='*60}")
    print(f"Comparing: {name1} vs {name2}")
    print(f"{'='*60}")
    
    all_methods = set(methods1.keys()) | set(methods2.keys())
    
    differences = []
    for method in sorted(all_methods):
        rank1 = methods1.get(method, 'N/A')
        rank2 = methods2.get(method, 'N/A')
        
        if rank1 != rank2:
            differences.append((method, rank1, rank2))
            print(f"  {method:15s}: {name1}=Rank {rank1}, {name2}=Rank {rank2}")
    
    if not differences:
        print(f"  ⚠️  Results are IDENTICAL (this should NOT happen with different indicators!)")
        return False
    else:
        print(f"  ✅  Found {len(differences)} ranking differences")
        return True

def main():
    # Configuration
    data_file = "/Users/zhaoqianxue/Desktop/UPenn/Ranking/demo_r/example_arena_style.csv"
    params = {
        'bigbetter': True,
        'B': 500,  # Lower for faster testing
        'seed': 42
    }
    
    print("="*70)
    print("Testing Indicator-Based Data Filtering")
    print("="*70)
    print(f"Data file: {data_file}")
    print(f"Parameters: bigbetter={params['bigbetter']}, B={params['B']}, seed={params['seed']}")
    print()
    
    # Test 1: Only 'code' indicator
    print("\n[1/3] Creating job with indicator='code' only...")
    job1 = create_job(data_file, **params, indicator_column='Task', selected_indicators=['code'])
    job1_id = job1['job_id']
    print(f"  Job ID: {job1_id}")
    
    if not poll_until_complete(job1_id):
        print("  ❌ Job 1 failed")
        return 1
    
    result1 = get_results(job1_id)
    print(f"  ✅ Completed: {len(result1.get('methods', []))} methods ranked")
    print(f"  Metadata: {result1.get('metadata', {})}")
    
    # Test 2: Only 'math' indicator
    print("\n[2/3] Creating job with indicator='math' only...")
    job2 = create_job(data_file, **params, indicator_column='Task', selected_indicators=['math'])
    job2_id = job2['job_id']
    print(f"  Job ID: {job2_id}")
    
    if not poll_until_complete(job2_id):
        print("  ❌ Job 2 failed")
        return 1
    
    result2 = get_results(job2_id)
    print(f"  ✅ Completed: {len(result2.get('methods', []))} methods ranked")
    print(f"  Metadata: {result2.get('metadata', {})}")
    
    # Test 3: Both 'code' and 'math' indicators
    print("\n[3/3] Creating job with both indicators=['code', 'math']...")
    job3 = create_job(data_file, **params, indicator_column='Task', selected_indicators=['code', 'math'])
    job3_id = job3['job_id']
    print(f"  Job ID: {job3_id}")
    
    if not poll_until_complete(job3_id):
        print("  ❌ Job 3 failed")
        return 1
    
    result3 = get_results(job3_id)
    print(f"  ✅ Completed: {len(result3.get('methods', []))} methods ranked")
    print(f"  Metadata: {result3.get('metadata', {})}")
    
    # Compare results
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)
    
    diff_1_2 = compare_results(result1, result2, "code only", "math only")
    diff_1_3 = compare_results(result1, result3, "code only", "both")
    diff_2_3 = compare_results(result2, result3, "math only", "both")
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    if diff_1_2 and diff_1_3 and diff_2_3:
        print("✅ SUCCESS: All three scenarios produce different results!")
        print("   This confirms that indicator filtering is working correctly.")
        return 0
    else:
        print("❌ FAILURE: Some scenarios produced identical results!")
        print("   This indicates that indicator filtering may not be working.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
