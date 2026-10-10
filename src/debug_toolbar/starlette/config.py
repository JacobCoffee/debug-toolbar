"""Starlette-specific configuration for the debug toolbar."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from debug_toolbar.core.config import DebugToolbarConfig

if TYPE_CHECKING:
    from starlette.requests import Request

    from debug_toolbar.core.panel import Panel


@dataclass
class StarletteDebugToolbarConfig(DebugToolbarConfig):
    """Starlette-specific configuration for the debug toolbar.

    Extends the base configuration with Starlette-specific options.

    Attributes:
        exclude_paths: URL paths to exclude from toolbar processing.
        exclude_patterns: Regex patterns for paths to exclude.
        show_on_errors: Whether to show toolbar on error responses.
        show_toolbar_callback: Callback receiving Starlette Request object.
    """

    exclude_paths: Sequence[str] = field(
        default_factory=lambda: [
            "/_debug_toolbar",
            "/static",
            "/favicon.ico",
        ]
    )
    exclude_patterns: Sequence[str] = field(default_factory=list)
    show_on_errors: bool = True
    show_toolbar_callback: Callable[[Request], bool] | None = None

    def __post_init__(self) -> None:
        """Add Starlette-specific panels to the default set."""
        default_panels: list[str | type[Panel]] = list(self.panels)

        if "debug_toolbar.starlette.panels.routes.RoutesPanel" not in default_panels:
            default_panels.append("debug_toolbar.starlette.panels.routes.RoutesPanel")

        self.panels = default_panels

    def should_show_toolbar(self, request: Request) -> bool:
        """Determine if the toolbar should be shown for this request.

        Args:
            request: The Starlette request object.

        Returns:
            True if the toolbar should be shown.
        """
        if not self.enabled:
            return False

        path = request.url.path

        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return False

        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                if re.match(pattern, path):
                    return False

        if self.allowed_hosts:
            host = request.headers.get("host", "").split(":")[0]
            if host not in self.allowed_hosts:
                return False

        if self.show_toolbar_callback is not None:
            return self.show_toolbar_callback(request)

        return True
