"""FastAPI integration for the debug toolbar.

This module provides FastAPI-specific components for integrating
the debug toolbar with FastAPI applications. It builds on the
Starlette adapter and adds FastAPI-specific features like
dependency injection tracking.

Example:
    >>> from fastapi import FastAPI
    >>> from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig
    >>>
    >>> app = FastAPI()
    >>> config = FastAPIDebugToolbarConfig(enabled=True)
    >>> setup_debug_toolbar(app, config)
"""

from __future__ import annotations

from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig
from debug_toolbar.fastapi.middleware import DebugToolbarMiddleware
from debug_toolbar.fastapi.setup import setup_debug_toolbar

__all__ = [
    "DebugToolbarMiddleware",
    "FastAPIDebugToolbarConfig",
    "setup_debug_toolbar",
]
