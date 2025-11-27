# Getting Started

## Installation

Install with your preferred package manager:

::::{tab-set}
:::{tab-item} pip
```bash
pip install debug-toolbar[litestar]
```
:::
:::{tab-item} uv
```bash
uv add debug-toolbar[litestar]
```
:::
:::{tab-item} poetry
```bash
poetry add debug-toolbar[litestar]
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
