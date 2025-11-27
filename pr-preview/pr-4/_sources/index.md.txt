# Async Debug Toolbar

An async-native debug toolbar for Python ASGI frameworks with first-class Litestar support.

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
