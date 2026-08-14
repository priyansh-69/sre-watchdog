"""Crash context extractor for Python exceptions and Starlette/FastAPI request objects."""

import traceback
from typing import Any, Dict, Optional

from starlette.requests import Request

from agentic_sre.core.sanitizer import Sanitizer


MAX_STACK_TRACE_CHARS = 8000
MAX_STACK_TRACE_LINES = 150
MAX_EXCEPTION_MSG_CHARS = 1000

# Explicit safe header allowlist for structured request data minimization
SAFE_HEADER_ALLOWLIST = {
    "host",
    "user-agent",
    "content-type",
    "accept",
    "accept-encoding",
    "accept-language",
    "x-request-id",
    "x-correlation-id",
    "x-forwarded-for",
    "x-forwarded-proto",
}


def truncate_stack_trace(
    stack_trace: str, max_chars: int = MAX_STACK_TRACE_CHARS, max_lines: int = MAX_STACK_TRACE_LINES
) -> str:
    """Intelligently truncates oversized stack traces while preserving top and bottom frames.

    Args:
        stack_trace: Input stack trace string.
        max_chars: Maximum character limit. Defaults to 8000.
        max_lines: Maximum line limit. Defaults to 150.

    Returns:
        Truncated stack trace string preserving entry frames and innermost failing frames.
    """
    if not stack_trace:
        return ""

    lines = stack_trace.splitlines()
    if len(lines) > max_lines or len(stack_trace) > max_chars:
        head_lines = lines[:30]
        tail_lines = lines[-70:]
        omitted_count = len(lines) - 100
        truncated_msg = f"\n\n... [TRUNCATED {max(omitted_count, 1)} STACK TRACE LINES TO PRESERVE CONTEXT WINDOW] ...\n\n"
        stack_trace = "\n".join(head_lines) + truncated_msg + "\n".join(tail_lines)

        if len(stack_trace) > max_chars:
            stack_trace = stack_trace[: max_chars - 100] + "\n\n... [TRUNCATED OVERSIZED STACK TRACE] ..."

    return stack_trace


class Extractor:
    """Extractor class for capturing structured crash context from exceptions and HTTP requests."""

    def __init__(self, sanitizer: Optional[Sanitizer] = None) -> None:
        """Initializes Extractor with an optional Sanitizer instance.

        Args:
            sanitizer: Optional Sanitizer instance. Defaults to a new Sanitizer instance.
        """
        self.sanitizer = sanitizer or Sanitizer()

    def extract(self, exc: Exception, request: Request) -> Dict[str, Any]:
        """Extracts structured, sanitized crash context from an exception and request object.

        Args:
            exc: Caught Python Exception.
            request: Starlette/FastAPI Request object.

        Returns:
            Dict containing HTTP method, URL, sanitized headers, failing frame metadata,
            and fully sanitized stack trace string.
        """
        tb = exc.__traceback__
        extracted_tb = traceback.extract_tb(tb)

        if extracted_tb:
            failing_frame = extracted_tb[-1]
            file_name = failing_frame.filename
            line_number = failing_frame.lineno or 0
            function_name = failing_frame.name
        else:
            file_name = "unknown"
            line_number = 0
            function_name = "unknown"

        # Format full raw stack trace string safely
        try:
            raw_stack_trace = "".join(traceback.format_exception(type(exc), exc, tb))
        except Exception as format_err:
            raw_stack_trace = f"Traceback formatting failed ({type(format_err).__name__}: {format_err})"

        sanitized_stack_trace = self.sanitizer.redact(raw_stack_trace)
        truncated_stack_trace = truncate_stack_trace(sanitized_stack_trace)

        # Safely convert exception message string (handles broken __str__ methods)
        try:
            raw_msg = str(exc)
        except Exception:
            raw_msg = f"<{type(exc).__name__} object with broken __str__ implementation>"

        if len(raw_msg) > MAX_EXCEPTION_MSG_CHARS:
            raw_msg = raw_msg[:MAX_EXCEPTION_MSG_CHARS] + " ... [TRUNCATED]"
        sanitized_msg = self.sanitizer.redact(raw_msg)

        # Extract and sanitize headers using Hybrid Allowlist Data Minimization
        raw_headers = dict(request.headers)
        sanitized_headers = self.sanitizer.sanitize_dict_allowlist(
            raw_headers, allowlist=SAFE_HEADER_ALLOWLIST
        )

        # Extract distributed tracing correlation ID
        headers_lower = {k.lower(): v for k, v in raw_headers.items()}
        correlation_id = (
            headers_lower.get("x-request-id")
            or headers_lower.get("x-correlation-id")
            or headers_lower.get("traceparent")
            or headers_lower.get("x-datadog-trace-id")
            or headers_lower.get("x-b3-traceid")
            or "none"
        )

        return {
            "method": request.method,
            "url": self.sanitizer.redact(str(request.url)),
            "correlation_id": self.sanitizer.redact(correlation_id),
            "headers": sanitized_headers,
            "exception_type": type(exc).__name__,
            "exception_message": sanitized_msg,
            "file_name": file_name,
            "line_number": line_number,
            "function_name": function_name,
            "stack_trace": truncated_stack_trace,
        }
