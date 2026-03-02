# Configuration

## Base Configuration

The `DebugToolbarConfig` class provides the base configuration options:

```python
from debug_toolbar import DebugToolbarConfig

config = DebugToolbarConfig(
    enabled=True,                    # Enable/disable toolbar
    panels=[...],                    # List of panel classes
    intercept_redirects=False,       # Show intermediate page on redirects
    max_request_history=50,          # Requests to keep in history
    api_path="/_debug_toolbar",      # API endpoint prefix
    static_path="/_debug_toolbar/static",  # Static assets path
    allowed_hosts=[],                # Host whitelist (empty = all)
    extra_panels=[],                 # Additional panels
    exclude_panels=[],               # Panels to disable
)
```

## Litestar Configuration

`LitestarDebugToolbarConfig` extends the base config with Litestar-specific options:

```python
from debug_toolbar.litestar import LitestarDebugToolbarConfig

config = LitestarDebugToolbarConfig(
    # All base options, plus:
    exclude_paths=["/_debug_toolbar", "/static"],  # Paths to skip
    exclude_patterns=[r"^/api/v\d+/internal"],     # Regex patterns
    show_on_errors=True,                           # Show on 4xx/5xx
    show_toolbar_callback=None,                    # Custom visibility check
)
```

## Configuration Options

### `enabled`

**Type**: `bool`
**Default**: `True`

Master switch for the toolbar. When `False`, no middleware is added.

### `panels`

**Type**: `list[str | type[Panel]]`
**Default**: Built-in panels

List of panel classes or import paths. Default panels:

- `debug_toolbar.core.panels.timer.TimerPanel`
- `debug_toolbar.core.panels.request.RequestPanel`
- `debug_toolbar.core.panels.response.ResponsePanel`
- `debug_toolbar.core.panels.logging.LoggingPanel`
- `debug_toolbar.core.panels.versions.VersionsPanel`

### `extra_panels`

**Type**: `list[str | type[Panel]]`
**Default**: `[]`

Additional panels to add to the default set.

```python
config = LitestarDebugToolbarConfig(
    extra_panels=[
        "debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel",
        "myapp.panels.CustomPanel",
    ],
)
```

### `exclude_panels`

**Type**: `list[str]`
**Default**: `[]`

Panel names to exclude from the default set.

```python
config = LitestarDebugToolbarConfig(
    exclude_panels=["VersionsPanel", "LoggingPanel"],
)
```

### `exclude_paths`

**Type**: `list[str]`
**Default**: `["/_debug_toolbar", "/static", "/favicon.ico"]`

URL paths to exclude from toolbar processing. Uses prefix matching.

### `show_toolbar_callback`

**Type**: `Callable[[Request], bool] | None`
**Default**: `None`

Custom function to determine toolbar visibility:

```python
def should_show(request: Request) -> bool:
    # Only show for authenticated admins
    return request.user and request.user.is_admin

config = LitestarDebugToolbarConfig(
    show_toolbar_callback=should_show,
)
```

### `memory_backend`

**Type**: `Literal["tracemalloc", "memray", "auto"]`
**Default**: `"auto"`

Memory profiling backend selection:
- `"tracemalloc"`: Python's built-in memory tracer (always available)
- `"memray"`: Bloomberg's advanced profiler (requires `pip install memray`, Linux/macOS only)
- `"auto"`: Automatically selects best available backend

### `profiler_backend`

**Type**: `Literal["cprofile", "pyinstrument"]`
**Default**: `"cprofile"`

Profiling backend selection:
- `"cprofile"`: Python's built-in cProfile profiler (always available)
- `"pyinstrument"`: Statistical sampling profiler (requires `pip install pyinstrument`)

### `profiler_top_functions`

**Type**: `int`
**Default**: `50`

Maximum number of functions to display in the profiling panel.

### `profiler_sort_by`

**Type**: `str`
**Default**: `"cumulative"`

Sort order for profiling results. Common values:
- `"cumulative"`: Sort by cumulative time (time spent in function and sub-calls)
- `"tottime"`: Sort by total time (time spent in function only)
- `"calls"`: Sort by number of calls

### `enable_flamegraph`

**Type**: `bool`
**Default**: `True`

Enable flame graph generation for the profiling panel. When enabled, a speedscope-compatible JSON file is generated that can be visualized at [speedscope.app](https://www.speedscope.app/).

### `panel_display_depth`

**Type**: `int`
**Default**: `10`

Maximum depth for nested data rendering in panels.

### `panel_display_max_items`

**Type**: `int`
**Default**: `100`

Maximum items to show in arrays/objects before truncation.

### `panel_display_max_string`

**Type**: `int`
**Default**: `1000`

Maximum string length before truncation.

## Environment-Based Configuration

Common pattern for different environments:

```python
import os

config = LitestarDebugToolbarConfig(
    enabled=os.getenv("DEBUG", "false").lower() == "true",
    allowed_hosts=["localhost", "127.0.0.1"] if os.getenv("DEBUG") else [],
)
```
