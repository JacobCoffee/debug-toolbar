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
