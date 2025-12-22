#!/usr/bin/env python3
"""
Test direction inference fix
"""

import requests
import json

BASE_URL = "http://localhost:8001"

# Upload the file
file_path = "demo_r/example_arena_style.csv"
with open(file_path, 'rb') as f:
    files = {'file': f}
    upload_response = requests.post(f"{BASE_URL}/api/agent/upload", files=files)
    file_id = upload_response.json()['file_id']

print(f"Uploaded file, ID: {file_id}")

# Call inspect_dataset to see direction inference
inspect_url = f"{BASE_URL}/api/agent/tools/inspect_dataset"
inspect_response = requests.post(inspect_url, json={"file_id": file_id})
result = inspect_response.json()

print(f"\nDirection inference result:")
print(f"  Direction: {result.get('infer_direction', {}).get('direction', 'N/A')}")
print(f"  Confidence: {result.get('infer_direction', {}).get('confidence', 'N/A')}")
print(f"  Reason: {result.get('infer_direction', {}).get('reason', 'N/A')[:200]}...")

# Check if it's higher
direction = result.get('infer_direction', {}).get('direction')
if direction == 'higher':
    print("\n✅ SUCCESS: Direction correctly identified as 'higher is better'")
else:
    print(f"\n❌ FAILURE: Direction is '{direction}' (should be 'higher')")
