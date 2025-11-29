"""Configuration system for the debug toolbar."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel


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
