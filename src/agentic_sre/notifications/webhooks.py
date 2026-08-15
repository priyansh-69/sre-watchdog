"""Async webhook dispatcher for Slack and Discord alerts."""

import logging
import os
from typing import Any, Dict, Optional

import httpx

from agentic_sre.notifications.dispatcher import (
    format_discord_payload,
    format_slack_payload,
)

logger = logging.getLogger("agentic_sre")

DEFAULT_TIMEOUT = httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0)

# Global connection-pooled HTTP client to prevent socket exhaustion
_SHARED_HTTP_CLIENT: Optional[httpx.AsyncClient] = None


def get_shared_http_client() -> httpx.AsyncClient:
    """Returns a shared, connection-pooled httpx.AsyncClient instance.

    Prevents OS socket exhaustion under high crash rates by reusing keep-alive TCP connections.
    """
    global _SHARED_HTTP_CLIENT
    if _SHARED_HTTP_CLIENT is None or _SHARED_HTTP_CLIENT.is_closed:
        _SHARED_HTTP_CLIENT = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _SHARED_HTTP_CLIENT


async def close_shared_http_client() -> None:
    """Gracefully closes the shared HTTP client connection pool."""
    global _SHARED_HTTP_CLIENT
    if _SHARED_HTTP_CLIENT is not None and not _SHARED_HTTP_CLIENT.is_closed:
        await _SHARED_HTTP_CLIENT.aclose()
        _SHARED_HTTP_CLIENT = None


async def dispatch_alerts(
    crash_context: Dict[str, Any],
    ai_rca: Dict[str, Any],
    slack_url: Optional[str] = None,
    discord_url: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> None:
    """Dispatches formatted crash alerts to configured Slack and Discord webhooks.

    Args:
        crash_context: Dictionary containing sanitized crash metadata.
        ai_rca: Dictionary containing AI root cause analysis.
        slack_url: Optional explicit Slack webhook URL. Defaults to SLACK_WEBHOOK_URL env var.
        discord_url: Optional explicit Discord webhook URL. Defaults to DISCORD_WEBHOOK_URL env var.
        client: Optional explicit AsyncClient instance. Defaults to shared pooled client.

    Fail-Silent Guarantee:
        Each webhook invocation runs inside an independent try/except block.
        If Slack fails, Discord will still execute and vice versa. No exception bubbles up.
    """
    target_slack_url = slack_url or os.environ.get("SLACK_WEBHOOK_URL")
    target_discord_url = discord_url or os.environ.get("DISCORD_WEBHOOK_URL")

    if not target_slack_url and not target_discord_url:
        logger.info(
            "[Agentic-SRE] Neither SLACK_WEBHOOK_URL nor DISCORD_WEBHOOK_URL configured. "
            "Skipping webhook dispatch."
        )
        return

    http_client = client or get_shared_http_client()

    # 1. Slack Dispatch
    if target_slack_url:
        try:
            slack_payload = format_slack_payload(crash_context, ai_rca)
            response = await http_client.post(target_slack_url, json=slack_payload)
            response.raise_for_status()
            logger.info("[Agentic-SRE] Successfully dispatched RCA report to Slack webhook.")
        except Exception as exc:
            # Fail-Silent rule: log without raising exception
            logger.error(f"[Agentic-SRE] Failed to dispatch Slack webhook: {exc}", exc_info=True)

    # 2. Discord Dispatch (Independent try/except block)
    if target_discord_url:
        try:
            discord_payload = format_discord_payload(crash_context, ai_rca)
            response = await http_client.post(target_discord_url, json=discord_payload)
            response.raise_for_status()
            logger.info("[Agentic-SRE] Successfully dispatched RCA report to Discord webhook.")
        except Exception as exc:
            # Fail-Silent rule: log without raising exception
            logger.error(f"[Agentic-SRE] Failed to dispatch Discord webhook: {exc}", exc_info=True)
