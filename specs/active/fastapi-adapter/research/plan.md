# Research Plan: FastAPI Adapter

**Date**: 2025-11-29
**Status**: Complete
**Complexity**: Simple (6 checkpoints)

---

## Executive Summary

This research phase analyzed FastAPI's architecture, dependency injection system, and integration patterns to inform the FastAPI adapter implementation. Key findings:

1. **FastAPI is built on Starlette** - Maximum code reuse possible from Starlette adapter
2. **DI system is the differentiator** - Dependency injection tracking is the unique value proposition
3. **Non-invasive tracking is feasible** - Can track dependencies at middleware level without monkey-patching
4. **Pattern consistency is maintained** - Existing Litestar patterns apply directly to FastAPI

---

## Research Questions

### 1. How does FastAPI's dependency injection system work internally?

**Answer**: FastAPI's DI system operates in three phases:

**Phase 1: Dependency Analysis (Startup)**
- Uses Python's `inspect` module to analyze route handler signatures
- Builds a `Dependant` tree representing all dependencies and sub-dependencies
- Stores metadata: parameter types, default values, dependency callables
- Happens once at application startup

**Phase 2: Dependency Resolution (Per Request)**
- `solve_dependencies()` function walks the Dependant tree
- Resolves dependencies in dependency-first order (bottom-up)
- Implements request-scoped caching by default
- Cache key: `(dependency_callable, param_values)`
- Returns resolved values to inject into route handler

**Phase 3: Cleanup (After Request)**
- For generator dependencies (with `yield`), runs cleanup code
- Closes database sessions, file handles, etc.
- Happens in finally blocks to ensure cleanup

**Key Functions**:
```python
# Build dependency tree
from fastapi.dependencies.utils import get_dependant
dependant = get_dependant(path="/", call=route_handler)

# Resolve dependencies
from fastapi.dependencies.utils import solve_dependencies
values, errors, background_tasks, _, _ = await solve_dependencies(
    request=request,
    dependant=dependant,
)
```

**Caching Behavior**:
- Default: Dependencies cached per request
- Override: `Depends(func, use_cache=False)` forces fresh resolution
- Cache hit: Returns stored value, duration ~0ms
- Cache miss: Executes dependency callable, duration varies

**Source**: Analysis of `fastapi.dependencies.utils` module + research articles

### 2. What are the differences between FastAPI and Starlette?

**Architectural Layers**:
```
FastAPI
├── Dependency Injection (unique to FastAPI)
├── Pydantic Validation (unique to FastAPI)
├── OpenAPI Generation (unique to FastAPI)
└── Starlette Core
    ├── Routing
    ├── Middleware
    ├── Request/Response
    └── ASGI Protocol
```

**Key Differences**:

| Feature | FastAPI | Starlette |
|---------|---------|-----------|
| DI System | Built-in, comprehensive | None |
| Validation | Pydantic automatic | Manual |
| OpenAPI | Auto-generated | None |
| Type Hints | Required, enforced | Optional |
| Performance | Slight overhead (validation) | Minimal |
| Use Case | API development | Generic ASGI |

**Implication for Debug Toolbar**:
- Starlette adapter handles: routing, middleware, request/response
- FastAPI adapter adds: DI tracking, validation insights (future)
- Maximum code reuse: Inherit/wrap Starlette middleware

### 3. How can we track dependency resolution without modifying FastAPI internals?

**Approach Options Evaluated**:

**Option A: Middleware-Level Inspection** ✅ RECOMMENDED
```python
async def track_dependencies_middleware(request, call_next):
    # Access route handler from request.scope
    route = request.scope.get("route")
    if isinstance(route, APIRoute):
        # Inspect dependency tree
        dependant = route.dependant
        # Walk tree, record structure
        # Actual resolution happens in route handler
    response = await call_next(request)
    return response
```

Pros:
- Non-invasive, no FastAPI internals modified
- Works across FastAPI versions (uses public API)
- Captures dependency structure reliably

