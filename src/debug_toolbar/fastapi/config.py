"""FastAPI-specific configuration for the debug toolbar."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from debug_toolbar.starlette.config import StarletteDebugToolbarConfig

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel
    from fastapi import Request


@dataclass
class FastAPIDebugToolbarConfig(StarletteDebugToolbarConfig):
    """FastAPI-specific configuration for the debug toolbar.

    Extends the Starlette configuration with FastAPI-specific options.

    Attributes:
        exclude_paths: URL paths to exclude from toolbar processing.
            Includes FastAPI's built-in documentation endpoints by default.
        show_toolbar_callback: Callback receiving FastAPI Request object.
        track_dependency_injection: Enable dependency injection tracking.
    """

    exclude_paths: Sequence[str] = field(
        default_factory=lambda: [
            "/_debug_toolbar",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/favicon.ico",
        ]
    )
    show_toolbar_callback: Callable[[Request], bool] | None = None
    track_dependency_injection: bool = True

    def __post_init__(self) -> None:
        """Add FastAPI-specific panels to the default set."""
        super().__post_init__()

        default_panels: list[str | type[Panel]] = list(self.panels)

        if self.track_dependency_injection:
            di_panel = "debug_toolbar.fastapi.panels.dependencies.DependencyInjectionPanel"
            if di_panel not in default_panels:
                default_panels.append(di_panel)

        self.panels = default_panels
