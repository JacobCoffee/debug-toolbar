"""Debug toolbar plugin for Litestar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

from debug_toolbar.core.toolbar import DebugToolbar
from debug_toolbar.litestar.config import LitestarDebugToolbarConfig
from debug_toolbar.litestar.middleware import DebugToolbarMiddleware

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

logger = logging.getLogger(__name__)


class DebugToolbarPlugin(InitPluginProtocol):
    """Litestar plugin for the debug toolbar.

    This plugin automatically configures the debug toolbar middleware
    and registers API routes for the toolbar interface.

    Example::

        from litestar import Litestar
        from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

        config = LitestarDebugToolbarConfig(
            enabled=True,
            exclude_paths=["/health", "/metrics"],
        )

        app = Litestar(
            route_handlers=[...],
            plugins=[DebugToolbarPlugin(config)],
        )

    """

    __slots__ = ("_config", "_toolbar")

    def __init__(self, config: LitestarDebugToolbarConfig | None = None) -> None:
        """Initialize the plugin.

        Args:
            config: Toolbar configuration. Uses defaults if not provided.
        """
        self._config = config or LitestarDebugToolbarConfig()
        self._toolbar: DebugToolbar | None = None

    @property
    def config(self) -> LitestarDebugToolbarConfig:
        """Get the plugin configuration."""
        return self._config

    @property
    def toolbar(self) -> DebugToolbar | None:
        """Get the toolbar instance."""
        return self._toolbar

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application with the debug toolbar.

        Args:
            app_config: The application configuration.

        Returns:
            The modified application configuration.
        """
        if not self._config.enabled:
            return app_config

        from debug_toolbar.litestar.routes import create_debug_toolbar_router
        from litestar.middleware import DefineMiddleware

        self._auto_add_websocket_panel(app_config)

        self._toolbar = DebugToolbar(self._config)

        middleware = DefineMiddleware(
            DebugToolbarMiddleware,
            config=self._config,
            toolbar=self._toolbar,
        )

        if app_config.middleware is None:
            app_config.middleware = [middleware]
        else:
            app_config.middleware = list(app_config.middleware) + [middleware]

        router = create_debug_toolbar_router(self._toolbar.storage)

        if app_config.route_handlers is None:
            app_config.route_handlers = [router]
        else:
            app_config.route_handlers = list(app_config.route_handlers) + [router]

        return app_config

    def _auto_add_websocket_panel(self, app_config: AppConfig) -> None:
        """Auto-detect WebSocket usage and add WebSocketPanel if found.

        Checks route handlers for WebSocket decorators/handlers and automatically
        adds the WebSocketPanel to extra_panels if WebSocket usage is detected.

        Args:
            app_config: The application configuration.
        """
        websocket_panel_path = "debug_toolbar.core.panels.websocket.WebSocketPanel"

        all_panels = list(self._config.panels) + list(self._config.extra_panels)
        panel_paths = [p if isinstance(p, str) else f"{p.__module__}.{p.__name__}" for p in all_panels]
        if websocket_panel_path in panel_paths or "WebSocketPanel" in [
            p.__name__ if isinstance(p, type) else p.split(".")[-1] for p in all_panels
        ]:
            return

        if self._detect_websocket_usage(app_config):
            logger.debug("WebSocket usage detected, auto-adding WebSocketPanel")
            self._config.extra_panels = list(self._config.extra_panels) + [websocket_panel_path]

    def _detect_websocket_usage(self, app_config: AppConfig) -> bool:  # noqa: PLR0911
        """Detect if the application uses WebSocket handlers.

        Checks for:
        - litestar.handlers.websocket decorator usage
        - litestar.handlers.WebsocketListener subclasses
        - Route handlers with WebSocket type annotations

        Args:
            app_config: The application configuration.

        Returns:
            True if WebSocket usage is detected, False otherwise.
        """
        if app_config.route_handlers is None:
            return False

        try:
            from litestar.handlers import WebsocketListener
            from litestar.handlers.websocket_handlers import WebsocketRouteHandler
        except ImportError:
            return False

        for handler in app_config.route_handlers:
            if isinstance(handler, type) and issubclass(handler, WebsocketListener):
                return True

            if isinstance(handler, WebsocketRouteHandler):
                return True

            if callable(handler) and hasattr(handler, "__wrapped__"):
                wrapped = handler.__wrapped__
                if isinstance(wrapped, WebsocketRouteHandler):
                    return True

            if hasattr(handler, "fn") and isinstance(handler, WebsocketRouteHandler):
                return True

        return False
