#!/usr/bin/env python3
"""Check CI format in system message"""

import os
import sys
import json
import re

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from code_app.backend.phase2_agent import prepare_phase2_messages

RESULTS_FILE = os.path.join(project_root, 'test_phase2_output', 'ranking_results.json')

# Load ranking results
with open(RESULTS_FILE, 'r') as f:
    ranking_results = json.load(f)

user_message = "Explain what these ranking results mean"

messages = prepare_phase2_messages(
    user_message=user_message,
    ranking_results=ranking_results,
    conversation_history=[],
    base_system_prompt=""
)

# Check system message
system_msg = next((msg for msg in messages if msg.get('role') == 'system'), None)
if system_msg:
    content = system_msg.get('content', '')
    
    # Find all CI patterns
    ci_patterns = re.findall(r'CI[:\s]*\[([^\]]+)\]', content, re.IGNORECASE)
    print(f"Found {len(ci_patterns)} CI patterns in system message:")
    
    has_decimal = False
    for i, ci_pattern in enumerate(ci_patterns[:20]):
        print(f"  {i+1}. [{ci_pattern}]")
        if '.' in ci_pattern:
            has_decimal = True
            print(f"      ✗ Contains decimal!")
    
    if has_decimal:
        print(f"\n✗ ERROR: System message contains decimal CI values!")
    else:
        print(f"\n✓ All CI values in system message are integers")
    
    # Check for specific problematic patterns
    if re.search(r'\[0\.\d+\]', content):
        print(f"\n✗ ERROR: Found decimal CI pattern like [0.8400]")
    if re.search(r'\[0\.\d+,\s*0\.\d+\]', content):
        print(f"\n✗ ERROR: Found decimal CI pattern like [0.8400, 0.8700]")

