"""Utility functions for GraphQL tracking."""

from __future__ import annotations

import traceback
from typing import Any, ClassVar

MAX_LIST_DISPLAY_ITEMS = 10


class StackCapture:
    """Utilities for capturing and filtering stack traces."""

    IGNORED_FRAMES: ClassVar[set[str]] = {
        "strawberry",
        "debug_toolbar",
        "asyncio",
        "concurrent",
        "graphql",
        "site-packages",
        "threading",
        "importlib",
    }

    MAX_FRAMES: ClassVar[int] = 5

    @classmethod
    def capture(cls, skip_frames: int = 4) -> list[dict[str, Any]]:
        """Capture current call stack, filtering library frames.

        Args:
            skip_frames: Number of frames to skip from top.

        Returns:
            List of frame dicts with file, line, function, code.
        """
        frames = []
        for frame_info in traceback.extract_stack()[:-skip_frames]:
            if any(ignored in frame_info.filename for ignored in cls.IGNORED_FRAMES):
                continue

            frames.append(
                {
                    "file": frame_info.filename,
                    "line": frame_info.lineno,
                    "function": frame_info.name,
                    "code": frame_info.line or "",
                }
            )

        return frames[-cls.MAX_FRAMES :] if len(frames) > cls.MAX_FRAMES else frames


def truncate_query(query: str, max_length: int = 1000) -> str:
    """Truncate long query strings.

    Args:
        query: GraphQL query string.
        max_length: Maximum length before truncation.

    Returns:
        Truncated query with ellipsis if needed.
    """
    if len(query) <= max_length:
        return query
    return query[:max_length] + "..."


def format_variables(variables: dict[str, Any], max_depth: int = 3) -> dict[str, Any]:
    """Format variables for display, truncating deep nesting.

    Args:
        variables: Query variables.
        max_depth: Maximum nesting depth.

    Returns:
        Formatted variables dict.
    """
    if max_depth <= 0:
        return {"...": "max depth reached"}

    formatted = {}
    for key, value in variables.items():
        if isinstance(value, dict):
            formatted[key] = format_variables(value, max_depth - 1)
        elif isinstance(value, list):
            formatted[key] = [
                format_variables(item, max_depth - 1) if isinstance(item, dict) else item
                for item in value[:MAX_LIST_DISPLAY_ITEMS]
            ]
            if len(value) > MAX_LIST_DISPLAY_ITEMS:
                formatted[key].append("...")
        else:
            formatted[key] = value

    return formatted


def get_operation_type_from_query(query: str) -> str:
    """Determine operation type from query string.

    Args:
        query: GraphQL query string.

    Returns:
        Operation type: 'query', 'mutation', or 'subscription'.
    """
    query_stripped = query.strip().lower()

    if query_stripped.startswith("mutation"):
        return "mutation"
    if query_stripped.startswith("subscription"):
        return "subscription"

    return "query"
