# ADR-001: Dual Package Architecture

## Status

Accepted

## Date

2025-11-26

## Context

We need to design a debug toolbar for async Python web applications, with initial support for Litestar. The key decisions involve:

1. **Package organization**: Single monolithic package vs. split core/plugin packages
2. **Framework coupling**: Tight integration vs. adapter pattern
3. **Async design**: Sync-first with async wrappers vs. async-native

### Requirements

- Support Litestar as primary framework
- Enable future support for other async frameworks (FastAPI, Starlette, Quart)
- Maintain clean separation between core functionality and framework integration
- Support optional SQLAlchemy/Advanced-Alchemy integration
- Minimize dependencies in core package

### Options Considered

#### Option 1: Monolithic Package

Single `litestar-debug-toolbar` package containing all functionality.

**Pros:**
- Simpler installation (`pip install litestar-debug-toolbar`)
- Single source of truth
- Easier maintenance

**Cons:**
- Framework-specific code mixed with generic code
- Cannot reuse core for other frameworks
- Litestar becomes hard dependency

#### Option 2: Dual Package with Shared Core

Two packages:
- `async-debug-toolbar`: Framework-agnostic core
- `litestar-debug-toolbar`: Litestar-specific plugin

**Pros:**
- Clean separation of concerns
- Core reusable for other frameworks
- Framework is optional dependency
- Smaller core package

**Cons:**
- More complex installation
- Two packages to maintain
- Version coordination required

#### Option 3: Plugin Architecture with Core

Single `async-debug-toolbar` package with optional extras:

```
pip install async-debug-toolbar[litestar]
pip install async-debug-toolbar[fastapi]
```

**Pros:**
- Single package to install
- Framework as optional extra
- Clear extension pattern

**Cons:**
- All code in one repo (could grow large)
- Plugin code shipped even if unused
- Namespace management complexity

## Decision

We will implement **Option 2: Dual Package with Shared Core**.

### Package Structure

```
async-debug-toolbar/              # Core package
  - Panel base classes
  - Configuration system
  - Storage backend
  - Template engine
  - Built-in panels
  - Abstract ASGI adapter

litestar-debug-toolbar/           # Plugin package
  - LitestarDebugToolbarPlugin
  - LitestarDebugToolbarMiddleware
  - LitestarAdapter (implements abstract adapter)
  - Litestar-specific panels
```

### Dependency Flow

```
litestar-debug-toolbar
    └── depends on: async-debug-toolbar>=1.0
    └── depends on: litestar>=2.0

async-debug-toolbar
    └── depends on: jinja2>=3.1
    └── optional[advanced-alchemy]: advanced-alchemy>=0.10
```

## Consequences

### Positive

1. **Framework Independence**: Core can be used as foundation for FastAPI, Starlette, Quart, etc.
2. **Minimal Dependencies**: Core has only Jinja2 as dependency
3. **Clear Boundaries**: Framework-specific code isolated in plugin package
4. **Testing Isolation**: Core tests don't require Litestar
5. **Versioning Flexibility**: Can release core and plugin independently

### Negative

1. **Installation Complexity**: Users install two packages (mitigated by `pip install litestar-debug-toolbar` which pulls in core)
2. **Cross-Package Changes**: Some changes require coordinated releases
3. **Documentation Split**: Must document both packages clearly

### Neutral

1. **Monorepo vs. Multi-repo**: We'll use a monorepo with both packages for easier development, but publish as separate PyPI packages

## Implementation Notes

### Core Package (`async-debug-toolbar`)

```toml
[project]
name = "async-debug-toolbar"
dependencies = ["jinja2>=3.1", "markupsafe>=2.1"]

[project.optional-dependencies]
advanced-alchemy = ["advanced-alchemy>=0.10", "sqlalchemy>=2.0"]
```

### Plugin Package (`litestar-debug-toolbar`)

```toml
[project]
name = "litestar-debug-toolbar"
dependencies = ["async-debug-toolbar>=1.0", "litestar>=2.0"]
```

### Abstract Adapter Pattern

The core defines an abstract `ASGIAdapter` that framework plugins implement:

```python
# async_debug_toolbar/adapters/base.py
class ASGIAdapter(ABC):
    @abstractmethod
    def get_routes(self) -> list[dict]: ...

    @abstractmethod
    def should_inject_toolbar(self, ...) -> bool: ...

    @abstractmethod
    def inject_toolbar(self, ...) -> bytes: ...
```

Framework plugins provide concrete implementations:

```python
# litestar_debug_toolbar/adapter.py
class LitestarAdapter(ASGIAdapter):
    def __init__(self, app: Litestar): ...
    def get_routes(self) -> list[dict]:
        # Litestar-specific route extraction
        ...
```

## Related Decisions

- ADR-002: Panel Architecture (TBD)
- ADR-003: Storage Backend Selection (TBD)
- ADR-004: Security Model (TBD)

## References

- [Django Debug Toolbar Architecture](https://django-debug-toolbar.readthedocs.io/)
- [FastAPI Debug Toolbar](https://github.com/mongkok/fastapi-debug-toolbar)
- [Flask Debug Toolbar](https://flask-debugtoolbar.readthedocs.io/)
- [Litestar Middleware Documentation](https://docs.litestar.dev/latest/usage/middleware/)
- [Litestar Plugin Documentation](https://docs.litestar.dev/latest/usage/plugins/)
