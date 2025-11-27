# debug-toolbar

<p align="center">
  <em>Async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.</em>
</p>

<p align="center">
  <a href="https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/ci.yml">
    <img src="https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/ci.yml/badge.svg" alt="Tests And Linting">
  </a>
  <a href="https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/publish.yml">
    <img src="https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/publish.yml/badge.svg" alt="Latest Release">
  </a>
  <a href="https://pypi.org/project/debug-toolbar/">
    <img src="https://img.shields.io/pypi/v/debug-toolbar.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/debug-toolbar/">
    <img src="https://img.shields.io/pypi/pyversions/debug-toolbar.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/JacobCoffee/async-python-debug-toolbar/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/JacobCoffee/async-python-debug-toolbar.svg" alt="License">
  </a>
</p>

---

**Documentation**: [https://jacobcoffee.github.io/async-python-debug-toolbar](https://jacobcoffee.github.io/async-python-debug-toolbar)

**Source Code**: [https://github.com/JacobCoffee/async-python-debug-toolbar](https://github.com/JacobCoffee/async-python-debug-toolbar)

---

## Features

- **Async-Native**: Built from the ground up for async/await patterns
- **Framework-Agnostic Core**: Core package works with any ASGI framework
- **Litestar Integration**: First-class plugin support for Litestar applications
- **Pluggable Panels**: Easy to add, remove, or customize debug panels
- **Minimal Overhead**: Negligible performance impact when disabled
- **Type-Safe**: Full type annotations with strict type checking

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
| **Routes** | Application routes (Litestar-specific) |
| **SQLAlchemy** | Query tracking (requires `advanced-alchemy` extra) |

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
git clone https://github.com/JacobCoffee/async-python-debug-toolbar.git
cd async-python-debug-toolbar

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
│   ├── panels/     # Built-in panels (timer, request, response, logging, versions)
│   ├── config.py   # DebugToolbarConfig
│   ├── context.py  # RequestContext (contextvars-based)
│   ├── panel.py    # Panel base class
│   ├── storage.py  # LRU request history storage
│   └── toolbar.py  # DebugToolbar manager
├── litestar/       # Litestar integration
│   ├── panels/     # Litestar-specific panels (routes)
│   ├── config.py   # LitestarDebugToolbarConfig
│   ├── middleware.py
│   └── plugin.py   # DebugToolbarPlugin
└── extras/         # Optional integrations
    └── advanced_alchemy/  # SQLAlchemy panel
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
