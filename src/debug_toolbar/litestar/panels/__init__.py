"""Litestar-specific panels for the debug toolbar."""

from __future__ import annotations

from debug_toolbar.litestar.panels.events import EventsPanel
from debug_toolbar.litestar.panels.routes import RoutesPanel

__all__ = ["EventsPanel", "RoutesPanel"]
