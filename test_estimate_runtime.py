#!/usr/bin/env python3
"""
Test the estimate_runtime tool directly
"""

import asyncio
import json
import sys

# Add the backend path to sys.path
backend_path = "/Users/zhaoqianxue/Desktop/UPenn/Ranking/code_app/backend"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from main import tool_estimate_runtime

async def test_estimate_runtime():
    """Test estimate_runtime with benchmark data"""
    print("🧮 TESTING ESTIMATE_RUNTIME TOOL")
    print("=" * 40)

    # Test benchmark data: 163 samples, 6 methods, B=2000 should be ~1 second
    result = await tool_estimate_runtime(163, 6, 2000)

    print(f"Input: 163 samples, 6 methods, B=2000")
    print(f"Result: {json.dumps(result, indent=2)}")

    eta_seconds = result.get('eta_seconds', 0)
    eta_formatted = result.get('eta_formatted', 'unknown')

    print(f"Expected: ~1 second")
    print(f"Actual: {eta_seconds} seconds ({eta_formatted})")

    if abs(eta_seconds - 1.0) < 0.1:  # Allow small tolerance
        print("✅ PASS: Estimate is accurate!")
        return True
    else:
        print(f"❌ FAIL: Estimate is off by {abs(eta_seconds - 1.0):.1f} seconds")
        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(test_estimate_runtime())
    sys.exit(0 if success else 1)