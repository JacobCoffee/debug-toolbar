# PRD: FastAPI Adapter

**Status**: Draft
**Slug**: `fastapi-adapter`
**Priority**: P1 (Largest ASGI user base)
**Complexity**: Simple (6 checkpoints)
**Created**: 2025-11-29
**Dependencies**: Starlette adapter (prerequisite)

---

## Metadata

| Key | Value |
|-----|-------|
| **Feature Type** | Framework Integration |
| **Estimated Effort** | 2-3 days |
| **Test Coverage Target** | 90%+ |
| **Breaking Changes** | None |
| **Required Reviewers** | Core maintainers |
| **Documentation Needs** | Integration guide, example app, API reference |

### Complexity Justification

This feature is classified as **Simple (6 checkpoints)** because:

1. **Builds on existing foundation**: FastAPI is built on top of Starlette, allowing maximum code reuse from the Starlette adapter
2. **Single unique feature**: The only FastAPI-specific addition is the Dependency Injection panel
3. **Well-defined scope**: Clear boundaries for middleware, config, and panel implementations
4. **Limited file changes**: Approximately 8-10 new files, no modifications to core
5. **Straightforward testing**: Standard panel and middleware test patterns apply
6. **Proven architecture**: Following established Litestar integration patterns

### Checkpoints

1. **Research & Design** (1-2 hours)
   - Analyze FastAPI DI system internals
   - Design hook mechanism for dependency tracking
   - Document architectural decisions

2. **Core Implementation** (4-6 hours)
   - FastAPIDebugToolbarConfig with framework-specific options
   - Middleware adapter (thin wrapper over Starlette)
   - Plugin/setup utilities

3. **Dependency Injection Panel** (6-8 hours)
   - DependencyInjectionPanel implementation
   - Hook into FastAPI's dependency resolution
   - Track cached vs fresh dependencies
   - Collect dependency graph and timing data

4. **Testing** (4-6 hours)
   - Unit tests for config, middleware, panel
   - Integration tests with FastAPI app
   - DI panel coverage with various dependency patterns
   - 90%+ coverage verification

5. **Example Application** (2-3 hours)
   - FastAPI app with realistic dependencies
   - Database sessions, auth, pagination examples
   - Documentation comments

6. **Review & Documentation** (2-3 hours)
   - Pattern extraction to library
   - Integration guide
   - API documentation
   - Quality gate verification

---

## Intelligence Context

### Pattern Recognition

**Similar Implementations Analyzed**:

1. **Litestar Integration** (`src/debug_toolbar/litestar/`)
   - Plugin pattern: `DebugToolbarPlugin(InitPluginProtocol)`
   - Framework-specific config extending `DebugToolbarConfig`
   - Middleware with ASGI interception
   - Framework-specific panels: `EventsPanel`, `RoutesPanel`
   - Metadata collection helpers in panel modules

2. **Events Panel** (`src/debug_toolbar/litestar/panels/events.py`)
   - Helper functions for extracting handler information
   - Metadata collection separate from panel logic
   - Recording execution timing and success/failure
   - Using `context.metadata` for framework-specific data

3. **Core Panel Architecture** (`src/debug_toolbar/core/panel.py`)
   - Abstract `generate_stats()` method
   - Optional lifecycle hooks: `process_request()`, `process_response()`
   - Panel data storage via `record_stats()` and `get_stats()`
   - Navigation title/subtitle patterns

**Key Patterns to Follow**:

- **Config Inheritance**: Extend `DebugToolbarConfig` with framework-specific options
- **Metadata Collection**: Use helper functions outside panel class, store in `context.metadata`
- **Middleware Delegation**: For FastAPI, delegate to Starlette middleware, add DI tracking hooks
- **Panel Isolation**: Keep dependency tracking logic separate from panel presentation
- **Type Safety**: PEP 604 unions, future annotations, ClassVar for panel metadata

### Architectural Insights

FastAPI is architecturally layered on Starlette's ASGI runtime:

```
FastAPI Layer (DI, validation, OpenAPI)
    ↓
Starlette Layer (routing, middleware, requests)
    ↓
ASGI Protocol
```

**Key Implication**: Maximum code reuse is possible. The FastAPI adapter should:
1. Inherit/wrap Starlette middleware
2. Add hooks for FastAPI-specific features (primarily DI)
3. Provide convenience utilities for FastAPI users

**Dependency Injection Architecture**:

FastAPI's DI system operates via:
- `fastapi.dependencies.utils.solve_dependencies()` - Core resolution function
- `fastapi.dependencies.models.Dependant` - Dependency graph node
- Request-scoped caching (default behavior)
- `use_cache=False` parameter to disable caching

**Tracking Strategy**: Monkey-patch or wrap `solve_dependencies` to collect:
- Dependency function/class being resolved
- Whether result came from cache
- Resolution time
- Sub-dependency tree
- Parameters injected

---

## Problem Statement

### Background

The debug-toolbar project provides async-native debugging capabilities for Python ASGI frameworks. It currently supports Litestar with framework-specific integrations. FastAPI, as one of the largest and most popular ASGI frameworks (used by millions of developers), represents a critical integration target.

