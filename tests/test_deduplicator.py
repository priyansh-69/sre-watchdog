"""Unit tests for CrashDeduplicator in Agentic-SRE."""

import time

from agentic_sre.core.deduplicator import CrashDeduplicator


def test_crash_deduplication_suppression():
    dedup = CrashDeduplicator(ttl_seconds=10)

    crash1 = {
        "exception_type": "ZeroDivisionError",
        "file_name": "app/routers/checkout.py",
        "line_number": 142,
        "function_name": "calculate_discount",
        "exception_message": "division by zero",
    }

    # First occurrence should not be suppressed
    assert not dedup.should_suppress(crash1)

    # Immediate second occurrence of identical crash should be suppressed
    assert dedup.should_suppress(crash1)


def test_crash_deduplication_ttl_expiry():
    dedup = CrashDeduplicator(ttl_seconds=1)

    crash1 = {
        "exception_type": "KeyError",
        "file_name": "app/auth.py",
        "line_number": 55,
        "function_name": "verify_token",
        "exception_message": "user_id",
    }

    assert not dedup.should_suppress(crash1)
    assert dedup.should_suppress(crash1)

    # Wait for TTL to expire
    time.sleep(1.1)

    # After TTL expiry, it should trigger analysis again
    assert not dedup.should_suppress(crash1)


def test_crash_deduplication_different_crashes():
    dedup = CrashDeduplicator(ttl_seconds=60)

    crash1 = {
        "exception_type": "ZeroDivisionError",
        "file_name": "app/routers/checkout.py",
        "line_number": 142,
        "function_name": "calculate_discount",
        "exception_message": "division by zero",
    }

    crash2 = {
        "exception_type": "ValueError",
        "file_name": "app/routers/checkout.py",
        "line_number": 145,
        "function_name": "calculate_discount",
        "exception_message": "invalid literal",
    }

    assert not dedup.should_suppress(crash1)
    assert not dedup.should_suppress(crash2)
