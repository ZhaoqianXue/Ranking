#!/usr/bin/env python3
"""
Test the complete Phase 1 workflow with sequential tool execution
"""

import asyncio
import json
import os
import sys
import uuid

# Add the backend path to sys.path
backend_path = os.path.join(os.path.dirname(__file__), 'code_app', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

async def test_phase1_workflow():
    """Test the complete Phase 1 workflow"""
    print("=" * 80)
    print("TESTING COMPLETE PHASE 1 WORKFLOW")
    print("=" * 80)

    # Create test data file
    test_file_id = str(uuid.uuid4())

    # Get the correct path where the file should be
    import main
    test_file_path = main._get_agent_file_path(test_file_id)

    test_data = """method,accuracy,loss,score,time
model_a,0.95,0.05,95.2,10.5
model_b,0.92,0.08,92.1,12.3
model_c,0.89,0.11,89.5,15.2
model_d,0.85,0.15,85.3,18.7
model_e,0.82,0.18,82.9,22.1
model_f,0.78,0.22,78.5,25.8"""

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    with open(test_file_path, 'w') as f:
        f.write(test_data)

    print(f"📁 Created test file: {test_file_path}")

    try:
        # Simulate the frontend request that triggers Phase 1 workflow
        analysis_message = f"START ANALYSIS - I have uploaded a CSV file with ID: {test_file_id}. Please immediately use the inspect_dataset tool to analyze the data structure, then infer_direction to determine ranking direction, and estimate_runtime to provide time estimates (use B=2000 for estimation and k_methods equal to length of recommended_columns)."

        system_content = f'User has uploaded a file with ID: {test_file_id}. This is a START ANALYSIS request - immediately execute: inspect_dataset → infer_direction → estimate_runtime workflow. When estimating runtime, ALWAYS use B=2000 for preview and set k_methods to the number of recommended_columns (fallback to numeric_candidates length).\n\nCRITICAL: After successfully calling all three tools (inspect_dataset, infer_direction, estimate_runtime), DO NOT generate ANY text response. Set the \'content\' field to an empty string ("") or null - do NOT use the word "EMPTY" as text. The UI will automatically display a Ranking Preview modal where users configure parameters. Do NOT ask users to specify ranking direction or provide any configuration via text.\n\n**CRITICAL: For file upload analysis (Phase 1), you MUST call tools ONE AT A TIME:**\n\n**STEP-BY-STEP WORKFLOW (MANDATORY):**\n1. **FIRST**: Call ONLY inspect_dataset(file_id="{test_file_id}") - analyze the data structure\n2. **THEN**: Call ONLY infer_direction(columns=[columns from step 1]) - infer ranking direction\n3. **FINALLY**: Call ONLY estimate_runtime(n_samples=[rows from step 1], k_methods=[numeric columns from step 1], B=2000)\n\n**ABSOLUTE RULES**:\n- NEVER call multiple tools in one response\n- NEVER call infer_direction or estimate_runtime before inspect_dataset\n- After calling a tool, STOP and wait for the result\n- Only call the next tool after receiving the previous tool\'s result\n\n**COMPLETION RULE**:\n- After successfully calling ALL THREE tools in sequence, set \'content\' to empty string ("") - NO TEXT RESPONSE\n- The UI will handle displaying results to the user\n\n**FORBIDDEN**:\n- No text responses during tool calling\n- No asking for user input\n- No explanations or summaries\n- No "please specify" or "next step" phrases'

        messages = [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': analysis_message}
        ]

        api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

        import aiohttp

        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages, 'api_key': api_key}
            async with session.post(
                'http://localhost:8001/api/agent/chat',
                json=payload,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ API call failed: {error_text}")
                    return False

                result = await resp.json()
                print("✅ API call successful")

                # Debug: Print the full response
                print("🔍 FULL RESPONSE:")
                for i, msg in enumerate(result.get('messages', [])):
                    role = msg.get('role')
                    if role == 'assistant':
                        content = (msg.get('content') or '')[:100]
                        tool_calls = msg.get('tool_calls', [])
                        print(f"  {i}. {role}: '{content}' + {len(tool_calls)} tool calls")
                        for tc in tool_calls:
                            name = tc.get('function', {}).get('name')
                            args = tc.get('function', {}).get('arguments', '{}')
                            print(f"     → {name}: {args}")
                    elif role == 'tool':
                        name = msg.get('name')
                        content = (msg.get('content') or '{}')[:100]
                        print(f"  {i}. {role} ({name}): {content}")
                    else:
                        content = (msg.get('content') or '')[:100]
                        print(f"  {i}. {role}: {content}")

                # Analyze the result
                messages = result.get('messages', [])
                print(f"\n📊 Total messages: {len(messages)}")

                # Extract tool calls and results
                tool_calls = []
                tool_results = {}

                for msg in messages:
                    if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                        tool_calls.extend(msg.get('tool_calls', []))
                    elif msg.get('role') == 'tool':
                        tool_name = msg.get('name')
                        content = msg.get('content', '{}')
                        try:
                            parsed = json.loads(content)
                            tool_results[tool_name] = parsed
                        except:
                            pass

                print(f"🔧 Total tool calls made: {len(tool_calls)}")
                print(f"📊 Tool results received: {len(tool_results)}")

                # Check each tool
                for tool_name in ['inspect_dataset', 'infer_direction', 'estimate_runtime']:
                    if tool_name in tool_results:
                        result = tool_results[tool_name]
                        if 'error' in result:
                            print(f"❌ {tool_name}: {result['error']}")
                        else:
                            print(f"✅ {tool_name}: Success")
                            if tool_name == 'inspect_dataset':
                                print(f"   📊 Rows: {result.get('n_rows')}, Columns: {result.get('n_cols')}")
                            elif tool_name == 'infer_direction':
                                print(f"   🎯 Direction: {result.get('direction')}")
                            elif tool_name == 'estimate_runtime':
                                print(f"   ⏱️  ETA: {result.get('eta_formatted')}")
                    else:
                        print(f"❌ {tool_name}: Not executed")

                # Check completion
                from main import _check_phase1_complete
                if _check_phase1_complete(messages):
                    print("🎉 PHASE 1 WORKFLOW COMPLETED SUCCESSFULLY!")
                    return True
                else:
                    print("⚠️  Phase 1 workflow not complete")
                    return False

    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    success = asyncio.run(test_phase1_workflow())
    sys.exit(0 if success else 1)