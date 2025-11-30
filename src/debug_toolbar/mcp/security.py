"""Security utilities for MCP server data redaction."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"auth[_-]?token", re.IGNORECASE),
    re.compile(r"access[_-]?token", re.IGNORECASE),
    re.compile(r"refresh[_-]?token", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"credit[_-]?card", re.IGNORECASE),
    re.compile(r"ssn", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
]

REDACTED = "[REDACTED]"


def is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data.

    Args:
        key: The key name to check.

    Returns:
        True if the key matches a sensitive pattern.
    """
    return any(pattern.search(key) for pattern in SENSITIVE_PATTERNS)


def redact_value(value: Any, key: str = "") -> Any:
    """Redact sensitive values based on key name.

    Args:
        value: The value to potentially redact.
        key: The key name associated with the value.

    Returns:
        The original value or REDACTED if sensitive.
    """
    if key and is_sensitive_key(key):
        return REDACTED
    return value


def redact_dict(data: dict[str, Any], *, deep: bool = True) -> dict[str, Any]:
    """Redact sensitive values from a dictionary.

    Args:
        data: Dictionary to redact.
        deep: Whether to recursively redact nested dicts.

    Returns:
        Dictionary with sensitive values redacted.
    """
    result = {}
    for key, value in data.items():
        if is_sensitive_key(key):
            result[key] = REDACTED
        elif deep and isinstance(value, dict):
            result[key] = redact_dict(value, deep=True)
        elif deep and isinstance(value, list):
            result[key] = [redact_dict(item, deep=True) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


def redact_sql_parameters(params: dict[str, Any] | tuple | list | None) -> dict[str, Any] | tuple | list | None:
    """Redact sensitive SQL query parameters.

    Args:
        params: SQL query parameters.

    Returns:
        Parameters with sensitive values redacted.
    """
    if params is None:
        return None

    if isinstance(params, dict):
        return redact_dict(params)

    if isinstance(params, list | tuple):
        return type(params)(redact_dict(p) if isinstance(p, dict) else p for p in params)

    return params


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive HTTP headers.

    Args:
        headers: HTTP headers dictionary.

    Returns:
        Headers with sensitive values redacted.
    """
    sensitive_headers = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "cookie",
        "set-cookie",
        "x-csrf-token",
    }

    return {k: REDACTED if k.lower() in sensitive_headers or is_sensitive_key(k) else v for k, v in headers.items()}
