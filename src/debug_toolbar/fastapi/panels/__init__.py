"""FastAPI-specific panels for the debug toolbar."""

from __future__ import annotations

from debug_toolbar.fastapi.panels.dependencies import DependencyInjectionPanel

__all__ = ["DependencyInjectionPanel"]
