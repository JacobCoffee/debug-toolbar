# Async Debug Toolbar

An async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.

## Screenshots

```{image} ../assets/toolbar-right-position.png
:alt: Debug Toolbar - Right Position
:width: 100%
```

````{dropdown} More Screenshots
:open:

### Full-Width Top Position
```{image} ../assets/toolbar-top-position.png
:alt: Debug Toolbar - Top Position
:width: 100%
```

### SQL Queries with EXPLAIN
```{image} ../assets/toolbar-users-queries.png
:alt: Debug Toolbar - SQL Queries
:width: 100%
```

### EXPLAIN Query Plan Modal
```{image} ../assets/toolbar-explain-modal.png
:alt: Debug Toolbar - EXPLAIN Modal
:width: 100%
```

### Light Theme
```{image} ../assets/toolbar-light-theme.png
:alt: Debug Toolbar - Light Theme
:width: 100%
```

### Request History
```{image} ../assets/toolbar-request-history.png
:alt: Debug Toolbar - Request History
:width: 100%
```
````

```{toctree}
:maxdepth: 2
:caption: Contents

getting-started
configuration
panels
custom-panels
```

```{toctree}
:maxdepth: 1
:caption: API Reference

api/index
```

```{toctree}
:maxdepth: 1
:caption: Architecture

architecture/ARCHITECTURE
architecture/adr/ADR-001-dual-package-architecture
architecture/adr/ADR-002-panel-system-design
architecture/adr/ADR-003-storage-and-context
```

## Features

- **Async-Native**: Built from the ground up for async/await patterns
- **Framework-Agnostic Core**: Core package works with any ASGI framework
- **Litestar Integration**: First-class plugin support for Litestar applications
- **Pluggable Panels**: Easy to add, remove, or customize debug panels
- **Minimal Overhead**: Negligible performance impact when disabled
- **Type-Safe**: Full type annotations with strict type checking
- **Dark/Light Themes**: Toggle between dark and light themes
- **Flexible Positioning**: Place toolbar on any edge (left, right, top, bottom)
- **SQL Query Analysis**: EXPLAIN query plans for PostgreSQL, SQLite, MySQL, MariaDB

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
# Core package only
pip install debug-toolbar

# With Litestar integration
pip install debug-toolbar[litestar]

# With Advanced-Alchemy SQLAlchemy panel
pip install debug-toolbar[advanced-alchemy]

# Everything
pip install debug-toolbar[all]
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
