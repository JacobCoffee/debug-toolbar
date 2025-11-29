# Built-in Panels

## Core Panels

### Timer Panel

**ID**: `TimerPanel`

Displays request timing information:

- Total request duration
- CPU time (user + system)
- Server-Timing header data

### Request Panel

**ID**: `RequestPanel`

Shows incoming request details:

- HTTP method and path
- Query parameters
- Headers
- Cookies
- Client information

### Response Panel

**ID**: `ResponsePanel`

Displays response information:

- Status code
- Response headers
- Content type
- Content length

### Logging Panel

**ID**: `LoggingPanel`

Captures log records during the request:

- Log level
- Logger name
- Message
- Source location
- Error/warning counts

### Versions Panel

**ID**: `VersionsPanel`

Shows environment information:

- Python version
- Platform details
- Installed packages

### Headers Panel

**ID**: `HeadersPanel`

Detailed HTTP header inspection with security analysis:

- Request headers categorized by type (content, caching, auth, CORS, etc.)
- Response headers with security analysis
- Missing security headers detection (CSP, X-Content-Type-Options, etc.)
- Cookie parsing and analysis
- Authorization header parsing (Basic, Bearer, etc.)
- Cache-Control directive breakdown

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.headers.HeadersPanel"],
)
```

### Settings Panel

**ID**: `SettingsPanel`

Application configuration viewer:

- Toolbar configuration settings
- App settings and environment
- Sensitive data redaction (passwords, secrets, API keys)
- Django-style settings support (when applicable)

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.settings.SettingsPanel"],
)
```

### Templates Panel

**ID**: `TemplatesPanel`

Template rendering tracking for Jinja2 and Mako:

- Template render times
- Template names and paths
- Context variables passed to templates
- Render count statistics

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.templates.TemplatesPanel"],
)
```

### Profiling Panel

**ID**: `ProfilingPanel`

Request profiling with flame graph visualization:

- cProfile-based request profiling
- Optional pyinstrument support
- Interactive flame graph generation (speedscope format)
- Function call statistics
- Cumulative and per-call timing

**Flame Graph Support**:

The profiling panel generates flame graphs in speedscope format. Access them via:

```
/_debug_toolbar/api/flamegraph/{request_id}
```

Download and visualize at [speedscope.app](https://www.speedscope.app/).

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.profiling.ProfilingPanel"],
)
```

### Alerts Panel

**ID**: `AlertsPanel`

Proactive issue detection panel that automatically identifies:

**Security Issues**:
- Missing security headers (CSP, X-Content-Type-Options, X-Frame-Options, etc.)
- Insecure cookies (missing Secure, HttpOnly, SameSite flags)
- CSRF protection issues on state-changing requests
- Debug mode enabled in production

**Performance Issues**:
- Large response sizes (warning at 1MB, critical at 10MB)
- Slow SQL queries (configurable threshold)

**Database Issues**:
- N+1 query pattern detection
- Excessive query counts from same code location
- Optimization suggestions

Each alert includes:
- Severity level (info, warning, critical)
- Category (security, performance, database, configuration)
- Actionable description

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.alerts.AlertsPanel"],
)
```

### Memory Panel

**ID**: `MemoryPanel`

Memory profiling and allocation tracking:

**Backends**:
- `tracemalloc`: Python's built-in memory tracer (default)
- `memray`: Advanced memory profiler (requires `pip install memray`)
- `auto`: Automatically selects the best available backend

**Features**:
- Memory allocation tracking per request
- Top allocations by size
- Memory snapshots comparison
- Peak memory usage
- Allocation source locations (file:line)

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.memory.MemoryPanel"],
    memory_backend="auto",  # "tracemalloc", "memray", or "auto"
)
```

### Cache Panel

**ID**: `CachePanel`

Redis and memcached operation tracking:

- Cache hits and misses
- Operation types (GET, SET, DELETE, etc.)
- Operation timing
- Key information
- Backend breakdown

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.cache.CachePanel"],
)
```

## Litestar-Specific Panels

### Routes Panel

**ID**: `RoutesPanel`

Litestar-specific panel showing:

- All registered routes
- HTTP methods
- Handler names
- Current matched route

*Automatically added for Litestar applications.*

### Events Panel

**ID**: `EventsPanel`

Litestar-specific panel showing lifecycle events and handlers:

- **Lifecycle hooks**: `on_startup`, `on_shutdown` handlers
- **Request hooks**: `before_request`, `after_request`, `after_response` handlers
- **Exception handlers**: Registered exception handlers with their exception types
- Handler function details (name, module, file location, line number)
- Total hook count and execution statistics

This panel helps you understand:
- What lifecycle hooks are registered in your application
- Which exception handlers are configured
- The source location of each handler for easy debugging

*Automatically added for Litestar applications.*

## Extra Panels

### SQLAlchemy Panel

**ID**: `SQLAlchemyPanel`

Requires `debug-toolbar[advanced-alchemy]`:

**Query Tracking**:
- Query count and total time
- Individual query details with SQL and parameters
- Duplicate query detection
- Slow query highlighting (configurable threshold)

**N+1 Query Detection**:
- Automatic detection of N+1 query patterns
- Groups similar queries by normalized SQL pattern and origin
- Shows call stack for each N+1 group
- Provides fix suggestions (eager loading, batching)
- Badges on affected queries (N+1, SLOW, DUP)

**EXPLAIN Support**:
- Execute EXPLAIN on any query
- Supports PostgreSQL, SQLite, MySQL, MariaDB
- View query execution plans

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel"],
)
```

## Recommended Configuration

For comprehensive debugging, enable all panels:

```python
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

config = LitestarDebugToolbarConfig(
    enabled=True,
    extra_panels=[
        "debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel",  # If using SQLAlchemy
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.core.panels.settings.SettingsPanel",
        "debug_toolbar.core.panels.templates.TemplatesPanel",
        "debug_toolbar.core.panels.profiling.ProfilingPanel",
        "debug_toolbar.core.panels.alerts.AlertsPanel",
        "debug_toolbar.core.panels.memory.MemoryPanel",
        "debug_toolbar.core.panels.cache.CachePanel",
    ],
)

app = Litestar(
    route_handlers=[...],
    plugins=[DebugToolbarPlugin(config)],
)
```
