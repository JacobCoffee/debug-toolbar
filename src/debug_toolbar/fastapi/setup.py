"""FastAPI debug toolbar setup utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from debug_toolbar.core import DebugToolbar
from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig
from debug_toolbar.fastapi.middleware import DebugToolbarMiddleware
from debug_toolbar.starlette.routes import create_debug_toolbar_routes

if TYPE_CHECKING:
    from fastapi import FastAPI


def setup_debug_toolbar(
    app: FastAPI,
    config: FastAPIDebugToolbarConfig | None = None,
) -> DebugToolbar:
    """Set up the debug toolbar for a FastAPI application.

    This is a convenience function that:
    1. Creates a toolbar configuration if not provided
    2. Creates a DebugToolbar instance
    3. Adds the debug toolbar middleware
    4. Registers the debug toolbar routes

    Args:
        app: The FastAPI application.
        config: Optional toolbar configuration. Uses defaults if not provided.

    Returns:
        The DebugToolbar instance.

    Example:
        >>> from fastapi import FastAPI
        >>> from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig
        >>>
        >>> app = FastAPI()
        >>> config = FastAPIDebugToolbarConfig(enabled=True)
        >>> toolbar = setup_debug_toolbar(app, config)
    """
    config = config or FastAPIDebugToolbarConfig()
    toolbar = DebugToolbar(config)

    if not config.enabled:
        return toolbar

    app.add_middleware(DebugToolbarMiddleware, config=config, toolbar=toolbar)  # type: ignore[arg-type]

    routes = create_debug_toolbar_routes(toolbar.storage)
    for route in routes:
        app.routes.append(route)

    return toolbar
