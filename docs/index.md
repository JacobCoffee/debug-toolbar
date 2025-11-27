# Debug Toolbar

An async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.

## Screenshots

```{image} ../assets/toolbar-right-position.png
:alt: Debug Toolbar
:width: 100%
```

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

:::{grid-item-card} Light Theme
:img-top: ../assets/toolbar-light-theme.png
Toggle dark/light themes
:::

:::{grid-item-card} Request History
:img-top: ../assets/toolbar-request-history.png
Browse past requests
:::

::::

## Key Features

- **Async-Native**: Built from the ground up for async/await patterns
- **Framework-Agnostic Core**: Works with any ASGI framework
- **Litestar Integration**: First-class plugin support
- **Pluggable Panels**: Easy to add, remove, or customize
- **Dark/Light Themes**: Toggle between themes
- **Flexible Positioning**: Left, right, top, or bottom
- **SQL Analysis**: EXPLAIN plans for PostgreSQL, SQLite, MySQL, MariaDB

## Quick Start

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

## Installation

```bash
pip install debug-toolbar[litestar]

# With SQLAlchemy panel
pip install debug-toolbar[advanced-alchemy]

# Everything
pip install debug-toolbar[all]
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Learn

getting-started
configuration
panels
custom-panels
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Reference

API Reference <api/index>
comparison
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
