#!/usr/bin/env python3
"""Debug CI format in messages"""

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

# Check user message
user_msg = next((msg for msg in messages if msg.get('role') == 'user'), None)
if user_msg:
    content = user_msg.get('content', '')
    print("USER MESSAGE CONTENT:")
    print("="*80)
    print(content)
    print("="*80)
    
    # Find CI patterns
    ci_patterns = re.findall(r'Confidence Interval[:\s]*\[([^\]]+)\]', content, re.IGNORECASE)
    print(f"\nCI patterns in user message: {ci_patterns}")
    
    # Check for any decimal numbers in brackets
    bracket_patterns = re.findall(r'\[([^\]]+)\]', content)
    print(f"\nAll bracket patterns: {bracket_patterns[:10]}")

