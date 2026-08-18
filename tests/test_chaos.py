"""Chaos Engineering and Red Team fuzzing tests for Agentic-SRE."""

import asyncio
from unittest.mock import MagicMock

import pytest

from agentic_sre.core.extractor import Extractor
from agentic_sre.core.sanitizer import Sanitizer
from agentic_sre.middleware import AgenticSREMiddleware


class BrokenStrException(Exception):
    """Custom exception with a broken __str__ method that raises another Exception."""

    def __str__(self) -> str:
        raise RuntimeError("Explosive __str__ error inside custom exception!")


def test_chaos_broken_str_exception():
    """Verifies Extractor safely handles exceptions with broken __str__ methods without crashing."""
    extractor = Extractor()
    exc = BrokenStrException("custom message")

    mock_request = MagicMock()
    mock_request.method = "GET"
    mock_request.url = "http://test.local/crash"
    mock_request.headers = {}

    extracted = extractor.extract(exc, mock_request)

    assert extracted["exception_type"] == "BrokenStrException"
    assert "broken __str__" in extracted["exception_message"]
    assert "BrokenStrException" in extracted["stack_trace"]


def test_chaos_bytes_and_malformed_encoding():
    """Verifies Sanitizer handles bytes, surrogate pairs, and non-printable characters safely."""
    sanitizer = Sanitizer()

    # Raw bytes input
    raw_bytes = b"Authorization: Bearer secret_token_123"
    sanitized_bytes = sanitizer.redact(raw_bytes)
    assert "secret_token_123" not in sanitized_bytes
    assert "[REDACTED]" in sanitized_bytes

    # Invalid surrogate pair string
    invalid_surrogate = "Header \ud83d value Authorization: Bearer eyJ1c2Vy"
    sanitized_surrogate = sanitizer.redact(invalid_surrogate)
    assert "eyJ1c2Vy" not in sanitized_surrogate
    assert "[REDACTED]" in sanitized_surrogate


@pytest.mark.asyncio
async def test_chaos_graceful_shutdown():
    """Verifies AgenticSREMiddleware.flush_pending_tasks drains pending tasks cleanly."""
    mock_app = MagicMock()
    middleware = AgenticSREMiddleware(mock_app)

    async def dummy_slow_task():
        await asyncio.sleep(0.05)

    task = asyncio.create_task(dummy_slow_task())
    middleware._background_tasks.add(task)
    task.add_done_callback(middleware._background_tasks.discard)

    assert len(middleware._background_tasks) == 1

    await middleware.flush_pending_tasks(timeout=1.0)

    assert len(middleware._background_tasks) == 0
