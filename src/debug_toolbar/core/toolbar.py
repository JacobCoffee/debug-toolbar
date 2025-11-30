"""Main debug toolbar manager class."""

from __future__ import annotations

import importlib
import logging
import time
from typing import TYPE_CHECKING, Any

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.context import RequestContext, ensure_request_context, get_request_context, set_request_context
from debug_toolbar.core.storage import ToolbarStorage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel


class DebugToolbar:
    """Main debug toolbar manager.

    Responsible for:
    - Panel lifecycle management (create, enable/disable, destroy)
    - Request context initialization
    - Data collection orchestration
    - Toolbar rendering coordination
    """

    __slots__ = ("_config", "_panel_classes", "_panels", "_storage")

    def __init__(
        self,
        config: DebugToolbarConfig | None = None,
    ) -> None:
        """Initialize the debug toolbar.

        Args:
            config: Configuration options. Uses defaults if not provided.
        """
        self._config = config or DebugToolbarConfig()
        self._storage = (
            self._config.storage
            if self._config.storage is not None
            else ToolbarStorage(max_size=self._config.max_request_history)
        )
        self._panel_classes: list[type[Panel]] = []
        self._panels: list[Panel] = []

        if self._config.enabled:
            self._load_panels()

    @property
    def config(self) -> DebugToolbarConfig:
        """Get the toolbar configuration."""
        return self._config

    @property
    def storage(self) -> ToolbarStorage:
        """Get the toolbar storage."""
        return self._storage

    @property
    def panels(self) -> list[Panel]:
        """Get all panel instances."""
        return self._panels

    @property
    def enabled_panels(self) -> list[Panel]:
        """Get only enabled panel instances."""
        return [p for p in self._panels if p.enabled]

    def _load_panels(self) -> None:
        """Load and instantiate panel classes."""
        self._panel_classes = []

        for panel_spec in self._config.get_all_panels():
            if isinstance(panel_spec, str):
                panel_class = self._import_panel(panel_spec)
            else:
                panel_class = panel_spec

            if panel_class is not None:
                self._panel_classes.append(panel_class)

        self._panels = [cls(self) for cls in self._panel_classes]

    def _import_panel(self, import_path: str) -> type[Panel] | None:
        """Import a panel class from a dotted path.

        Args:
            import_path: Dotted import path like 'module.submodule.ClassName'.

        Returns:
            The panel class, or None if import fails.
        """
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError, ValueError) as e:
            logger.warning("Failed to import panel '%s': %s", import_path, e)
            return None

    def get_panel(self, panel_id: str) -> Panel | None:
        """Get a panel by its ID.

        Args:
            panel_id: The panel's unique identifier.

        Returns:
            The panel instance, or None if not found.
        """
        for panel in self._panels:
            if panel.get_panel_id() == panel_id:
                return panel
        return None

    async def process_request(self) -> RequestContext:
        """Start processing a request.

        Creates a new request context and notifies all panels.

        Returns:
            The new request context.
        """
        context = ensure_request_context()
        context.record_timing("request_start", time.perf_counter())

        for panel in self.enabled_panels:
            await panel.process_request(context)

        return context

    async def process_response(self, context: RequestContext | None = None) -> None:
        """Finish processing a request.

        Collects stats from all panels and stores in history.

        Args:
            context: The request context. Uses current context if not provided.
        """
        if context is None:
            context = get_request_context()

        if context is None:
            return

        context.record_timing("request_end", time.perf_counter())

        start = context.get_timing("request_start")
        end = context.get_timing("request_end")
        if start is not None and end is not None:
            context.record_timing("total_time", end - start)

        for panel in self.enabled_panels:
            stats = await panel.generate_stats(context)
            panel.record_stats(context, stats)
            await panel.process_response(context)

        self._storage.store_from_context(context)
        set_request_context(None)

    def get_server_timing_header(self, context: RequestContext | None = None) -> str:
        """Generate Server-Timing header value.

        Args:
            context: The request context. Uses current context if not provided.

        Returns:
            Server-Timing header value string.
        """
        if context is None:
            context = get_request_context()

        if context is None:
            return ""

        timings: list[str] = []

        total_time = context.get_timing("total_time")
        if total_time is not None:
            timings.append(f'total;dur={total_time * 1000:.2f};desc="Total"')

        for panel in self.enabled_panels:
            panel_timings = panel.generate_server_timing(context)
            for name, duration in panel_timings.items():
                timings.append(f'{name};dur={duration * 1000:.2f};desc="{panel.title}"')

        return ", ".join(timings)

    def get_toolbar_data(self, context: RequestContext | None = None) -> dict[str, Any]:
        """Get all data for rendering the toolbar.

        Args:
            context: The request context. Uses current context if not provided.

        Returns:
            Dictionary with toolbar data including all panel stats.
        """
        if context is None:
            context = get_request_context()

        if context is None:
            return {}

        panels_data = []
        for panel in self.enabled_panels:
            panels_data.append(
                {
                    "panel_id": panel.get_panel_id(),
                    "title": panel.title,
                    "nav_title": panel.get_nav_title(),
                    "nav_subtitle": panel.get_nav_subtitle(),
                    "has_content": panel.has_content,
                    "stats": panel.get_stats(context),
                }
            )

        return {
            "request_id": str(context.request_id),
            "panels": panels_data,
            "timing": context.timing_data,
            "metadata": context.metadata,
        }
