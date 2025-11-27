# Async Python Debug Toolbar

[![CI](https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/ci.yml/badge.svg)](https://github.com/JacobCoffee/async-python-debug-toolbar/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/async-debug-toolbar.svg)](https://badge.fury.io/py/async-debug-toolbar)
[![Python Version](https://img.shields.io/pypi/pyversions/async-debug-toolbar)](https://pypi.org/project/async-debug-toolbar/)
[![License](https://img.shields.io/github/license/JacobCoffee/async-python-debug-toolbar)](https://github.com/JacobCoffee/async-python-debug-toolbar/blob/main/LICENSE)

An async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.

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
pip install async-debug-toolbar

# With Litestar integration
pip install async-debug-toolbar[litestar]

# With Advanced-Alchemy SQLAlchemy panel
pip install async-debug-toolbar[advanced-alchemy]

# Everything
pip install async-debug-toolbar[all]
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add async-debug-toolbar[litestar]
```

## Quick Start

### Litestar

```python
from litestar import Litestar, get
from litestar_debug_toolbar import DebugToolbarPlugin, LitestarDebugToolbarConfig

@get("/")
async def index() -> dict[str, str]:
    return {"message": "Hello, World!"}

config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/health", "/metrics"],
)

app = Litestar(
    route_handlers=[index],
    plugins=[DebugToolbarPlugin(config)],
)
```

### Generic ASGI (Coming Soon)

```python
from async_debug_toolbar import DebugToolbar, DebugToolbarConfig

config = DebugToolbarConfig(enabled=True)
toolbar = DebugToolbar(config)

# Use with your ASGI framework's middleware system
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

## Configuration Options

```python
from litestar_debug_toolbar import LitestarDebugToolbarConfig

config = LitestarDebugToolbarConfig(
    # Enable/disable the toolbar
    enabled=True,

    # Paths to exclude from toolbar processing
    exclude_paths=["/_debug_toolbar", "/static", "/health"],

    # Maximum requests to keep in history
    max_request_history=50,

    # Whether to intercept redirects
    intercept_redirects=False,

    # Custom callback to determine if toolbar should show
    show_toolbar_callback=lambda request: request.app.debug,

    # Additional panels to include
    extra_panels=["myapp.panels.CustomPanel"],

    # Panels to exclude from defaults
    exclude_panels=["VersionsPanel"],
)
```

## Creating Custom Panels

```python
from async_debug_toolbar.panel import Panel
from async_debug_toolbar.context import RequestContext
from typing import Any, ClassVar

class MyCustomPanel(Panel):
    panel_id: ClassVar[str] = "MyCustomPanel"
    title: ClassVar[str] = "My Panel"
    template: ClassVar[str] = "panels/my_panel.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        return {
            "custom_data": "Your debug information here",
            "metrics": calculate_metrics(),
        }
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

## Architecture

This project uses a dual-package architecture:

- **async-debug-toolbar**: Framework-agnostic core with panels, storage, and context management
- **litestar-debug-toolbar**: Thin integration layer providing Litestar plugin and middleware

See [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) for detailed design documentation.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.rst](CONTRIBUTING.rst) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgements

Inspired by:
- [django-debug-toolbar](https://github.com/django-commons/django-debug-toolbar)
- [flask-debugtoolbar](https://github.com/pallets-eco/flask-debugtoolbar)
- [fastapi-debug-toolbar](https://github.com/mongkok/fastapi-debug-toolbar)
