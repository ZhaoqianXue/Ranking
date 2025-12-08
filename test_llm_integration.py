#!/usr/bin/env python3
"""
End-to-end test for LLM tool calling integration
Tests the complete agent_chat workflow with actual LLM calls
"""

import asyncio
import json
import os
import sys
import uuid
import shutil
from typing import Dict, Any

# Add the backend path to sys.path
backend_path = os.path.join(os.path.dirname(__file__), 'code_app', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import tool_inspect_dataset, tool_infer_direction, tool_estimate_runtime

async def test_llm_agent_chat_integration(api_key: str):
    """Test the complete LLM agent chat integration with sequential tool calls"""
    print("=" * 80)
    print("TESTING COMPLETE LLM AGENT CHAT INTEGRATION")
    print("=" * 80)

    # Create test data file in the correct agent_uploads directory
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

    try:
        print(f"📤 Starting sequential tool call test for file: {test_file_id}")
        print(f"API Key: {'*' * 20}...{'*' * 4}")
        print(f"Test data location: {test_file_path}")
        print(f"📁 File exists: {os.path.exists(test_file_path)}")

        # Phase 1: Call tools sequentially
        all_messages = []
        tool_results = {}

        # Step 1: Call inspect_dataset
        print("\n🔍 Step 1: Calling inspect_dataset...")
        analysis_message = f"START ANALYSIS - I have uploaded a CSV file with ID: {test_file_id}. Please immediately use the inspect_dataset tool to analyze the data structure, then infer_direction to determine ranking direction, and estimate_runtime to provide time estimates (use B=2000 for estimation and k_methods equal to length of recommended_columns)."

        # Prepare messages for API with Phase 1 guidance (copying frontend behavior)
        system_content = f'User has uploaded a file with ID: {test_file_id}. This is a START ANALYSIS request - immediately execute: inspect_dataset → infer_direction → estimate_runtime workflow. When estimating runtime, ALWAYS use B=2000 for preview and set k_methods to the number of recommended_columns (fallback to numeric_candidates length).\n\nCRITICAL: After successfully calling all three tools (inspect_dataset, infer_direction, estimate_runtime), DO NOT generate ANY text response. Set the \'content\' field to an empty string ("") or null - do NOT use the word "EMPTY" as text. The UI will automatically display a Ranking Preview modal where users configure parameters. Do NOT ask users to specify ranking direction or provide any configuration via text.'

        messages_step1 = [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': analysis_message}
        ]

        result1 = await call_agent_chat(messages_step1, api_key)
        if not result1:
            print("❌ Step 1 failed: No response from API")
            return False
        if 'error' in result1 and result1['error']:
            print(f"❌ Step 1 failed: {result1['error']}")
            return False
        print(f"✅ Step 1 API call successful")

        # Debug: print the assistant message
        assistant_msg = result1.get('assistant_message', {})
        print(f"🤖 Assistant response: {assistant_msg.get('content', 'No content')[:200]}...")

        all_messages.extend(result1.get('messages', []))
        tool_results.update(await extract_tool_results(all_messages))

        # Check if inspect_dataset succeeded
        if 'inspect_dataset' not in tool_results or 'error' in tool_results['inspect_dataset']:
            print("❌ inspect_dataset failed or not called")
            return False

        inspect_data = tool_results['inspect_dataset']
        print(f"✅ inspect_dataset result: {inspect_data.get('n_rows')} rows, {inspect_data.get('n_cols')} cols")

        # Step 2: Call infer_direction
        print("\n🔍 Step 2: Calling infer_direction...")
        columns = inspect_data.get('columns', [])
        numeric_candidates = inspect_data.get('numeric_candidates', [])

        messages_step2 = all_messages + [
            {
                'role': 'user',
                'content': f'Now please use the infer_direction tool with these columns: {columns}'
            }
        ]

        result2 = await call_agent_chat(messages_step2, api_key)
        if not result2:
            print("❌ Step 2 failed: No response from API")
            return False
        if 'error' in result2 and result2['error']:
            print(f"❌ Step 2 failed: {result2['error']}")
            return False
        print(f"✅ Step 2 API call successful")

        all_messages.extend(result2.get('messages', []))
        tool_results.update(await extract_tool_results(all_messages))

        # Check if infer_direction succeeded
        if 'infer_direction' not in tool_results or 'error' in tool_results['infer_direction']:
            print("❌ infer_direction failed or not called")
            return False

        direction_data = tool_results['infer_direction']
        print(f"✅ infer_direction result: {direction_data.get('direction')} (confidence: {direction_data.get('confidence', 0)})")

        # Step 3: Call estimate_runtime
        print("\n🔍 Step 3: Calling estimate_runtime...")
        n_samples = inspect_data.get('n_rows', 0)
        k_methods = len(numeric_candidates)

        messages_step3 = all_messages + [
            {
                'role': 'user',
                'content': f'Finally, please use the estimate_runtime tool with n_samples={n_samples}, k_methods={k_methods}, B=2000.'
            }
        ]

        result3 = await call_agent_chat(messages_step3, api_key)
        if not result3:
            print("❌ Step 3 failed: No response from API")
            return False
        if 'error' in result3 and result3['error']:
            print(f"❌ Step 3 failed: {result3['error']}")
            return False
        print(f"✅ Step 3 API call successful")

        all_messages.extend(result3.get('messages', []))
        tool_results.update(await extract_tool_results(all_messages))

        # Check if estimate_runtime succeeded
        if 'estimate_runtime' not in tool_results or 'error' in tool_results['estimate_runtime']:
            print("❌ estimate_runtime failed or not called")
            return False

        runtime_data = tool_results['estimate_runtime']
        print(f"✅ estimate_runtime result: {runtime_data.get('eta_formatted')} ({runtime_data.get('eta_seconds')} seconds)")

        # Analyze final results
        return await analyze_llm_response({
            'messages': all_messages,
            'assistant_message': result3.get('assistant_message')
        }, test_file_id)

    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

async def call_agent_chat(messages, api_key):
    """Helper function to call agent_chat endpoint"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        try:
            payload = {'messages': messages, 'api_key': api_key}
            async with session.post(
                'http://localhost:8001/api/agent/chat',
                json=payload,
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ API call failed with status {resp.status}: {error_text}")
                    return None

                return await resp.json()

        except Exception as e:
            print(f"❌ API call exception: {str(e)}")
            return None

async def extract_tool_results(messages):
    """Extract tool results from messages"""
    tool_results = {}

    for msg in messages:
        if msg.get('role') == 'tool':
            tool_name = msg.get('name')
            content = msg.get('content', '{}')
            try:
                parsed = json.loads(content) if isinstance(content, str) else content
                if tool_name:
                    tool_results[tool_name] = parsed
            except:
                pass

    return tool_results

async def analyze_llm_response(result: Dict[str, Any], test_file_id: str) -> bool:
    """Analyze the LLM response to verify tool calling worked correctly"""
    print("\n📥 RECEIVED LLM RESPONSE")
    print("-" * 50)

    if 'error' in result:
        print(f"❌ LLM returned error: {result['error']}")
        print(f"🔍 Full response: {json.dumps(result, indent=2)}")
        return False

    messages = result.get('messages', [])
    if not messages:
        print("❌ No messages returned")
        return False

    print(f"📊 Total messages in conversation: {len(messages)}")

    # Analyze tool calls
    tool_calls_found = []
    tool_results = {}

    for i, msg in enumerate(messages):
        role = msg.get('role')
        if role == 'assistant':
            tool_calls = msg.get('tool_calls', [])
            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc.get('function', {}).get('name')
                    if tool_name:
                        tool_calls_found.append(tool_name)
                        print(f"🤖 Assistant called tool: {tool_name} (message {i})")

        elif role == 'tool':
            tool_name = msg.get('name')
            content = msg.get('content', '{}')
            try:
                parsed = json.loads(content) if isinstance(content, str) else content
                if tool_name:
                    tool_results[tool_name] = parsed
                    print(f"🔧 Tool {tool_name} returned: {type(parsed).__name__} with {len(parsed) if isinstance(parsed, dict) else 'N/A'} fields")
            except:
                print(f"⚠️  Could not parse tool result for {tool_name}")

    # Verify all three Phase 1 tools were called
    required_tools = {'inspect_dataset', 'infer_direction', 'estimate_runtime'}
    called_tools = set(tool_calls_found)

    print("\n🔍 ANALYSIS RESULTS")
    print(f"Required tools: {required_tools}")
    print(f"Called tools: {called_tools}")

    missing_tools = required_tools - called_tools
    if missing_tools:
        print(f"❌ Missing tool calls: {missing_tools}")
        return False

    extra_tools = called_tools - required_tools
    if extra_tools:
        print(f"⚠️  Unexpected tool calls: {extra_tools}")

    # Verify tool results
    print("\n📋 TOOL RESULTS VALIDATION")
    success_count = 0

    # Check inspect_dataset result
    if 'inspect_dataset' in tool_results:
        inspect_result = tool_results['inspect_dataset']
        if 'error' in inspect_result:
            print(f"❌ inspect_dataset failed: {inspect_result['error']}")
        else:
            rows = inspect_result.get('n_rows', 0)
            cols = inspect_result.get('n_cols', 0)
            numeric_cols = inspect_result.get('numeric_candidates', [])
            print(f"✅ inspect_dataset: {rows} rows, {cols} cols, {len(numeric_cols)} numeric columns")
            success_count += 1
    else:
        print("❌ inspect_dataset result not found")

    # Check infer_direction result
    if 'infer_direction' in tool_results:
        direction_result = tool_results['infer_direction']
        if 'error' in direction_result:
            print(f"❌ infer_direction failed: {direction_result['error']}")
        else:
            direction = direction_result.get('direction')
            confidence = direction_result.get('confidence', 0)
            print(f"✅ infer_direction: {direction} (confidence: {confidence})")
            success_count += 1
    else:
        print("❌ infer_direction result not found")

    # Check estimate_runtime result
    if 'estimate_runtime' in tool_results:
        runtime_result = tool_results['estimate_runtime']
        if 'error' in runtime_result:
            print(f"❌ estimate_runtime failed: {runtime_result['error']}")
        else:
            eta = runtime_result.get('eta_seconds', 0)
            formatted = runtime_result.get('eta_formatted', 'unknown')
            print(f"✅ estimate_runtime: {formatted} ({eta} seconds)")
            success_count += 1
    else:
        print("❌ estimate_runtime result not found")

    # Check final assistant message
    assistant_message = result.get('assistant_message')
    if assistant_message:
        content = assistant_message.get('content', '').strip()
        if content:
            print(f"⚠️  Assistant generated text content: '{content[:100]}...'")
            print("   (Should be empty string for Phase 1 completion)")
        else:
            print("✅ Assistant correctly returned empty content (Phase 1 complete)")

    # Summary
    print("\n🎯 FINAL RESULT")
    print(f"Tool calls: {len(called_tools)}/{len(required_tools)} required tools called")
    print(f"Tool results: {success_count}/{len(required_tools)} tools succeeded")

    if success_count == len(required_tools) and len(called_tools) == len(required_tools):
        print("🎉 LLM INTEGRATION TEST PASSED!")
        print("   All three Phase 1 tools were called correctly and returned valid results.")
        return True
    else:
        print("❌ LLM INTEGRATION TEST FAILED!")
        print("   Some tools were not called or returned errors.")
        return False

async def main():
    """Run the LLM integration test"""
    print("🤖 LLM AGENT CHAT INTEGRATION TEST")
    print("This test verifies that the LLM can correctly call all three Phase 1 tools")
    print("and return valid results for file analysis.\n")

    # Use the provided API key
    api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")

    success = await test_llm_agent_chat_integration(api_key)

    print("\n" + "=" * 80)
    if success:
        print("✅ INTEGRATION TEST SUCCESSFUL")
        print("The LLM agent correctly executes the Phase 1 workflow!")
    else:
        print("❌ INTEGRATION TEST FAILED")
        print("The LLM agent has issues with tool calling or result processing.")
    print("=" * 80)

    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)