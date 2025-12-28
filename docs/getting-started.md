# Getting Started

## Installation

Install with your preferred package manager:

::::{tab-set}
:::{tab-item} pip
```bash
# For Litestar
pip install debug-toolbar[litestar]

# For Starlette
pip install debug-toolbar[starlette]

# For FastAPI
pip install debug-toolbar[fastapi]
```
:::
:::{tab-item} uv
```bash
# For Litestar
uv add debug-toolbar[litestar]

# For Starlette
uv add debug-toolbar[starlette]

# For FastAPI
uv add debug-toolbar[fastapi]
```
:::
:::{tab-item} poetry
```bash
# For Litestar
poetry add debug-toolbar[litestar]

# For Starlette
poetry add debug-toolbar[starlette]

# For FastAPI
poetry add debug-toolbar[fastapi]
```
:::
::::

## Basic Litestar Usage

Add the debug toolbar plugin to your Litestar application:

```python
from litestar import Litestar, get
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

@get("/")
async def index() -> str:
    return "<html><body><h1>Hello World</h1></body></html>"

config = LitestarDebugToolbarConfig(
    enabled=True,  # Enable in development
)

app = Litestar(
    route_handlers=[index],
    plugins=[DebugToolbarPlugin(config)],
)
```

The toolbar will automatically inject itself into HTML responses.

## Starlette Usage

Add the debug toolbar middleware to your Starlette application:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse
from starlette.routing import Route
from debug_toolbar.core import DebugToolbar
from debug_toolbar.starlette import (
    DebugToolbarMiddleware,
    StarletteDebugToolbarConfig,
    create_debug_toolbar_routes,
)

async def homepage(request):
    return HTMLResponse("<html><body><h1>Hello World</h1></body></html>")

config = StarletteDebugToolbarConfig(enabled=True)
toolbar = DebugToolbar(config)

app = Starlette(
    routes=[
        Route("/", homepage),
        *create_debug_toolbar_routes(toolbar.storage),
    ],
    middleware=[
        Middleware(DebugToolbarMiddleware, config=config, toolbar=toolbar),
    ],
)
```

## FastAPI Usage

Use the convenience function to set up the debug toolbar with FastAPI:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig

app = FastAPI()

config = FastAPIDebugToolbarConfig(
    enabled=True,
    track_dependency_injection=True,  # Track FastAPI DI resolution
)
toolbar = setup_debug_toolbar(app, config)

@app.get("/", response_class=HTMLResponse)
async def homepage():
    return "<html><body><h1>Hello World</h1></body></html>"
```

The `setup_debug_toolbar` function automatically:
- Adds the debug toolbar middleware
- Registers the toolbar routes
- Returns the toolbar instance for further customization

### Tracking Dependency Injection

FastAPI's dependency injection can be tracked with the DI panel:

```python
from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig

app = FastAPI()
config = FastAPIDebugToolbarConfig(
    enabled=True,
    track_dependency_injection=True,
)
setup_debug_toolbar(app, config)

def get_db():
    return {"connected": True}

def get_user(db=Depends(get_db)):
    return {"name": "John", "db": db}

@app.get("/", response_class=HTMLResponse)
async def homepage(user=Depends(get_user)):
    return f"<html><body><h1>Hello {user['name']}</h1></body></html>"
```

The Dependencies panel will show:
- All resolved dependencies
- Cache hit/miss rates
- Resolution times

## Configuration

Common configuration options:

```python
config = LitestarDebugToolbarConfig(
    # Enable/disable the toolbar
    enabled=True,

    # Paths to exclude from toolbar
    exclude_paths=["/_debug_toolbar", "/static", "/health"],

    # Maximum requests in history
    max_request_history=50,

    # Show toolbar even on error responses
    show_on_errors=True,
)
```

See the {doc}`configuration` page for all options.

## With Advanced-Alchemy

Track SQL queries with the SQLAlchemy panel:

```python
from litestar import Litestar
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin, SQLAlchemyAsyncConfig
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

# Database configuration
db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///app.db",
)

# Debug toolbar configuration
toolbar_config = LitestarDebugToolbarConfig(
    enabled=True,
    extra_panels=["debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel"],
)

app = Litestar(
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        DebugToolbarPlugin(toolbar_config),
    ],
)
```

## Next Steps

- Learn about all {doc}`configuration` options
- See available {doc}`panels`
- Create your own {doc}`custom-panels`
