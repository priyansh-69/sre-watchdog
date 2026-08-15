"""Notifications module for Agentic-SRE (dispatcher, webhooks)."""

from agentic_sre.notifications.dispatcher import (
    format_discord_payload,
    format_slack_payload,
)
from agentic_sre.notifications.webhooks import dispatch_alerts

__all__ = [
    "format_slack_payload",
    "format_discord_payload",
    "dispatch_alerts",
]
