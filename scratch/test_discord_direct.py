"""Scratch script to test Discord webhook notification dispatching locally or against a live URL."""

import asyncio
import os
import sys
from typing import Any, Dict

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
import httpx

sys.path.insert(0, "src")

from agentic_sre.notifications.dispatcher import format_discord_payload
from agentic_sre.notifications.webhooks import dispatch_alerts


# Sample crash metadata for testing
SAMPLE_CRASH_CONTEXT: Dict[str, Any] = {
    "method": "POST",
    "url": "http://127.0.0.1:8000/v1/checkout/process",
    "headers": {"content-type": "application/json", "authorization": "Bearer [REDACTED]"},
    "exception_type": "ZeroDivisionError",
    "exception_message": "division by zero",
    "file_name": "app/routers/checkout.py",
    "line_number": 142,
    "function_name": "calculate_discount",
    "stack_trace": "Traceback (most recent call last):\n  File 'app/routers/checkout.py', line 142, in calculate_discount\n    rate = total / items_count\nZeroDivisionError: division by zero",
}

SAMPLE_AI_RCA: Dict[str, Any] = {
    "error_summary": "Division by zero occurred because items_count was 0 for an empty cart.",
    "root_cause_hypothesis": "The calculate_discount function does not validate if items_count > 0 before division.",
    "failing_component": "app/routers/checkout.py:142 in calculate_discount()",
    "suggested_fix": "if items_count == 0:\n    return 0.0\nrate = total / items_count",
}


async def mock_discord_receiver(request: Request):
    """Local mock Discord server route that receives and prints the webhook payload."""
    payload = await request.json()
    print("\n------------------------------------------------------------")
    print("🎯 LOCAL MOCK DISCORD SERVER RECEIVED EMBED PAYLOAD:")
    print("------------------------------------------------------------")
    embed = payload.get("embeds", [{}])[0]
    print(f"Title: {embed.get('title')}")
    print(f"Color: {embed.get('color')} (Hex #DC2626)")
    print("\nFields Received:")
    for field in embed.get("fields", []):
        print(f"  • {field.get('name')}: {field.get('value')}")
    print("------------------------------------------------------------\n")
    return JSONResponse({"status": "ok"})


async def run_local_mock_test():
    """Starts a local receiver on port 8001 and tests Discord webhook formatting."""
    print("🧪 Testing Discord Webhook Dispatch against Local Mock Server...")
    
    app = Starlette(routes=[Route("/mock-discord", mock_discord_receiver, methods=["POST"])])
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning")
    server = uvicorn.Server(config)
    
    # Run server in background task
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.5)  # Wait for mock server to bind

    mock_webhook_url = "http://127.0.0.1:8001/mock-discord"
    await dispatch_alerts(
        crash_context=SAMPLE_CRASH_CONTEXT,
        ai_rca=SAMPLE_AI_RCA,
        discord_url=mock_webhook_url,
    )

    await asyncio.sleep(0.5)
    server.should_exit = True
    await server_task


async def run_live_test(discord_url: str):
    """Sends a real test alert to a live Discord Webhook URL."""
    print(f"🚀 Dispatching Real Test Crash Alert to Live Discord Webhook: {discord_url[:35]}...")
    await dispatch_alerts(
        crash_context=SAMPLE_CRASH_CONTEXT,
        ai_rca=SAMPLE_AI_RCA,
        discord_url=discord_url,
    )
    print("✅ Live Discord Alert Dispatched! Check your Discord Channel.")


if __name__ == "__main__":
    env_discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if env_discord_url:
        asyncio.run(run_live_test(env_discord_url))
    else:
        asyncio.run(run_local_mock_test())
