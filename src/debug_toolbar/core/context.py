"""Request context management using contextvars for async-safe data propagation."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


@dataclass
class RequestContext:
    """Request-scoped context for debug toolbar data collection.

    This context is stored in a contextvar and is accessible throughout the
    request lifecycle without passing it explicitly through the call stack.

    Attributes:
        request_id: Unique identifier for this request.
        panel_data: Dictionary of data collected by panels, keyed by panel_id.
        timing_data: Dictionary of timing measurements.
        metadata: Additional metadata about the request.
    """

    request_id: UUID = field(default_factory=uuid4)
    panel_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    timing_data: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def store_panel_data(self, panel_id: str, key: str, value: Any) -> None:
        """Store data for a specific panel.

        Args:
            panel_id: The panel's identifier.
            key: The data key.
            value: The data value.
        """
        if panel_id not in self.panel_data:
            self.panel_data[panel_id] = {}
        self.panel_data[panel_id][key] = value

    def get_panel_data(self, panel_id: str) -> dict[str, Any]:
        """Get all data for a specific panel.

        Args:
            panel_id: The panel's identifier.

        Returns:
            Dictionary of panel data, or empty dict if no data exists.
        """
        return self.panel_data.get(panel_id, {})

    def record_timing(self, name: str, duration: float) -> None:
        """Record a timing measurement.

        Args:
            name: The name of the timing measurement.
            duration: The duration in seconds.
        """
        self.timing_data[name] = duration

    def get_timing(self, name: str) -> float | None:
        """Get a timing measurement.

        Args:
            name: The name of the timing measurement.

        Returns:
            The duration in seconds, or None if not recorded.
        """
        return self.timing_data.get(name)


def get_request_context() -> RequestContext | None:
    """Get the current request context.

    Returns:
        The current RequestContext, or None if no context is set.
    """
    return _request_context.get()


def set_request_context(context: RequestContext | None) -> None:
    """Set the current request context.

    Args:
        context: The RequestContext to set, or None to clear.
    """
    _request_context.set(context)


def ensure_request_context() -> RequestContext:
    """Get or create a request context.

    Returns:
        The current RequestContext, creating a new one if none exists.
    """
    ctx = get_request_context()
    if ctx is None:
        ctx = RequestContext()
        set_request_context(ctx)
    return ctx
