# debug-toolbar

<p align="center">
  <em>Async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.</em>
</p>

<p align="center">
  <a href="https://github.com/JacobCoffee/debug-toolbar/actions/workflows/ci.yml">
    <img src="https://github.com/JacobCoffee/debug-toolbar/actions/workflows/ci.yml/badge.svg" alt="Tests And Linting">
  </a>
  <a href="https://github.com/JacobCoffee/debug-toolbar/actions/workflows/publish.yml">
    <img src="https://github.com/JacobCoffee/debug-toolbar/actions/workflows/publish.yml/badge.svg" alt="Latest Release">
  </a>
  <a href="https://pypi.org/project/debug-toolbar/">
    <img src="https://img.shields.io/pypi/v/debug-toolbar.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/debug-toolbar/">
    <img src="https://img.shields.io/pypi/pyversions/debug-toolbar.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/JacobCoffee/debug-toolbar/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/JacobCoffee/debug-toolbar.svg" alt="License">
  </a>
</p>

---

**Documentation**: [https://jacobcoffee.github.io/debug-toolbar](https://jacobcoffee.github.io/debug-toolbar)

**Source Code**: [https://github.com/JacobCoffee/debug-toolbar](https://github.com/JacobCoffee/debug-toolbar)

---

## Screenshots

<p align="center">
  <img src="assets/toolbar-right-position.png" alt="Debug Toolbar - Right Position" width="100%">
</p>

<details>
<summary>More Screenshots</summary>

### Full-Width Top Position
<img src="assets/toolbar-top-position.png" alt="Debug Toolbar - Top Position" width="100%">

### SQL Queries with EXPLAIN
<img src="assets/toolbar-users-queries.png" alt="Debug Toolbar - SQL Queries" width="100%">

### EXPLAIN Query Plan Modal
<img src="assets/toolbar-explain-modal.png" alt="Debug Toolbar - EXPLAIN Modal" width="100%">

### Light Theme
<img src="assets/toolbar-light-theme.png" alt="Debug Toolbar - Light Theme" width="100%">

### Request History
<img src="assets/toolbar-request-history.png" alt="Debug Toolbar - Request History" width="100%">

### Events Panel (Lifecycle Hooks)
<img src="assets/toolbar-events-panel.png" alt="Debug Toolbar - Events Panel" width="100%">

### N+1 Query Detection
<img src="assets/toolbar-n-plus-one-detection.png" alt="Debug Toolbar - N+1 Detection" width="100%">

### Alerts Panel (Proactive Issue Detection)
<img src="assets/panel-alerts-expanded.png" alt="Debug Toolbar - Alerts Panel" width="100%">

### MCP Integration (Claude Code)
<img src="assets/mcp-integration-example.png" alt="Debug Toolbar - MCP Integration with Claude Code" width="100%">

### Memory Panel
<img src="assets/panel-memory-expanded.png" alt="Debug Toolbar - Memory Panel" width="100%">

### SQL Panel with Query Analysis
<img src="assets/panel-sql-expanded.png" alt="Debug Toolbar - SQL Panel" width="100%">

### Profiling Panel
<img src="assets/panel-profiling-expanded.png" alt="Debug Toolbar - Profiling Panel" width="100%">

</details>

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
- **N+1 Detection**: Automatic detection of N+1 query patterns with fix suggestions
- **Flame Graphs**: Interactive profiling visualization in speedscope format
- **Memory Profiling**: Multi-backend support (tracemalloc, memray)
- **Proactive Alerts**: Automatic detection of security, performance, and database issues
- **MCP Integration**: AI assistant integration for automated debugging with Claude Code

## Installation

```bash
# Core package only
pip install debug-toolbar

# With Litestar integration
pip install debug-toolbar[litestar]

# With Advanced-Alchemy SQLAlchemy panel
pip install debug-toolbar[advanced-alchemy]

# All extras
pip install debug-toolbar[all]
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add debug-toolbar[litestar]
```

## Quick Start

### Litestar

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

### With SQLAlchemy (Advanced-Alchemy)

```python
from litestar import Litestar
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin, SQLAlchemyAsyncConfig
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

db_config = SQLAlchemyAsyncConfig(connection_string="sqlite+aiosqlite:///app.db")
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

### Generic ASGI

```python
from debug_toolbar import DebugToolbar, DebugToolbarConfig

config = DebugToolbarConfig(enabled=True)
toolbar = DebugToolbar(config)

# Wrap your ASGI app
app = toolbar.wrap(your_asgi_app)
```

## Built-in Panels

| Panel | Description |
|-------|-------------|
| **Timer** | Request timing and CPU time |
| **Request** | HTTP method, path, headers, cookies |
| **Response** | Status code, response headers |
| **Logging** | Log records captured during request |
| **Versions** | Python and package versions |
| **Headers** | Categorized headers with security analysis |
| **Settings** | Application configuration viewer |
| **Templates** | Jinja2/Mako render tracking |
| **Profiling** | cProfile/pyinstrument with flame graphs |
| **Alerts** | Proactive security/performance issue detection |
| **Memory** | Memory profiling (tracemalloc/memray) |
| **Cache** | Redis/memcached operation tracking |
| **Routes** | Application routes (Litestar-specific) |
| **Events** | Lifecycle hooks and exception handlers (Litestar-specific) |
| **SQLAlchemy** | Query tracking with N+1 detection (requires `advanced-alchemy` extra) |

## Configuration

```python
from debug_toolbar.litestar import LitestarDebugToolbarConfig

config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/static", "/health"],
    max_request_history=50,
    intercept_redirects=False,
    show_toolbar_callback=lambda request: request.app.debug,
    extra_panels=["myapp.panels.CustomPanel"],
    exclude_panels=["VersionsPanel"],
)
```

## Creating Custom Panels

```python
from typing import Any, ClassVar
from debug_toolbar.core import Panel, RequestContext

class MyCustomPanel(Panel):
    panel_id: ClassVar[str] = "MyCustomPanel"
    title: ClassVar[str] = "My Panel"
    template: ClassVar[str] = "panels/my_panel.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        return {"custom_data": "Your debug information here"}
```

## Development

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/debug-toolbar.git
cd debug-toolbar

# Install dependencies
make dev

# Run tests
make test

# Run all CI checks
make ci
```

## Package Structure

```
debug_toolbar/
├── core/           # Framework-agnostic core
│   ├── panels/     # Built-in panels
│   │   ├── timer.py, request.py, response.py  # Default panels
│   │   ├── headers.py, settings.py            # Optional panels
│   │   ├── profiling.py, memory/, alerts.py   # Advanced panels
│   │   └── templates.py, cache.py             # Integration panels
│   ├── config.py   # DebugToolbarConfig
│   ├── context.py  # RequestContext (contextvars-based)
│   ├── panel.py    # Panel base class
│   ├── storage.py  # LRU request history storage
│   └── toolbar.py  # DebugToolbar manager
├── litestar/       # Litestar integration
│   ├── panels/     # Litestar-specific panels (routes, events)
│   ├── config.py   # LitestarDebugToolbarConfig
│   ├── middleware.py
│   └── plugin.py   # DebugToolbarPlugin
└── extras/         # Optional integrations
    └── advanced_alchemy/  # SQLAlchemy panel with N+1 detection
```

## Versioning

This project uses [Semantic Versioning](https://semver.org/).

- Major versions introduce breaking changes
- Major versions support currently supported Litestar versions
- See the [Litestar Versioning Policy](https://litestar.dev/about/litestar-releases#version-numbering) for details

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.rst](CONTRIBUTING.rst) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgements

Inspired by:
- [django-debug-toolbar](https://github.com/django-commons/django-debug-toolbar)
- [flask-debugtoolbar](https://github.com/pallets-eco/flask-debugtoolbar)
- [fastapi-debug-toolbar](https://github.com/mongkok/fastapi-debug-toolbar)
