#!/usr/bin/env python3
"""
Simulate frontend request to test Phase 2 agent endpoint
"""

import os
import sys
import json
import asyncio
import aiohttp

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Load ranking results
RESULTS_FILE = os.path.join(project_root, 'test_phase2_output', 'ranking_results.json')
API_BASE_URL = "http://127.0.0.1:8001"

async def test_frontend_simulation():
    """Simulate frontend request"""
    
    # Load ranking results
    if not os.path.exists(RESULTS_FILE):
        print(f"ERROR: Results file not found at {RESULTS_FILE}")
        return
    
    with open(RESULTS_FILE, 'r') as f:
        ranking_results = json.load(f)
    
    print("="*80)
    print("FRONTEND SIMULATION TEST")
    print("="*80)
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\nERROR: OPENAI_API_KEY environment variable not set")
        return
    
    # Simulate frontend request format
    # Frontend sends messages with HTML content
    messages = [
        {
            'role': 'user',
            'content': 'Explain what these ranking results mean'  # Simulate button click
        }
    ]
    
    payload = {
        'messages': messages,
        'api_key': api_key,
        'ranking_results': ranking_results  # Frontend passes this
    }
    
    print(f"\n1. Sending request to {API_BASE_URL}/api/agent/chat")
    print(f"   - Messages: {len(messages)}")
    print(f"   - Has ranking_results: {bool(ranking_results)}")
    print(f"   - Methods count: {len(ranking_results.get('methods', []))}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/api/agent/chat',
                json=payload,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"\n✗ ERROR: HTTP {resp.status}")
                    print(f"   {error_text}")
                    return
                
                result = await resp.json()
                
                print(f"\n2. Response received (status: {resp.status})")
                
                assistant_message = result.get('assistant_message', {})
                content = assistant_message.get('content', '')
                
                if not content:
                    print("\n✗ ERROR: No content in response")
                    print(f"   Result: {json.dumps(result, indent=2)}")
                    return
                
                print(f"\n3. Response content ({len(content)} chars):")
                print("="*80)
                print(content)
                print("="*80)
                
                # Validate
                print(f"\n4. Validating response...")
                
                methods = ranking_results.get('methods', [])
                sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
                top_methods = sorted_methods[:3]
                
                found_methods = []
                for method in top_methods:
                    method_name = method.get('name', '')
                    if method_name and method_name.lower() in content.lower():
                        found_methods.append(method_name)
                
                if found_methods:
                    print(f"   ✓ Response contains method names: {found_methods}")
                else:
                    print(f"   ✗ ERROR: Response does NOT contain method names!")
                
                forbidden = [
                    "Please specify",
                    "Please note that I can only assist",
                    "kindly refer to the results",
                    "various models"
                ]
                
                found_forbidden = [p for p in forbidden if p.lower() in content.lower()]
                if found_forbidden:
                    print(f"   ✗ ERROR: Response contains forbidden phrases: {found_forbidden}")
                else:
                    print(f"   ✓ Response does not contain forbidden phrases")
                
                # Save response
                output_file = os.path.join(project_root, 'test_phase2_output', 'frontend_simulation_response.txt')
                with open(output_file, 'w') as f:
                    f.write(content)
                print(f"\n5. Saved response to: {output_file}")
                
    except aiohttp.ClientError as e:
        print(f"\n✗ ERROR: Connection error - {e}")
        print("   Make sure the backend server is running on port 8001")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\nNOTE: This test requires the backend server to be running.")
    print("Start it with: cd code_app/backend && python main.py")
    print()
    asyncio.run(test_frontend_simulation())

