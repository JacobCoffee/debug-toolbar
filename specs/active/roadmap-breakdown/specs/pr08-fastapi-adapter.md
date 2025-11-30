# Spec: PR #8 - FastAPI Adapter

## Metadata
- **PR Number**: 8
- **Priority**: P1
- **Complexity**: Low
- **Estimated Files**: 4-5
- **Dependencies**: PR #7 (Starlette Adapter)
- **Implementation Order**: 4

---

## Problem Statement

FastAPI is the most popular ASGI framework with a massive user base. Supporting FastAPI is critical for adoption of this debug toolbar as the "default choice for ASGI debugging."

Since FastAPI is built on Starlette, most of the work is done by the Starlette adapter. This PR adds FastAPI-specific features like dependency injection tracking.

---

## Goals

1. Provide FastAPI-specific middleware/plugin
2. Create dependency injection panel
3. Support FastAPIDebugToolbarConfig
4. Example with FastAPI-specific features
5. Documentation for FastAPI users

---

## Non-Goals

- Pydantic validation debugging (separate panel)
- OpenAPI documentation integration (PR #4)
- Background tasks panel (uses SAQ panel)

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ debug_toolbar/fastapi/                          │
├─────────────────────────────────────────────────┤
│ __init__.py    - Public exports                 │
│ plugin.py      - FastAPI integration            │
│ config.py      - FastAPIDebugToolbarConfig      │
│ panels/        - FastAPI-specific panels        │
│   └── dependencies.py - DI tracking panel       │
└─────────────────────────────────────────────────┘
         │
         │ builds on
         ▼
┌─────────────────────────────────────────────────┐
│ debug_toolbar/starlette/                        │
├─────────────────────────────────────────────────┤
│ Reuses Starlette middleware and routes          │
└─────────────────────────────────────────────────┘
```

### FastAPI Integration

```python
# src/debug_toolbar/fastapi/plugin.py
from fastapi import FastAPI
from debug_toolbar.starlette.middleware import DebugToolbarMiddleware
from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig

def setup_debug_toolbar(app: FastAPI, config: FastAPIDebugToolbarConfig | None = None):
    """Add debug toolbar to FastAPI application."""
    config = config or FastAPIDebugToolbarConfig()

    # Add middleware
    app.add_middleware(DebugToolbarMiddleware, config=config)

    # Patch dependency resolution for tracking
    if config.track_dependencies:
        _patch_dependency_resolution(app)
```

### Dependency Injection Panel

FastAPI's DI system resolves dependencies for each request. Tracking this provides valuable debugging info.

```python
# src/debug_toolbar/fastapi/panels/dependencies.py
class DependenciesPanel(Panel):
    """Panel showing FastAPI dependency injection resolution."""

    panel_id = "DependenciesPanel"
    title = "Dependencies"
    template = "panels/dependencies.html"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        deps = context.metadata.get("resolved_dependencies", [])
        return {
            "dependencies": deps,
            "total_count": len(deps),
            "total_time_ms": sum(d.get("duration_ms", 0) for d in deps),
            "cached_count": sum(1 for d in deps if d.get("cached")),
        }
```

### Dependency Tracking

Hook into FastAPI's dependency resolution:

```python
from fastapi.dependencies.utils import solve_dependencies

_original_solve = solve_dependencies

async def tracked_solve_dependencies(*args, **kwargs):
    start = time.perf_counter()
    result = await _original_solve(*args, **kwargs)
    duration = (time.perf_counter() - start) * 1000

    # Record dependency resolution
    DependencyTracker.record(
        name=dependency.__name__,
        duration_ms=duration,
        cached=was_cached,
    )

    return result
```

### Configuration

```python
# src/debug_toolbar/fastapi/config.py
@dataclass
class FastAPIDebugToolbarConfig(StarletteDebugToolbarConfig):
    """FastAPI-specific debug toolbar configuration."""

    track_dependencies: bool = True

    default_panels: tuple[str, ...] = (
        "debug_toolbar.core.panels.timer.TimerPanel",
        "debug_toolbar.core.panels.request.RequestPanel",
        "debug_toolbar.core.panels.response.ResponsePanel",
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.starlette.panels.routes.StarletteRoutesPanel",
        "debug_toolbar.fastapi.panels.dependencies.DependenciesPanel",
        # ... rest of core panels
    )
```

### Files to Create

```
src/debug_toolbar/fastapi/
├── __init__.py
├── plugin.py
├── config.py
└── panels/
    ├── __init__.py
    └── dependencies.py

tests/integration/
└── test_fastapi_integration.py

examples/
└── fastapi_app.py

docs/frameworks/
└── fastapi.md
```

---

## Acceptance Criteria

- [ ] FastAPI middleware works (via Starlette)
- [ ] Dependency injection panel shows resolved deps
- [ ] Dependency timing captured
- [ ] Cached dependencies indicated
- [ ] Nested dependencies shown correctly
- [ ] setup_debug_toolbar() function works
- [ ] Example application functional
- [ ] Integration tests pass
- [ ] 90%+ test coverage
- [ ] Documentation complete

---

## Testing Strategy

### Unit Tests
```python
class TestDependenciesPanel:
    async def test_tracks_dependency(self):
        """Should record dependency resolution."""

    async def test_tracks_cached_dependency(self):
        """Should indicate cached dependencies."""

    async def test_tracks_nested_dependencies(self):
        """Should show dependency hierarchy."""

    async def test_measures_timing(self):
        """Should measure resolution time."""
```

### Integration Tests
```python
class TestFastAPIIntegration:
    async def test_full_request_cycle(self):
        """Test complete request with toolbar."""

    async def test_dependency_tracking(self):
        """Verify dependency panel works."""
```

---

## Example Application

```python
# examples/fastapi_app.py
from fastapi import FastAPI, Depends
from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig

app = FastAPI()

# Setup debug toolbar
config = FastAPIDebugToolbarConfig(enabled=True)
setup_debug_toolbar(app, config)

# Example dependency
async def get_db():
    return {"connected": True}

@app.get("/")
async def homepage(db=Depends(get_db)):
    return {"message": "Hello", "db": db}
```

---

## UI Design - Dependencies Panel

```
┌─────────────────────────────────────────────────┐
│ Dependencies                           5 resolved│
├─────────────────────────────────────────────────┤
│ Total Resolution Time: 12.5ms                   │
│ Cached: 2/5                                     │
├─────────────────────────────────────────────────┤
│ Dependency                    Time    Cached    │
│ ├─ get_current_user          5.2ms   ✗         │
│ │  └─ get_db_session         3.1ms   ✓         │
│ ├─ get_settings              0.1ms   ✓         │
│ ├─ validate_permissions      2.3ms   ✗         │
│ └─ get_request_id            0.1ms   ✗         │
└─────────────────────────────────────────────────┘
```

---

## Implementation Notes

1. **Starlette Reuse**: Maximum code reuse from Starlette adapter
2. **DI Patching**: Patch at app startup, restore on shutdown
3. **Dependency Caching**: FastAPI caches some deps per request
4. **Nested Dependencies**: Track full resolution tree
5. **Generator Dependencies**: Handle async generators correctly

### FastAPI Dependency Types

```python
# Handle all dependency types:
# - Callable returning value
# - Async callable
# - Generator (with yield)
# - Async generator
# - Class-based dependencies
```

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Debug Toolbar (competitor)](https://fastapi-debug-toolbar.domake.io/)
- Pattern: `src/debug_toolbar/starlette/` (from PR #7)
