"""Unit tests for Sanitizer PII and secret redaction."""

from agentic_sre.core.sanitizer import Sanitizer


def test_redact_bearer_token():
    sanitizer = Sanitizer()
    text = "Header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.secret"
    result = sanitizer.redact(text)
    assert "eyJhbGciOiJIUzI1NiJ9" not in result
    assert "[REDACTED]" in result


def test_redact_api_keys_and_passwords():
    sanitizer = Sanitizer()
    text = "config api_key='sk-12345' password=\"secret123\""
    result = sanitizer.redact(text)
    assert "sk-12345" not in result
    assert "secret123" not in result
    assert "[REDACTED]" in result


def test_redact_credit_cards():
    sanitizer = Sanitizer()
    text = "Card number 4532-0154-9871-2345 failed"
    result = sanitizer.redact(text)
    assert "4532-0154-9871-2345" not in result
    assert "[REDACTED]" in result


def test_redact_email_addresses():
    sanitizer = Sanitizer()
    text = "User email user.name@example.com logged in"
    result = sanitizer.redact(text)
    assert "user.name@example.com" not in result
    assert "[REDACTED]" in result


def test_sanitize_dict_headers():
    sanitizer = Sanitizer()
    headers = {
        "Authorization": "Bearer token_xyz",
        "X-Api-Key": "my-secret-key",
        "Content-Type": "application/json",
        "X-User-Email": "dev@company.com",
        "X-Session-ID": "session_9999",
    }
    sanitized = sanitizer.sanitize_dict(headers)
    assert sanitized["Authorization"] == "[REDACTED]"
    assert sanitized["X-Api-Key"] == "[REDACTED]"
    assert sanitized["Content-Type"] == "application/json"
    assert sanitized["X-User-Email"] == "[REDACTED]"
    assert sanitized["X-Session-ID"] == "[REDACTED]"


def test_sanitize_list_and_basic_auth():
    sanitizer = Sanitizer()
    data = {
        "items": [
            {"password": "secret_pass_123"},
            "Header Authorization: Basic dXNlcjpwYXNz",
        ]
    }
    sanitized = sanitizer.sanitize_dict(data)
    assert sanitized["items"][0]["password"] == "[REDACTED]"
    assert "dXNlcjpwYXNz" not in sanitized["items"][1]
    assert "[REDACTED]" in sanitized["items"][1]


def test_stack_trace_truncation():
    from agentic_sre.core.extractor import truncate_stack_trace

    # Create a 500-line artificial stack trace
    long_stack_trace = "\n".join(
        [f"  File 'app/module.py', line {i}, in func_{i}" for i in range(500)]
    )
    result = truncate_stack_trace(long_stack_trace, max_lines=150)
    assert "[TRUNCATED" in result
    assert "func_0" in result
    assert "func_499" in result
