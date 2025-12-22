#!/usr/bin/env python3
"""
Test script to debug Phase 2 agent functionality
Uses example_data.csv to generate ranking results and test Phase 2 responses
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
import shutil

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from code_app.backend.phase2_agent import (
    prepare_phase2_messages,
    is_phase2_request,
    extract_ranking_results_from_messages
)

# Paths
EXAMPLE_DATA_PATH = os.path.join(project_root, 'demo_r', 'example_data.csv')
R_SCRIPT_PATH = os.path.join(project_root, 'demo_r', 'ranking_cli.R')
OUTPUT_DIR = os.path.join(project_root, 'test_phase2_output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_ranking_analysis():
    """Run ranking analysis on example_data.csv to generate results"""
    print("="*80)
    print("STEP 1: Running ranking analysis on example_data.csv")
    print("="*80)
    
    # Create temp directory for output
    temp_output = os.path.join(OUTPUT_DIR, 'ranking_results')
    os.makedirs(temp_output, exist_ok=True)
    
    # Run R script
    cmd = [
        'Rscript',
        R_SCRIPT_PATH,
        '--csv', EXAMPLE_DATA_PATH,
        '--bigbetter', '1',  # Higher is better
        '--B', '2000',
        '--seed', '42',
        '--out', temp_output
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode != 0:
        print(f"ERROR: R script failed!")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return None
    
    # Load results
    results_path = os.path.join(temp_output, 'ranking_results.json')
    if not os.path.exists(results_path):
        print(f"ERROR: Results file not found at {results_path}")
        return None
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    print(f"\n✓ Ranking analysis completed!")
    print(f"  - Total methods: {len(results.get('methods', []))}")
    print(f"  - Top 3 methods:")
    methods = sorted(results.get('methods', []), key=lambda x: x.get('rank', 999))
    for i, method in enumerate(methods[:3]):
        print(f"    {i+1}. {method.get('name')}: rank={method.get('rank')}, theta={method.get('theta_hat', 0):.4f}")
    
    return results

def test_prepare_phase2_messages(ranking_results):
    """Test prepare_phase2_messages function"""
    print("\n" + "="*80)
    print("STEP 2: Testing prepare_phase2_messages")
    print("="*80)
    
    user_message = "Explain what these ranking results mean"
    
    messages = prepare_phase2_messages(
        user_message=user_message,
        ranking_results=ranking_results,
        conversation_history=[],
        base_system_prompt="You are a helpful assistant."
    )
    
    print(f"\n✓ Prepared {len(messages)} messages")
    
    # Check system message
    system_msg = next((msg for msg in messages if msg.get('role') == 'system'), None)
    if system_msg:
        content = system_msg.get('content', '')
        print(f"\nSystem message length: {len(content)} characters")
        print(f"\nSystem message preview (first 500 chars):")
        print("-" * 80)
        print(content[:500])
        print("-" * 80)
        
        # Check if data is in system message
        if 'COMPLETE RANKING RESULTS DATA' in content:
            print("\n✓ System message contains 'COMPLETE RANKING RESULTS DATA'")
        else:
            print("\n✗ ERROR: System message does NOT contain 'COMPLETE RANKING RESULTS DATA'")
        
        # Check if method names are present
        methods = ranking_results.get('methods', [])
        if methods:
            first_method_name = methods[0].get('name', '')
            if first_method_name and first_method_name in content:
                print(f"✓ System message contains method name: {first_method_name}")
            else:
                print(f"✗ ERROR: System message does NOT contain method name: {first_method_name}")
    
    # Check user message
    user_msg = next((msg for msg in messages if msg.get('role') == 'user'), None)
    if user_msg:
        content = user_msg.get('content', '')
        print(f"\nUser message length: {len(content)} characters")
        print(f"\nUser message preview (first 500 chars):")
        print("-" * 80)
        print(content[:500])
        print("-" * 80)
        
        # Check if data is in user message
        if 'RANKING RESULTS DATA' in content:
            print("\n✓ User message contains 'RANKING RESULTS DATA'")
        else:
            print("\n✗ ERROR: User message does NOT contain 'RANKING RESULTS DATA'")
        
        # Check if method names are present
        methods = ranking_results.get('methods', [])
        if methods:
            first_method_name = methods[0].get('name', '')
            if first_method_name and first_method_name in content:
                print(f"✓ User message contains method name: {first_method_name}")
            else:
                print(f"✗ ERROR: User message does NOT contain method name: {first_method_name}")
    
    return messages

def test_is_phase2_request(ranking_results):
    """Test is_phase2_request function"""
    print("\n" + "="*80)
    print("STEP 3: Testing is_phase2_request")
    print("="*80)
    
    test_messages = [
        {'role': 'user', 'content': 'Explain what these ranking results mean'}
    ]
    
    is_phase2 = is_phase2_request(test_messages, ranking_results)
    print(f"\nis_phase2_request returned: {is_phase2}")
    
    if is_phase2:
        print("✓ Correctly identified as Phase 2 request")
    else:
        print("✗ ERROR: Failed to identify as Phase 2 request")
    
    return is_phase2

async def test_api_call(messages, api_key=None):
    """Test actual API call (requires API key)"""
    print("\n" + "="*80)
    print("STEP 4: Testing API call")
    print("="*80)
    
    if not api_key:
        print("\n⚠ Skipping API call test (no API key provided)")
        print("To test API call, set OPENAI_API_KEY environment variable")
        return None
    
    from code_app.backend.main import _call_openai
    
    print(f"\nCalling OpenAI API with {len(messages)} messages...")
    completion = await _call_openai(messages, tools=[], api_key=api_key)
    
    if completion.get("error"):
        print(f"\n✗ ERROR: API call failed: {completion.get('error')}")
        return None
    
    choice = (completion.get("choices") or [{}])[0]
    assistant_msg = choice.get("message") or {}
    content = assistant_msg.get("content", "")
    
    print(f"\n✓ API call successful!")
    print(f"Response length: {len(content)} characters")
    print(f"\nResponse preview (first 500 chars):")
    print("-" * 80)
    print(content[:500])
    print("-" * 80)
    
    # Check if response uses actual data
    methods = ranking_results.get('methods', [])
    if methods:
        first_method_name = methods[0].get('name', '')
        if first_method_name and first_method_name in content:
            print(f"\n✓ Response contains method name: {first_method_name}")
        else:
            print(f"\n✗ ERROR: Response does NOT contain method name: {first_method_name}")
            print("This indicates the model is not using the provided data!")
    
    # Check for forbidden generic responses
    forbidden_phrases = [
        "Please specify",
        "I don't have access",
        "various models",
        "higher-ranked models"
    ]
    
    found_forbidden = []
    for phrase in forbidden_phrases:
        if phrase.lower() in content.lower():
            found_forbidden.append(phrase)
    
    if found_forbidden:
        print(f"\n✗ ERROR: Response contains forbidden generic phrases: {found_forbidden}")
    else:
        print("\n✓ Response does not contain forbidden generic phrases")
    
    return content

def main():
    """Main test function"""
    print("\n" + "="*80)
    print("PHASE 2 AGENT DEBUG TEST")
    print("="*80)
    
    # Step 1: Generate ranking results
    ranking_results = run_ranking_analysis()
    if not ranking_results:
        print("\n✗ Failed to generate ranking results. Exiting.")
        return
    
    # Save results for inspection
    results_file = os.path.join(OUTPUT_DIR, 'ranking_results.json')
    with open(results_file, 'w') as f:
        json.dump(ranking_results, f, indent=2)
    print(f"\n✓ Saved ranking results to: {results_file}")
    
    # Step 2: Test prepare_phase2_messages
    messages = test_prepare_phase2_messages(ranking_results)
    
    # Step 3: Test is_phase2_request
    test_is_phase2_request(ranking_results)
    
    # Step 4: Test API call (if API key available)
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("\n" + "="*80)
        print("Running async API test...")
        print("="*80)
        response = asyncio.run(test_api_call(messages, api_key))
        
        if response:
            # Save response
            response_file = os.path.join(OUTPUT_DIR, 'api_response.txt')
            with open(response_file, 'w') as f:
                f.write(response)
            print(f"\n✓ Saved API response to: {response_file}")
    else:
        print("\n⚠ Set OPENAI_API_KEY environment variable to test API call")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print(f"\nCheck output files in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()

