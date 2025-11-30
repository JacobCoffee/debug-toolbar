# Litestar Skill

Quick reference for Litestar framework patterns in this project.

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="litestar")
# Returns: /litestar-org/litestar

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="plugins",
    mode="code"
)
```

## Project-Specific Patterns

### Plugin Implementation

Location: `src/debug_toolbar/litestar/plugin.py`

```python
"""Plugin implementation pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class DebugToolbarPlugin(InitPluginProtocol):
    """Litestar plugin for the debug toolbar."""

    __slots__ = ("_config", "_toolbar")

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._toolbar = None

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application."""
        if not self._config.enabled:
            return app_config

        # Add middleware
        # Add routes
        return app_config
```

### Middleware Implementation

Location: `src/debug_toolbar/litestar/middleware.py`

```python
"""Middleware implementation pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.middleware import AbstractMiddleware

if TYPE_CHECKING:
    from litestar import Request
    from litestar.types import ASGIApp, Receive, Scope, Send


class DebugToolbarMiddleware(AbstractMiddleware):
    """ASGI middleware for debug toolbar."""

    def __init__(self, app: ASGIApp, config: Config, toolbar: DebugToolbar) -> None:
        super().__init__(app)
        self.config = config
        self.toolbar = toolbar

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Process request
        await self.app(scope, receive, send)
```

### Route Handlers

Location: `src/debug_toolbar/litestar/routes/handlers.py`

```python
"""Route handler pattern."""

from __future__ import annotations

from litestar import Router, get
from litestar.response import Response


@get("/_debug_toolbar/data/{request_id:str}")
async def get_toolbar_data(request_id: str) -> dict:
    """Get toolbar data for a request."""
    return {}


def create_debug_toolbar_router(storage: ToolbarStorage) -> Router:
    """Create the debug toolbar router."""
    return Router(
        path="/_debug_toolbar",
        route_handlers=[get_toolbar_data],
    )
```

## Testing Patterns

### Litestar App Testing

```python
"""Litestar testing pattern."""

from __future__ import annotations

import pytest
from litestar import Litestar, get
from litestar.testing import TestClient

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig


class TestLitestarIntegration:
    """Integration tests with Litestar."""

    def test_plugin_integration(self) -> None:
        """Test plugin integrates correctly."""

        @get("/")
        async def handler() -> dict:
            return {"status": "ok"}

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[handler],
            plugins=[DebugToolbarPlugin(config)],
        )

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
```

## Related Files

- `src/debug_toolbar/litestar/__init__.py`
- `src/debug_toolbar/litestar/plugin.py`
- `src/debug_toolbar/litestar/middleware.py`
- `src/debug_toolbar/litestar/config.py`
- `src/debug_toolbar/litestar/routes/`
- `src/debug_toolbar/litestar/panels/`
- `tests/integration/test_litestar_middleware.py`
