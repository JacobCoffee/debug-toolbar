"""Built-in panels for the async debug toolbar."""

from __future__ import annotations

from debug_toolbar.core.panels.alerts import AlertsPanel
from debug_toolbar.core.panels.async_profiler import AsyncProfilerPanel
from debug_toolbar.core.panels.cache import CachePanel
from debug_toolbar.core.panels.headers import HeadersPanel
from debug_toolbar.core.panels.logging import LoggingPanel
from debug_toolbar.core.panels.memory import MemoryPanel
from debug_toolbar.core.panels.profiling import ProfilingPanel
from debug_toolbar.core.panels.request import RequestPanel
from debug_toolbar.core.panels.response import ResponsePanel
from debug_toolbar.core.panels.settings import SettingsPanel
from debug_toolbar.core.panels.templates import TemplatesPanel
from debug_toolbar.core.panels.timer import TimerPanel
from debug_toolbar.core.panels.versions import VersionsPanel
from debug_toolbar.core.panels.websocket import WebSocketPanel

__all__ = [
    "AlertsPanel",
    "AsyncProfilerPanel",
    "CachePanel",
    "HeadersPanel",
    "LoggingPanel",
    "MemoryPanel",
    "ProfilingPanel",
    "RequestPanel",
    "ResponsePanel",
    "SettingsPanel",
    "TemplatesPanel",
    "TimerPanel",
    "VersionsPanel",
    "WebSocketPanel",
]
