# Debug Toolbar

An async-native debug toolbar for Python ASGI frameworks with support for Litestar, Starlette, and FastAPI.

## Installation

`````{tab-set}
````{tab-item} uv
```bash
# With Litestar integration
uv add debug-toolbar[litestar]

# With Starlette integration
uv add debug-toolbar[starlette]

# With FastAPI integration
uv add debug-toolbar[fastapi]

# With Advanced-Alchemy SQLAlchemy panel
uv add debug-toolbar[advanced-alchemy]

# Everything
uv add debug-toolbar[all]
```
````

````{tab-item} pip
```bash
# With Litestar integration
pip install debug-toolbar[litestar]

# With Starlette integration
pip install debug-toolbar[starlette]

# With FastAPI integration
pip install debug-toolbar[fastapi]

# With Advanced-Alchemy SQLAlchemy panel
pip install debug-toolbar[advanced-alchemy]

# Everything
pip install debug-toolbar[all]
```
````

````{tab-item} pdm
```bash
# With Litestar integration
pdm add debug-toolbar[litestar]

# With Starlette integration
pdm add debug-toolbar[starlette]

# With FastAPI integration
pdm add debug-toolbar[fastapi]

# With Advanced-Alchemy SQLAlchemy panel
pdm add debug-toolbar[advanced-alchemy]

# Everything
pdm add debug-toolbar[all]
```
````

````{tab-item} poetry
```bash
# With Litestar integration
poetry add debug-toolbar[litestar]

# With Starlette integration
poetry add debug-toolbar[starlette]

# With FastAPI integration
poetry add debug-toolbar[fastapi]

# With Advanced-Alchemy SQLAlchemy panel
poetry add debug-toolbar[advanced-alchemy]

# Everything
poetry add debug-toolbar[all]
```
````
`````

---

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Getting Started
:link: getting-started
:link-type: doc

New to debug-toolbar? Start here for installation and your first integration.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc

Learn how to configure panels, themes, positioning, and behavior.
:::

:::{grid-item-card} Built-in Panels
:link: panels
:link-type: doc

Explore the built-in panels: Timer, Request, Response, SQL, Logging, and more.
:::

:::{grid-item-card} Creating Custom Panels
:link: custom-panels
:link-type: doc

Build your own debug panels with the extensible panel system.
:::

:::{grid-item-card} MCP Server (AI Integration)
:link: mcp
:link-type: doc

Let Claude Code analyze your debug data with the MCP server integration.
:::

:::{grid-item-card} Debug Toolbar Comparison
:link: comparison
:link-type: doc

See how debug-toolbar compares to Django, Flask, and FastAPI debug toolbars.
:::
::::

## Quick Start

::::{tab-set}
:::{tab-item} Litestar
```python
from litestar import Litestar, get
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

@get("/")
async def index() -> dict[str, str]:
    return {"message": "Hello, World!"}

config = LitestarDebugToolbarConfig(enabled=True)
app = Litestar(
    route_handlers=[index],
    plugins=[DebugToolbarPlugin(config)],
)
```
:::
:::{tab-item} FastAPI
```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from debug_toolbar.fastapi import setup_debug_toolbar, FastAPIDebugToolbarConfig

app = FastAPI()
config = FastAPIDebugToolbarConfig(enabled=True)
setup_debug_toolbar(app, config)

@app.get("/", response_class=HTMLResponse)
async def index():
    return "<html><body><h1>Hello World</h1></body></html>"
```
:::
:::{tab-item} Starlette
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
    routes=[Route("/", homepage), *create_debug_toolbar_routes(toolbar.storage)],
    middleware=[Middleware(DebugToolbarMiddleware, config=config, toolbar=toolbar)],
)
```
:::
::::

## Features

- **Async-Native**: Built from the ground up for async/await patterns
- **Multi-Framework Support**: Litestar, Starlette, and FastAPI integrations
- **Framework-Agnostic Core**: Works with any ASGI framework
- **FastAPI DI Tracking**: Monitor dependency injection resolution and caching
- **Pluggable Panels**: Easy to add, remove, or customize
- **Dark/Light Themes**: Toggle between themes
- **Flexible Positioning**: Left, right, top, or bottom
- **SQL Analysis**: EXPLAIN plans for PostgreSQL, SQLite, MySQL, MariaDB
- **N+1 Detection**: Automatic detection of N+1 query patterns with fix suggestions
- **Flame Graphs**: Interactive profiling visualization in speedscope format
- **Memory Profiling**: Multi-backend support (tracemalloc, memray)
- **Proactive Alerts**: Automatic security, performance, and database issue detection
- **Lifecycle Events**: Track Litestar hooks and exception handlers
- **MCP Server**: AI assistant integration for Claude Code analysis

## Screenshots

::::{grid} 1
:gutter: 2

:::{grid-item-card} Default View
:img-top: ../assets/toolbar-right-position.png
Right-side toolbar with all panels
:::

::::

::::{grid} 2
:gutter: 2

:::{grid-item-card} Top Position
:img-top: ../assets/toolbar-top-position.png
Full-width horizontal layout
:::

:::{grid-item-card} SQL Queries
:img-top: ../assets/toolbar-users-queries.png
Query tracking with EXPLAIN
:::

:::{grid-item-card} N+1 Detection
:img-top: ../assets/toolbar-n-plus-one-detection.png
Automatic N+1 query detection with fix suggestions
:::

:::{grid-item-card} Light Theme
:img-top: ../assets/toolbar-light-theme.png
Toggle dark/light themes
:::

:::{grid-item-card} Request History
:img-top: ../assets/toolbar-request-history.png
Browse past requests
:::

:::{grid-item-card} Events Panel
:img-top: ../assets/toolbar-events-panel.png
Lifecycle hooks and exception handlers
:::

:::{grid-item-card} Alerts Panel
:img-top: ../assets/panel-alerts-expanded.png
Proactive security and performance issue detection
:::

:::{grid-item-card} Memory Panel
:img-top: ../assets/panel-memory-expanded.png
Memory allocation tracking (tracemalloc/memray)
:::

:::{grid-item-card} SQL Panel
:img-top: ../assets/panel-sql-expanded.png
Query analysis with N+1 detection and EXPLAIN
:::

:::{grid-item-card} Profiling Panel
:img-top: ../assets/panel-profiling-expanded.png
cProfile with flame graph visualization
:::

::::

```{toctree}
:maxdepth: 2
:hidden:
:caption: Learn

getting-started
configuration
panels
custom-panels
mcp
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Reference

API Reference <api/index>
comparison
changelog
```

```{toctree}
:maxdepth: 1
:hidden:
:caption: Architecture

architecture/index
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
