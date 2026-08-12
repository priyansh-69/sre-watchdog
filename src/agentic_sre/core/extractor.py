"""Crash context extractor for Python exceptions and Starlette/FastAPI request objects."""

import traceback
from typing import Any, Dict, Optional

from starlette.requests import Request

from agentic_sre.core.sanitizer import Sanitizer


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

        # Format full raw stack trace string
        raw_stack_trace = "".join(traceback.format_exception(type(exc), exc, tb))
        sanitized_stack_trace = self.sanitizer.redact(raw_stack_trace)

        # Extract and sanitize headers
        raw_headers = dict(request.headers)
        sanitized_headers = self.sanitizer.sanitize_dict(raw_headers)

        return {
            "method": request.method,
            "url": str(request.url),
            "headers": sanitized_headers,
            "exception_type": type(exc).__name__,
            "exception_message": self.sanitizer.redact(str(exc)),
            "file_name": file_name,
            "line_number": line_number,
            "function_name": function_name,
            "stack_trace": sanitized_stack_trace,
        }
