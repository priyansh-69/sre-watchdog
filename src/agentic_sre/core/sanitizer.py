"""Regex-based PII & sensitive credential sanitizer for Agentic-SRE."""

import re
from typing import Any, Dict, Optional, Set


class Sanitizer:
    """Sanitizer class for scrubbing PII, passwords, API keys, bearer tokens, credit cards, and emails."""

    # Key matching pattern for sensitive keys in dictionaries
    SENSITIVE_KEY_PATTERN = re.compile(
        r"(?i)^(.*)?(password|passwd|secret|token|api[_\-]?key|apikey|auth|bearer|cookie|set-cookie|proxy-authorization|session|access[_\-]?token|refresh[_\-]?token|private[_\-]?key|signature|credential)(.*)?$"
    )

    # Patterns for text redaction: list of (compiled_regex, replacement_string)
    PATTERNS = [
        # Bearer & Basic Auth Header Tokens (e.g. Bearer eyJ... or Basic dXNl...)
        (
            re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9\-\._~\+\/]+=*"),
            r"\1 [REDACTED]",
        ),
        # JWT Tokens (eyJ...)
        (
            re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
            "[REDACTED]",
        ),
        # Key-Value assignments & JSON fields (handles quoted strings with spaces)
        (
            re.compile(
                r"(?i)\b(password|passwd|secret|token|api[_\-]?key|apikey|auth|bearer|session|access[_\-]?token)\s*[:=]\s*(?:'[^']*'|\"[^\"]*\"|[^\s'\";,]+)"
            ),
            r"\1=[REDACTED]",
        ),
        # Credit Card Numbers (13 to 19 digits, plain or separated by spaces/hyphens)
        (
            re.compile(
                r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
            ),
            "[REDACTED]",
        ),
        (
            re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "[REDACTED]",
        ),
        # Email Addresses
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "[REDACTED]",
        ),
    ]

    def redact(self, text: str) -> str:
        """Scrubs sensitive data (bearer tokens, API keys, passwords, credit cards, emails) from text.

        Args:
            text: Input string (e.g., stack trace string or log message).

        Returns:
            Sanitized string with sensitive information replaced by [REDACTED].
        """
        if not text:
            return ""

        sanitized = text
        for pattern, replacement in self.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redacts sensitive key-value pairs and string values in a dictionary.

        Args:
            data: Input dictionary (e.g., request headers, query parameters).

        Returns:
            Sanitized dictionary with sensitive values replaced by [REDACTED].
        """
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            if self.SENSITIVE_KEY_PATTERN.match(str(key)):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self.redact(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict)
                    else self.redact(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def sanitize_dict_allowlist(
        self, data: Dict[str, Any], allowlist: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Recursively sanitizes dictionary keys against a strict allowlist.

        Non-allowlisted keys are replaced with [REDACTED] to enforce data minimization.

        Args:
            data: Input dictionary (e.g. request headers).
            allowlist: Optional set of lowercased safe keys.

        Returns:
            Sanitized dictionary containing only allowlisted safe keys.
        """
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if allowlist is not None and key_lower not in allowlist:
                sanitized[key] = "[REDACTED]"
            elif self.SENSITIVE_KEY_PATTERN.match(key_lower):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str):
                sanitized[key] = self.redact(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict_allowlist(value, allowlist=allowlist)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict_allowlist(item, allowlist=allowlist) if isinstance(item, dict)
                    else self.redact(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
