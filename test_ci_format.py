#!/usr/bin/env python3
"""
Test CI format in Phase 2 responses
"""

import os
import sys
import json
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from code_app.backend.phase2_agent import prepare_phase2_messages
from code_app.backend.main import _call_openai

RESULTS_FILE = os.path.join(project_root, 'test_phase2_output', 'ranking_results.json')
API_KEY = os.getenv('OPENAI_API_KEY', '')

async def test_ci_format():
    """Test CI format in actual API response"""
    
    # Load ranking results
    if not os.path.exists(RESULTS_FILE):
        print(f"ERROR: Results file not found at {RESULTS_FILE}")
        return
    
    with open(RESULTS_FILE, 'r') as f:
        ranking_results = json.load(f)
    
    print("="*80)
    print("TESTING CI FORMAT IN PHASE 2 RESPONSE")
    print("="*80)
    
    # Check CI values in ranking results
    print("\n1. Checking CI values in ranking results:")
    methods = ranking_results.get('methods', [])
    for method in methods[:3]:
        ci = method.get('ci_two_sided', [None, None])
        print(f"   {method.get('name')}: CI = {ci}")
    
    # Prepare messages
    user_message = "Explain what these ranking results mean"
    
    print(f"\n2. Preparing Phase 2 messages...")
    messages = prepare_phase2_messages(
        user_message=user_message,
        ranking_results=ranking_results,
        conversation_history=[],
        base_system_prompt=""
    )
    
    # Check system message for CI format
    system_msg = next((msg for msg in messages if msg.get('role') == 'system'), None)
    if system_msg:
        content = system_msg.get('content', '')
        # Search for CI patterns
        import re
        ci_patterns = re.findall(r'CI[:\s]*\[([^\]]+)\]', content)
        print(f"\n3. CI patterns found in system message:")
        for ci_pattern in ci_patterns[:5]:
            print(f"   {ci_pattern}")
    
    # Check user message for CI format
    user_msg = next((msg for msg in messages if msg.get('role') == 'user'), None)
    if user_msg:
        content = user_msg.get('content', '')
        ci_patterns = re.findall(r'CI[:\s]*\[([^\]]+)\]', content)
        print(f"\n4. CI patterns found in user message:")
        for ci_pattern in ci_patterns[:5]:
            print(f"   {ci_pattern}")
    
    # Call API
    print(f"\n5. Calling OpenAI API...")
    completion = await _call_openai(messages, tools=[], api_key=API_KEY)
    
    if completion.get("error"):
        print(f"   ✗ ERROR: {completion.get('error')}")
        return
    
    choice = (completion.get("choices") or [{}])[0]
    assistant_msg = choice.get("message") or {}
    response = assistant_msg.get("content", "")
    
    print(f"\n6. Response received ({len(response)} chars)")
    print("="*80)
    print("RESPONSE:")
    print("="*80)
    print(response)
    print("="*80)
    
    # Check for CI patterns in response
    ci_patterns = re.findall(r'CI[:\s]*\[([^\]]+)\]', response)
    print(f"\n7. CI patterns found in response:")
    has_decimal = False
    for ci_pattern in ci_patterns:
        print(f"   {ci_pattern}")
        # Check if contains decimal
        if '.' in ci_pattern:
            has_decimal = True
            print(f"      ✗ Contains decimal!")
    
    if has_decimal:
        print(f"\n✗ ERROR: Response contains decimal CI values!")
    else:
        print(f"\n✓ All CI values are integers")
    
    # Save response
    output_file = os.path.join(project_root, 'test_phase2_output', 'ci_format_test_response.txt')
    with open(output_file, 'w') as f:
        f.write(response)
    print(f"\n8. Saved response to: {output_file}")

if __name__ == "__main__":
    asyncio.run(test_ci_format())

