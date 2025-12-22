#!/usr/bin/env python3
"""
Complete API test for Phase 2 agent - tests actual OpenAI API call
"""

import os
import sys
import json
import asyncio

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from code_app.backend.phase2_agent import prepare_phase2_messages
from code_app.backend.main import _call_openai

# Load ranking results from test output
RESULTS_FILE = os.path.join(project_root, 'test_phase2_output', 'ranking_results.json')

async def test_phase2_api():
    """Test Phase 2 API with actual OpenAI call"""
    
    # Load ranking results
    if not os.path.exists(RESULTS_FILE):
        print(f"ERROR: Results file not found at {RESULTS_FILE}")
        print("Please run test_phase2_debug.py first to generate ranking results")
        return
    
    with open(RESULTS_FILE, 'r') as f:
        ranking_results = json.load(f)
    
    print("="*80)
    print("PHASE 2 API TEST")
    print("="*80)
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\nERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    # Prepare messages
    user_message = "Explain what these ranking results mean"
    
    print(f"\n1. Preparing Phase 2 messages...")
    messages = prepare_phase2_messages(
        user_message=user_message,
        ranking_results=ranking_results,
        conversation_history=[],
        base_system_prompt="You are a helpful assistant."
    )
    
    print(f"   ✓ Prepared {len(messages)} messages")
    
    # Show system message preview
    system_msg = next((msg for msg in messages if msg.get('role') == 'system'), None)
    if system_msg:
        content = system_msg.get('content', '')
        print(f"   System message length: {len(content)} chars")
        print(f"   First 300 chars: {content[:300]}...")
    
    # Show user message preview
    user_msg = next((msg for msg in messages if msg.get('role') == 'user'), None)
    if user_msg:
        content = user_msg.get('content', '')
        print(f"   User message length: {len(content)} chars")
        print(f"   First 300 chars: {content[:300]}...")
    
    # Call API
    print(f"\n2. Calling OpenAI API...")
    completion = await _call_openai(messages, tools=[], api_key=api_key)
    
    if completion.get("error"):
        print(f"   ✗ ERROR: {completion.get('error')}")
        return
    
    choice = (completion.get("choices") or [{}])[0]
    assistant_msg = choice.get("message") or {}
    response = assistant_msg.get("content", "")
    
    print(f"\n3. Response received ({len(response)} chars)")
    print("="*80)
    print("RESPONSE:")
    print("="*80)
    print(response)
    print("="*80)
    
    # Validate response
    print(f"\n4. Validating response...")
    
    methods = ranking_results.get('methods', [])
    sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
    top_methods = sorted_methods[:3]
    
    # Check for actual method names
    found_methods = []
    for method in top_methods:
        method_name = method.get('name', '')
        if method_name and method_name.lower() in response.lower():
            found_methods.append(method_name)
    
    if found_methods:
        print(f"   ✓ Response contains method names: {found_methods}")
    else:
        print(f"   ✗ ERROR: Response does NOT contain any method names!")
        print(f"   Expected to see: {[m.get('name') for m in top_methods]}")
    
    # Check for forbidden phrases
    forbidden = [
        "Please specify",
        "I don't have access",
        "various models",
        "higher-ranked models"
    ]
    
    found_forbidden = [p for p in forbidden if p.lower() in response.lower()]
    if found_forbidden:
        print(f"   ✗ ERROR: Response contains forbidden phrases: {found_forbidden}")
    else:
        print(f"   ✓ Response does not contain forbidden generic phrases")
    
    # Check for specific numbers
    top_method = top_methods[0] if top_methods else None
    if top_method:
        theta = top_method.get('theta_hat', 0)
        theta_str = f"{theta:.4f}"
        if theta_str in response or str(theta) in response:
            print(f"   ✓ Response contains theta_hat value: {theta}")
        else:
            print(f"   ⚠ Response may not contain specific theta_hat value")
    
    # Save response
    output_file = os.path.join(project_root, 'test_phase2_output', 'api_response.txt')
    with open(output_file, 'w') as f:
        f.write(response)
    print(f"\n5. Saved response to: {output_file}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_phase2_api())

