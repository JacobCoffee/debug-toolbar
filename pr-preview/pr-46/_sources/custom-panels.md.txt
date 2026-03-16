# Creating Custom Panels

## Basic Panel Structure

Create a custom panel by subclassing `Panel`:

```python
from typing import Any, ClassVar
from debug_toolbar.core.panel import Panel
from debug_toolbar.core.context import RequestContext

class MyPanel(Panel):
    panel_id: ClassVar[str] = "MyPanel"
    title: ClassVar[str] = "My Custom Panel"
    template: ClassVar[str] = "panels/my_panel.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Custom"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        return {
            "custom_data": "Hello from my panel!",
            "timestamp": time.time(),
        }
```

## Panel Lifecycle

Panels have three main lifecycle methods:

### `process_request`

Called at the start of request processing:

```python
async def process_request(self, context: RequestContext) -> None:
    # Initialize tracking, start timers, etc.
    self._start_time = time.perf_counter()
```

### `generate_stats`

Called to collect data for the panel:

```python
async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
    return {
        "duration": time.perf_counter() - self._start_time,
        "items_processed": len(self._items),
    }
```

### `process_response`

Called at the end of request processing:

```python
async def process_response(self, context: RequestContext) -> None:
    # Cleanup, finalize data
    self._items.clear()
```

## Using Request Context

The `RequestContext` stores data for the current request:

```python
async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
    # Access request metadata
    method = context.metadata.get("method", "")
    path = context.metadata.get("path", "")

    # Access timing data
    total_time = context.get_timing("total_time")

    # Store panel-specific data
    context.store_panel_data(self.panel_id, "my_key", "my_value")

    return {"method": method, "path": path}
```

## Server-Timing Integration

Add data to the Server-Timing header:

```python
def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
    stats = self.get_stats(context)
    return {
        "custom": stats.get("duration", 0),
    }
```

## Registering Custom Panels

Add your panel via configuration:

```python
config = LitestarDebugToolbarConfig(
    extra_panels=["myapp.panels.MyPanel"],
)
```

Or directly as a class:

```python
from myapp.panels import MyPanel

config = LitestarDebugToolbarConfig(
    extra_panels=[MyPanel],
)
```
