# API Reference

Complete API documentation for debug-toolbar.

## Core

### Configuration

```{eval-rst}
.. py:class:: debug_toolbar.core.config.DebugToolbarConfig

   Base configuration for the debug toolbar.

   :param enabled: Enable/disable the toolbar (default: True)
   :type enabled: bool
   :param exclude_paths: Paths to exclude from toolbar (default: ["/_debug_toolbar", "/static"])
   :type exclude_paths: list[str]
   :param max_request_history: Maximum requests to store (default: 50)
   :type max_request_history: int
   :param panels: List of panel class paths to enable
   :type panels: list[str]
   :param extra_panels: Additional panels to add
   :type extra_panels: list[str]
   :param exclude_panels: Panels to exclude
   :type exclude_panels: list[str]
```

### Panel Base Class

```{eval-rst}
.. py:class:: debug_toolbar.core.panel.Panel

   Base class for debug toolbar panels.

   :cvar panel_id: Unique identifier for the panel
   :cvar title: Display title
   :cvar template: Template name for rendering
   :cvar has_content: Whether panel has expandable content

   .. py:method:: generate_stats(context: RequestContext) -> dict[str, Any]
      :async:

      Generate statistics for this panel.

   .. py:method:: generate_server_timing(context: RequestContext) -> str

      Generate Server-Timing header value.
```

### Request Context

```{eval-rst}
.. py:class:: debug_toolbar.core.context.RequestContext

   Request-scoped context using contextvars.

   :param request_id: Unique request identifier
   :type request_id: UUID
   :param start_time: Request start timestamp
   :type start_time: float

   .. py:method:: get_current() -> RequestContext | None
      :classmethod:

      Get the current request context.

   .. py:method:: set_current(context: RequestContext) -> None
      :classmethod:

      Set the current request context.
```

### Storage

```{eval-rst}
.. py:class:: debug_toolbar.core.storage.RequestStorage

   LRU storage for request history.

   :param max_size: Maximum number of requests to store
   :type max_size: int

   .. py:method:: store(request_id: UUID, data: dict) -> None

      Store request data.

   .. py:method:: get(request_id: UUID) -> dict | None

      Retrieve request data by ID.

   .. py:method:: list_requests() -> list[dict]

      List all stored requests (newest first).
```

## Litestar Integration

### Plugin

```{eval-rst}
.. py:class:: debug_toolbar.litestar.plugin.DebugToolbarPlugin

   Litestar plugin for the debug toolbar.

   :param config: Toolbar configuration
   :type config: LitestarDebugToolbarConfig

   **Example:**

   .. code-block:: python

      from litestar import Litestar
      from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

      config = LitestarDebugToolbarConfig(enabled=True)
      app = Litestar(plugins=[DebugToolbarPlugin(config)])
```

### Configuration

```{eval-rst}
.. py:class:: debug_toolbar.litestar.config.LitestarDebugToolbarConfig

   Litestar-specific configuration extending DebugToolbarConfig.

   :param show_toolbar_callback: Callable to determine if toolbar should show
   :type show_toolbar_callback: Callable[[Request], bool] | None
   :param intercept_redirects: Intercept redirects to show toolbar
   :type intercept_redirects: bool
```

### Middleware

```{eval-rst}
.. py:class:: debug_toolbar.litestar.middleware.DebugToolbarMiddleware

   ASGI middleware that injects the toolbar into HTML responses.
```

## Built-in Panels

### Timer Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.timer.TimerPanel

   Displays request timing information.

   **Stats:**

   - ``total_time``: Total request duration (ms)
   - ``user_cpu_time``: User CPU time
   - ``system_cpu_time``: System CPU time
```

### Request Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.request.RequestPanel

   Displays HTTP request information.

   **Stats:**

   - ``method``: HTTP method
   - ``path``: Request path
   - ``query_params``: Query string parameters
   - ``headers``: Request headers
   - ``cookies``: Request cookies
```

### Response Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.response.ResponsePanel

   Displays HTTP response information.

   **Stats:**

   - ``status_code``: Response status
   - ``headers``: Response headers
   - ``content_length``: Response size
```

### Headers Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.headers.HeadersPanel

   Categorized display of HTTP headers with security analysis.

   **Categories:**

   - Security headers (CSP, HSTS, X-Frame-Options)
   - Caching headers
   - CORS headers
   - Authentication headers (redacted)
```

### Logging Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.logging.LoggingPanel

   Captures log records during request processing.

   **Stats:**

   - ``records``: List of log records with level, message, timestamp
```

### Profiling Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.profiling.ProfilingPanel

   CPU profiling with cProfile or pyinstrument.

   :cvar profiler_backend: "cprofile" or "pyinstrument"
```

### Alerts Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.alerts.AlertsPanel

   Proactive issue detection panel.

   **Detection Categories:**

   - Security: Missing headers, insecure cookies, CSRF issues
   - Performance: Large responses, slow queries
   - Database: N+1 patterns, query optimization
   - Configuration: Debug mode in production

   **Stats:**

   - ``alerts``: List of detected alerts with severity and suggestions
   - ``total_alerts``: Total alert count
   - ``by_severity``: Counts by severity level
   - ``by_category``: Counts by category
```

### Memory Panel

```{eval-rst}
.. py:class:: debug_toolbar.core.panels.memory.MemoryPanel

   Memory profiling with multiple backend support.

   **Backends:**

   - ``tracemalloc``: Built-in Python tracer (default)
   - ``memray``: Advanced profiler (Linux/macOS, requires install)

   **Stats:**

   - ``memory_before``: Memory at request start
   - ``memory_after``: Memory at request end
   - ``memory_delta``: Memory change during request
   - ``top_allocations``: Largest allocations by file/line
```

### SQLAlchemy Panel

```{eval-rst}
.. py:class:: debug_toolbar.extras.advanced_alchemy.panel.SQLAlchemyPanel

   Tracks SQLAlchemy queries with timing and EXPLAIN support.

   **Stats:**

   - ``queries``: List of executed queries
   - ``total_queries``: Query count
   - ``total_time``: Total query time
   - ``duplicate_queries``: Detected duplicate queries
   - ``n_plus_one_groups``: Detected N+1 query patterns

   **Features:**

   - Query timing
   - Parameter display
   - Duplicate detection
   - N+1 query detection with fix suggestions
   - EXPLAIN query plans (PostgreSQL, SQLite, MySQL, MariaDB)
```

## Litestar-Specific Panels

### Routes Panel

```{eval-rst}
.. py:class:: debug_toolbar.litestar.panels.routes.RoutesPanel

   Displays all registered routes in the Litestar application.

   **Stats:**

   - ``routes``: List of all routes with methods and handlers
   - ``current_route``: The matched route for this request
```

### Events Panel

```{eval-rst}
.. py:class:: debug_toolbar.litestar.panels.events.EventsPanel

   Tracks Litestar lifecycle events and hooks.

   **Stats:**

   - ``lifecycle_hooks``: on_startup, on_shutdown handlers
   - ``request_hooks``: before_request, after_request, after_response handlers
   - ``exception_handlers``: Registered exception handlers
   - ``executed_hooks``: Hooks that ran during this request
```

## Module Reference

```{eval-rst}
.. autosummary::
   :toctree: _autosummary

   debug_toolbar.core.config
   debug_toolbar.core.panel
   debug_toolbar.core.context
   debug_toolbar.core.storage
   debug_toolbar.core.toolbar
   debug_toolbar.core.panels
   debug_toolbar.litestar.plugin
   debug_toolbar.litestar.config
   debug_toolbar.litestar.middleware
   debug_toolbar.litestar.panels
```