### User Pain Points

1. **No FastAPI-specific debugging**: FastAPI developers lack visibility into framework-specific features like dependency injection
2. **Dependency black box**: No way to see which dependencies are cached vs freshly resolved per request
3. **Performance mysteries**: Difficulty identifying which dependencies are slow or called multiple times
4. **Integration friction**: Generic ASGI tooling doesn't understand FastAPI's DI system
5. **Missing dev tools**: Unlike Django Debug Toolbar, no comprehensive debugging solution for FastAPI

### Target Users

- **Primary**: FastAPI application developers in development/staging environments
- **Secondary**: API architects optimizing dependency injection patterns
- **Tertiary**: Teams migrating from other frameworks seeking familiar debugging tools

### Success Criteria

1. **Functional**: Developers can install and use debug toolbar in FastAPI apps with <5 lines of code
2. **Visibility**: DI panel shows all resolved dependencies with cache status and timing
3. **Performance**: Overhead <5% in development, zero overhead when disabled
4. **Adoption**: Featured in FastAPI documentation examples within 6 months
5. **Reliability**: 90%+ test coverage, no false positives in dependency tracking

---

## Goals and Non-Goals

### Goals

1. **Provide FastAPI adapter** with idiomatic integration pattern (app.add_middleware or similar)
2. **Track dependency injection** with comprehensive visibility into resolution, caching, and timing
3. **Maintain FastAPI patterns** - support Depends(), Security(), and class-based dependencies
4. **Enable debugging workflows** - inspect dependency graphs, identify performance bottlenecks
5. **Deliver complete example** - realistic FastAPI app demonstrating DI panel capabilities

### Non-Goals

1. **Starlette adapter development** - prerequisite, assumed complete
2. **OpenAPI panel** - FastAPI's auto-generated docs are sufficient
3. **Pydantic validation panel** - out of scope for v1
4. **Production deployment** - debug toolbar is development-only
5. **Dependency injection modifications** - read-only tracking, no behavior changes

---

## Acceptance Criteria

### Must Have

1. **FastAPIDebugToolbarConfig**
   - [ ] Extends `DebugToolbarConfig` with FastAPI-specific options
   - [ ] `show_toolbar_callback` accepts FastAPI `Request` object
   - [ ] `exclude_paths` includes default patterns (`/docs`, `/redoc`, `/openapi.json`)
   - [ ] `track_dependency_injection: bool = True` flag to enable/disable DI tracking
   - [ ] Automatic panel registration for DI panel when enabled

2. **Middleware Integration**
   - [ ] Compatible with `app.add_middleware()` pattern
   - [ ] Delegates to Starlette middleware for request/response handling
   - [ ] Hooks into dependency resolution before route handler execution
   - [ ] Cleans up context vars after request completes
   - [ ] Handles streaming responses correctly

3. **Dependency Injection Panel**
   - [ ] Panel ID: `DependencyInjectionPanel`
   - [ ] Title: "Dependencies"
   - [ ] Shows all resolved dependencies for current request
   - [ ] Displays cache status (cached, fresh) for each dependency
   - [ ] Reports resolution time in milliseconds
   - [ ] Visualizes dependency graph (dependencies with sub-dependencies)
   - [ ] Distinguishes between function, class, and generator dependencies
   - [ ] Handles `Depends()` and `Security()` equally
   - [ ] Shows parameter values passed to dependency constructors
   - [ ] Gracefully handles circular dependencies (detection + warning)

4. **DI Tracking Implementation**
   - [ ] Non-invasive: Uses context vars, not monkey patching if possible
   - [ ] Collects dependency metadata: name, module, type, cache key
   - [ ] Tracks resolution timing with microsecond precision
   - [ ] Records cache hits/misses
   - [ ] Builds dependency tree structure
   - [ ] Stores data in `context.metadata["dependencies"]`
   - [ ] Helper function: `collect_dependency_metadata()`
   - [ ] Helper function: `record_dependency_resolution()`

5. **Testing**
   - [ ] 90%+ coverage for all new modules
   - [ ] Unit tests for config, middleware, panel
   - [ ] Integration test: FastAPI app with debug toolbar
   - [ ] Test: Function-based dependencies tracked correctly
   - [ ] Test: Class-based dependencies tracked correctly
   - [ ] Test: Generator dependencies (with yield) tracked correctly
   - [ ] Test: Sub-dependencies appear in tree structure
   - [ ] Test: Cached dependencies marked as cached
   - [ ] Test: `use_cache=False` dependencies always fresh
   - [ ] Test: Multiple dependencies with same cache key
   - [ ] Test: Dependency resolution timing accuracy

6. **Example Application**
   - [ ] Located at `examples/fastapi_basic/`
   - [ ] Demonstrates common dependency patterns:
     - Database session with yield
     - Pagination parameters (class-based)
     - Authentication/authorization
     - Nested dependencies
     - Cached vs non-cached examples
   - [ ] README with setup instructions
   - [ ] Requirements file with FastAPI, Uvicorn
   - [ ] Inline comments explaining DI panel features

### Should Have

