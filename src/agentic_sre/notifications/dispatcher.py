"""Payload formatting utilities for Slack Block Kit and Discord Embed notifications."""

from typing import Any, Dict


def format_slack_payload(crash_context: Dict[str, Any], ai_rca: Dict[str, Any]) -> Dict[str, Any]:
    """Formats crash metadata and AI root cause analysis into a Slack Block Kit payload.

    Args:
        crash_context: Dictionary containing sanitized crash metadata.
        ai_rca: Dictionary containing AI root cause analysis.

    Returns:
        Dict representing Slack Block Kit message structure.
    """
    endpoint_str = f"{crash_context.get('method', 'GET')} {crash_context.get('url', 'unknown')}"
    exception_str = f"{crash_context.get('exception_type', 'Exception')}: {crash_context.get('exception_message', '')}"
    failing_loc = (
        f"{crash_context.get('file_name', 'unknown')}:"
        f"{crash_context.get('line_number', 0)} in "
        f"{crash_context.get('function_name', 'unknown')}()"
    )

    correlation_id = crash_context.get("correlation_id", "none")

    error_summary = ai_rca.get("error_summary") or "No summary provided."
    root_cause = ai_rca.get("root_cause_hypothesis") or "No hypothesis provided."
    suggested_fix = ai_rca.get("suggested_fix") or "# No code fix suggested."

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔴 [CRITICAL CRASH] FastAPI 500 Internal Server Error",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*📍 Endpoint:*\n`{endpoint_str}`"},
                {"type": "mrkdwn", "text": f"*🔗 Correlation ID:*\n`{correlation_id}`"},
                {"type": "mrkdwn", "text": f"*💥 Exception:*\n`{exception_str}`"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*📁 Failing Location:*\n`{failing_loc}`"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🧠 AI Root Cause Analysis*\n_{error_summary}_\n\n{root_cause}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*💡 Suggested Fix*\n```python\n{suggested_fix}\n```",
            },
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⏱️ Agentic-SRE v0.1.0 • Autonomous SRE Detective",
                }
            ],
        },
    ]

    return {"blocks": blocks}


def format_discord_payload(crash_context: Dict[str, Any], ai_rca: Dict[str, Any]) -> Dict[str, Any]:
    """Formats crash metadata and AI root cause analysis into a Discord Embed payload.

    Args:
        crash_context: Dictionary containing sanitized crash metadata.
        ai_rca: Dictionary containing AI root cause analysis.

    Returns:
        Dict representing Discord webhook embed payload.
    """
    endpoint_str = f"{crash_context.get('method', 'GET')} {crash_context.get('url', 'unknown')}"
    exception_str = f"{crash_context.get('exception_type', 'Exception')}: {crash_context.get('exception_message', '')}"
    failing_loc = (
        f"{crash_context.get('file_name', 'unknown')}:"
        f"{crash_context.get('line_number', 0)} in "
        f"{crash_context.get('function_name', 'unknown')}()"
    )
    correlation_id = crash_context.get("correlation_id", "none")

    error_summary = ai_rca.get("error_summary") or "No summary provided."
    root_cause = ai_rca.get("root_cause_hypothesis") or "No hypothesis provided."
    suggested_fix = ai_rca.get("suggested_fix") or "# No code fix suggested."

    embed = {
        "title": "🔴 [CRITICAL CRASH] FastAPI 500 Internal Server Error",
        "color": 14427686,  # Hex #DC2626
        "fields": [
            {
                "name": "📍 Endpoint",
                "value": f"`{endpoint_str}`",
                "inline": True,
            },
            {
                "name": "🔗 Correlation ID",
                "value": f"`{correlation_id}`",
                "inline": True,
            },
            {
                "name": "💥 Exception",
                "value": f"`{exception_str}`",
                "inline": False,
            },
            {
                "name": "📁 Failing Location",
                "value": f"`{failing_loc}`",
                "inline": False,
            },
            {
                "name": "🧠 AI Root Cause Analysis",
                "value": f"*{error_summary}*\n\n{root_cause}",
                "inline": False,
            },
            {
                "name": "💡 Suggested Fix",
                "value": f"```python\n{suggested_fix}\n```",
                "inline": False,
            },
        ],
        "footer": {"text": "Agentic-SRE v0.1.0 • Autonomous SRE Detective"},
    }

    return {"embeds": [embed]}
