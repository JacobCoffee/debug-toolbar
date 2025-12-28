# Async Python Debug Toolbar - Architecture Document

**Version:** 1.0.0
**Status:** Proposed
**Author:** Architecture Agent
**Date:** 2025-11-26

---

## Table of Contents

1. [Overview](#1-overview)
2. [Package Structure](#2-package-structure)
3. [Core Components](#3-core-components)
4. [Built-in Panels](#4-built-in-panels)
5. [Extension Points](#5-extension-points)
6. [Litestar Plugin Design](#6-litestar-plugin-design)
7. [Advanced-Alchemy Integration](#7-advanced-alchemy-integration)
8. [Data Flow](#8-data-flow)
9. [Security Considerations](#9-security-considerations)
10. [Performance Considerations](#10-performance-considerations)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Overview

### 1.1 Purpose

The Async Python Debug Toolbar provides real-time debugging and profiling capabilities for async Python web applications. It consists of two packages:

1. **async-debug-toolbar** (core): Framework-agnostic debug toolbar with async-first design
2. **litestar-debug-toolbar** (plugin): Thin integration layer for Litestar applications

### 1.2 Design Goals

- **Async-Native**: Built from the ground up for async/await patterns
- **Framework-Agnostic Core**: Core package has no framework dependencies
- **Pluggable Panels**: Easy to add, remove, or customize panels
- **Minimal Overhead**: Negligible performance impact in production (disabled state)
- **Type-Safe**: Full type annotations with strict mypy/ty compliance
- **Modern Python**: Requires Python 3.11+ for optimal async performance

### 1.3 Architecture Principles

| Principle | Description |
|-----------|-------------|
| Separation of Concerns | Core toolbar logic separate from framework integration |
| Dependency Injection | Panels receive context, not global state |
| Async Context Propagation | Use contextvars for request-scoped data |
| Lazy Evaluation | Panels compute data only when accessed |
| LRU Caching | Bounded memory usage for toolbar data storage |

---

## 2. Package Structure

### 2.1 Repository Layout

```
debug-toolbar/
├── src/
│   ├── async_debug_toolbar/          # Core package
│   │   ├── __init__.py
│   │   ├── py.typed
│   │   ├── toolbar.py                # DebugToolbar manager
│   │   ├── panel.py                  # Base Panel class
│   │   ├── config.py                 # Settings system
│   │   ├── storage.py                # LRU cache storage
│   │   ├── context.py                # Request context (contextvars)
│   │   ├── rendering/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py             # Template engine abstraction
│   │   │   ├── jinja.py              # Jinja2 implementation
│   │   │   └── templates/            # Default HTML templates
│   │   ├── assets/
│   │   │   ├── css/
│   │   │   └── js/
│   │   ├── panels/
│   │   │   ├── __init__.py
│   │   │   ├── timer.py
│   │   │   ├── request.py
│   │   │   ├── response.py
│   │   │   ├── logging.py
│   │   │   ├── profiling.py
│   │   │   ├── versions.py
│   │   │   └── routes.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   └── base.py               # Abstract ASGI adapter
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── timing.py
│   │       └── formatting.py
│   │
│   └── litestar_debug_toolbar/       # Litestar plugin package
│       ├── __init__.py
│       ├── py.typed
│       ├── plugin.py                 # LitestarDebugToolbarPlugin
│       ├── middleware.py             # LitestarDebugToolbarMiddleware
│       ├── adapter.py                # Litestar ASGI adapter
│       ├── config.py                 # Litestar-specific config
│       └── panels/
│           └── routes.py             # Litestar routes panel
│
├── extras/
│   └── advanced_alchemy/             # Optional AA integration
│       ├── __init__.py
│       ├── panel.py                  # SQLAlchemyPanel
│       └── hooks.py                  # Session event hooks
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/
│   ├── architecture/
│   └── api/
│
├── pyproject.toml
├── Makefile
└── README.md
```

### 2.2 Package Dependencies

```toml
# pyproject.toml - Core package
[project]
name = "async-debug-toolbar"
requires-python = ">=3.11"
dependencies = [
    "jinja2>=3.1",
    "markupsafe>=2.1",
]

[project.optional-dependencies]
litestar = ["litestar-debug-toolbar"]
sqlalchemy = ["async-debug-toolbar[advanced-alchemy]"]
advanced-alchemy = [
    "advanced-alchemy>=0.10",
    "sqlalchemy>=2.0",
]

# Litestar plugin package
[project]
name = "litestar-debug-toolbar"
dependencies = [
    "async-debug-toolbar>=1.0",
    "litestar>=2.0",
]
```

---

## 3. Core Components

### 3.1 DebugToolbar Manager

The central orchestrator managing panel lifecycle and data collection.

```python
# src/async_debug_toolbar/toolbar.py
from __future__ import annotations

import uuid
from collections import OrderedDict
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Sequence

from async_debug_toolbar.config import DebugToolbarConfig
from async_debug_toolbar.context import get_request_context, set_request_context
from async_debug_toolbar.storage import ToolbarStorage

if TYPE_CHECKING:
    from async_debug_toolbar.panel import Panel
    from async_debug_toolbar.adapters.base import ASGIAdapter


class DebugToolbar:
    """Main debug toolbar manager.

    Responsibilities:
    - Panel lifecycle management (create, enable/disable, destroy)
    - Request context initialization
    - Data collection orchestration
    - Toolbar rendering coordination
    """

    __slots__ = (
        "_config",
        "_storage",
        "_panels",
        "_adapter",
        "_request_id",
    )

    def __init__(
        self,
        config: DebugToolbarConfig,
        adapter: ASGIAdapter,
    ) -> None:
        self._config = config
        self._adapter = adapter
        self._storage = ToolbarStorage(max_size=config.max_history)
        self._panels: OrderedDict[str, Panel] = OrderedDict()
        self._request_id: str | None = None

        self._initialize_panels()

    def _initialize_panels(self) -> None:
        """Load and instantiate configured panels."""
        for panel_path in self._config.panels:
            panel_class = self._load_panel_class(panel_path)
            panel = panel_class(toolbar=self, config=self._config)
            self._panels[panel.panel_id] = panel

    @staticmethod
    @lru_cache(maxsize=64)
    def _load_panel_class(panel_path: str) -> type[Panel]:
        """Dynamically load panel class from dotted path."""
        module_path, class_name = panel_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)

    async def process_request(self, scope: dict[str, Any]) -> str:
        """Initialize context for a new request. Returns request_id."""
        self._request_id = str(uuid.uuid4())

        ctx = {
            "request_id": self._request_id,
            "scope": scope,
            "panels_data": {},
            "start_time": None,
            "end_time": None,
        }
        set_request_context(ctx)

        for panel in self._panels.values():
            if panel.enabled:
                await panel.process_request(scope)

        return self._request_id

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        """Finalize data collection after response."""
        ctx = get_request_context()
        if ctx is None:
            return

        for panel in self._panels.values():
            if panel.enabled:
                await panel.process_response(scope, status_code, headers, body)

        # Store collected data
        self._storage.store(
            request_id=ctx["request_id"],
            data={
                "panels": ctx["panels_data"],
                "start_time": ctx["start_time"],
                "end_time": ctx["end_time"],
                "status_code": status_code,
                "path": scope.get("path", "/"),
                "method": scope.get("method", "GET"),
            },
        )

    def get_panel(self, panel_id: str) -> Panel | None:
        """Retrieve panel by ID."""
        return self._panels.get(panel_id)

    def get_panels(self) -> Sequence[Panel]:
        """Get all panels in order."""
        return list(self._panels.values())

    @property
    def storage(self) -> ToolbarStorage:
        """Access toolbar storage."""
        return self._storage

    @property
    def config(self) -> DebugToolbarConfig:
        """Access toolbar configuration."""
        return self._config

    @property
    def adapter(self) -> ASGIAdapter:
        """Access framework adapter."""
        return self._adapter
```

### 3.2 Base Panel Class

Abstract base class defining the panel interface.

```python
# src/async_debug_toolbar/panel.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from async_debug_toolbar.context import get_request_context

if TYPE_CHECKING:
    from async_debug_toolbar.toolbar import DebugToolbar
    from async_debug_toolbar.config import DebugToolbarConfig


class Panel(ABC):
    """Abstract base class for debug toolbar panels.

    Lifecycle:
    1. __init__: Panel instantiation (once per toolbar)
    2. process_request: Called at request start
    3. process_response: Called after response
    4. generate_stats: Compute panel statistics
    5. generate_server_timing: Generate Server-Timing header value
    6. render: Generate panel HTML
    """

    # Class-level configuration
    panel_id: ClassVar[str]
    title: ClassVar[str]
    template: ClassVar[str]

    # Whether panel is enabled by default
    default_enabled: ClassVar[bool] = True

    # Panel ordering weight (lower = earlier)
    weight: ClassVar[int] = 100

    # Scripts to include in rendered toolbar
    scripts: ClassVar[list[str]] = []

    # Styles to include in rendered toolbar
    styles: ClassVar[list[str]] = []

    __slots__ = ("_toolbar", "_config", "_enabled")

    def __init__(
        self,
        toolbar: DebugToolbar,
        config: DebugToolbarConfig,
    ) -> None:
        self._toolbar = toolbar
        self._config = config
        self._enabled = self.default_enabled

    @property
    def enabled(self) -> bool:
        """Check if panel is enabled."""
        panel_config = self._config.panel_options.get(self.panel_id, {})
        return panel_config.get("enabled", self._enabled)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set panel enabled state."""
        self._enabled = value

    async def process_request(self, scope: dict[str, Any]) -> None:
        """Hook called at request start. Override to collect request data."""
        pass

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        """Hook called after response. Override to collect response data."""
        pass

    @abstractmethod
    async def generate_stats(self) -> dict[str, Any]:
        """Generate statistics for this panel.

        Returns:
            Dictionary of statistics to be stored and rendered.
        """
        ...

    def generate_server_timing(self) -> str | None:
        """Generate Server-Timing header value for this panel.

        Returns:
            Server-Timing metric string or None if not applicable.
        """
        return None

    def record_stats(self, stats: dict[str, Any]) -> None:
        """Store statistics in request context."""
        ctx = get_request_context()
        if ctx is not None:
            ctx["panels_data"][self.panel_id] = stats

    def get_stats(self) -> dict[str, Any]:
        """Retrieve stored statistics from context."""
        ctx = get_request_context()
        if ctx is None:
            return {}
        return ctx["panels_data"].get(self.panel_id, {})

    @property
    def nav_title(self) -> str:
        """Title shown in toolbar navigation."""
        return self.title

    @property
    def nav_subtitle(self) -> str:
        """Subtitle shown in toolbar navigation (e.g., timing)."""
        return ""

    @property
    def has_content(self) -> bool:
        """Whether panel has content to display."""
        return True

    def get_template_context(self) -> dict[str, Any]:
        """Get context for template rendering."""
        return {
            "panel": self,
            "stats": self.get_stats(),
        }
```

### 3.3 Configuration System

Dataclass-based configuration with sensible defaults.

```python
# src/async_debug_toolbar/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# Default panels in display order
DEFAULT_PANELS: list[str] = [
    "async_debug_toolbar.panels.timer.TimerPanel",
    "async_debug_toolbar.panels.request.RequestPanel",
    "async_debug_toolbar.panels.response.ResponsePanel",
    "async_debug_toolbar.panels.logging.LoggingPanel",
    "async_debug_toolbar.panels.versions.VersionsPanel",
    "async_debug_toolbar.panels.routes.RoutesPanel",
]


@dataclass
class DebugToolbarConfig:
    """Configuration for the debug toolbar.

    Attributes:
        enabled: Master switch for toolbar (default: True in DEBUG mode)
        panels: List of panel class paths to load
        panel_options: Per-panel configuration overrides
        max_history: Maximum requests to keep in history (LRU)
        show_on_redirects: Show toolbar on redirect responses
        intercept_redirects: Intercept and display redirect info
        results_cache_size: Size of template rendering cache
        root_path: URL path prefix for toolbar endpoints
        show_toolbar_callback: Callable to determine if toolbar shows
        insert_before: HTML tag before which to insert toolbar
        extra_scripts: Additional JS files to include
        extra_styles: Additional CSS files to include
    """

    enabled: bool = True
    panels: list[str] = field(default_factory=lambda: DEFAULT_PANELS.copy())
    panel_options: dict[str, dict[str, Any]] = field(default_factory=dict)
    max_history: int = 50
    show_on_redirects: bool = True
    intercept_redirects: bool = False
    results_cache_size: int = 25
    root_path: str = "/_debug_toolbar"
    show_toolbar_callback: Callable[[dict[str, Any]], bool] | None = None
    insert_before: str = "</body>"
    extra_scripts: list[str] = field(default_factory=list)
    extra_styles: list[str] = field(default_factory=list)

    # Security settings
    allowed_hosts: list[str] = field(default_factory=lambda: ["127.0.0.1", "localhost"])
    require_local: bool = True

    # Performance settings
    enable_profiling: bool = False
    profiling_threshold_ms: float = 100.0

    def __post_init__(self) -> None:
        if not self.root_path.startswith("/"):
            self.root_path = f"/{self.root_path}"
        self.root_path = self.root_path.rstrip("/")

    def should_show_toolbar(self, scope: dict[str, Any]) -> bool:
        """Determine if toolbar should be displayed for this request."""
        if not self.enabled:
            return False

        if self.show_toolbar_callback is not None:
            return self.show_toolbar_callback(scope)

        # Check for local request if required
        if self.require_local:
            client = scope.get("client")
            if client is None:
                return False
            client_host = client[0] if isinstance(client, tuple) else client
            if client_host not in self.allowed_hosts:
                return False

        # Skip toolbar's own requests
        path = scope.get("path", "")
        if path.startswith(self.root_path):
            return False

        return True

    def add_panel(self, panel_path: str, index: int | None = None) -> None:
        """Add a panel to the configuration."""
        if panel_path not in self.panels:
            if index is not None:
                self.panels.insert(index, panel_path)
            else:
                self.panels.append(panel_path)

    def remove_panel(self, panel_path: str) -> None:
        """Remove a panel from the configuration."""
        if panel_path in self.panels:
            self.panels.remove(panel_path)
```

### 3.4 Storage Backend

LRU-based storage for toolbar request history.

```python
# src/async_debug_toolbar/storage.py
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ToolbarRecord:
    """A single toolbar record for one request."""

    request_id: str
    timestamp: datetime
    method: str
    path: str
    status_code: int
    start_time: float | None
    end_time: float | None
    panels_data: dict[str, Any]

    @property
    def duration_ms(self) -> float | None:
        """Request duration in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class ToolbarStorage:
    """Thread-safe LRU storage for toolbar data.

    Uses OrderedDict for O(1) access and LRU eviction.
    Thread-safe for concurrent access from multiple requests.
    """

    __slots__ = ("_max_size", "_data", "_lock")

    def __init__(self, max_size: int = 50) -> None:
        self._max_size = max_size
        self._data: OrderedDict[str, ToolbarRecord] = OrderedDict()
        self._lock = threading.RLock()

    def store(self, request_id: str, data: dict[str, Any]) -> None:
        """Store toolbar data for a request."""
        record = ToolbarRecord(
            request_id=request_id,
            timestamp=datetime.now(),
            method=data.get("method", "GET"),
            path=data.get("path", "/"),
            status_code=data.get("status_code", 200),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            panels_data=data.get("panels", {}),
        )

        with self._lock:
            # Move to end if exists (LRU update)
            if request_id in self._data:
                self._data.move_to_end(request_id)
            self._data[request_id] = record

            # Evict oldest if over capacity
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)

    def get(self, request_id: str) -> ToolbarRecord | None:
        """Retrieve toolbar data by request ID."""
        with self._lock:
            record = self._data.get(request_id)
            if record is not None:
                self._data.move_to_end(request_id)
            return record

    def get_history(self, limit: int | None = None) -> list[ToolbarRecord]:
        """Get request history, most recent first."""
        with self._lock:
            records = list(reversed(self._data.values()))
            if limit is not None:
                records = records[:limit]
            return records

    def clear(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
```

### 3.5 Request Context

Context variable management for request-scoped data.

```python
# src/async_debug_toolbar/context.py
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, TypedDict


class RequestContext(TypedDict):
    """Type definition for request context."""

    request_id: str
    scope: dict[str, Any]
    panels_data: dict[str, Any]
    start_time: float | None
    end_time: float | None


_request_context: ContextVar[RequestContext | None] = ContextVar(
    "debug_toolbar_context",
    default=None,
)


def get_request_context() -> RequestContext | None:
    """Get the current request context."""
    return _request_context.get()


def set_request_context(ctx: RequestContext) -> None:
    """Set the current request context."""
    _request_context.set(ctx)


def clear_request_context() -> None:
    """Clear the current request context."""
    _request_context.set(None)


class RequestContextManager:
    """Async context manager for request context lifecycle."""

    __slots__ = ("_ctx", "_token")

    def __init__(self, ctx: RequestContext) -> None:
        self._ctx = ctx
        self._token = None

    async def __aenter__(self) -> RequestContext:
        self._token = _request_context.set(self._ctx)
        return self._ctx

    async def __aexit__(self, *args: Any) -> None:
        if self._token is not None:
            _request_context.reset(self._token)
```

### 3.6 Template/Rendering System

Jinja2-based rendering with async support.

```python
# src/async_debug_toolbar/rendering/engine.py
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from async_debug_toolbar.panel import Panel
    from async_debug_toolbar.toolbar import DebugToolbar


class TemplateEngine(ABC):
    """Abstract template engine interface."""

    @abstractmethod
    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with context."""
        ...

    @abstractmethod
    def render_toolbar(
        self,
        toolbar: DebugToolbar,
        request_id: str,
    ) -> str:
        """Render the complete toolbar HTML."""
        ...

    @abstractmethod
    def render_panel(
        self,
        panel: Panel,
        stats: dict[str, Any],
    ) -> str:
        """Render a single panel's content."""
        ...
```

```python
# src/async_debug_toolbar/rendering/jinja.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from async_debug_toolbar.rendering.engine import TemplateEngine

if TYPE_CHECKING:
    from async_debug_toolbar.panel import Panel
    from async_debug_toolbar.toolbar import DebugToolbar


TEMPLATES_DIR = Path(__file__).parent / "templates"


class JinjaTemplateEngine(TemplateEngine):
    """Jinja2-based template engine implementation."""

    __slots__ = ("_env", "_cache_size")

    def __init__(
        self,
        templates_dir: Path | None = None,
        cache_size: int = 25,
    ) -> None:
        self._cache_size = cache_size

        loader = FileSystemLoader([
            templates_dir or TEMPLATES_DIR,
            TEMPLATES_DIR,  # Fallback to defaults
        ])

        self._env = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,  # Sync rendering for simplicity
        )

        # Register custom filters
        self._env.filters["format_bytes"] = self._format_bytes
        self._env.filters["format_duration"] = self._format_duration
        self._env.filters["highlight_sql"] = self._highlight_sql

    @staticmethod
    def _format_bytes(value: int) -> str:
        """Format byte size for display."""
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(value) < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"

    @staticmethod
    def _format_duration(value: float) -> str:
        """Format duration in ms for display."""
        if value < 1:
            return f"{value * 1000:.2f} us"
        if value < 1000:
            return f"{value:.2f} ms"
        return f"{value / 1000:.2f} s"

    @staticmethod
    def _highlight_sql(sql: str) -> Markup:
        """Basic SQL syntax highlighting."""
        keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER",
            "OUTER", "ON", "AND", "OR", "INSERT", "UPDATE", "DELETE",
            "CREATE", "DROP", "ALTER", "INDEX", "TABLE", "INTO", "VALUES",
            "SET", "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET",
            "UNION", "ALL", "DISTINCT", "AS", "IN", "NOT", "NULL", "IS",
            "LIKE", "BETWEEN", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
        ]

        result = sql
        for kw in keywords:
            result = result.replace(
                f" {kw} ",
                f' <span class="sql-keyword">{kw}</span> ',
            )
        return Markup(result)

    @lru_cache(maxsize=25)
    def _get_template(self, template_name: str):
        """Get cached template."""
        return self._env.get_template(template_name)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with context."""
        template = self._get_template(template_name)
        return template.render(context)

    def render_toolbar(
        self,
        toolbar: DebugToolbar,
        request_id: str,
    ) -> str:
        """Render the complete toolbar HTML."""
        record = toolbar.storage.get(request_id)
        if record is None:
            return ""

        panels_html = []
        for panel in toolbar.get_panels():
            if panel.enabled:
                panel_stats = record.panels_data.get(panel.panel_id, {})
                panels_html.append({
                    "panel": panel,
                    "stats": panel_stats,
                    "content": self.render_panel(panel, panel_stats),
                })

        context = {
            "toolbar": toolbar,
            "request_id": request_id,
            "record": record,
            "panels": panels_html,
            "config": toolbar.config,
        }

        return self.render("toolbar.html", context)

    def render_panel(
        self,
        panel: Panel,
        stats: dict[str, Any],
    ) -> str:
        """Render a single panel's content."""
        context = panel.get_template_context()
        context["stats"] = stats
        return self.render(panel.template, context)
```

### 3.7 Abstract ASGI Adapter

Interface for framework-specific integration.

```python
# src/async_debug_toolbar/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Awaitable

if TYPE_CHECKING:
    from async_debug_toolbar.toolbar import DebugToolbar

ASGIApp = Callable[
    [dict[str, Any], Callable[[], Awaitable[dict]], Callable[[dict], Awaitable[None]]],
    Awaitable[None],
]


class ASGIAdapter(ABC):
    """Abstract adapter for framework-specific ASGI integration.

    Implement this for each framework to handle:
    - Route extraction
    - Request/response body access
    - Framework-specific features
    """

    @abstractmethod
    def get_routes(self) -> list[dict[str, Any]]:
        """Extract available routes from the application.

        Returns:
            List of route dictionaries with keys:
            - path: URL pattern
            - methods: List of HTTP methods
            - name: Route name (optional)
            - handler: Handler function/class name
        """
        ...

    @abstractmethod
    def get_request_body(self, scope: dict[str, Any]) -> bytes | None:
        """Get the request body if available.

        Note: Body may need to be buffered by middleware.
        """
        ...

    @abstractmethod
    def get_response_body(
        self,
        scope: dict[str, Any],
        body: bytes,
    ) -> bytes:
        """Get the response body for inspection."""
        ...

    @abstractmethod
    def should_inject_toolbar(
        self,
        scope: dict[str, Any],
        headers: list[tuple[bytes, bytes]],
    ) -> bool:
        """Determine if toolbar should be injected into response."""
        ...

    @abstractmethod
    def inject_toolbar(
        self,
        body: bytes,
        toolbar_html: str,
        insert_before: str,
    ) -> bytes:
        """Inject toolbar HTML into response body."""
        ...

    def get_dependency(self, name: str) -> Any:
        """Get a framework dependency by name (e.g., database session)."""
        return None
```

---

## 4. Built-in Panels

### 4.1 TimerPanel

Captures request timing metrics.

```python
# src/async_debug_toolbar/panels/timer.py
from __future__ import annotations

import time
from typing import Any, ClassVar

from async_debug_toolbar.context import get_request_context
from async_debug_toolbar.panel import Panel


class TimerPanel(Panel):
    """Panel displaying request timing information."""

    panel_id: ClassVar[str] = "timer"
    title: ClassVar[str] = "Time"
    template: ClassVar[str] = "panels/timer.html"
    weight: ClassVar[int] = 10

    async def process_request(self, scope: dict[str, Any]) -> None:
        ctx = get_request_context()
        if ctx is not None:
            ctx["start_time"] = time.perf_counter()

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        ctx = get_request_context()
        if ctx is not None:
            ctx["end_time"] = time.perf_counter()

        stats = await self.generate_stats()
        self.record_stats(stats)

    async def generate_stats(self) -> dict[str, Any]:
        ctx = get_request_context()
        if ctx is None:
            return {}

        start = ctx.get("start_time")
        end = ctx.get("end_time")

        if start is None or end is None:
            return {"total_time_ms": None}

        total_time = (end - start) * 1000

        return {
            "total_time_ms": total_time,
            "start_time": start,
            "end_time": end,
        }

    def generate_server_timing(self) -> str | None:
        stats = self.get_stats()
        total = stats.get("total_time_ms")
        if total is not None:
            return f"total;dur={total:.2f}"
        return None

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        total = stats.get("total_time_ms")
        if total is not None:
            return f"{total:.2f} ms"
        return ""
```

### 4.2 RequestPanel

Displays request information.

```python
# src/async_debug_toolbar/panels/request.py
from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import parse_qs

from async_debug_toolbar.panel import Panel


class RequestPanel(Panel):
    """Panel displaying request information."""

    panel_id: ClassVar[str] = "request"
    title: ClassVar[str] = "Request"
    template: ClassVar[str] = "panels/request.html"
    weight: ClassVar[int] = 20

    async def process_request(self, scope: dict[str, Any]) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)

    async def generate_stats(self) -> dict[str, Any]:
        from async_debug_toolbar.context import get_request_context

        ctx = get_request_context()
        if ctx is None:
            return {}

        scope = ctx["scope"]

        # Parse headers
        headers = {}
        for key, value in scope.get("headers", []):
            key_str = key.decode("latin-1") if isinstance(key, bytes) else key
            value_str = value.decode("latin-1") if isinstance(value, bytes) else value
            headers[key_str] = value_str

        # Parse query string
        query_string = scope.get("query_string", b"")
        if isinstance(query_string, bytes):
            query_string = query_string.decode("latin-1")
        query_params = parse_qs(query_string)

        # Get cookies
        cookies = {}
        cookie_header = headers.get("cookie", "")
        if cookie_header:
            for item in cookie_header.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value

        return {
            "method": scope.get("method", "GET"),
            "path": scope.get("path", "/"),
            "query_string": query_string,
            "query_params": query_params,
            "headers": headers,
            "cookies": cookies,
            "client": scope.get("client"),
            "server": scope.get("server"),
            "scheme": scope.get("scheme", "http"),
            "http_version": scope.get("http_version", "1.1"),
            "asgi": scope.get("asgi", {}),
        }
```

### 4.3 ResponsePanel

Displays response information.

```python
# src/async_debug_toolbar/panels/response.py
from __future__ import annotations

from typing import Any, ClassVar

from async_debug_toolbar.panel import Panel


class ResponsePanel(Panel):
    """Panel displaying response information."""

    panel_id: ClassVar[str] = "response"
    title: ClassVar[str] = "Response"
    template: ClassVar[str] = "panels/response.html"
    weight: ClassVar[int] = 30

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        stats = await self._generate_response_stats(status_code, headers, body)
        self.record_stats(stats)

    async def _generate_response_stats(
        self,
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> dict[str, Any]:
        # Parse headers
        response_headers = {}
        content_type = "application/octet-stream"

        for key, value in headers:
            key_str = key.decode("latin-1") if isinstance(key, bytes) else key
            value_str = value.decode("latin-1") if isinstance(value, bytes) else value
            response_headers[key_str] = value_str
            if key_str.lower() == "content-type":
                content_type = value_str

        # Body preview (truncated for large responses)
        body_preview = None
        body_size = len(body)

        if body_size > 0 and body_size < 10000:
            if "text" in content_type or "json" in content_type or "xml" in content_type:
                try:
                    body_preview = body.decode("utf-8")
                except UnicodeDecodeError:
                    body_preview = body.decode("latin-1")

        return {
            "status_code": status_code,
            "headers": response_headers,
            "content_type": content_type,
            "body_size": body_size,
            "body_preview": body_preview,
        }

    async def generate_stats(self) -> dict[str, Any]:
        return self.get_stats()

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        status = stats.get("status_code")
        if status is not None:
            return str(status)
        return ""
```

### 4.4 LoggingPanel

Captures logs during request processing.

```python
# src/async_debug_toolbar/panels/logging.py
from __future__ import annotations

import logging
import threading
from typing import Any, ClassVar

from async_debug_toolbar.context import get_request_context
from async_debug_toolbar.panel import Panel


class ToolbarLoggingHandler(logging.Handler):
    """Logging handler that captures logs for the toolbar."""

    def __init__(self) -> None:
        super().__init__()
        self._records: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        ctx = get_request_context()
        if ctx is None:
            return

        request_id = ctx["request_id"]

        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcname": record.funcName,
            "time": record.created,
        }

        if record.exc_info:
            log_entry["exception"] = self.format(record)

        with self._lock:
            if request_id not in self._records:
                self._records[request_id] = []
            self._records[request_id].append(log_entry)

    def get_records(self, request_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return self._records.pop(request_id, [])


class LoggingPanel(Panel):
    """Panel displaying captured log messages."""

    panel_id: ClassVar[str] = "logging"
    title: ClassVar[str] = "Logging"
    template: ClassVar[str] = "panels/logging.html"
    weight: ClassVar[int] = 40

    _handler: ToolbarLoggingHandler | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._setup_handler()

    def _setup_handler(self) -> None:
        if LoggingPanel._handler is None:
            LoggingPanel._handler = ToolbarLoggingHandler()
            LoggingPanel._handler.setLevel(logging.DEBUG)
            logging.root.addHandler(LoggingPanel._handler)

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)

    async def generate_stats(self) -> dict[str, Any]:
        ctx = get_request_context()
        if ctx is None or self._handler is None:
            return {"records": [], "count": 0}

        records = self._handler.get_records(ctx["request_id"])

        # Group by level
        by_level = {}
        for record in records:
            level = record["level"]
            if level not in by_level:
                by_level[level] = 0
            by_level[level] += 1

        return {
            "records": records,
            "count": len(records),
            "by_level": by_level,
        }

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        count = stats.get("count", 0)
        if count > 0:
            return str(count)
        return ""
```

### 4.5 ProfilingPanel

cProfile integration for detailed profiling.

```python
# src/async_debug_toolbar/panels/profiling.py
from __future__ import annotations

import cProfile
import io
import pstats
from typing import Any, ClassVar

from async_debug_toolbar.context import get_request_context
from async_debug_toolbar.panel import Panel


class ProfilingPanel(Panel):
    """Panel for cProfile-based request profiling."""

    panel_id: ClassVar[str] = "profiling"
    title: ClassVar[str] = "Profiling"
    template: ClassVar[str] = "panels/profiling.html"
    weight: ClassVar[int] = 90
    default_enabled: ClassVar[bool] = False  # Disabled by default due to overhead

    _profiler: cProfile.Profile | None = None

    async def process_request(self, scope: dict[str, Any]) -> None:
        if not self._config.enable_profiling:
            return

        self._profiler = cProfile.Profile()
        self._profiler.enable()

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        if self._profiler is None:
            return

        self._profiler.disable()
        stats = await self.generate_stats()
        self.record_stats(stats)
        self._profiler = None

    async def generate_stats(self) -> dict[str, Any]:
        if self._profiler is None:
            return {"enabled": False, "stats": None}

        # Generate stats output
        stream = io.StringIO()
        ps = pstats.Stats(self._profiler, stream=stream)
        ps.sort_stats("cumulative")
        ps.print_stats(50)

        stats_text = stream.getvalue()

        # Parse into structured data
        calls = []
        for stat in ps.stats.items():
            (filename, lineno, func), (cc, nc, tt, ct, callers) = stat
            calls.append({
                "filename": filename,
                "lineno": lineno,
                "function": func,
                "primitive_calls": cc,
                "total_calls": nc,
                "total_time": tt,
                "cumulative_time": ct,
            })

        # Sort by cumulative time
        calls.sort(key=lambda x: x["cumulative_time"], reverse=True)

        return {
            "enabled": True,
            "stats_text": stats_text,
            "calls": calls[:50],  # Top 50 calls
            "total_calls": ps.total_calls,
            "total_time": ps.total_tt,
        }

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        if stats.get("enabled"):
            total_time = stats.get("total_time", 0)
            return f"{total_time * 1000:.1f} ms"
        return "Off"
```

### 4.6 VersionsPanel

Displays Python and package versions.

```python
# src/async_debug_toolbar/panels/versions.py
from __future__ import annotations

import platform
import sys
from importlib.metadata import distributions, version
from typing import Any, ClassVar

from async_debug_toolbar.panel import Panel


class VersionsPanel(Panel):
    """Panel displaying Python and package versions."""

    panel_id: ClassVar[str] = "versions"
    title: ClassVar[str] = "Versions"
    template: ClassVar[str] = "panels/versions.html"
    weight: ClassVar[int] = 100

    async def generate_stats(self) -> dict[str, Any]:
        # Python info
        python_info = {
            "version": sys.version,
            "version_info": list(sys.version_info),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "executable": sys.executable,
        }

        # Installed packages
        packages = []
        for dist in distributions():
            packages.append({
                "name": dist.metadata["Name"],
                "version": dist.metadata["Version"],
            })

        packages.sort(key=lambda x: x["name"].lower())

        # Key packages (highlight these)
        key_packages = [
            "litestar",
            "async-debug-toolbar",
            "litestar-debug-toolbar",
            "sqlalchemy",
            "advanced-alchemy",
            "pydantic",
            "uvicorn",
            "starlette",
        ]

        highlighted = []
        for pkg_name in key_packages:
            try:
                pkg_version = version(pkg_name)
                highlighted.append({"name": pkg_name, "version": pkg_version})
            except Exception:
                pass

        return {
            "python": python_info,
            "packages": packages,
            "highlighted": highlighted,
        }

    async def process_request(self, scope: dict[str, Any]) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)
```

### 4.7 RoutesPanel

Displays available routes.

```python
# src/async_debug_toolbar/panels/routes.py
from __future__ import annotations

from typing import Any, ClassVar

from async_debug_toolbar.panel import Panel


class RoutesPanel(Panel):
    """Panel displaying available application routes."""

    panel_id: ClassVar[str] = "routes"
    title: ClassVar[str] = "Routes"
    template: ClassVar[str] = "panels/routes.html"
    weight: ClassVar[int] = 80

    async def generate_stats(self) -> dict[str, Any]:
        adapter = self._toolbar.adapter
        routes = adapter.get_routes()

        # Group routes by path prefix
        grouped = {}
        for route in routes:
            path = route.get("path", "/")
            prefix = "/" + path.strip("/").split("/")[0] if path != "/" else "/"
            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append(route)

        return {
            "routes": routes,
            "grouped": grouped,
            "count": len(routes),
        }

    async def process_request(self, scope: dict[str, Any]) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        count = stats.get("count", 0)
        return str(count)
```

---

## 5. Extension Points

### 5.1 Creating Custom Panels

Custom panels extend the base `Panel` class:

```python
# Example: Custom CachePanel
from async_debug_toolbar.panel import Panel
from typing import Any, ClassVar


class CachePanel(Panel):
    """Custom panel for cache statistics."""

    panel_id: ClassVar[str] = "cache"
    title: ClassVar[str] = "Cache"
    template: ClassVar[str] = "panels/cache.html"
    weight: ClassVar[int] = 60

    # Track cache operations
    _hits: int = 0
    _misses: int = 0
    _operations: list[dict[str, Any]] = []

    async def process_request(self, scope: dict[str, Any]) -> None:
        # Reset per-request state
        self._hits = 0
        self._misses = 0
        self._operations = []

    def record_hit(self, key: str, value: Any) -> None:
        """Call this from your cache wrapper."""
        self._hits += 1
        self._operations.append({
            "type": "hit",
            "key": key,
        })

    def record_miss(self, key: str) -> None:
        """Call this from your cache wrapper."""
        self._misses += 1
        self._operations.append({
            "type": "miss",
            "key": key,
        })

    async def generate_stats(self) -> dict[str, Any]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "operations": self._operations,
            "hit_rate": self._hits / (self._hits + self._misses) if self._operations else 0,
        }

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)
```

### 5.2 Panel Registration

Register custom panels via configuration:

```python
from async_debug_toolbar.config import DebugToolbarConfig

config = DebugToolbarConfig(
    panels=[
        # Built-in panels
        "async_debug_toolbar.panels.timer.TimerPanel",
        "async_debug_toolbar.panels.request.RequestPanel",
        # Custom panel
        "myapp.panels.cache.CachePanel",
    ],
    panel_options={
        "cache": {
            "enabled": True,
            "show_values": False,
        },
    },
)
```

### 5.3 Hook System

Hooks allow panels to intercept various points in the request lifecycle:

```python
# src/async_debug_toolbar/hooks.py
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Awaitable


class HookType(Enum):
    """Available hook points."""

    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"
    ON_ERROR = "on_error"


HookCallback = Callable[[dict[str, Any]], Awaitable[None]]


class HookRegistry:
    """Registry for toolbar hooks."""

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[HookCallback]] = {
            hook: [] for hook in HookType
        }

    def register(self, hook_type: HookType, callback: HookCallback) -> None:
        """Register a hook callback."""
        self._hooks[hook_type].append(callback)

    def unregister(self, hook_type: HookType, callback: HookCallback) -> None:
        """Unregister a hook callback."""
        if callback in self._hooks[hook_type]:
            self._hooks[hook_type].remove(callback)

    async def trigger(self, hook_type: HookType, context: dict[str, Any]) -> None:
        """Trigger all callbacks for a hook type."""
        for callback in self._hooks[hook_type]:
            await callback(context)
```

### 5.4 Template Customization

Override templates by providing a custom templates directory:

```python
from pathlib import Path
from async_debug_toolbar.rendering.jinja import JinjaTemplateEngine

engine = JinjaTemplateEngine(
    templates_dir=Path("/path/to/custom/templates"),
)
```

---

## 6. Litestar Plugin Design

### 6.1 Plugin Implementation

```python
# src/litestar_debug_toolbar/plugin.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from litestar.plugins import InitPluginProtocol

from async_debug_toolbar.config import DebugToolbarConfig
from async_debug_toolbar.toolbar import DebugToolbar
from litestar_debug_toolbar.adapter import LitestarAdapter
from litestar_debug_toolbar.middleware import DebugToolbarMiddleware

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


@dataclass
class DebugToolbarPlugin(InitPluginProtocol):
    """Litestar plugin for the debug toolbar.

    Usage:
        from litestar import Litestar
        from litestar_debug_toolbar import DebugToolbarPlugin

        app = Litestar(
            plugins=[DebugToolbarPlugin()],
        )

    With configuration:
        from litestar_debug_toolbar import DebugToolbarPlugin, DebugToolbarConfig

        plugin = DebugToolbarPlugin(
            config=DebugToolbarConfig(
                panels=[...],
                max_history=100,
            ),
        )

        app = Litestar(plugins=[plugin])
    """

    config: DebugToolbarConfig = field(default_factory=DebugToolbarConfig)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Initialize the debug toolbar on app startup."""
        if not self.config.enabled:
            return app_config

        # Add Litestar-specific panels
        if "litestar_debug_toolbar.panels.routes.LitestarRoutesPanel" not in self.config.panels:
            # Replace generic routes panel with Litestar-specific one
            try:
                idx = self.config.panels.index("async_debug_toolbar.panels.routes.RoutesPanel")
                self.config.panels[idx] = "litestar_debug_toolbar.panels.routes.LitestarRoutesPanel"
            except ValueError:
                self.config.panels.append("litestar_debug_toolbar.panels.routes.LitestarRoutesPanel")

        # Store config for middleware access
        app_config.state["debug_toolbar_config"] = self.config

        # Add middleware (will be initialized when app is available)
        app_config.middleware.insert(0, DebugToolbarMiddleware)

        # Add toolbar route handlers
        from litestar_debug_toolbar.handlers import create_toolbar_handlers
        toolbar_handlers = create_toolbar_handlers(self.config)
        app_config.route_handlers.extend(toolbar_handlers)

        return app_config
```

### 6.2 Middleware Implementation

```python
# src/litestar_debug_toolbar/middleware.py
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from litestar.middleware import AbstractMiddleware
from litestar.enums import ScopeType

from async_debug_toolbar.toolbar import DebugToolbar
from async_debug_toolbar.context import RequestContextManager
from litestar_debug_toolbar.adapter import LitestarAdapter

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.types import ASGIApp, Receive, Scope, Send, Message


class DebugToolbarMiddleware(AbstractMiddleware):
    """ASGI middleware for the debug toolbar.

    Handles:
    - Request/response interception
    - Panel data collection coordination
    - Toolbar HTML injection
    - Server-Timing header generation
    """

    scopes = {ScopeType.HTTP}
    exclude = ["/_debug_toolbar"]

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._toolbar: DebugToolbar | None = None
        self._adapter: LitestarAdapter | None = None

    def _get_toolbar(self, scope: Scope) -> DebugToolbar | None:
        """Lazily initialize toolbar from app state."""
        if self._toolbar is None:
            litestar_app: Litestar = scope["app"]
            config = litestar_app.state.get("debug_toolbar_config")

            if config is None or not config.enabled:
                return None

            self._adapter = LitestarAdapter(litestar_app)
            self._toolbar = DebugToolbar(config=config, adapter=self._adapter)

        return self._toolbar

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process request through toolbar."""
        toolbar = self._get_toolbar(scope)

        if toolbar is None or not toolbar.config.should_show_toolbar(scope):
            await self.app(scope, receive, send)
            return

        # Initialize request context
        request_id = await toolbar.process_request(scope)

        # Capture response
        response_started = False
        status_code = 200
        response_headers: list[tuple[bytes, bytes]] = []
        body_parts: list[bytes] = []

        async def capture_send(message: Message) -> None:
            nonlocal response_started, status_code, response_headers

            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    body_parts.append(body)

                # Only send on final body chunk
                more_body = message.get("more_body", False)
                if not more_body:
                    # Process response through toolbar
                    full_body = b"".join(body_parts)
                    await toolbar.process_response(
                        scope,
                        status_code,
                        response_headers,
                        full_body,
                    )

                    # Inject toolbar if appropriate
                    if self._should_inject(response_headers):
                        full_body = self._inject_toolbar(
                            toolbar,
                            request_id,
                            full_body,
                        )

                    # Add Server-Timing header
                    server_timing = self._generate_server_timing(toolbar)
                    if server_timing:
                        response_headers.append(
                            (b"Server-Timing", server_timing.encode())
                        )

                    # Update content-length
                    response_headers = [
                        (k, v) for k, v in response_headers
                        if k.lower() != b"content-length"
                    ]
                    response_headers.append(
                        (b"Content-Length", str(len(full_body)).encode())
                    )

                    # Send modified response
                    await send({
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": response_headers,
                    })
                    await send({
                        "type": "http.response.body",
                        "body": full_body,
                        "more_body": False,
                    })
                    return

            # Pass through for non-final messages
            if message["type"] == "http.response.start":
                return  # Will be sent with body
            await send(message)

        await self.app(scope, receive, capture_send)

    def _should_inject(self, headers: list[tuple[bytes, bytes]]) -> bool:
        """Check if toolbar should be injected based on content type."""
        for key, value in headers:
            if key.lower() == b"content-type":
                content_type = value.decode("latin-1").lower()
                return "text/html" in content_type
        return False

    def _inject_toolbar(
        self,
        toolbar: DebugToolbar,
        request_id: str,
        body: bytes,
    ) -> bytes:
        """Inject toolbar HTML into response body."""
        from async_debug_toolbar.rendering.jinja import JinjaTemplateEngine

        engine = JinjaTemplateEngine()
        toolbar_html = engine.render_toolbar(toolbar, request_id)

        insert_before = toolbar.config.insert_before.encode()
        if insert_before in body:
            return body.replace(insert_before, toolbar_html.encode() + insert_before)

        return body + toolbar_html.encode()

    def _generate_server_timing(self, toolbar: DebugToolbar) -> str:
        """Generate Server-Timing header from all panels."""
        timings = []
        for panel in toolbar.get_panels():
            if panel.enabled:
                timing = panel.generate_server_timing()
                if timing:
                    timings.append(timing)
        return ", ".join(timings)
```

### 6.3 Litestar Adapter

```python
# src/litestar_debug_toolbar/adapter.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from async_debug_toolbar.adapters.base import ASGIAdapter

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.routes import HTTPRoute


class LitestarAdapter(ASGIAdapter):
    """ASGI adapter for Litestar framework."""

    __slots__ = ("_app",)

    def __init__(self, app: Litestar) -> None:
        self._app = app

    def get_routes(self) -> list[dict[str, Any]]:
        """Extract routes from Litestar application."""
        routes = []

        for route in self._app.routes:
            if hasattr(route, "path"):
                route_info = {
                    "path": route.path,
                    "methods": [],
                    "name": getattr(route, "name", None),
                    "handler": None,
                }

                # Extract methods and handler info
                if hasattr(route, "route_handlers"):
                    for handler in route.route_handlers:
                        route_info["methods"].extend(
                            list(handler.http_methods) if hasattr(handler, "http_methods") else []
                        )
                        route_info["handler"] = f"{handler.fn.__module__}.{handler.fn.__name__}"

                routes.append(route_info)

        return routes

    def get_request_body(self, scope: dict[str, Any]) -> bytes | None:
        """Get request body from scope extensions."""
        return scope.get("_debug_toolbar_body")

    def get_response_body(
        self,
        scope: dict[str, Any],
        body: bytes,
    ) -> bytes:
        """Return response body as-is."""
        return body

    def should_inject_toolbar(
        self,
        scope: dict[str, Any],
        headers: list[tuple[bytes, bytes]],
    ) -> bool:
        """Check if toolbar should be injected."""
        for key, value in headers:
            if key.lower() == b"content-type":
                content_type = value.decode("latin-1").lower()
                return "text/html" in content_type
        return False

    def inject_toolbar(
        self,
        body: bytes,
        toolbar_html: str,
        insert_before: str,
    ) -> bytes:
        """Inject toolbar HTML into response."""
        marker = insert_before.encode()
        if marker in body:
            return body.replace(marker, toolbar_html.encode() + marker)
        return body + toolbar_html.encode()

    def get_dependency(self, name: str) -> Any:
        """Get Litestar dependency by name."""
        return self._app.state.get(name)
```

### 6.4 Toolbar Route Handlers

```python
# src/litestar_debug_toolbar/handlers.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar import Controller, get, Response
from litestar.response import Template
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND

if TYPE_CHECKING:
    from litestar import Request
    from async_debug_toolbar.config import DebugToolbarConfig


def create_toolbar_handlers(config: DebugToolbarConfig) -> list[type]:
    """Create route handlers for toolbar API."""

    class DebugToolbarController(Controller):
        """Controller for debug toolbar endpoints."""

        path = config.root_path
        tags = ["Debug Toolbar"]

        @get("/")
        async def toolbar_index(self, request: Request) -> Response:
            """Toolbar index page showing request history."""
            toolbar = request.app.state.get("debug_toolbar")
            if toolbar is None:
                return Response(
                    content={"error": "Toolbar not initialized"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            history = toolbar.storage.get_history(limit=50)
            return Response(
                content={
                    "history": [
                        {
                            "request_id": r.request_id,
                            "timestamp": r.timestamp.isoformat(),
                            "method": r.method,
                            "path": r.path,
                            "status_code": r.status_code,
                            "duration_ms": r.duration_ms,
                        }
                        for r in history
                    ],
                },
            )

        @get("/request/{request_id:str}")
        async def toolbar_request(
            self,
            request: Request,
            request_id: str,
        ) -> Response:
            """Get toolbar data for a specific request."""
            toolbar = request.app.state.get("debug_toolbar")
            if toolbar is None:
                return Response(
                    content={"error": "Toolbar not initialized"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            record = toolbar.storage.get(request_id)
            if record is None:
                return Response(
                    content={"error": "Request not found"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            return Response(
                content={
                    "request_id": record.request_id,
                    "timestamp": record.timestamp.isoformat(),
                    "method": record.method,
                    "path": record.path,
                    "status_code": record.status_code,
                    "duration_ms": record.duration_ms,
                    "panels": record.panels_data,
                },
            )

        @get("/panel/{request_id:str}/{panel_id:str}")
        async def toolbar_panel(
            self,
            request: Request,
            request_id: str,
            panel_id: str,
        ) -> Response:
            """Get specific panel data for a request."""
            toolbar = request.app.state.get("debug_toolbar")
            if toolbar is None:
                return Response(
                    content={"error": "Toolbar not initialized"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            record = toolbar.storage.get(request_id)
            if record is None:
                return Response(
                    content={"error": "Request not found"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            panel_data = record.panels_data.get(panel_id)
            if panel_data is None:
                return Response(
                    content={"error": "Panel not found"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            return Response(content=panel_data)

        @get("/static/{path:path}")
        async def toolbar_static(
            self,
            request: Request,
            path: str,
        ) -> Response:
            """Serve static assets for toolbar."""
            from pathlib import Path
            import mimetypes

            assets_dir = Path(__file__).parent.parent / "async_debug_toolbar" / "assets"
            file_path = assets_dir / path

            if not file_path.exists() or not file_path.is_file():
                return Response(
                    content={"error": "File not found"},
                    status_code=HTTP_404_NOT_FOUND,
                )

            content_type, _ = mimetypes.guess_type(str(file_path))
            content = file_path.read_bytes()

            return Response(
                content=content,
                media_type=content_type or "application/octet-stream",
            )

    return [DebugToolbarController]
```

### 6.5 Litestar Routes Panel

```python
# src/litestar_debug_toolbar/panels/routes.py
from __future__ import annotations

from typing import Any, ClassVar, TYPE_CHECKING

from async_debug_toolbar.panels.routes import RoutesPanel

if TYPE_CHECKING:
    from litestar import Litestar


class LitestarRoutesPanel(RoutesPanel):
    """Enhanced routes panel for Litestar applications."""

    panel_id: ClassVar[str] = "litestar_routes"
    title: ClassVar[str] = "Routes"
    template: ClassVar[str] = "panels/litestar_routes.html"

    async def generate_stats(self) -> dict[str, Any]:
        """Generate Litestar-specific route information."""
        adapter = self._toolbar.adapter
        base_routes = adapter.get_routes()

        # Enhance with Litestar-specific metadata
        enhanced_routes = []
        for route in base_routes:
            enhanced = {
                **route,
                "guards": [],
                "dependencies": [],
                "middleware": [],
                "tags": [],
            }
            enhanced_routes.append(enhanced)

        # Group by tags
        by_tag: dict[str, list] = {}
        for route in enhanced_routes:
            tags = route.get("tags", ["untagged"])
            for tag in tags:
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append(route)

        return {
            "routes": enhanced_routes,
            "by_tag": by_tag,
            "count": len(enhanced_routes),
        }
```

---

## 7. Advanced-Alchemy Integration

### 7.1 SQLAlchemy Panel

```python
# extras/advanced_alchemy/panel.py
from __future__ import annotations

import time
from typing import Any, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field

from async_debug_toolbar.panel import Panel
from async_debug_toolbar.context import get_request_context

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class QueryRecord:
    """Record of a single database query."""

    sql: str
    params: dict[str, Any] | tuple | None
    duration_ms: float
    stack_trace: str | None = None
    explain_plan: str | None = None
    is_select: bool = False
    rows_affected: int | None = None


class SQLAlchemyPanel(Panel):
    """Panel for SQLAlchemy query tracking and analysis.

    Features:
    - Query capture with timing
    - EXPLAIN plan generation (optional)
    - Query deduplication detection
    - N+1 query detection
    - Stack trace capture
    """

    panel_id: ClassVar[str] = "sqlalchemy"
    title: ClassVar[str] = "SQLAlchemy"
    template: ClassVar[str] = "panels/sqlalchemy.html"
    weight: ClassVar[int] = 50

    _queries: list[QueryRecord]
    _enable_explain: bool
    _capture_stack: bool

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._queries = []

        # Panel-specific options
        options = self._config.panel_options.get("sqlalchemy", {})
        self._enable_explain = options.get("enable_explain", False)
        self._capture_stack = options.get("capture_stack", True)

    async def process_request(self, scope: dict[str, Any]) -> None:
        """Reset query list for new request."""
        self._queries = []

    def record_query(
        self,
        sql: str,
        params: dict[str, Any] | tuple | None,
        duration_ms: float,
        rows_affected: int | None = None,
    ) -> None:
        """Record a query execution (called from event hooks)."""
        import traceback

        stack_trace = None
        if self._capture_stack:
            stack_trace = "".join(traceback.format_stack()[:-2])

        record = QueryRecord(
            sql=sql,
            params=params,
            duration_ms=duration_ms,
            stack_trace=stack_trace,
            is_select=sql.strip().upper().startswith("SELECT"),
            rows_affected=rows_affected,
        )

        self._queries.append(record)

    async def generate_stats(self) -> dict[str, Any]:
        """Generate query statistics."""
        total_time = sum(q.duration_ms for q in self._queries)

        # Detect duplicate queries
        query_counts: dict[str, int] = {}
        for query in self._queries:
            sql = query.sql
            query_counts[sql] = query_counts.get(sql, 0) + 1

        duplicates = {sql: count for sql, count in query_counts.items() if count > 1}

        # Detect potential N+1 queries
        n_plus_one = []
        for sql, count in duplicates.items():
            if count > 5 and "SELECT" in sql.upper():
                n_plus_one.append({"sql": sql, "count": count})

        # Group by type
        selects = [q for q in self._queries if q.is_select]
        writes = [q for q in self._queries if not q.is_select]

        return {
            "queries": [
                {
                    "sql": q.sql,
                    "params": q.params,
                    "duration_ms": q.duration_ms,
                    "stack_trace": q.stack_trace,
                    "explain_plan": q.explain_plan,
                    "is_select": q.is_select,
                    "rows_affected": q.rows_affected,
                }
                for q in self._queries
            ],
            "count": len(self._queries),
            "total_time_ms": total_time,
            "select_count": len(selects),
            "write_count": len(writes),
            "duplicates": duplicates,
            "n_plus_one": n_plus_one,
            "has_issues": len(duplicates) > 0 or len(n_plus_one) > 0,
        }

    async def process_response(
        self,
        scope: dict[str, Any],
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        stats = await self.generate_stats()
        self.record_stats(stats)

    def generate_server_timing(self) -> str | None:
        stats = self.get_stats()
        total = stats.get("total_time_ms")
        count = stats.get("count", 0)
        if total is not None:
            return f"db;dur={total:.2f};desc=\"{count} queries\""
        return None

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        count = stats.get("count", 0)
        total = stats.get("total_time_ms", 0)
        if count > 0:
            return f"{count} / {total:.1f}ms"
        return ""
```

### 7.2 Advanced-Alchemy Event Hooks

```python
# extras/advanced_alchemy/hooks.py
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.engine.cursor import CursorResult


def setup_sqlalchemy_hooks(panel: Any) -> None:
    """Set up SQLAlchemy event hooks for query tracking."""

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Record query start time."""
        conn.info["debug_toolbar_start_time"] = time.perf_counter()

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Record query completion and duration."""
        start_time = conn.info.pop("debug_toolbar_start_time", None)
        if start_time is None:
            return

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get rows affected for non-SELECT queries
        rows_affected = None
        if not statement.strip().upper().startswith("SELECT"):
            rows_affected = cursor.rowcount

        panel.record_query(
            sql=statement,
            params=parameters,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
        )


async def setup_async_hooks(panel: Any, engine: Any) -> None:
    """Set up hooks for async SQLAlchemy engines."""
    from sqlalchemy.ext.asyncio import AsyncEngine

    if not isinstance(engine, AsyncEngine):
        return

    # Async engine wraps sync engine
    setup_sqlalchemy_hooks(panel)
```

### 7.3 Integration with Litestar Plugin

```python
# extras/advanced_alchemy/__init__.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from async_debug_toolbar.config import DebugToolbarConfig

if TYPE_CHECKING:
    from litestar import Litestar


def configure_advanced_alchemy_panel(
    config: DebugToolbarConfig,
    enable_explain: bool = False,
    capture_stack: bool = True,
) -> None:
    """Configure the SQLAlchemy panel for Advanced-Alchemy.

    Usage:
        from async_debug_toolbar.config import DebugToolbarConfig
        from async_debug_toolbar.extras.advanced_alchemy import configure_advanced_alchemy_panel

        config = DebugToolbarConfig()
        configure_advanced_alchemy_panel(config, enable_explain=True)
    """
    # Add panel if not present
    panel_path = "async_debug_toolbar.extras.advanced_alchemy.panel.SQLAlchemyPanel"
    if panel_path not in config.panels:
        # Insert after response panel
        try:
            idx = config.panels.index("async_debug_toolbar.panels.response.ResponsePanel")
            config.panels.insert(idx + 1, panel_path)
        except ValueError:
            config.panels.append(panel_path)

    # Configure panel options
    config.panel_options["sqlalchemy"] = {
        "enabled": True,
        "enable_explain": enable_explain,
        "capture_stack": capture_stack,
    }


def init_advanced_alchemy_hooks(app: Litestar) -> None:
    """Initialize Advanced-Alchemy hooks after app startup.

    Call this in your app's on_startup handler:

        from async_debug_toolbar.extras.advanced_alchemy import init_advanced_alchemy_hooks

        async def on_startup(app: Litestar) -> None:
            init_advanced_alchemy_hooks(app)
    """
    from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
    from async_debug_toolbar.extras.advanced_alchemy.hooks import setup_sqlalchemy_hooks

    toolbar = app.state.get("debug_toolbar")
    if toolbar is None:
        return

    panel = toolbar.get_panel("sqlalchemy")
    if panel is None:
        return

    # Find SQLAlchemy plugin and get engine
    for plugin in app.plugins:
        if isinstance(plugin, SQLAlchemyPlugin):
            # Set up hooks for sync engine
            if hasattr(plugin, "engine"):
                setup_sqlalchemy_hooks(panel)
            break
```

---

## 8. Data Flow

### 8.1 Request Lifecycle

```
                                    ASGI Application
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DebugToolbarMiddleware                               │
│                                                                              │
│   1. Check should_show_toolbar(scope)                                       │
│      └─► If false, pass through to app                                      │
│                                                                              │
│   2. toolbar.process_request(scope)                                         │
│      ├─► Generate request_id (UUID)                                         │
│      ├─► Initialize RequestContext (contextvar)                             │
│      └─► Call panel.process_request() for each enabled panel                │
│                                                                              │
│   3. await app(scope, receive, capture_send)                                │
│      └─► Application processes request                                       │
│      └─► Panels record data via record_stats()                              │
│                                                                              │
│   4. capture_send intercepts response                                        │
│      ├─► Capture status_code, headers, body                                 │
│      └─► Call panel.process_response() for each enabled panel               │
│                                                                              │
│   5. toolbar.process_response(scope, status, headers, body)                 │
│      ├─► Finalize panel statistics                                          │
│      └─► Store in ToolbarStorage (LRU)                                      │
│                                                                              │
│   6. Inject toolbar if HTML response                                         │
│      ├─► Render toolbar HTML                                                │
│      ├─► Insert before </body>                                              │
│      └─► Update Content-Length header                                       │
│                                                                              │
│   7. Add Server-Timing header                                                │
│      └─► Collect from all panels                                            │
│                                                                              │
│   8. Send modified response                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Panel Data Collection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Panel Lifecycle                                 │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ process_request(scope)                                               │   │
│   │   • Called when request starts                                       │   │
│   │   • Initialize panel-specific tracking (e.g., start timer)          │   │
│   │   • Access scope for request data                                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ [During Request Processing]                                          │   │
│   │   • Panel hooks (e.g., SQLAlchemy events) collect data              │   │
│   │   • Logging handler captures log records                             │   │
│   │   • Profiler runs (if enabled)                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ process_response(scope, status_code, headers, body)                  │   │
│   │   • Called after response generated                                  │   │
│   │   • Finalize data collection (e.g., stop timer)                     │   │
│   │   • Access response for data extraction                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ generate_stats() -> dict[str, Any]                                   │   │
│   │   • Compute final statistics                                         │   │
│   │   • Return dictionary for storage/rendering                          │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ record_stats(stats)                                                  │   │
│   │   • Store in RequestContext.panels_data[panel_id]                   │   │
│   │   • Data persisted to ToolbarStorage                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ToolbarStorage (LRU)                              │
│                                                                              │
│   max_size = 50 (configurable)                                              │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ OrderedDict[request_id -> ToolbarRecord]                             │   │
│   │                                                                      │   │
│   │   "abc-123" ─► ToolbarRecord(                                       │   │
│   │                   request_id="abc-123",                             │   │
│   │                   timestamp=datetime(...),                          │   │
│   │                   method="GET",                                      │   │
│   │                   path="/api/users",                                 │   │
│   │                   status_code=200,                                   │   │
│   │                   duration_ms=45.2,                                  │   │
│   │                   panels_data={                                      │   │
│   │                       "timer": {...},                                │   │
│   │                       "request": {...},                              │   │
│   │                       "sqlalchemy": {...},                           │   │
│   │                   }                                                  │   │
│   │               )                                                      │   │
│   │                                                                      │   │
│   │   "def-456" ─► ToolbarRecord(...)                                   │   │
│   │   ...                                                                │   │
│   │   [Oldest entries evicted when max_size exceeded]                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   Operations:                                                                │
│   • store(request_id, data) ─► O(1) insert, LRU eviction                   │
│   • get(request_id) ─► O(1) lookup, moves to end (LRU update)              │
│   • get_history(limit) ─► Returns most recent N records                     │
│   • Thread-safe via RLock                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Security Considerations

### 9.1 Access Control

| Risk | Mitigation |
|------|------------|
| Sensitive data exposure | Toolbar disabled by default in production |
| Remote access | `require_local=True` restricts to localhost |
| Host spoofing | Validate against `allowed_hosts` list |
| Path traversal | Sanitize static file paths |

### 9.2 Configuration Best Practices

```python
# Production-safe configuration
config = DebugToolbarConfig(
    # Only enable via environment variable
    enabled=os.getenv("DEBUG_TOOLBAR_ENABLED", "false").lower() == "true",

    # Restrict to local access
    require_local=True,
    allowed_hosts=["127.0.0.1", "localhost", "::1"],

    # Custom callback for fine-grained control
    show_toolbar_callback=lambda scope: (
        scope.get("app").debug
        and scope.get("client", ("",))[0] in ["127.0.0.1", "::1"]
    ),
)
```

### 9.3 Data Sanitization

Panels must sanitize sensitive data:

```python
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}

SENSITIVE_PARAMS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
}

def sanitize_value(key: str, value: str) -> str:
    """Redact sensitive values."""
    key_lower = key.lower()
    if any(s in key_lower for s in SENSITIVE_PARAMS):
        return "[REDACTED]"
    return value
```

---

## 10. Performance Considerations

### 10.1 Overhead Analysis

| Component | Enabled Overhead | Disabled Overhead |
|-----------|-----------------|-------------------|
| Middleware check | ~0.1ms | ~0.01ms |
| Panel processing | 1-5ms | 0ms |
| Template rendering | 2-10ms | 0ms |
| Storage operations | ~0.1ms | 0ms |
| **Total** | **3-15ms** | **~0.01ms** |

### 10.2 Optimization Strategies

1. **Lazy Initialization**: Toolbar and panels initialized on first request
2. **Conditional Processing**: Skip all panel logic when disabled
3. **LRU Caching**: Bounded memory for request history
4. **Template Caching**: Compiled templates cached
5. **Async-Native**: No blocking operations in request path

### 10.3 Memory Usage

```
Base toolbar instance:    ~50 KB
Per request (50 history): ~10 KB average
  - Timer panel:          ~100 bytes
  - Request panel:        ~2 KB
  - Response panel:       ~1 KB (truncated body)
  - Logging panel:        ~1-10 KB (varies)
  - SQLAlchemy panel:     ~5 KB (10 queries avg)

Total memory footprint:   ~550 KB (50 requests)
```

### 10.4 Profiling Panel Impact

The ProfilingPanel has significant overhead and should only be enabled when needed:

| Mode | Overhead |
|------|----------|
| Disabled | 0ms |
| Basic profiling | 20-100ms |
| With call graph | 50-200ms |

---

## 11. Implementation Roadmap

### Phase 1: Core Foundation (Week 1-2)

- [ ] Project scaffolding with uv
- [ ] Core config and settings system
- [ ] Request context management
- [ ] Storage backend with LRU
- [ ] Base Panel abstract class
- [ ] Template engine with Jinja2

### Phase 2: Built-in Panels (Week 2-3)

- [ ] TimerPanel
- [ ] RequestPanel
- [ ] ResponsePanel
- [ ] LoggingPanel
- [ ] VersionsPanel
- [ ] RoutesPanel

### Phase 3: Litestar Integration (Week 3-4)

- [ ] LitestarAdapter implementation
- [ ] DebugToolbarMiddleware
- [ ] DebugToolbarPlugin
- [ ] Route handlers for toolbar API
- [ ] Static asset serving

### Phase 4: Advanced Features (Week 4-5)

- [ ] ProfilingPanel with cProfile
- [ ] SQLAlchemyPanel for Advanced-Alchemy
- [ ] Event hooks system
- [ ] N+1 query detection
- [ ] EXPLAIN plan integration

### Phase 5: UI/UX (Week 5-6)

- [ ] Toolbar HTML/CSS/JS assets
- [ ] Panel templates
- [ ] History view
- [ ] Request detail view
- [ ] Theme support (light/dark)

### Phase 6: Testing & Documentation (Week 6-7)

- [ ] Unit tests (90%+ coverage)
- [ ] Integration tests with Litestar
- [ ] Performance benchmarks
- [ ] API documentation
- [ ] Usage examples

### Phase 7: Polish & Release (Week 7-8)

- [ ] Security audit
- [ ] Performance optimization
- [ ] PyPI packaging
- [ ] Release automation
- [ ] Announcement/marketing

---

## Appendix A: API Quick Reference

### Toolbar Configuration

```python
from async_debug_toolbar.config import DebugToolbarConfig

config = DebugToolbarConfig(
    enabled=True,
    panels=[...],
    max_history=50,
    root_path="/_debug_toolbar",
)
```

### Litestar Integration

```python
from litestar import Litestar
from litestar_debug_toolbar import DebugToolbarPlugin

app = Litestar(
    plugins=[DebugToolbarPlugin()],
)
```

### Custom Panel

```python
from async_debug_toolbar.panel import Panel

class MyPanel(Panel):
    panel_id = "my_panel"
    title = "My Panel"
    template = "panels/my_panel.html"

    async def generate_stats(self) -> dict:
        return {"custom": "data"}
```

### Advanced-Alchemy Integration

```python
from litestar_debug_toolbar import DebugToolbarPlugin
from async_debug_toolbar.extras.advanced_alchemy import configure_advanced_alchemy_panel

config = DebugToolbarConfig()
configure_advanced_alchemy_panel(config)

app = Litestar(
    plugins=[DebugToolbarPlugin(config=config)],
)
```

---

## Appendix B: Template Structure

### Base Toolbar Template

```html
<!-- templates/toolbar.html -->
<!DOCTYPE html>
<div id="debug-toolbar" class="debug-toolbar">
  <div class="toolbar-handle">
    <button class="toolbar-toggle">Debug</button>
  </div>

  <div class="toolbar-content">
    <nav class="toolbar-nav">
      {% for panel_data in panels %}
      <button class="nav-item" data-panel="{{ panel_data.panel.panel_id }}">
        <span class="nav-title">{{ panel_data.panel.title }}</span>
        <span class="nav-subtitle">{{ panel_data.panel.nav_subtitle }}</span>
      </button>
      {% endfor %}
    </nav>

    <div class="panels-container">
      {% for panel_data in panels %}
      <div class="panel" id="panel-{{ panel_data.panel.panel_id }}">
        {{ panel_data.content|safe }}
      </div>
      {% endfor %}
    </div>
  </div>
</div>

<link rel="stylesheet" href="{{ config.root_path }}/static/css/toolbar.css">
<script src="{{ config.root_path }}/static/js/toolbar.js"></script>
```

---

*Document Version: 1.0.0*
*Last Updated: 2025-11-26*
*Status: Proposed*
