# ADR-002: Panel System Design

## Status

Accepted

## Date

2025-11-26

## Context

The debug toolbar needs an extensible panel system that allows:

1. Built-in panels for common debugging needs
2. Framework-specific panels (e.g., Litestar routes)
3. Third-party panels (e.g., SQLAlchemy, Redis, custom business logic)
4. Easy panel development by end users

### Requirements

- Panels must have a clear lifecycle aligned with request/response
- Panels must be able to collect data during request processing
- Panels must support both sync and async operations
- Panels should be loadable via string paths for configuration
- Panels must render their own content via templates

### Options Considered

#### Option 1: Callback-Based Panels

```python
def timer_panel(request, response):
    return {"start": ..., "end": ...}
```

**Pros:** Simple, functional style
**Cons:** Limited lifecycle control, no state management

#### Option 2: Protocol-Based Panels

```python
class Panel(Protocol):
    panel_id: str
    def process_request(self, scope): ...
    def process_response(self, scope, status, headers, body): ...
```

**Pros:** Type-safe, flexible implementation
**Cons:** Less discoverable, no inheritance benefits

#### Option 3: Abstract Base Class

```python
class Panel(ABC):
    panel_id: ClassVar[str]
    title: ClassVar[str]
    template: ClassVar[str]

    @abstractmethod
    async def generate_stats(self) -> dict: ...
```

**Pros:** Clear contract, inheritance for shared behavior
**Cons:** More rigid, requires class definition

## Decision

We will implement **Option 3: Abstract Base Class** with the following design:

### Panel Lifecycle

```
__init__(toolbar, config)     # Once per toolbar instance
    │
    ▼
process_request(scope)        # Called at request start
    │
    ▼
[Application processing]
    │
    ▼
process_response(...)         # Called after response
    │
    ▼
generate_stats()              # Compute final statistics
    │
    ▼
record_stats(stats)           # Store in request context
```

### Base Panel Class

```python
class Panel(ABC):
    # Class-level configuration (override in subclasses)
    panel_id: ClassVar[str]
    title: ClassVar[str]
    template: ClassVar[str]
    default_enabled: ClassVar[bool] = True
    weight: ClassVar[int] = 100  # For ordering
    scripts: ClassVar[list[str]] = []
    styles: ClassVar[list[str]] = []

    def __init__(self, toolbar: DebugToolbar, config: DebugToolbarConfig) -> None:
        self._toolbar = toolbar
        self._config = config

    @property
    def enabled(self) -> bool:
        """Check panel_options for runtime enable/disable."""
        ...

    async def process_request(self, scope: dict) -> None:
        """Optional: Collect request data."""
        pass

    async def process_response(self, scope, status, headers, body) -> None:
        """Optional: Collect response data."""
        pass

    @abstractmethod
    async def generate_stats(self) -> dict[str, Any]:
        """Required: Return statistics dictionary."""
        ...

    def generate_server_timing(self) -> str | None:
        """Optional: Contribute to Server-Timing header."""
        return None

    def record_stats(self, stats: dict) -> None:
        """Store stats in request context."""
        ...

    def get_stats(self) -> dict:
        """Retrieve stored stats."""
        ...

    @property
    def nav_title(self) -> str:
        """Title for toolbar navigation."""
        return self.title

    @property
    def nav_subtitle(self) -> str:
        """Subtitle (e.g., timing) for navigation."""
        return ""
```

### Panel Registration

Panels are registered via configuration:

```python
config = DebugToolbarConfig(
    panels=[
        "async_debug_toolbar.panels.timer.TimerPanel",
        "async_debug_toolbar.panels.request.RequestPanel",
        "myapp.panels.CustomPanel",
    ],
    panel_options={
        "timer": {"enabled": True},
        "custom": {"my_option": "value"},
    },
)
```

### Dynamic Loading

Panels are loaded from dotted paths at toolbar initialization:

```python
@lru_cache(maxsize=64)
def _load_panel_class(panel_path: str) -> type[Panel]:
    module_path, class_name = panel_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)
```

## Consequences

### Positive

1. **Clear Contract**: Abstract base class defines expected interface
2. **Shared Behavior**: Common methods like `record_stats` implemented once
3. **Type Safety**: Full type hints with ClassVar for class-level config
4. **Discoverability**: IDEs can show all overridable methods
5. **Lifecycle Control**: Explicit hooks for request/response phases
6. **Async Native**: All lifecycle methods are async

### Negative

1. **Inheritance Lock-in**: Must subclass Panel (no duck typing)
2. **Boilerplate**: Requires class definition even for simple panels
3. **ClassVar Complexity**: Class-level vs instance-level attributes can confuse

### Mitigations

1. Provide a `SimplePanel` helper for trivial cases:

```python
class SimplePanel(Panel):
    """Base for panels that only need generate_stats."""

    async def process_request(self, scope): pass
    async def process_response(self, *args): pass

    # Subclass only needs to implement generate_stats
```

2. Document the distinction between ClassVar and instance attributes clearly

## Built-in Panels

| Panel | panel_id | Purpose | Weight |
|-------|----------|---------|--------|
| TimerPanel | timer | Request timing | 10 |
| RequestPanel | request | Headers, query params | 20 |
| ResponsePanel | response | Status, headers, body | 30 |
| LoggingPanel | logging | Captured logs | 40 |
| SQLAlchemyPanel | sqlalchemy | DB queries | 50 |
| VersionsPanel | versions | Python/packages | 100 |
| RoutesPanel | routes | Available routes | 80 |
| ProfilingPanel | profiling | cProfile data | 90 |

## Template Convention

Each panel provides a Jinja2 template:

```
templates/
  panels/
    timer.html
    request.html
    response.html
    ...
```

Template receives:
- `panel`: Panel instance
- `stats`: Result of `generate_stats()`

Example:

```html
<!-- panels/timer.html -->
<div class="panel-content">
  <h3>Request Timing</h3>
  <dl>
    <dt>Total Time</dt>
    <dd>{{ stats.total_time_ms|format_duration }}</dd>
  </dl>
</div>
```

## References

- Django Debug Toolbar Panel API
- Flask Debug Toolbar Panel class
- FastAPI Debug Toolbar Panel implementation