7. **Documentation**
   - [ ] Installation guide in main README
   - [ ] Integration guide: `docs/integrations/fastapi.md`
   - [ ] API reference for `FastAPIDebugToolbarConfig`
   - [ ] DI panel usage guide with screenshots
   - [ ] Performance notes (overhead estimates)
   - [ ] Migration guide from generic ASGI setup

8. **Panel Enhancements**
   - [ ] Nav subtitle shows total dependencies resolved
   - [ ] Color coding: green (cached), blue (fresh)
   - [ ] Expandable tree view for sub-dependencies
   - [ ] Click to view source location for dependency function
   - [ ] Summary stats: total count, cache hit rate, total time

### Nice to Have

9. **Advanced Features**
   - [ ] Dependency graph visualization (D3.js or similar)
   - [ ] Highlight slow dependencies (>10ms)
   - [ ] Diff view: compare dependency resolution across requests
   - [ ] Export dependency tree as JSON
   - [ ] Search/filter dependencies by name or module

10. **Developer Experience**
    - [ ] Type stubs for excellent IDE support
    - [ ] Warning if DI tracking overhead >5%
    - [ ] Automatic detection of FastAPI app (vs Starlette)
    - [ ] Helpful error messages for misconfiguration

### Won't Have (This Release)

- OpenAPI/Swagger panel (FastAPI's built-in docs sufficient)
- Pydantic validation panel (future enhancement)
- Request body inspection beyond generic request panel
- WebSocket dependency tracking (not supported in v1)
- Background task dependency tracking

---

## Technical Approach

### Architecture Overview

```
FastAPI Application
    ↓
DebugToolbarMiddleware (FastAPI-aware)
    ↓ (wraps)
StarletteDebugToolbarMiddleware
    ↓ (adds)
DI Tracking Hooks
    ↓
DebugToolbar → DependencyInjectionPanel
```

### Component Design

#### 1. FastAPIDebugToolbarConfig

**Location**: `src/debug_toolbar/fastapi/config.py`

```python
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from debug_toolbar.core.config import DebugToolbarConfig

if TYPE_CHECKING:
    from debug_toolbar.core.panel import Panel
    from fastapi import Request


@dataclass
class FastAPIDebugToolbarConfig(DebugToolbarConfig):
    """FastAPI-specific configuration for the debug toolbar.

    Extends the base configuration with FastAPI-specific options.

    Attributes:
        exclude_paths: URL paths to exclude from toolbar processing.
        show_toolbar_callback: Callback receiving FastAPI Request object.
        track_dependency_injection: Enable dependency injection tracking.
    """

    exclude_paths: Sequence[str] = field(
        default_factory=lambda: [
            "/_debug_toolbar",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/favicon.ico",
        ]
    )
    show_toolbar_callback: Callable[[Request], bool] | None = None
    track_dependency_injection: bool = True

    def __post_init__(self) -> None:
        """Add FastAPI-specific panels to the default set."""
        default_panels: list[str | type[Panel]] = list(self.panels)

        if self.track_dependency_injection:
            if "debug_toolbar.fastapi.panels.dependencies.DependencyInjectionPanel" not in default_panels:
                default_panels.append(
                    "debug_toolbar.fastapi.panels.dependencies.DependencyInjectionPanel"
                )

        self.panels = default_panels

    def should_show_toolbar(self, request: Request) -> bool:
        """Determine if the toolbar should be shown for this request."""
        if not self.enabled:
            return False

        path = request.url.path

        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return False

        if self.allowed_hosts:
            host = request.headers.get("host", "").split(":")[0]
            if host not in self.allowed_hosts:
                return False

        if self.show_toolbar_callback is not None:
            return self.show_toolbar_callback(request)

        return True
```

#### 2. Middleware Integration

**Location**: `src/debug_toolbar/fastapi/middleware.py`

**Strategy**: Wrap Starlette middleware, add DI tracking hooks.

Key responsibilities:
- Initialize request context
- Install DI tracking hooks before route execution
- Delegate request/response handling to Starlette middleware
- Clean up tracking hooks and context after request

**Pattern**: Use context vars to store tracking state, avoiding global state.

#### 3. Dependency Injection Panel

**Location**: `src/debug_toolbar/fastapi/panels/dependencies.py`

**Panel Structure**:

```python
class DependencyInjectionPanel(Panel):
    panel_id: ClassVar[str] = "DependencyInjectionPanel"
    title: ClassVar[str] = "Dependencies"
    template: ClassVar[str] = "panels/dependencies.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Dependencies"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate dependency statistics from context metadata."""
        dependencies_data = context.metadata.get("dependencies", {})

        resolved = dependencies_data.get("resolved", [])
        dependency_tree = dependencies_data.get("tree", {})
        cache_stats = dependencies_data.get("cache_stats", {})

        total_time_ms = sum(d.get("duration_ms", 0) for d in resolved)
        cached_count = sum(1 for d in resolved if d.get("cached", False))

        return {
            "resolved_dependencies": resolved,
            "dependency_tree": dependency_tree,
            "total_count": len(resolved),
            "cached_count": cached_count,
            "cache_hit_rate": cached_count / len(resolved) if resolved else 0,
            "total_time_ms": total_time_ms,
            "cache_stats": cache_stats,
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing count."""
        # Will be set dynamically based on stats
        return ""
```

**Metadata Structure** (stored in `context.metadata["dependencies"]`):

```python
{
    "resolved": [
        {
            "name": "get_db",
            "type": "function",  # "function", "class", "generator"
            "module": "myapp.dependencies",
            "cached": False,
            "duration_ms": 1.234,
            "cache_key": "get_db:request_scope",
            "dependency_path": ["get_db"],
            "params": {},
            "source_file": "/path/to/file.py",
            "source_line": 42,
        },
        # ... more dependencies
    ],
    "tree": {
        "get_current_user": {
            "info": {...},
            "sub_dependencies": {
                "get_db": {...},
                "get_token": {...},
            }
        }
    },
    "cache_stats": {
        "hits": 5,
        "misses": 3,
        "total": 8,
    }
}
```

#### 4. Dependency Tracking Helpers

**Location**: `src/debug_toolbar/fastapi/panels/dependencies.py`

Helper functions (pattern from EventsPanel):

```python
def collect_dependency_metadata(app: FastAPI, context: RequestContext) -> None:
    """Collect dependency metadata from a FastAPI app."""
    # Initialize metadata structure
    context.metadata["dependencies"] = {
        "resolved": [],
        "tree": {},
        "cache_stats": {"hits": 0, "misses": 0, "total": 0},
    }


def record_dependency_resolution(
    context: RequestContext,
    dependency_name: str,
    dependency_type: str,
    cached: bool,
    duration_ms: float,
    cache_key: str | None = None,
    params: dict[str, Any] | None = None,
) -> None:
    """Record a dependency resolution event."""
    if "dependencies" not in context.metadata:
        collect_dependency_metadata(None, context)

    resolution_record = {
        "name": dependency_name,
        "type": dependency_type,
        "cached": cached,
        "duration_ms": duration_ms,
        "cache_key": cache_key,
        "params": params or {},
    }

    context.metadata["dependencies"]["resolved"].append(resolution_record)

    # Update cache stats
    stats = context.metadata["dependencies"]["cache_stats"]
    stats["total"] += 1
    if cached:
        stats["hits"] += 1
    else:
        stats["misses"] += 1
```

#### 5. DI System Hooking Strategy

**Challenge**: FastAPI's dependency resolution happens deep in the framework, in `fastapi.dependencies.utils.solve_dependencies()`.

**Approach Options**:

**Option A: Middleware-level wrapper** (Recommended)
- Wrap the route handler in middleware
- Use FastAPI's internal `get_dependant` to inspect dependencies
- Track before/after timestamps for resolution
- Pro: Non-invasive, doesn't modify FastAPI internals
- Con: Less granular, might miss sub-dependency timing

**Option B: Monkey-patch solve_dependencies**
- Wrap `solve_dependencies` with tracking logic
- Pro: Most accurate tracking, captures all resolutions
- Con: Invasive, fragile across FastAPI versions

**Option C: Custom Depends wrapper**
- Provide `DebugDepends()` instead of `Depends()`
- Pro: Explicit, no magic
- Con: Requires code changes, defeats purpose

**Recommendation**: Start with **Option A** (middleware-level), add Option B if needed for accuracy.

**Implementation** (Option A):

```python
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute
import time

async def track_dependencies(request: Request, call_next):
    context = get_request_context()

    # Get route handler from request
    route = request.scope.get("route")
    if isinstance(route, APIRoute):
        dependant = route.dependant

        # Walk dependency tree
        def walk_dependencies(dep, path=[]):
            dep_name = dep.call.__name__ if hasattr(dep.call, '__name__') else str(dep.call)
            current_path = path + [dep_name]

            start_time = time.perf_counter()
            # Dependency will be resolved by FastAPI's machinery
            # We track the structure here, actual resolution happens in route handler

            for sub_dep in dep.dependencies:
                walk_dependencies(sub_dep, current_path)

        if dependant:
            walk_dependencies(dependant)

    response = await call_next(request)
    return response
```

### File Structure

```
src/debug_toolbar/fastapi/
├── __init__.py                          # Public API exports
├── config.py                            # FastAPIDebugToolbarConfig
├── middleware.py                        # DebugToolbarMiddleware
├── setup.py                             # setup_debug_toolbar() helper
└── panels/
    ├── __init__.py
    └── dependencies.py                  # DependencyInjectionPanel + helpers

examples/fastapi_basic/
├── main.py                              # FastAPI app with toolbar
├── dependencies.py                      # Example dependency functions
├── requirements.txt                     # FastAPI, uvicorn, debug-toolbar
└── README.md                            # Setup instructions

tests/unit/
├── test_fastapi_config.py               # Config tests
├── test_fastapi_middleware.py           # Middleware tests
└── test_dependency_injection_panel.py   # DI panel tests

tests/integration/
└── test_fastapi_integration.py          # End-to-end FastAPI tests
```

### Dependencies

**Required**:
- `fastapi` >= 0.100.0 (for modern DI system)
- `starlette` >= 0.27.0 (via FastAPI)
- Starlette adapter (must be implemented first)

**Optional**:
- `uvicorn` (for examples/testing)
- `sqlalchemy` (for realistic example dependencies)

**Development**:
- `pytest-asyncio` (existing)
- `httpx` (for testing FastAPI endpoints)

### Testing Strategy

#### Unit Tests

1. **Config Tests** (`test_fastapi_config.py`)
   - Test default exclude paths include FastAPI docs
   - Test `track_dependency_injection` flag adds DI panel
   - Test `should_show_toolbar()` with FastAPI Request
   - Test `__post_init__()` panel registration

2. **Middleware Tests** (`test_fastapi_middleware.py`)
   - Test middleware initializes request context
   - Test middleware delegates to Starlette middleware
   - Test middleware excludes FastAPI docs paths
   - Test middleware handles exceptions gracefully
   - Test cleanup of context vars

3. **DI Panel Tests** (`test_dependency_injection_panel.py`)
   - Test `generate_stats()` with empty dependencies
   - Test `generate_stats()` with function dependencies
   - Test `generate_stats()` with class dependencies
   - Test `generate_stats()` with generator dependencies
   - Test cache hit rate calculation
   - Test dependency tree structure
   - Test timing aggregation

4. **Helper Function Tests**
   - Test `collect_dependency_metadata()` initialization
   - Test `record_dependency_resolution()` updates metadata
   - Test cache stats tracking (hits/misses)
   - Test dependency tree building

#### Integration Tests

1. **FastAPI App Integration** (`test_fastapi_integration.py`)
   - Create FastAPI app with debug toolbar
   - Define test dependencies (function, class, generator)
   - Make requests and verify toolbar injection
   - Verify DI panel appears in toolbar data
   - Verify dependency metadata collected correctly
   - Test with nested dependencies
   - Test with cached dependencies

2. **Real-world Patterns**
   - Database session dependency (yield pattern)
   - Pagination dependency (class-based)
   - Authentication dependency (Security())
   - Multiple dependencies in single route

#### Coverage Targets

- `config.py`: 95%+
- `middleware.py`: 90%+
- `panels/dependencies.py`: 95%+
- Overall: 90%+

#### Test Patterns (from existing codebase)

```python
"""Tests for FastAPI dependency injection panel."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from debug_toolbar.core.context import RequestContext, set_request_context
from debug_toolbar.fastapi.panels.dependencies import (
    DependencyInjectionPanel,
    collect_dependency_metadata,
    record_dependency_resolution,
)


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


class TestDependencyInjectionPanel:
    """Tests for DependencyInjectionPanel class."""

    def test_panel_class_attributes(self, mock_toolbar: MagicMock) -> None:
        """Test panel class attributes are set correctly."""
        panel = DependencyInjectionPanel(mock_toolbar)
        assert panel.get_panel_id() == "DependencyInjectionPanel"
        assert panel.title == "Dependencies"
        assert panel.has_content is True

    @pytest.mark.asyncio
    async def test_generate_stats_with_empty_dependencies(
        self, mock_toolbar: MagicMock
    ) -> None:
        """Test generate_stats with no dependencies."""
        set_request_context(None)  # Cleanup

        panel = DependencyInjectionPanel(mock_toolbar)
        context = RequestContext()
        context.metadata["dependencies"] = {
            "resolved": [],
            "tree": {},
            "cache_stats": {"hits": 0, "misses": 0, "total": 0},
        }

        stats = await panel.generate_stats(context)

        assert stats["total_count"] == 0
        assert stats["cached_count"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["total_time_ms"] == 0

        set_request_context(None)  # Cleanup
```

---

## Files to Create/Modify

### New Files

1. `src/debug_toolbar/fastapi/__init__.py`
   - Export `FastAPIDebugToolbarConfig`
   - Export `setup_debug_toolbar` helper
   - Export middleware

2. `src/debug_toolbar/fastapi/config.py`
   - `FastAPIDebugToolbarConfig` dataclass
   - `should_show_toolbar()` method

3. `src/debug_toolbar/fastapi/middleware.py`
   - `DebugToolbarMiddleware` class
   - Request/response handling
   - DI tracking hooks

4. `src/debug_toolbar/fastapi/setup.py`
   - `setup_debug_toolbar(app, config)` helper function
   - Convenience wrapper for middleware registration

5. `src/debug_toolbar/fastapi/panels/__init__.py`
   - Export `DependencyInjectionPanel`

6. `src/debug_toolbar/fastapi/panels/dependencies.py`
   - `DependencyInjectionPanel` class
   - `collect_dependency_metadata()` helper
   - `record_dependency_resolution()` helper
   - `_get_dependency_info()` helper (similar to `_get_handler_info`)

7. `examples/fastapi_basic/main.py`
   - FastAPI application example
   - Multiple dependency patterns
   - Route handlers demonstrating DI

8. `examples/fastapi_basic/dependencies.py`
   - Example dependency functions
   - Database, auth, pagination examples

9. `examples/fastapi_basic/requirements.txt`
   - FastAPI, uvicorn, debug-toolbar

10. `examples/fastapi_basic/README.md`
    - Setup and run instructions
    - Feature highlights

11. `tests/unit/test_fastapi_config.py`
    - Config tests (15+ test cases)

12. `tests/unit/test_fastapi_middleware.py`
    - Middleware tests (10+ test cases)

13. `tests/unit/test_dependency_injection_panel.py`
    - DI panel tests (20+ test cases)

14. `tests/integration/test_fastapi_integration.py`
    - Integration tests (8+ test cases)

### Modified Files

1. `src/debug_toolbar/__init__.py`
   - Add FastAPI imports to public API (conditional on fastapi install)

2. `README.md`
   - Add FastAPI to supported frameworks list
   - Add quickstart example for FastAPI

3. `pyproject.toml`
   - Add `fastapi` extra: `pip install debug-toolbar[fastapi]`
   - Add FastAPI to test dependencies

4. `docs/integrations/README.md` (if exists)
   - Add link to FastAPI integration guide

### Documentation Files

1. `docs/integrations/fastapi.md`
   - Complete integration guide
   - Installation instructions
   - Configuration options
   - Dependency injection panel guide
   - Troubleshooting

2. `docs/panels/dependency-injection.md`
   - DI panel features
   - Interpreting dependency data
   - Performance optimization tips

---

## Example Application

### Main Application (`examples/fastapi_basic/main.py`)

```python
"""FastAPI application with debug toolbar example.

This example demonstrates the debug toolbar integration with FastAPI,
showcasing the dependency injection panel with various dependency patterns.

Run with:
    uvicorn main:app --reload

Then visit:
    http://localhost:8000/
    http://localhost:8000/docs  # Toolbar should be excluded
    http://localhost:8000/users/123
"""

from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from debug_toolbar.fastapi import FastAPIDebugToolbarConfig, setup_debug_toolbar
from dependencies import (
    get_db,
    get_current_user,
    CommonQueryParams,
    get_settings,
)

# Create FastAPI app
app = FastAPI(
    title="Debug Toolbar Example",
    description="Example FastAPI app with debug toolbar",
)

# Configure and setup debug toolbar
config = FastAPIDebugToolbarConfig(
    enabled=True,
    track_dependency_injection=True,
    exclude_paths=[
        "/_debug_toolbar",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)
setup_debug_toolbar(app, config)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """Home page with simple HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Debug Toolbar Example</title></head>
    <body>
        <h1>FastAPI Debug Toolbar Example</h1>
        <p>Check the debug toolbar at the bottom of the page!</p>
        <ul>
            <li><a href="/users/123">View User 123</a> - Shows auth + DB dependencies</li>
            <li><a href="/items?skip=10&limit=20">List Items</a> - Shows pagination dependency</li>
            <li><a href="/settings">Settings</a> - Shows cached dependency</li>
        </ul>
    </body>
    </html>
    """


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: dict = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get user by ID - demonstrates auth + database dependencies.

    Dependencies:
    - get_db: Database session (generator with yield)
    - get_current_user: Current authenticated user (depends on get_db)
    """
    if user_id not in db["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user": db["users"][user_id],
        "requested_by": current_user["username"],
    }


@app.get("/items")
async def list_items(
    commons: CommonQueryParams = Depends(),
    db: dict = Depends(get_db),
) -> dict:
    """List items with pagination - demonstrates class-based dependency.

    Dependencies:
    - CommonQueryParams: Class-based dependency with q, skip, limit
    - get_db: Database session
    """
    items = db["items"]

    # Apply filters
    if commons.q:
        items = [item for item in items if commons.q.lower() in item["name"].lower()]

    # Apply pagination
    paginated = items[commons.skip : commons.skip + commons.limit]

    return {
        "items": paginated,
        "total": len(items),
        "skip": commons.skip,
        "limit": commons.limit,
    }


@app.get("/settings")
async def get_app_settings(settings: dict = Depends(get_settings)) -> dict:
    """Get application settings - demonstrates cached dependency.

    Dependencies:
    - get_settings: Cached application settings (uses default caching)
    """
    return {"settings": settings}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Dependencies Module (`examples/fastapi_basic/dependencies.py`)

```python
"""Example dependencies for FastAPI debug toolbar demo.

Demonstrates various dependency patterns:
- Function-based dependencies
- Generator dependencies (with yield)
- Class-based dependencies
- Nested dependencies
- Cached vs non-cached dependencies
"""

from __future__ import annotations

from typing import Annotated
from fastapi import Depends, Header, HTTPException, Query, status


# ============================================================================
# Database Dependency (Generator with Yield)
# ============================================================================

def get_db():
    """Get database session.

    This is a generator dependency that yields a database connection.
    The cleanup code after yield runs after the request completes.
    """
    # In production, this would be a real database session
    db = {
        "users": {
            123: {"id": 123, "username": "alice", "email": "alice@example.com"},
            456: {"id": 456, "username": "bob", "email": "bob@example.com"},
        },
        "items": [
            {"id": 1, "name": "Widget"},
            {"id": 2, "name": "Gadget"},
            {"id": 3, "name": "Doohickey"},
        ],
    }
    try:
        yield db
    finally:
        # Cleanup: close database connection
        pass


# ============================================================================
# Authentication Dependencies (Nested)
# ============================================================================

async def get_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Extract and validate authentication token.

    This is a sub-dependency used by get_current_user.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    # In production, validate token format
    return authorization


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    db: Annotated[dict, Depends(get_db)],
) -> dict:
    """Get current authenticated user.

    Demonstrates nested dependencies:
    - Depends on get_token (authentication)
    - Depends on get_db (data access)
    """
    # In production, decode token and fetch user from database
    # For demo, return first user
    return list(db["users"].values())[0]


