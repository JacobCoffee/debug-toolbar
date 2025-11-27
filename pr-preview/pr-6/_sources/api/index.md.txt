# API Reference

Complete API documentation for all public classes and functions.

## Quick Navigation

**Core**

- {class}`~debug_toolbar.core.config.DebugToolbarConfig` - Base configuration
- {class}`~debug_toolbar.core.panel.Panel` - Panel base class
- {class}`~debug_toolbar.core.context.RequestContext` - Request context
- {class}`~debug_toolbar.core.toolbar.DebugToolbar` - Toolbar manager
- {class}`~debug_toolbar.core.storage.RequestStorage` - Request history storage

**Litestar Integration**

- {class}`~debug_toolbar.litestar.plugin.DebugToolbarPlugin` - Litestar plugin
- {class}`~debug_toolbar.litestar.config.LitestarDebugToolbarConfig` - Litestar config
- {class}`~debug_toolbar.litestar.middleware.DebugToolbarMiddleware` - ASGI middleware

**Panels**

- {class}`~debug_toolbar.core.panels.timer.TimerPanel` - Request timing
- {class}`~debug_toolbar.core.panels.request.RequestPanel` - Request info
- {class}`~debug_toolbar.core.panels.response.ResponsePanel` - Response info
- {class}`~debug_toolbar.core.panels.headers.HeadersPanel` - HTTP headers
- {class}`~debug_toolbar.core.panels.logging.LoggingPanel` - Log capture
- {class}`~debug_toolbar.core.panels.profiling.ProfilingPanel` - CPU profiling
- {class}`~debug_toolbar.extras.advanced_alchemy.panel.SQLAlchemyPanel` - SQL queries

## Module Reference

```{eval-rst}
.. autosummary::
   :toctree: _autosummary
   :recursive:

   debug_toolbar
```
