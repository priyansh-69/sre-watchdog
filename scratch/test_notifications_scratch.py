import asyncio
import os
import sys
sys.path.insert(0, "src")

from agentic_sre.notifications.dispatcher import (
    format_slack_payload,
    format_discord_payload,
)
from agentic_sre.notifications.webhooks import dispatch_alerts


def test_formatters():
    crash_context = {
        "method": "POST",
        "url": "http://api.local/v1/checkout",
        "headers": {"authorization": "[REDACTED]"},
        "exception_type": "KeyError",
        "exception_message": "'discount_code'",
        "file_name": "app/routers/checkout.py",
        "line_number": 84,
        "function_name": "checkout_endpoint",
        "stack_trace": "Traceback (most recent call last):\n  File 'checkout.py', line 84..."
    }

    ai_rca = {
        "error_summary": "Missing discount_code key in payload.",
        "root_cause_hypothesis": "The payload dictionary accessed discount_code without get().",
        "failing_component": "app/routers/checkout.py:84 in checkout_endpoint()",
        "suggested_fix": "discount = payload.get('discount_code', None)"
    }

    # 1. Test Slack Payload Formatter
    slack_payload = format_slack_payload(crash_context, ai_rca)
    print("Slack Payload Blocks count:", len(slack_payload["blocks"]))
    assert "blocks" in slack_payload
    assert slack_payload["blocks"][0]["text"]["text"] == "🔴 [CRITICAL CRASH] FastAPI 500 Internal Server Error"
    print("PASS: Slack Block Kit payload formatted correctly.")

    # 2. Test Discord Payload Formatter
    discord_payload = format_discord_payload(crash_context, ai_rca)
    print("Discord Embeds count:", len(discord_payload["embeds"]))
    assert "embeds" in discord_payload
    embed = discord_payload["embeds"][0]
    assert embed["color"] == 14427686
    assert len(embed["fields"]) == 6
    print("PASS: Discord Embed payload formatted correctly.\n")


async def test_dispatch_alerts_fail_silent():
    crash_context = {
        "method": "GET",
        "url": "http://api.local/test",
        "exception_type": "ValueError",
        "exception_message": "Test failure",
        "file_name": "test.py",
        "line_number": 10,
        "function_name": "test_func",
        "stack_trace": "Traceback..."
    }
    ai_rca = {
        "error_summary": "Test error",
        "root_cause_hypothesis": "Test hypothesis",
        "failing_component": "test.py:10",
        "suggested_fix": "fix()"
    }

    # Test fail-silent dispatch with dummy URLs
    await dispatch_alerts(
        crash_context,
        ai_rca,
        slack_url="https://invalid-slack-url.example/hooks/123",
        discord_url="https://invalid-discord-url.example/api/webhooks/456"
    )
    print("PASS: dispatch_alerts completed fail-silently without throwing exceptions.")


if __name__ == "__main__":
    test_formatters()
    asyncio.run(test_dispatch_alerts_fail_silent())
