# PRD: Starlette Adapter for Debug Toolbar

**Slug**: `starlette-adapter`
**Priority**: P1 (Expands user base 10x)
**Complexity**: Medium (8 checkpoints)
**Created**: 2025-11-29
**Status**: Planning

---

## Metadata

| Field | Value |
|-------|-------|
| **Feature Type** | Framework Integration |
| **Estimated LOC** | ~800 lines (implementation + tests) |
| **Files to Create** | 8 new files |
| **Files to Modify** | 2 files (pyproject.toml, README) |
| **Test Coverage Target** | 90%+ |
| **Similar Implementations** | `src/debug_toolbar/litestar/` (reference) |
| **Dependencies** | starlette >= 0.27.0 |

---

## Intelligence Context

### Complexity Assessment: Medium (8 Checkpoints)

This feature involves:
- New framework integration (2-3 core files)
- Framework-specific panel (routes panel)
- Configuration system extending base config
- Middleware implementation using pure ASGI pattern
- Example application
- Comprehensive test suite

**Rationale**: Similar to Litestar integration but simpler (no plugin system, no lifecycle hooks). Starlette is more minimal, requiring less framework-specific code.

### Pattern Analysis

Analyzed 3 similar implementations in the codebase:

1. **Litestar Integration** (`src/debug_toolbar/litestar/`)
   - Plugin-based setup using `InitPluginProtocol`
   - Middleware extends `AbstractMiddleware`
   - Framework-specific config extends `DebugToolbarConfig`
   - Routes panel collects from `app.routes`
   - Events panel for lifecycle hooks

2. **Core Middleware Pattern** (`src/debug_toolbar/litestar/middleware.py`)
   - ResponseState dataclass for tracking
   - Send wrapper for response interception
   - HTML injection at `</body>` tag
   - Server-Timing header support
   - Graceful error handling

3. **Core Panel Pattern** (`src/debug_toolbar/core/panel.py`)
   - Abstract base class with `generate_stats()`
   - ClassVar metadata (panel_id, title, template)
   - Request/response lifecycle hooks
   - Context-based data storage

### Key Differences: Starlette vs Litestar

| Aspect | Litestar | Starlette |
|--------|----------|-----------|
| Setup Pattern | Plugin (`InitPluginProtocol`) | Direct middleware |
| Middleware Base | `AbstractMiddleware` | Pure ASGI or `BaseHTTPMiddleware` |
| Route Collection | `app.routes` (typed) | `app.routes` (simpler) |
| Lifecycle Hooks | `before_request`, `after_request` | None (middleware only) |
| Config Integration | `AppConfig.middleware` | `app.add_middleware()` |
| Type System | Extensive Litestar types | Starlette types |

### Starlette-Specific Considerations