Cons:
- Less granular timing (can't measure individual sub-dependencies)
- Doesn't capture cache hits/misses directly

**Option B: Monkey-Patch solve_dependencies** ⚠️ FRAGILE
```python
original_solve = fastapi.dependencies.utils.solve_dependencies

async def tracked_solve_dependencies(*args, **kwargs):
    start = time.perf_counter()
    result = await original_solve(*args, **kwargs)
    duration = time.perf_counter() - start
    # Record timing
    return result

fastapi.dependencies.utils.solve_dependencies = tracked_solve_dependencies
```

Pros:
- Most accurate timing
- Captures every resolution
- Can detect cache hits/misses

Cons:
- Invasive, fragile across versions
- Breaks if FastAPI changes internals
- Hard to test

**Option C: Custom Depends Wrapper** ❌ REQUIRES CODE CHANGES
```python
def DebugDepends(dependency):
    @wraps(dependency)
    async def wrapper(*args, **kwargs):
        # Track resolution
        return await dependency(*args, **kwargs)
    return Depends(wrapper)
```

Pros:
- Explicit, no magic
- Full control

Cons:
- Requires user code changes
- Defeats purpose of transparent debugging
- Verbose

**Decision**: Start with **Option A** (middleware-level), document Option B for future enhancement if needed.

### 4. What patterns from Litestar integration apply to FastAPI?

**Applicable Patterns**:

1. **Config Inheritance Pattern**
   ```python
   @dataclass
   class LitestarDebugToolbarConfig(DebugToolbarConfig):
       exclude_paths: Sequence[str] = field(...)
       show_toolbar_callback: Callable[[Request], bool] | None = None
   ```
   ✅ **Apply to FastAPI**: Same pattern, different framework types

2. **Framework-Specific Panels Pattern**
   ```python
   def __post_init__(self) -> None:
       default_panels = list(self.panels)
       default_panels.append("debug_toolbar.litestar.panels.routes.RoutesPanel")
       self.panels = default_panels
   ```
   ✅ **Apply to FastAPI**: Auto-register DependencyInjectionPanel

3. **Metadata Collection Helper Pattern**
   ```python
   def collect_events_metadata(app: Litestar, context: RequestContext) -> None:
       context.metadata["events"] = {...}
   ```
   ✅ **Apply to FastAPI**: `collect_dependency_metadata(app, context)`

4. **Middleware Delegation Pattern**
   ```python
   class DebugToolbarMiddleware(AbstractMiddleware):
       async def __call__(self, scope, receive, send):
           # Framework-specific logic
           await self.app(scope, receive, send)
   ```
   ✅ **Apply to FastAPI**: Wrap Starlette middleware, add DI hooks

5. **Panel Statistics Pattern**
   ```python
   async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
       data = context.metadata.get("events", {})
       return {
           "total_hooks": len(data.get("hooks", [])),
           # ... computed stats
       }
   ```
   ✅ **Apply to FastAPI**: Same pattern for dependency stats

**Pattern Compliance Checklist**:
- [ ] PEP 604 unions (`T | None`)
- [ ] Future annotations import
- [ ] ClassVar for panel metadata
- [ ] TYPE_CHECKING imports
- [ ] Context var cleanup in tests
- [ ] Google-style docstrings

### 5. What metadata should the Dependency Injection panel collect?

**Required Metadata** (per dependency):

```python
{
    "name": str,              # Dependency function/class name
    "type": str,              # "function", "class", "generator"
    "module": str,            # Module path
    "cached": bool,           # From cache or fresh resolution
    "duration_ms": float,     # Resolution time
    "cache_key": str,         # FastAPI's internal cache key (optional)
    "dependency_path": list,  # Path from root to this dependency
    "params": dict,           # Parameters passed to dependency
    "source_file": str,       # Source code location
    "source_line": int,       # Line number
}
```

**Aggregate Statistics**:

```python
{
    "total_count": int,         # Total dependencies resolved
    "cached_count": int,        # How many from cache
    "cache_hit_rate": float,    # Percentage cached
    "total_time_ms": float,     # Total resolution time
    "cache_stats": {
        "hits": int,
        "misses": int,
        "total": int,
    },
}
```

**Dependency Tree Structure**:

```python
{
    "get_current_user": {
        "info": {...},  # Dependency metadata
        "sub_dependencies": {
            "get_db": {...},
            "get_token": {...},
        }
    }
}
```

**UI Presentation**:
- List view: All dependencies with cache status
- Tree view: Expandable hierarchy
- Color coding: Green (cached), Blue (fresh), Red (slow >10ms)
- Summary bar: "8 dependencies (5 cached, 62% hit rate, 12.3ms total)"

### 6. What are realistic example dependencies for the demo app?

**Categories of Dependencies**:

1. **Database Session** (Generator Pattern)
   ```python
   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()
   ```
   - Demonstrates: yield pattern, cleanup, common use case

2. **Authentication** (Nested Dependencies)
   ```python
   async def get_current_user(
       token: str = Depends(get_token),
       db: Session = Depends(get_db),
   ):
       user = db.query(User).filter(User.token == token).first()
       if not user:
           raise HTTPException(401)
       return user
   ```
   - Demonstrates: sub-dependencies, error handling

3. **Pagination** (Class-Based)
   ```python
   class CommonQueryParams:
       def __init__(
           self,
           q: str | None = None,
           skip: int = 0,
           limit: int = 100,
       ):
           self.q = q
           self.skip = skip
           self.limit = limit
   ```
   - Demonstrates: class-based DI, query parameters

4. **Settings** (Cached)
   ```python
   @lru_cache()
   def get_settings():
       return Settings()
   ```
   - Demonstrates: caching behavior

5. **Request Validation** (Security)
   ```python
   async def get_api_key(
       api_key: str = Security(api_key_header),
   ):
       if api_key != "secret-key":
           raise HTTPException(403)
       return api_key
   ```
   - Demonstrates: Security() usage

**Example Routes**:
- `GET /`: Home page (no dependencies)
- `GET /users/{id}`: Auth + DB (nested dependencies)
- `GET /items`: Pagination + DB (class-based dependency)
- `GET /settings`: Cached dependency
- `GET /protected`: Security dependency

---

## Pattern Analysis

### Litestar Plugin Pattern

**File**: `src/debug_toolbar/litestar/plugin.py`

**Key Elements**:
1. Implements `InitPluginProtocol`
2. `__slots__` for memory efficiency
3. `on_app_init()` modifies `AppConfig`
4. Creates toolbar instance
5. Registers middleware and routes

**FastAPI Equivalent**:
- No `InitPluginProtocol` in FastAPI
- Use `app.add_middleware()` directly
- Helper function: `setup_debug_toolbar(app, config)`

### Litestar Config Pattern

**File**: `src/debug_toolbar/litestar/config.py`

**Key Elements**:
1. Extends `DebugToolbarConfig`
2. `exclude_paths` with framework-specific defaults
3. `show_toolbar_callback` with framework-specific request type
4. `__post_init__()` for panel registration

**FastAPI Application**:
```python
@dataclass
class FastAPIDebugToolbarConfig(DebugToolbarConfig):
    exclude_paths: Sequence[str] = field(
        default_factory=lambda: [
            "/_debug_toolbar",
            "/docs",          # FastAPI-specific
            "/redoc",         # FastAPI-specific
            "/openapi.json",  # FastAPI-specific
        ]
    )
    show_toolbar_callback: Callable[[FastAPIRequest], bool] | None = None
    track_dependency_injection: bool = True  # FastAPI-specific

    def __post_init__(self) -> None:
        if self.track_dependency_injection:
            self.panels.append("debug_toolbar.fastapi.panels.dependencies.DependencyInjectionPanel")
```

### Events Panel Pattern

**File**: `src/debug_toolbar/litestar/panels/events.py`

**Key Elements**:
1. Helper function outside class: `collect_events_metadata()`
2. Helper function for recording: `record_hook_execution()`
3. Private helper: `_get_handler_info()`
4. Panel only handles presentation, not collection

**FastAPI Application**:
```python
# Helper functions
def collect_dependency_metadata(app: FastAPI, context: RequestContext) -> None:
    """Initialize dependency metadata structure."""
    context.metadata["dependencies"] = {
        "resolved": [],
        "tree": {},
        "cache_stats": {"hits": 0, "misses": 0, "total": 0},
    }

def record_dependency_resolution(
    context: RequestContext,
    dependency_name: str,
    cached: bool,
    duration_ms: float,
    **kwargs
) -> None:
    """Record a dependency resolution event."""
    # Implementation

def _get_dependency_info(dependency: Callable) -> dict[str, Any]:
    """Extract metadata from dependency callable."""
    # Similar to _get_handler_info()
```

---

## Architecture Decisions

### AD-1: Middleware Strategy

**Decision**: Wrap Starlette middleware, add FastAPI-specific DI tracking hooks.

**Rationale**:
- FastAPI is built on Starlette - leverage existing work
- DI tracking is the only FastAPI-specific addition
- Avoids code duplication
- Maintains separation of concerns

**Alternatives Considered**:
- Implement from scratch: Too much duplication
- Pure Starlette adapter: Loses FastAPI features

**Impact**:
- Starlette adapter becomes a dependency
- FastAPI middleware is thin wrapper
- Easy to maintain

### AD-2: DI Tracking Approach

**Decision**: Middleware-level inspection using public FastAPI APIs.

**Rationale**:
- Non-invasive, version-stable
- Uses `route.dependant` (public API)
- Graceful degradation if internals change
- Sufficient accuracy for debugging use case

**Alternatives Considered**:
- Monkey-patching: Too fragile
- Custom Depends: Requires code changes

**Impact**:
- Timing accuracy: Route-level, not per-dependency
- Cache detection: Inferred, not direct
- Maintenance: Low overhead

### AD-3: Panel Scope

**Decision**: DI panel in v1, OpenAPI/Pydantic panels deferred.

**Rationale**:
- DI is unique value proposition
- OpenAPI auto-docs already excellent in FastAPI
- Pydantic validation errors already clear
- Focused scope for initial release

**Alternatives Considered**:
- All features v1: Too large scope
- Minimal adapter: Loses differentiation

**Impact**:
- Clear value proposition
- Manageable scope
- Room for future enhancement

### AD-4: Configuration Pattern

**Decision**: Extend `DebugToolbarConfig`, add FastAPI-specific options.

**Rationale**:
- Consistent with Litestar pattern
- Type-safe with dataclass
- Easy to document
- IDE-friendly

**Alternatives Considered**:
- Dictionary config: Less type-safe
- Separate config: Breaks consistency

**Impact**:
- Familiar to existing users
- Consistent API across adapters

---

## Technical Constraints

1. **FastAPI Version Support**
   - Minimum: 0.100.0 (modern DI system)
   - Target: 0.115.0+ (latest stable)
   - Breaking changes: Monitor `fastapi.dependencies` module

2. **Starlette Dependency**
   - Requires Starlette adapter completed first
   - Version alignment with FastAPI's Starlette version

3. **Python Version**
   - 3.10+ (project standard)
   - PEP 604 unions required
   - Async/await support

4. **Performance Budget**
   - <5% overhead with DI tracking enabled
   - <2% overhead with DI tracking disabled
   - 0% overhead when toolbar disabled

5. **Testing Requirements**
   - 90%+ code coverage
   - Integration tests with real FastAPI app
   - Benchmark tests for overhead

---

## Risk Mitigation

### Risk: FastAPI Internal Changes

**Mitigation**:
- Use public APIs where possible (`route.dependant`)
- Version pin FastAPI in tests
- Monitor FastAPI releases
- Integration tests catch breakage early

### Risk: DI Tracking Overhead

**Mitigation**:
- Benchmark early in development
- Make tracking optional (`track_dependency_injection=False`)
- Optimize hot paths
- Document overhead in README

### Risk: Starlette Adapter Delays

**Mitigation**:
- Coordinate with Starlette adapter owner
- Start implementation with mock Starlette adapter
- Clear dependency in project plan

---

## Implementation Priorities

### P0: Critical Path
1. Starlette adapter (blocking dependency)
2. FastAPI config
3. Middleware integration
4. Basic DI panel (list view)

### P1: Core Features
1. DI tracking hooks
2. Dependency tree structure
3. Cache detection
4. Example application

### P2: Nice-to-Have
1. Tree visualization
2. Source code links
3. Performance warnings
4. Export functionality

---

## Testing Strategy

### Unit Tests (75% of coverage)

1. **Config Tests** (~15 test cases)
   - Default values
   - Panel registration
   - Path exclusion logic
   - Callback validation

2. **Middleware Tests** (~12 test cases)
   - Request/response flow
   - Context initialization
   - Exception handling
   - Path exclusion

3. **DI Panel Tests** (~20 test cases)
   - Empty dependencies
   - Function dependencies
   - Class dependencies
   - Generator dependencies
   - Tree structure
   - Statistics calculation

4. **Helper Function Tests** (~10 test cases)
   - Metadata collection
   - Dependency recording
   - Info extraction

### Integration Tests (25% of coverage)

1. **FastAPI App Tests** (~8 test cases)
   - Full request cycle
   - Multiple dependency types
   - Nested dependencies
   - Cache behavior
   - Error scenarios

2. **Real-world Patterns** (~5 test cases)
   - Database session
   - Authentication
   - Pagination
   - Settings

---

## Documentation Plan

### User-Facing

1. **README.md Update**
   - Add FastAPI to supported frameworks
   - Quickstart example
   - Link to integration guide

2. **Integration Guide** (`docs/integrations/fastapi.md`)
   - Installation steps
   - Basic setup
   - Configuration options
   - Advanced usage
   - Troubleshooting

3. **DI Panel Guide** (`docs/panels/dependency-injection.md`)
   - What it shows
   - How to interpret
   - Performance tips
   - Common patterns

### Developer-Facing

1. **Architecture Doc**
   - Component diagram
   - Data flow
   - Extension points

2. **API Reference**
   - Config options
   - Middleware API
   - Panel API
   - Helper functions

---

## Knowledge Transfer

### Patterns for Pattern Library

After implementation, extract these patterns:

1. **Framework Adapter Pattern**
   - Config inheritance
   - Middleware wrapping
   - Panel registration

2. **Dependency Tracking Pattern**
   - Metadata collection
   - Resolution recording
   - Tree building

3. **Testing Pattern**
   - Mock framework app
   - Integration fixtures
   - Coverage strategy

---

## Word Count

**Research Plan**: ~2,400 words

---

## Completion Checklist

- [x] Research questions answered
- [x] Patterns analyzed
- [x] Architecture decisions documented
- [x] Risks identified and mitigated
- [x] Testing strategy defined
- [x] Ready for implementation phase

**Research Complete**: 2025-11-29