# ============================================================================
# Class-Based Dependency
# ============================================================================

class CommonQueryParams:
    """Common pagination and search parameters.

    This is a class-based dependency. FastAPI will instantiate it
    and inject the query parameters.
    """

    def __init__(
        self,
        q: str | None = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
    ):
        self.q = q
        self.skip = skip
        self.limit = limit


# ============================================================================
# Cached Dependency
# ============================================================================

_settings_cache: dict | None = None

def get_settings() -> dict:
    """Get application settings.

    This dependency uses manual caching to demonstrate cache behavior.
    FastAPI also has built-in request-scoped caching.
    """
    global _settings_cache

    if _settings_cache is None:
        # Simulate expensive settings load
        _settings_cache = {
            "app_name": "Debug Toolbar Example",
            "version": "1.0.0",
            "debug": True,
        }

    return _settings_cache
```

---

## Performance Considerations

### Overhead Estimates

- **Baseline (toolbar disabled)**: 0% overhead
- **Toolbar enabled, DI tracking disabled**: 2-3% overhead (Starlette middleware)
- **Toolbar enabled, DI tracking enabled**: 4-5% overhead (DI tracking + middleware)

### Optimization Strategies

1. **Lazy initialization**: Only track dependencies when toolbar will be shown
2. **Efficient data structures**: Use lists for append-only operations
3. **Minimal instrumentation**: Track only essential metadata
4. **Context vars**: Avoid global state, thread-local overhead
5. **Conditional imports**: Import FastAPI types only when needed

### Performance Testing

Include benchmark in tests:

```python
@pytest.mark.benchmark
async def test_dependency_tracking_overhead(benchmark, fastapi_app):
    """Ensure DI tracking overhead is <5%."""
    # Measure baseline
    baseline_duration = await benchmark_request(fastapi_app, tracking=False)

    # Measure with tracking
    tracking_duration = await benchmark_request(fastapi_app, tracking=True)

    overhead_pct = ((tracking_duration - baseline_duration) / baseline_duration) * 100
    assert overhead_pct < 5.0, f"Overhead {overhead_pct:.1f}% exceeds 5% threshold"
