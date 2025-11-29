# Built-in Panels

## Timer Panel

**ID**: `TimerPanel`

Displays request timing information:

- Total request duration
- CPU time (user + system)
- Server-Timing header data

## Request Panel

**ID**: `RequestPanel`

Shows incoming request details:

- HTTP method and path
- Query parameters
- Headers
- Cookies
- Client information

## Response Panel

**ID**: `ResponsePanel`

Displays response information:

- Status code
- Response headers
- Content type
- Content length

## Logging Panel

**ID**: `LoggingPanel`

Captures log records during the request:

- Log level
- Logger name
- Message
- Source location
- Error/warning counts

## Versions Panel

**ID**: `VersionsPanel`

Shows environment information:

- Python version
- Platform details
- Installed packages

## Routes Panel (Litestar)

**ID**: `RoutesPanel`

Litestar-specific panel showing:

- All registered routes
- HTTP methods
- Handler names
- Current matched route

## Events Panel (Litestar)

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

## SQLAlchemy Panel (Extra)

**ID**: `SQLAlchemyPanel`

Requires `debug-toolbar[advanced-alchemy]`:

- Query count
- Total query time
- Individual query details
- Duplicate query detection
- Slow query highlighting

Enable in config:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel"],
)
```
