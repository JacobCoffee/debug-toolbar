"""Debug toolbar plugin for Litestar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

from debug_toolbar.litestar.config import LitestarDebugToolbarConfig
from debug_toolbar.litestar.middleware import DebugToolbarMiddleware

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class DebugToolbarPlugin(InitPluginProtocol):
    """Litestar plugin for the debug toolbar.

    This plugin automatically configures the debug toolbar middleware
    and registers API routes for the toolbar interface.

    Example::

        from litestar import Litestar
        from litestar_debug_toolbar import DebugToolbarPlugin, LitestarDebugToolbarConfig

        config = LitestarDebugToolbarConfig(
            enabled=True,
            exclude_paths=["/health", "/metrics"],
        )

        app = Litestar(
            route_handlers=[...],
            plugins=[DebugToolbarPlugin(config)],
        )

    """

    __slots__ = ("_config",)

    def __init__(self, config: LitestarDebugToolbarConfig | None = None) -> None:
        """Initialize the plugin.

        Args:
            config: Toolbar configuration. Uses defaults if not provided.
        """
        self._config = config or LitestarDebugToolbarConfig()

    @property
    def config(self) -> LitestarDebugToolbarConfig:
        """Get the plugin configuration."""
        return self._config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application with the debug toolbar.

        Args:
            app_config: The application configuration.

        Returns:
            The modified application configuration.
        """
        if not self._config.enabled:
            return app_config

        from litestar.middleware import DefineMiddleware

        middleware = DefineMiddleware(DebugToolbarMiddleware, config=self._config)

        if app_config.middleware is None:
            app_config.middleware = [middleware]
        else:
            app_config.middleware = list(app_config.middleware) + [middleware]

        return app_config
