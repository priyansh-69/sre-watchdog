import asyncio
import sys
sys.path.insert(0, "src")

import pytest
from agentic_sre.ai.base import BaseAIProvider
from agentic_sre.ai.gemini import GeminiProvider


def test_base_provider_abstract():
    """Verify that BaseAIProvider cannot be instantiated directly."""
    try:
        provider = BaseAIProvider()
        assert False, "BaseAIProvider should be abstract and not directly instantiable"
    except TypeError:
        print("PASS: BaseAIProvider correctly enforces abstract class constraints.")


async def test_gemini_provider_fallback():
    """Verify GeminiProvider fail-silent fallback behavior without API key."""
    provider = GeminiProvider(api_key=None)

    sample_crash_context = {
        "method": "POST",
        "url": "http://api.local/v1/checkout",
        "headers": {"content-type": "application/json"},
        "exception_type": "KeyError",
        "exception_message": "'discount_code'",
        "file_name": "app/routers/checkout.py",
        "line_number": 84,
        "function_name": "checkout_endpoint",
        "stack_trace": "Traceback (most recent call last):\n  File 'app/routers/checkout.py', line 84, in checkout_endpoint\n    discount = payload['discount_code']\nKeyError: 'discount_code'"
    }

    rca = await provider.analyze_error(sample_crash_context)
    print("Fall-back RCA Output:", rca)

    # Check required keys exist
    required_keys = ["error_summary", "root_cause_hypothesis", "failing_component", "suggested_fix"]
    for key in required_keys:
        assert key in rca, f"Missing key '{key}' in RCA output"

    assert "KeyError" in rca["error_summary"]
    assert "checkout.py:84" in rca["failing_component"]
    print("PASS: GeminiProvider fallback returns valid structured dictionary.")


if __name__ == "__main__":
    test_base_provider_abstract()
    asyncio.run(test_gemini_provider_fallback())
