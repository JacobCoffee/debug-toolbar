# Spec: PR #7 - Starlette Adapter

## Metadata
- **PR Number**: 7
- **Priority**: P1
- **Complexity**: Medium
- **Estimated Files**: 8-10
- **Dependencies**: None
- **Implementation Order**: 3

---

## Problem Statement

Starlette is the foundation for FastAPI and many ASGI frameworks. Supporting Starlette directly:
1. Expands our user base significantly
2. Enables FastAPI support (builds on Starlette)
3. Validates our framework-agnostic core design

Currently, the debug toolbar only works with Litestar. To become the "default choice for ASGI debugging," we need multi-framework support.

---

## Goals

1. Create Starlette middleware for toolbar injection
2. Implement Starlette-specific routes panel
3. Provide StarletteDebugToolbarConfig
4. Create example application
5. Document integration process

---

## Non-Goals

- Starlette-specific panels beyond Routes (v1)
- Automatic dependency detection
- Backwards compatibility with Starlette < 0.27

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ debug_toolbar/starlette/                        │
├─────────────────────────────────────────────────┤
│ middleware.py    - ASGI middleware              │
│ config.py        - StarletteDebugToolbarConfig  │
│ routes.py        - Toolbar API routes           │
│ panels/          - Starlette-specific panels    │
│   └── routes.py  - Starlette routes panel       │
└─────────────────────────────────────────────────┘
         │
         │ uses
         ▼
┌─────────────────────────────────────────────────┐
│ debug_toolbar/core/                             │
├─────────────────────────────────────────────────┤
│ Reuses all core panels, context, storage        │
└─────────────────────────────────────────────────┘
```

### Middleware Implementation

```python
# src/debug_toolbar/starlette/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class DebugToolbarMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: StarletteDebugToolbarConfig | None = None):
        super().__init__(app)
        self.config = config or StarletteDebugToolbarConfig()
        self.toolbar = DebugToolbar(self.config)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._should_intercept(request):
            return await call_next(request)

        # Create context
        context = self._create_context(request)

        # Process request
        await self.toolbar.process_request(context)

        # Call actual handler
        response = await call_next(request)

        # Process response
        await self.toolbar.process_response(context)

        # Inject toolbar if HTML
        if self._should_inject(response):
            response = self._inject_toolbar(response, context)

        return response
```

### Routes Panel

```python
# src/debug_toolbar/starlette/panels/routes.py
class StarletteRoutesPanel(Panel):
    """Panel showing Starlette application routes."""

    panel_id = "StarletteRoutesPanel"
    title = "Routes"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        app = context.metadata.get("app")
        routes = self._collect_routes(app)
        return {
            "routes": routes,
            "matched_route": context.metadata.get("matched_route"),
        }

    def _collect_routes(self, app: Starlette) -> list[dict]:
        """Recursively collect routes from Starlette app."""
        routes = []
        for route in app.routes:
            routes.append(self._route_to_dict(route))
        return routes
```

### Configuration

```python
# src/debug_toolbar/starlette/config.py
@dataclass
class StarletteDebugToolbarConfig(DebugToolbarConfig):
    """Starlette-specific debug toolbar configuration."""

    # Starlette-specific defaults
    default_panels: tuple[str, ...] = (
        "debug_toolbar.core.panels.timer.TimerPanel",
        "debug_toolbar.core.panels.request.RequestPanel",
        "debug_toolbar.core.panels.response.ResponsePanel",
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.starlette.panels.routes.StarletteRoutesPanel",
        # ... rest of core panels
    )
```

### Files to Create

```
src/debug_toolbar/starlette/
├── __init__.py
├── middleware.py
├── config.py
├── routes.py              # Toolbar API endpoints
└── panels/
    ├── __init__.py
    └── routes.py          # Starlette routes panel

tests/integration/
└── test_starlette_integration.py

examples/
└── starlette_app.py

docs/frameworks/
└── starlette.md
```

---

## Acceptance Criteria

- [ ] Middleware injects toolbar into HTML responses
- [ ] All core panels work with Starlette
- [ ] Starlette routes panel shows app routes
- [ ] Route matching info displayed
- [ ] Toolbar API routes work (/debug-toolbar/*)
- [ ] Static assets served correctly
- [ ] Configuration via StarletteDebugToolbarConfig
- [ ] Example application runs and works
- [ ] Integration tests pass
- [ ] 90%+ test coverage
- [ ] Documentation complete

---

## Testing Strategy

### Unit Tests
```python
class TestStarletteMiddleware:
    async def test_injects_toolbar(self):
        """Should inject toolbar into HTML responses."""

    async def test_skips_non_html(self):
        """Should not modify JSON/binary responses."""

    async def test_respects_disabled(self):
        """Should skip when disabled."""

    async def test_toolbar_routes(self):
        """Should handle toolbar API routes."""
```

### Integration Tests
```python
class TestStarletteIntegration:
    async def test_full_request_cycle(self):
        """Test complete request with toolbar."""

    async def test_panels_generate_stats(self):
        """Verify all panels work."""

    async def test_history_storage(self):
        """Test request history."""
```

---

## Example Application

```python
# examples/starlette_app.py
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from debug_toolbar.starlette import DebugToolbarMiddleware, StarletteDebugToolbarConfig

async def homepage(request):
    return HTMLResponse("<html><body><h1>Hello</h1></body></html>")

routes = [
    Route("/", homepage),
]

config = StarletteDebugToolbarConfig(enabled=True)
app = Starlette(routes=routes)
app.add_middleware(DebugToolbarMiddleware, config=config)
```

---

## API Routes

```
GET  /_debug-toolbar/                    # Toolbar home
GET  /_debug-toolbar/static/{path}       # Static assets
GET  /_debug-toolbar/history/            # Request history
GET  /_debug-toolbar/history/{id}        # Request detail
GET  /_debug-toolbar/panel/{id}/{panel}  # Panel content
```

---

## Implementation Notes

1. **Route Collection**: Starlette uses `app.routes` list
2. **Request State**: Use `request.state` for context
3. **Response Modification**: Need to handle streaming responses
4. **Static Files**: Reuse existing static assets
5. **Templates**: Reuse existing Jinja2 templates

### Starlette Route Types

```python
from starlette.routing import Route, Mount, WebSocketRoute

# Need to handle:
# - Route (regular HTTP)
# - Mount (sub-applications)
# - WebSocketRoute
```

---

## References

- [Starlette Documentation](https://www.starlette.io/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- Pattern: `src/debug_toolbar/litestar/middleware.py`
- Pattern: `src/debug_toolbar/litestar/plugin.py`