```

---

## Security Considerations

1. **Development only**: Toolbar must be disabled in production
2. **No secrets in panel**: Avoid displaying dependency parameter values that might contain secrets
3. **Path exclusion**: Exclude health check, metrics endpoints by default
4. **Configuration validation**: Warn if toolbar enabled without DEBUG flag
5. **CORS safety**: Don't expose toolbar on different origins

### Recommendations

- Add warning when `enabled=True` and environment not in ("development", "dev", "local")
- Sanitize parameter values in DI panel (mask anything named "password", "token", "secret")
- Document security best practices in integration guide

---

## Migration Path

### For Users Coming From Generic ASGI Setup

Before:
```python
from debug_toolbar.asgi import DebugToolbarMiddleware

app.add_middleware(DebugToolbarMiddleware)
```

After:
```python
from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig

config = FastAPIDebugToolbarConfig(track_dependency_injection=True)
setup_debug_toolbar(app, config)
```

### For Users Coming From Django Debug Toolbar

Familiar concepts:
- Panel-based architecture (same)
- Middleware integration (similar)
- Configuration via settings (similar, but dataclass-based)
- Request history (same)

New concepts:
- ASGI async support
- Framework-specific panels (DI panel unique to FastAPI)
- Programmatic configuration vs settings file

---

## Open Questions

1. **DI Tracking Granularity**: Should we track every sub-dependency or just top-level?
   - **Recommendation**: Track all, provide tree view to collapse

2. **Cache Key Display**: Should we show FastAPI's internal cache keys or abstracted names?
   - **Recommendation**: Show human-readable names, tooltip with cache key

3. **Performance Threshold**: At what overhead do we warn users?
   - **Recommendation**: Warn at >5% overhead, error at >10%

4. **WebSocket Support**: Should DI tracking work for WebSocket endpoints?
   - **Recommendation**: Not in v1, add in future release

5. **Dependency Override Detection**: Should we detect and show `app.dependency_overrides`?
   - **Recommendation**: Yes, very useful for testing scenarios

---

## Success Metrics

### Development Metrics

- [ ] 90%+ test coverage achieved
- [ ] All acceptance criteria met
- [ ] Example app runs without errors
- [ ] Documentation complete and reviewed
- [ ] Zero critical bugs in code review

### Adoption Metrics (6 months post-release)

- [ ] 100+ GitHub stars
- [ ] Featured in FastAPI documentation or awesome-fastapi list
- [ ] 1000+ PyPI downloads per month
- [ ] <5 bug reports related to FastAPI adapter
- [ ] Positive community feedback (Reddit, Discord, etc.)

### Performance Metrics

- [ ] <5% overhead in development mode
- [ ] 0% overhead when disabled
- [ ] <100ms added latency per request (99th percentile)

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FastAPI internal API changes | Medium | High | Use public APIs where possible, version pin, integration tests |
| DI tracking overhead too high | Low | Medium | Benchmark early, optimize hot paths, make tracking optional |
| Starlette adapter not ready | Low | Critical | Coordinate with Starlette adapter owner, hard dependency |
| Dependency graph complexity | Medium | Low | Limit tree depth, provide collapse/expand UI |
| Circular dependency detection | Low | Medium | Implement cycle detection, show warning instead of crash |

---

## Timeline

### Week 1: Foundation
- **Day 1-2**: Research and design (this PRD)
- **Day 3**: Starlette adapter review, dependencies setup
- **Day 4**: Config and middleware implementation
- **Day 5**: Testing framework setup

### Week 2: Core Features
- **Day 1-2**: DI panel implementation
- **Day 3**: DI tracking hooks
- **Day 4-5**: Testing (unit + integration)

### Week 3: Polish
- **Day 1**: Example application
- **Day 2**: Documentation
- **Day 3**: Performance benchmarks
- **Day 4**: Code review iteration
- **Day 5**: Release preparation

**Total**: ~15 working days

---

## Appendices

### A. Research Notes

**FastAPI Dependency Injection System**:

FastAPI's DI system is based on:
1. **Inspection**: Uses `inspect` module to analyze function signatures
2. **Dependant tree**: Builds a tree of dependencies at startup
3. **Resolution**: `solve_dependencies()` resolves dependencies per request
4. **Caching**: Default request-scoped caching, can be disabled with `use_cache=False`
5. **Context**: Uses `contextlib.contextmanager` for generator dependencies

**Key Functions**:
- `fastapi.dependencies.utils.solve_dependencies()`
- `fastapi.dependencies.utils.get_dependant()`
- `fastapi.dependencies.models.Dependant`

**Caching Behavior**:
- Dependencies with same parameters are cached within a request
- Cache key includes dependency callable and parameter values
- Sub-dependencies are also cached
- `use_cache=False` forces fresh resolution

**Sources**:
- [FastAPI Dependency Injection: Beyond The Basics](https://dev.turmansolutions.ai/2025/08/26/fastapi-dependency-injection-beyond-the-basics/)
- [FastAPI Dependency Caching](https://www.compilenrun.com/docs/framework/fastapi/fastapi-dependency-injection/fastapi-dependency-caching/)
- [Understanding FastAPI's Built-In Dependency Injection](https://developer-service.blog/understading-fastapis-built-in-dependency-injection/)
- [Inside FastAPI's Routing Core](https://zalt.me/blog/2025/10/inside-fastapi-routing)
- [FastAPI DI That Scales Without Drama](https://medium.com/@2nick2patel2/fastapi-di-that-scales-without-drama-fa9b5c995183)

### B. Alternative Approaches Considered

**Alternative 1: Standalone FastAPI Package**
- Pros: Independent versioning, smaller dependency
- Cons: Code duplication, maintenance overhead
- Decision: Rejected - prefer monorepo for consistency

**Alternative 2: Generic ASGI + FastAPI Plugin**
- Pros: Minimal code, reuses generic ASGI adapter
- Cons: Loses FastAPI-specific features (DI tracking)
- Decision: Rejected - DI panel is key value proposition

**Alternative 3: FastAPI Middleware Only (No Config)**
- Pros: Simpler API, less code
- Cons: Less flexible, harder to customize
- Decision: Rejected - config consistency across adapters important

### C. Related Work

**Similar Projects**:
- [Django Debug Toolbar](https://github.com/jazzband/django-debug-toolbar): Inspiration for panel architecture
- [Flask-DebugToolbar](https://github.com/flask-debugtoolbar/flask-debugtoolbar): Similar concept for Flask
- [fastapi-profiler](https://github.com/sunhailin-leo/fastapi_profiler): Performance profiling only

**Differences**:
- Our approach: Comprehensive, panel-based, async-native
- DI panel: Unique to our implementation
- ASGI-first design vs framework-specific

### D. Glossary

- **DI**: Dependency Injection
- **ASGI**: Asynchronous Server Gateway Interface
- **Panel**: Modular debug information display component
- **Middleware**: ASGI middleware that intercepts requests/responses
- **Context**: Request-scoped data container using contextvars
- **Dependant**: FastAPI's internal dependency graph node
- **Cache hit**: Dependency resolved from cache
- **Cache miss**: Dependency freshly resolved

---

## Word Count

**Total PRD**: ~5,800 words
**Research Plan**: ~2,400 words (see research/plan.md)
**Combined**: ~8,200 words

---

## Approval

- [ ] Technical accuracy verified
- [ ] Acceptance criteria complete and measurable
- [ ] Testing strategy comprehensive
- [ ] Performance considerations addressed
- [ ] Security implications reviewed
- [ ] Ready for implementation phase

**Approved by**: [Pending]
**Date**: [Pending]

---

**End of PRD**