Based on research and [Starlette documentation](https://starlette.dev/middleware/):

1. **Pure ASGI Middleware Preferred**: BaseHTTPMiddleware has known limitations with contextvars and streaming responses. Pure ASGI middleware is recommended for production use.

2. **No Plugin System**: Starlette doesn't have a formal plugin protocol. Integration is manual via:
   ```python
   from starlette.applications import Starlette
   from starlette.middleware import Middleware

   app = Starlette(
       routes=[...],
       middleware=[
           Middleware(DebugToolbarMiddleware, config=config)
       ]
   )
   ```

3. **Route Registration**: Starlette uses Mount for path prefixes:
   ```python
   from starlette.routing import Mount, Route

   routes = [
       Mount('/_debug_toolbar', routes=[...])
   ]
   ```

4. **Request/Response API**: Similar to Litestar but simpler:
   - `Request(scope)` for request data
   - `Response()` for responses
   - No complex lifecycle system

---

## Problem Statement

### Current State

The debug-toolbar project currently supports:
- **Core ASGI framework**: Framework-agnostic panels and storage
- **Litestar integration**: Production-ready with 402 passing tests
- **Example apps**: Litestar-only demonstrations

### User Pain Points

1. **FastAPI/Starlette Users Excluded**: Developers using FastAPI (built on Starlette) or pure Starlette have no access to the toolbar.

2. **Market Size**: Starlette/FastAPI has 10x+ the user base of Litestar:
   - FastAPI: 76k+ GitHub stars
   - Starlette: 10k+ GitHub stars
   - Litestar: 5k+ GitHub stars

3. **Competitive Gap**: Django Debug Toolbar and flask-debugtoolbar dominate their ecosystems. ASGI frameworks lack a modern, feature-rich debugging solution.

### Opportunity

Expanding to Starlette unlocks:
- **FastAPI ecosystem**: Automatic compatibility with FastAPI applications
- **Framework diversity**: Demonstrates true framework-agnostic architecture
- **Community growth**: Access to larger developer community
- **Validation**: Proves the core panel system works across frameworks

---

## Acceptance Criteria

### Must Have (P0)

1. **Pure ASGI Middleware**
   - ✅ Implements pure ASGI pattern (not BaseHTTPMiddleware)
   - ✅ Intercepts HTTP requests and responses
   - ✅ Injects toolbar HTML into HTML responses
   - ✅ Adds Server-Timing headers
   - ✅ Handles errors gracefully without breaking app

2. **Starlette Configuration**
   - ✅ `StarletteDebugToolbarConfig` extends `DebugToolbarConfig`
   - ✅ `exclude_paths` for filtering routes
   - ✅ `exclude_patterns` for regex-based filtering
   - ✅ `show_toolbar_callback` accepting Starlette Request
   - ✅ Default exclusions: `/_debug_toolbar`, `/static`

3. **Routes Panel**
   - ✅ Displays all registered Starlette routes
   - ✅ Shows HTTP methods, paths, handler names
   - ✅ Highlights current/matched route
   - ✅ Handles Route, Mount, WebSocketRoute types
   - ✅ Gracefully handles routes without names

4. **API Routes**
   - ✅ `GET /_debug_toolbar/` - Request history page
   - ✅ `GET /_debug_toolbar/{request_id}` - Request detail page
   - ✅ `GET /_debug_toolbar/api/requests` - JSON list
   - ✅ `GET /_debug_toolbar/api/requests/{request_id}` - JSON detail
   - ✅ `GET /_debug_toolbar/static/toolbar.css` - CSS
   - ✅ `GET /_debug_toolbar/static/toolbar.js` - JavaScript

5. **Example Application**
   - ✅ Basic Starlette app with toolbar
   - ✅ Multiple routes demonstrating features
   - ✅ README with setup/run instructions
   - ✅ Demonstrates all core panels

6. **Documentation**
   - ✅ Installation instructions in main README
   - ✅ Starlette-specific usage guide
   - ✅ Configuration examples
   - ✅ Comparison with Litestar integration

### Should Have (P1)

7. **Advanced Example**
   - ✅ Starlette app with Jinja2 templates
   - ✅ Database integration (SQLAlchemy)
   - ✅ Demonstrates advanced panels (Memory, Profiling)
   - ✅ Production-like configuration

8. **Integration Helpers**
   - ✅ `create_debug_toolbar_app()` factory function
   - ✅ Auto-configuration from environment variables
   - ✅ Debug mode detection

### Nice to Have (P2)

9. **FastAPI Example**
   - ⭕ FastAPI app using Starlette adapter
   - ⭕ Demonstrates compatibility
   - ⭕ Shows OpenAPI integration

10. **Performance Optimization**
    - ⭕ Minimal overhead for excluded routes
    - ⭕ Lazy panel initialization
    - ⭕ Response streaming support

---

## Technical Approach

### Architecture Overview

```
src/debug_toolbar/
├── core/                      # Framework-agnostic (existing)
│   ├── panel.py
│   ├── toolbar.py
│   ├── config.py
│   └── panels/
├── litestar/                  # Litestar integration (existing)
│   ├── middleware.py
│   ├── plugin.py
│   └── panels/
└── starlette/                 # NEW: Starlette integration
    ├── __init__.py            # Public API
    ├── middleware.py          # Pure ASGI middleware
    ├── config.py              # Starlette config
    ├── routes.py              # Route handlers
    └── panels/
        ├── __init__.py
        └── routes.py          # Routes panel
```

### Implementation Pattern: Pure ASGI Middleware

Following [Starlette middleware best practices](https://starlette.dev/middleware/), we'll use pure ASGI middleware instead of BaseHTTPMiddleware:

**Pattern Rationale**:
- ✅ No contextvars propagation issues
- ✅ Better performance (no extra async wrapper)
- ✅ Streaming response support
- ✅ Framework-agnostic (works with any ASGI app)

**Reference**: Analyzed from `/encode/starlette` documentation and existing Litestar implementation.

---

## Files to Create

### 1. `src/debug_toolbar/starlette/__init__.py`

**Purpose**: Public API exports

**Size**: ~30 lines

**Pattern Reference**: `src/debug_toolbar/litestar/__init__.py`

**Exports**:
```python
from debug_toolbar.starlette.config import StarletteDebugToolbarConfig
from debug_toolbar.starlette.middleware import DebugToolbarMiddleware
from debug_toolbar.starlette.routes import create_debug_toolbar_router

__all__ = [
    "StarletteDebugToolbarConfig",
    "DebugToolbarMiddleware",
    "create_debug_toolbar_router",
]
```

---

### 2. `src/debug_toolbar/starlette/middleware.py`

**Purpose**: Pure ASGI middleware for request/response interception

**Size**: ~350 lines

**Pattern Reference**: `src/debug_toolbar/litestar/middleware.py` (adapt to pure ASGI)

**Key Components**:

1. **ResponseState Dataclass** (reuse pattern):
```python
@dataclass
class ResponseState:
    """Tracks response state during middleware processing."""
    started: bool = False
    body_chunks: list[bytes] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 200
    is_html: bool = False
    headers_sent: bool = False
    original_headers: list[tuple[bytes, bytes]] = field(default_factory=list)
```

2. **Pure ASGI Middleware Class**:
```python
class DebugToolbarMiddleware:
    """Pure ASGI middleware for the debug toolbar.

    This middleware:
    - Initializes the request context for each request
    - Collects request/response metadata
    - Injects the toolbar HTML into responses
    - Adds Server-Timing headers
    """

    def __init__(
        self,
        app: ASGIApp,
        config: StarletteDebugToolbarConfig | None = None,
        toolbar: DebugToolbar | None = None,
    ) -> None:
        self.app = app
        self.config = config or StarletteDebugToolbarConfig()
        self.toolbar = toolbar or DebugToolbar(self.config)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if not self.config.should_show_toolbar(request):
            await self.app(scope, receive, send)
            return

        # Process request, intercept response, inject toolbar
        # Pattern follows Litestar implementation
```

3. **Response Interception** (adapt Litestar pattern):
   - `_create_send_wrapper()` - Wrap send callback
   - `_handle_response_start()` - Capture headers/status
   - `_handle_response_body()` - Buffer HTML responses
   - `_inject_toolbar()` - Insert toolbar HTML
   - `_handle_exception()` - Error recovery

4. **Metadata Collection**:
   - `_populate_request_metadata()` - Extract request data
   - `_populate_routes_metadata()` - Collect route information

**Type Safety**: Use Starlette's type hints from `starlette.types`:
```python
from starlette.types import ASGIApp, Message, Scope, Receive, Send
```

---

### 3. `src/debug_toolbar/starlette/config.py`

**Purpose**: Starlette-specific configuration

**Size**: ~85 lines

**Pattern Reference**: `src/debug_toolbar/litestar/config.py`

**Implementation**:
```python
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from debug_toolbar.core.config import DebugToolbarConfig

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel
    from starlette.requests import Request


@dataclass
class StarletteDebugToolbarConfig(DebugToolbarConfig):
    """Starlette-specific configuration for the debug toolbar.

    Extends the base configuration with Starlette-specific options.

    Attributes:
        exclude_paths: URL paths to exclude from toolbar processing.
        exclude_patterns: Regex patterns for paths to exclude.
        show_on_errors: Whether to show toolbar on error responses.
        show_toolbar_callback: Callback receiving Starlette Request object.
    """

    exclude_paths: Sequence[str] = field(
        default_factory=lambda: [
            "/_debug_toolbar",
            "/static",
            "/favicon.ico",
        ]
    )
    exclude_patterns: Sequence[str] = field(default_factory=list)
    show_on_errors: bool = True
    show_toolbar_callback: Callable[[Request], bool] | None = None

    def __post_init__(self) -> None:
        """Add Starlette-specific panels to the default set."""
        default_panels: list[str | type[Panel]] = list(self.panels)

        if "debug_toolbar.starlette.panels.routes.RoutesPanel" not in default_panels:
            default_panels.append("debug_toolbar.starlette.panels.routes.RoutesPanel")

        self.panels = default_panels

    def should_show_toolbar(self, request: Request) -> bool:
        """Determine if the toolbar should be shown for this request.

        Args:
            request: The Starlette request object.

        Returns:
            True if the toolbar should be shown.
        """
        if not self.enabled:
            return False

        path = request.url.path

        # Check excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return False

        # Check excluded patterns
        if self.exclude_patterns:
            import re
            for pattern in self.exclude_patterns:
                if re.match(pattern, path):
                    return False

        # Check allowed hosts
        if self.allowed_hosts:
            host = request.headers.get("host", "").split(":")[0]
            if host not in self.allowed_hosts:
                return False

        # Custom callback
        if self.show_toolbar_callback is not None:
            return self.show_toolbar_callback(request)

        return True
```

---

### 4. `src/debug_toolbar/starlette/routes.py`

**Purpose**: API route handlers for toolbar interface

**Size**: ~100 lines (simplified, reuses core handlers)

**Pattern Reference**: `src/debug_toolbar/litestar/routes/handlers.py`

**Implementation**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route

if TYPE_CHECKING:
    from debug_toolbar.core.storage import ToolbarStorage


def create_debug_toolbar_router(storage: ToolbarStorage) -> Mount:
    """Create the debug toolbar router with routes.

    Args:
        storage: The toolbar storage instance.

    Returns:
        Configured Mount for debug toolbar.
    """
    # Import rendering functions from litestar routes (they're framework-agnostic)
    from debug_toolbar.litestar.routes.handlers import (
        _render_request_row,
        _render_panel_content,
        get_toolbar_css,
        get_toolbar_js,
    )

    async def get_toolbar_index(request):
        """Get the debug toolbar history page."""
        requests = storage.get_all()
        rows_html = [_render_request_row(rid, data) for rid, data in requests]
        empty_row = '<tr><td colspan="5" class="empty">No requests recorded yet</td></tr>'
        tbody_content = "".join(rows_html) if rows_html else empty_row

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Debug Toolbar - Request History</title>
    <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
</head>
<body>
    <div class="toolbar-page">
        <header class="toolbar-header">
            <h1>Debug Toolbar</h1>
            <p>Request History ({len(requests)} requests)</p>
        </header>
        <main class="toolbar-main">
            <table class="requests-table">
                <thead>
                    <tr>
                        <th>Request ID</th><th>Method</th><th>Path</th>
                        <th>Status</th><th>Time</th>
                    </tr>
                </thead>
                <tbody>{tbody_content}</tbody>
            </table>
        </main>
    </div>
    <script src="/_debug_toolbar/static/toolbar.js"></script>
</body>
</html>"""
        return HTMLResponse(html)

    async def get_request_detail(request):
        """Get detailed view for a specific request."""
        request_id = UUID(request.path_params["request_id"])
        data = storage.get(request_id)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

        # Similar to Litestar implementation...
        # (render detail page)
        return HTMLResponse(html)

    async def get_requests_json(request):
        """Get all requests as JSON."""
        requests = storage.get_all()
        return JSONResponse([
            {
                "request_id": str(rid),
                "metadata": d.get("metadata", {}),
                "timing": d.get("timing_data", {}),
            }
            for rid, d in requests
        ])

    async def get_request_json(request):
        """Get a specific request as JSON."""
        request_id = UUID(request.path_params["request_id"])
        data = storage.get(request_id)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
        return JSONResponse({"request_id": str(request_id), **data})

    async def get_static_css(request):
        """Serve the toolbar CSS."""
        css = get_toolbar_css()
        return Response(content=css, media_type="text/css")

    async def get_static_js(request):
        """Serve the toolbar JavaScript."""
        js = get_toolbar_js()
        return Response(content=js, media_type="application/javascript")

    routes = [
        Route("/", endpoint=get_toolbar_index),
        Route("/{request_id:uuid}", endpoint=get_request_detail),
        Route("/api/requests", endpoint=get_requests_json),
        Route("/api/requests/{request_id:uuid}", endpoint=get_request_json),
        Route("/static/toolbar.css", endpoint=get_static_css),
        Route("/static/toolbar.js", endpoint=get_static_js),
    ]

    return Mount("/_debug_toolbar", routes=routes)
```

**Note**: Reuses rendering functions from Litestar handlers as they're framework-agnostic HTML generators.

---

### 5. `src/debug_toolbar/starlette/panels/__init__.py`

**Purpose**: Panel exports

**Size**: ~10 lines

**Content**:
```python
from debug_toolbar.starlette.panels.routes import RoutesPanel

__all__ = ["RoutesPanel"]
```

---

### 6. `src/debug_toolbar/starlette/panels/routes.py`

**Purpose**: Starlette-specific routes panel

**Size**: ~80 lines

**Pattern Reference**: `src/debug_toolbar/litestar/panels/routes.py`

**Implementation**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class RoutesPanel(Panel):
    """Panel displaying Starlette application routes.

    Shows:
    - All registered routes (Route, Mount, WebSocketRoute)
    - HTTP methods for each route
    - Handler names and paths
    - Current matched route
    """

    panel_id: ClassVar[str] = "RoutesPanel"
    title: ClassVar[str] = "Routes"
    template: ClassVar[str] = "panels/routes.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Routes"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate route statistics."""
        routes_info = context.metadata.get("routes", [])

        return {
            "routes": routes_info,
            "route_count": len(routes_info),
            "current_route": context.metadata.get("matched_route", ""),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""
```

**Route Collection Logic** (in middleware):
```python
def _populate_routes_metadata(self, app, request, context):
    """Populate route information from the Starlette app."""
    try:
        routes_info = []

        for route in app.routes:
            route_data = {"path": route.path}

            # Handle different route types
            if hasattr(route, "methods"):
                route_data["methods"] = sorted(route.methods)

            if hasattr(route, "name"):
                route_data["name"] = route.name

            if hasattr(route, "endpoint"):
                endpoint = route.endpoint
                route_data["handler"] = getattr(endpoint, "__name__", str(endpoint))

            routes_info.append(route_data)

        context.metadata["routes"] = routes_info

        # Detect matched route from scope
        scope = request.scope
        if "route" in scope:
            route = scope["route"]
            context.metadata["matched_route"] = getattr(route, "path", "")

    except Exception:
        context.metadata["routes"] = []
        context.metadata["matched_route"] = ""
```

---

### 7. `examples/starlette_basic/app.py`

**Purpose**: Basic example application

**Size**: ~150 lines

**Pattern Reference**: `examples/litestar_basic/app.py`

**Implementation**:
```python
"""Basic Starlette application with debug toolbar.

This example demonstrates using debug-toolbar
with a simple Starlette application.

Run with: uvicorn examples.starlette_basic.app:app --reload
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route

from debug_toolbar.starlette import (
    DebugToolbarMiddleware,
    StarletteDebugToolbarConfig,
    create_debug_toolbar_router,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def homepage(request):
    """Home page."""
    logger.info("Home page accessed")
    html = f"""<!DOCTYPE html>
<html>
<head><title>Starlette Debug Toolbar Example</title></head>
<body>
    <h1>Starlette Debug Toolbar Example</h1>
    <p>Welcome to the Starlette debug toolbar demo!</p>
    <p>Current time: {datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/users">Users</a></li>
        <li><a href="/api/status">API Status (JSON)</a></li>
    </ul>
    <p>The debug toolbar should appear on the right side of this page.</p>
    <p><a href="/_debug_toolbar/">View Request History</a></p>
</body>
</html>"""
    return HTMLResponse(html)


async def about(request):
    """About page."""
    logger.info("About page accessed")
    html = """<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About</h1>
    <p>This is a simple Starlette application demonstrating the debug toolbar.</p>
    <h2>Core Panels</h2>
    <ul>
        <li>Timer Panel - Request timing</li>
        <li>Request Panel - Request details</li>
        <li>Response Panel - Response info</li>
        <li>Logging Panel - Captured logs</li>
        <li>Versions Panel - Environment info</li>
        <li>Routes Panel - Starlette routes</li>
    </ul>
    <a href="/">Back to Home</a>
</body>
</html>"""
    return HTMLResponse(html)


async def users(request):
    """Users page."""
    logger.info("Users page accessed")
    user_list = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]

    rows = "".join(
        f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['email']}</td></tr>"
        for u in user_list
    )

    html = f"""<!DOCTYPE html>
<html>
<head><title>Users</title></head>
<body>
    <h1>Users</h1>
    <table border="1">
        <thead><tr><th>ID</th><th>Name</th><th>Email</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <a href="/">Back to Home</a>
</body>
</html>"""
    return HTMLResponse(html)


async def api_status(request):
    """API status endpoint."""
    logger.info("API status requested")
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": "1.0.0",
    })


# Configure debug toolbar
toolbar_config = StarletteDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
)

# Create toolbar storage and router
from debug_toolbar.core.toolbar import DebugToolbar
toolbar = DebugToolbar(toolbar_config)
debug_router = create_debug_toolbar_router(toolbar.storage)

# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/", endpoint=homepage),
        Route("/about", endpoint=about),
        Route("/users", endpoint=users),
        Route("/api/status", endpoint=api_status),
        debug_router,  # Mount debug toolbar routes
    ],
    middleware=[
        Middleware(DebugToolbarMiddleware, config=toolbar_config, toolbar=toolbar),
    ],
)
```

---

### 8. `examples/starlette_basic/README.md`

**Purpose**: Example documentation

**Size**: ~50 lines

**Content**: Setup instructions, run commands, feature demonstration.

---

## Files to Modify

### 1. `pyproject.toml`

**Change**: Add starlette as optional dependency

```toml
[project.optional-dependencies]
starlette = [
    "starlette>=0.27.0",
]
```

### 2. `README.md`

**Change**: Add Starlette installation and usage section

```markdown
## Starlette Integration

### Installation

```bash
pip install debug-toolbar[starlette]
```

### Usage

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from debug_toolbar.starlette import (
    DebugToolbarMiddleware,
    StarletteDebugToolbarConfig,
    create_debug_toolbar_router,
)

toolbar_config = StarletteDebugToolbarConfig(enabled=True)
toolbar = DebugToolbar(toolbar_config)

app = Starlette(
    routes=[
        # Your routes here
        create_debug_toolbar_router(toolbar.storage),
    ],
    middleware=[
        Middleware(DebugToolbarMiddleware, config=toolbar_config, toolbar=toolbar),
    ],
)
```

See `examples/starlette_basic/` for a complete example.
```

---

## Testing Strategy

### Test Coverage Target: 90%+

### Test Files to Create

1. **`tests/starlette/test_middleware.py`** (~250 lines)
   - Test middleware initialization
   - Test request interception
   - Test toolbar injection into HTML
   - Test Server-Timing headers
   - Test error handling
   - Test excluded paths
   - Test non-HTML responses

2. **`tests/starlette/test_config.py`** (~150 lines)
   - Test config defaults
   - Test `should_show_toolbar()` logic
   - Test path exclusion
   - Test pattern exclusion
   - Test callback override

3. **`tests/starlette/test_routes.py`** (~100 lines)
   - Test route handler responses
   - Test history page rendering
   - Test detail page rendering
   - Test JSON API endpoints
   - Test static file serving

4. **`tests/starlette/panels/test_routes_panel.py`** (~100 lines)
   - Test route collection
   - Test stats generation
   - Test various route types (Route, Mount, WebSocket)
   - Test matched route detection

### Test Fixtures (in `tests/starlette/conftest.py`)

```python
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from debug_toolbar.starlette import (
    DebugToolbarMiddleware,
    StarletteDebugToolbarConfig,
    create_debug_toolbar_router,
)


@pytest.fixture
def starlette_config():
    """Default Starlette toolbar config."""
    return StarletteDebugToolbarConfig(enabled=True)


@pytest.fixture
def toolbar(starlette_config):
    """Toolbar instance."""
    from debug_toolbar.core.toolbar import DebugToolbar
    return DebugToolbar(starlette_config)


@pytest.fixture
def app(starlette_config, toolbar):
    """Basic Starlette app with toolbar."""
    async def homepage(request):
        return HTMLResponse("<html><body>Hello</body></html>")

    return Starlette(
        routes=[
            Route("/", endpoint=homepage),
            create_debug_toolbar_router(toolbar.storage),
        ],
        middleware=[
            Middleware(DebugToolbarMiddleware, config=starlette_config, toolbar=toolbar),
        ],
    )


@pytest.fixture
def client(app):
    """Test client."""
    return TestClient(app)
```

### Test Patterns

**Pattern 1: Toolbar Injection**
```python
def test_toolbar_injection(client):
    """Should inject toolbar into HTML responses."""
    response = client.get("/")
    assert response.status_code == 200
    assert b'<div id="debug-toolbar"' in response.content
    assert b'<script src="/_debug_toolbar/static/toolbar.js">' in response.content
```

**Pattern 2: Path Exclusion**
```python
def test_excluded_paths(client):
    """Should not inject toolbar for excluded paths."""
    response = client.get("/_debug_toolbar/")
    assert b'<div id="debug-toolbar"' not in response.content
```

**Pattern 3: Panel Data Collection**
```python
@pytest.mark.asyncio
async def test_routes_panel_collection(toolbar, context):
    """Should collect route information."""
    from debug_toolbar.starlette.panels.routes import RoutesPanel

    panel = RoutesPanel(toolbar)
    stats = await panel.generate_stats(context)

    assert "routes" in stats
    assert "route_count" in stats
    assert stats["route_count"] > 0
```

### Integration Tests

Test complete request/response cycle:
- HTML response with toolbar injection
- JSON response without toolbar
- Error handling preserves response
- Multiple concurrent requests
- WebSocket routes (no toolbar)

---

## Research Summary

### Total Research: ~2,800 words

#### Pattern Library Analysis

Reviewed existing patterns from `specs/guides/patterns/README.md`:
- Panel implementation pattern (Abstract base class)
- Testing patterns (fixtures, cleanup)
- Plugin patterns (Litestar-specific, not applicable)
- Type handling (PEP 604, future annotations)

#### Litestar Integration Study

Analyzed 5 key files (~1,500 LOC):
1. `middleware.py` - Response interception, HTML injection
2. `plugin.py` - InitPluginProtocol implementation
3. `config.py` - Framework-specific configuration
4. `routes.py` - Routes panel implementation
5. `routes/handlers.py` - API handlers and rendering

**Key Learnings**:
- ResponseState pattern for tracking response data
- Send wrapper for ASGI message interception
- Graceful error handling with buffered responses
- Framework-agnostic HTML rendering functions (reusable!)

#### Starlette Documentation Research

Sources consulted:
- [Starlette Middleware Documentation](https://starlette.dev/middleware/)
- [Stack Overflow: Starlette Middleware Patterns](https://stackoverflow.com/questions/71525132/how-to-write-a-custom-fastapi-middleware-class)
- [GitHub: BaseHTTPMiddleware Issues](https://github.com/encode/starlette/discussions/2654)

**Key Insights**:
1. **Pure ASGI > BaseHTTPMiddleware**: BaseHTTPMiddleware has known issues:
   - Breaks contextvars for downstream middleware
   - Incompatible with streaming responses
   - Performance overhead from extra async wrapper

2. **Pure ASGI Pattern**:
   ```python
   class ASGIMiddleware:
       def __init__(self, app: ASGIApp) -> None:
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] != "http":
               return await self.app(scope, receive, send)

           async def send_wrapper(message: Message) -> None:
               # Intercept response
               await send(message)

           await self.app(scope, receive, send_wrapper)
   ```

3. **Starlette Type System**: Import from `starlette.types`:
   - `ASGIApp`, `Scope`, `Receive`, `Send`, `Message`
   - Compatible with Litestar's ASGI types

#### Example Applications

Studied `examples/litestar_basic/app.py`:
- Plugin-based setup (not applicable to Starlette)
- Route registration patterns
- Configuration examples
- Panel demonstrations

**Adaptation Strategy**:
- Replace plugin with direct middleware registration
- Use `Middleware()` wrapper in `Starlette(middleware=[...])`
- Mount debug routes using `Mount()` or direct inclusion

---

## Development Checklist (8 Checkpoints)

### Phase 1: Core Implementation (3 checkpoints)

- [ ] **Checkpoint 1: Middleware & Config**
  - Create `middleware.py` with pure ASGI pattern
  - Create `config.py` with Starlette-specific options
  - Create `__init__.py` with public API
  - Unit tests for config and middleware initialization

- [ ] **Checkpoint 2: Request/Response Interception**
  - Implement send wrapper for response interception
  - Implement HTML toolbar injection
  - Implement Server-Timing headers
  - Error handling with graceful degradation
  - Tests for injection and error scenarios

- [ ] **Checkpoint 3: Routes & Storage**
  - Create `routes.py` with API handlers
  - Implement route collection in middleware
  - Create routes panel
  - Tests for route handlers and panel

### Phase 2: Integration & Examples (3 checkpoints)

- [ ] **Checkpoint 4: Basic Example**
  - Create `examples/starlette_basic/app.py`
  - Create example README
  - Manual testing with uvicorn
  - Verify all core panels work

- [ ] **Checkpoint 5: Advanced Example**
  - Create advanced example with templates
  - Add database integration
  - Demonstrate advanced panels
  - Production-like configuration

- [ ] **Checkpoint 6: Documentation**
  - Update main README with Starlette section
  - Add installation instructions
  - Create usage guide
  - Document configuration options

### Phase 3: Quality & Testing (2 checkpoints)

- [ ] **Checkpoint 7: Test Coverage**
  - Complete test suite (4 test files)
  - Achieve 90%+ coverage
  - Integration tests
  - Run full test suite (all 402 + new tests pass)

- [ ] **Checkpoint 8: Review & Polish**
  - Code review against patterns
  - Type checking with `make type-check`
  - Linting with `make lint`
  - Performance testing
  - Pattern extraction for future integrations

---

## Success Metrics

### Quantitative

1. **Test Coverage**: 90%+ for all new modules
2. **Backward Compatibility**: All 402 existing tests still pass
3. **Performance**: <5ms overhead for excluded routes
4. **Code Quality**: Pass `make lint` and `make type-check`

### Qualitative

1. **API Consistency**: Starlette API mirrors Litestar API patterns
2. **Documentation**: Clear setup instructions, runnable examples
3. **Developer Experience**: Installation and setup in <5 minutes
4. **Pattern Reusability**: Extracted patterns for future frameworks

### Community Impact

1. **User Adoption**: Example apps demonstrate all features
2. **Framework Agnostic**: Validates core architecture design
3. **Future Frameworks**: Clear template for Django, Flask adaptations
4. **Documentation**: Contribution guidelines for new integrations

---

## Risks & Mitigations

### Risk 1: Pure ASGI Complexity

**Risk**: Pure ASGI middleware is more complex than BaseHTTPMiddleware

**Mitigation**:
- Extensive pattern analysis from Litestar implementation
- Starlette documentation provides clear examples
- TestClient makes testing straightforward
- Can reuse 80% of Litestar middleware logic

### Risk 2: Route Collection Differences

**Risk**: Starlette route structure may differ from Litestar

**Mitigation**:
- Both use similar `app.routes` API
- Starlette routes are simpler (no complex handler metadata)
- Graceful fallbacks for missing attributes
- Comprehensive testing with various route types

### Risk 3: Framework Compatibility

**Risk**: Breaking changes in Starlette API

**Mitigation**:
- Pin minimum version: `starlette>=0.27.0`
- Use stable ASGI spec (won't change)
- Type hints catch API changes early
- CI tests against multiple Starlette versions

### Risk 4: FastAPI Compatibility

**Risk**: FastAPI may have additional requirements

**Mitigation**:
- FastAPI is built on Starlette (automatic compatibility)
- Starlette adapter works with any ASGI app
- Create FastAPI example in P2 (nice-to-have)
- Document any FastAPI-specific considerations

---

## Future Enhancements (Post-MVP)

### Phase 11 Candidates

1. **FastAPI-Specific Panels**
   - OpenAPI/Schema panel
   - Dependency injection panel
   - Pydantic validation panel

2. **WebSocket Support**
   - WebSocket connection tracking
   - Message logging panel
   - Performance metrics

3. **Performance Optimization**
   - Response streaming (chunked transfer)
   - Lazy panel initialization
   - Cached route collection

4. **Developer Tools**
   - `debug-toolbar init starlette` CLI command
   - Auto-configuration from environment
   - Integration with Starlette lifespan

---

## Appendix A: Code Patterns

### Pattern 1: Pure ASGI Send Wrapper

```python
async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] != "http":
        await self.app(scope, receive, send)
        return

    state = ResponseState()

    async def send_wrapper(message: Message) -> None:
        if message["type"] == "http.response.start":
            # Capture headers, status
            state.started = True
            state.status_code = message["status"]
            state.headers = dict(message.get("headers", []))

        elif message["type"] == "http.response.body":
            # Buffer body for HTML injection
            state.body_chunks.append(message.get("body", b""))

            if not message.get("more_body", False):
                # All body received, inject toolbar
                await self._inject_and_send(send, state)
                return

        await send(message)

    try:
        await self.app(scope, receive, send_wrapper)
    except Exception:
        # Error recovery
        if state.started and not state.headers_sent:
            await self._send_buffered(send, state)
        raise
```

### Pattern 2: Framework-Agnostic Route Handler

```python
async def get_toolbar_index(request):
    """Reusable across Litestar and Starlette."""
    storage = request.app.state.toolbar_storage  # Framework-specific access

    # All rendering is pure Python (no framework deps)
    from debug_toolbar.litestar.routes.handlers import _render_request_row

    requests = storage.get_all()
    rows_html = [_render_request_row(rid, data) for rid, data in requests]

    return HTMLResponse(build_history_page(rows_html))
```

### Pattern 3: Starlette Route Collection

```python
def _collect_routes(app) -> list[dict]:
    """Collect routes from Starlette app."""
    routes = []

    for route in app.routes:
        route_data = {"path": getattr(route, "path", "/")}

        # Different route types have different attributes
        if hasattr(route, "methods"):
            route_data["methods"] = sorted(route.methods)

        if hasattr(route, "name") and route.name:
            route_data["name"] = route.name

        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            route_data["handler"] = getattr(endpoint, "__name__", str(endpoint))

        routes.append(route_data)

    return routes
```

---

## Appendix B: Dependencies

### Required Dependencies

```toml
[project.optional-dependencies]
starlette = [
    "starlette>=0.27.0",  # Stable ASGI middleware API
]
```

### Development Dependencies (Already Present)

- pytest
- pytest-asyncio
- pytest-cov
- ruff
- ty (type checker)

### Example Dependencies

```toml
[project.optional-dependencies]
examples-starlette = [
    "uvicorn>=0.20.0",  # ASGI server
    "jinja2>=3.0.0",    # Template engine (advanced example)
]
```

---

## Appendix C: Comparison Matrix

### Litestar vs Starlette Integration

| Aspect | Litestar | Starlette |
|--------|----------|-----------|
| **Setup Pattern** | Plugin | Direct middleware |
| **Lines of Code** | ~500 (middleware + plugin) | ~400 (middleware only) |
| **Middleware Base** | `AbstractMiddleware` | Pure ASGI |
| **Route Registration** | `app_config.route_handlers.append()` | `routes=[...]` in constructor |
| **Config Integration** | `on_app_init()` hook | Manual in app setup |
| **Type System** | Litestar types | Starlette types |
| **Lifecycle Hooks** | before/after_request | Middleware only |
| **Complexity** | Medium-High | Medium |
| **Unique Panels** | EventsPanel | None (simpler framework) |

---

## Appendix D: Sources

### Documentation

- [Starlette Middleware](https://starlette.dev/middleware/)
- [Starlette Types](https://github.com/encode/starlette/blob/master/starlette/types.py)
- [ASGI Specification](https://asgi.readthedocs.io/)

### Research Articles

- [BaseHTTPMiddleware Issues Discussion](https://github.com/encode/starlette/discussions/2654)
- [Starlette Context Middleware](https://starlette-context.readthedocs.io/en/latest/middleware.html)
- [Stack Overflow: Custom Starlette Middleware](https://stackoverflow.com/questions/71525132/how-to-write-a-custom-fastapi-middleware-class)

### Codebase Analysis

- `src/debug_toolbar/litestar/middleware.py` - Response interception patterns
- `src/debug_toolbar/core/panel.py` - Panel ABC
- `examples/litestar_basic/app.py` - Integration examples

---

**End of PRD**

**Total Word Count**: ~7,200 words (PRD: 4,400 + Research: 2,800)

**Pattern References**: 8 established patterns
**Code Examples**: 15+ implementation snippets
**Test Coverage Strategy**: 4 test files, 90%+ target
