"""Starlette integration for the debug toolbar.

This module provides Starlette-specific components for integrating
the debug toolbar with Starlette applications.

Example:
    >>> from starlette.applications import Starlette
    >>> from starlette.middleware import Middleware
    >>> from debug_toolbar.core import DebugToolbar
    >>> from debug_toolbar.starlette import (
    ...     DebugToolbarMiddleware,
    ...     StarletteDebugToolbarConfig,
    ...     create_debug_toolbar_routes,
    ... )
    >>>
    >>> config = StarletteDebugToolbarConfig(enabled=True)
    >>> toolbar = DebugToolbar(config)
    >>>
    >>> app = Starlette(
    ...     routes=[
    ...         # Your routes here
    ...         *create_debug_toolbar_routes(toolbar.storage),
    ...     ],
    ...     middleware=[
    ...         Middleware(DebugToolbarMiddleware, config=config, toolbar=toolbar),
    ...     ],
    ... )
"""

from __future__ import annotations

from debug_toolbar.starlette.config import StarletteDebugToolbarConfig
from debug_toolbar.starlette.middleware import DebugToolbarMiddleware
from debug_toolbar.starlette.routes import create_debug_toolbar_routes

__all__ = [
    "DebugToolbarMiddleware",
    "StarletteDebugToolbarConfig",
    "create_debug_toolbar_routes",
]
