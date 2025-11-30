"""Configuration system for the debug toolbar."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel
    from debug_toolbar.core.storage import ToolbarStorage


@dataclass
class DebugToolbarConfig:
    """Configuration for the debug toolbar.

    Attributes:
        enabled: Whether the toolbar is enabled. Defaults to True.
        panels: List of panel classes or import paths to include.
        intercept_redirects: Whether to intercept redirects for debugging.
        show_toolbar_callback: Optional callback to determine if toolbar should be shown.
        insert_before: HTML tag to insert toolbar before. Defaults to "</body>".
        max_request_history: Maximum number of requests to store in history.
        api_path: URL path prefix for toolbar API endpoints.
        static_path: URL path prefix for static assets.
        allowed_hosts: List of allowed hosts. Empty list means all hosts.
        extra_panels: Additional panels to add beyond defaults.
        exclude_panels: Panel names to exclude from defaults.
        memory_backend: Memory profiling backend. "auto" selects best available.
        panel_display_depth: Max depth for nested data rendering. Defaults to 10.
        panel_display_max_items: Max items to show in arrays/objects. Defaults to 100.
        panel_display_max_string: Max string length before truncation. Defaults to 1000.
        async_profiler_backend: Async profiler backend. "auto" selects best available.
        async_blocking_threshold_ms: Threshold for blocking call detection. Defaults to 100.
        async_enable_blocking_detection: Whether to detect blocking calls. Defaults to True.
        async_enable_event_loop_monitoring: Whether to monitor event loop lag. Defaults to True.
        async_event_loop_lag_threshold_ms: Threshold for lag alerts. Defaults to 10.
        async_capture_task_stacks: Whether to capture task creation stacks. Defaults to True.
        async_max_stack_depth: Maximum stack depth to capture. Defaults to 10.
        websocket_tracking_enabled: Whether to track WebSocket connections. Defaults to True.
        websocket_max_connections: Maximum number of connections to track. Defaults to 50.
        websocket_max_messages_per_connection: Maximum messages per connection. Defaults to 100.
        websocket_max_message_size: Maximum message size to store in bytes. Defaults to 10240.
        websocket_connection_ttl: Connection time-to-live in seconds. Defaults to 3600.
    """

    enabled: bool = True
    panels: Sequence[str | type[Panel]] = field(
        default_factory=lambda: [
            "debug_toolbar.core.panels.timer.TimerPanel",
            "debug_toolbar.core.panels.request.RequestPanel",
            "debug_toolbar.core.panels.response.ResponsePanel",
            "debug_toolbar.core.panels.logging.LoggingPanel",
            "debug_toolbar.core.panels.versions.VersionsPanel",
        ]
    )
    intercept_redirects: bool = False
    show_toolbar_callback: Callable[..., bool] | None = None
    insert_before: str = "</body>"
    max_request_history: int = 50
    api_path: str = "/_debug_toolbar"
    static_path: str = "/_debug_toolbar/static"
    allowed_hosts: Sequence[str] = field(default_factory=list)
    extra_panels: Sequence[str | type[Panel]] = field(default_factory=list)
    exclude_panels: Sequence[str] = field(default_factory=list)
    memory_backend: Literal["tracemalloc", "memray", "auto"] = "auto"
    panel_display_depth: int = 10
    panel_display_max_items: int = 100
    panel_display_max_string: int = 1000

    async_profiler_backend: Literal["taskfactory", "yappi", "auto"] = "auto"
    async_blocking_threshold_ms: float = 100.0
    async_enable_blocking_detection: bool = True
    async_enable_event_loop_monitoring: bool = True
    async_event_loop_lag_threshold_ms: float = 10.0
    async_capture_task_stacks: bool = True
    async_max_stack_depth: int = 10

    websocket_tracking_enabled: bool = True
    websocket_max_connections: int = 50
    websocket_max_messages_per_connection: int = 100
    websocket_max_message_size: int = 10240
    websocket_connection_ttl: int = 3600

    storage: ToolbarStorage | None = None

    def get_all_panels(self) -> list[str | type[Panel]]:
        """Get all panels including extras, excluding excluded panels."""
        all_panels = list(self.panels) + list(self.extra_panels)
        if not self.exclude_panels:
            return all_panels

        excluded = set(self.exclude_panels)
        return [
            p
            for p in all_panels
            if (isinstance(p, str) and p.split(".")[-1] not in excluded)
            or (isinstance(p, type) and p.__name__ not in excluded)
        ]
