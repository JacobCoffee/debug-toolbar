# Debug Toolbar Comparison

A comprehensive comparison of debug-toolbar against other popular Python debug toolbars and observability tools.

## Quick Comparison Matrix

| Feature | debug-toolbar | Django Debug Toolbar | Flask Debug Toolbar | FastAPI Debug Toolbar | Sentry Spotlight |
|---------|---------------------------|---------------------|--------------------|--------------------|-----------------|
| **Async-First** | **Yes** | No (experimental) | No | Partial | Yes |
| **ASGI Native** | **Yes** | No (WSGI) | No (WSGI) | Yes | N/A |
| **Framework** | Litestar (+ agnostic core) | Django | Flask | FastAPI | Any (SDK-based) |
| **License** | MIT | BSD-3 | BSD-3 | BSD-3 | Apache-2.0 |

---

## Panel Comparison

### Core Debugging Panels

| Panel | Ours | Django | Flask | FastAPI | Spotlight |
|-------|:----:|:------:|:-----:|:-------:|:---------:|
| **Timer/Performance** | **Yes** | Yes | Yes | Yes | Yes |
| **Request Info** | **Yes** | Yes | Yes | Yes | Yes |
| **Response Info** | **Yes** | Partial | Partial | Partial | Yes |
| **Headers (categorized)** | **Yes** | Basic | Basic | Basic | Partial |
| **Logging** | **Yes** | No | Yes | Yes | **Yes** |
| **Versions** | **Yes** | Yes | Yes | No | No |
| **Routes** | **Yes** | No | Yes | No | No |
| **Settings/Config** | **Yes** | Yes | Yes | No | No |

### Database Panels

| Panel | Ours | Django | Flask | FastAPI | Spotlight |
|-------|:----:|:------:|:-----:|:-------:|:---------:|
| **SQLAlchemy** | **Yes** | No | Yes | Yes | Yes |
| **Django ORM** | No | **Yes** | No | No | Yes |
| **Tortoise ORM** | No | No | No | **Yes** | No |
| **SQL Query Timing** | **Yes** | Yes | Yes | Yes | Yes |
| **Query Parameters** | **Yes** | Yes | Yes | Yes | Yes |
| **Duplicate Detection** | **Yes** | No | No | No | No |
| **Slow Query Highlighting** | **Yes** | No | No | No | Yes |
| **EXPLAIN Plans** | **Yes** | **Yes** | No | No | Yes |
| **N+1 Detection** | **Yes** | No | No | No | Yes |

### Profiling & Performance

| Panel | Ours | Django | Flask | FastAPI | Spotlight |
|-------|:----:|:------:|:-----:|:-------:|:---------:|
| **cProfile** | **Yes** | Yes | Yes | No | No |
| **pyinstrument** | **Yes** | No | No | **Yes** | No |
| **Flame Graphs** | **Yes** | Plugin | No | No | No |
| **CPU Time (user/sys)** | **Yes** | Yes | Yes | No | No |
| **Server-Timing Header** | **Yes** | No | No | No | No |
| **Distributed Tracing** | No | No | No | No | **Yes** |

### Caching & Templates

| Panel | Ours | Django | Flask | FastAPI | Spotlight |
|-------|:----:|:------:|:-----:|:-------:|:---------:|
| **Redis Tracking** | **Yes** | Plugin | No | No | No |
| **Memcached Tracking** | **Yes** | Plugin | No | No | No |
| **Cache Hit/Miss Stats** | **Yes** | Yes | No | No | No |
| **Jinja2 Templates** | **Yes** | No | Yes | No | No |
| **Mako Templates** | **Yes** | No | No | No | No |
| **Django Templates** | No | **Yes** | No | No | No |
| **Template Editor** | No | No | **Yes** | No | No |

### Security & Headers

| Panel | Ours | Django | Flask | FastAPI | Spotlight |
|-------|:----:|:------:|:-----:|:-------:|:---------:|
| **Security Header Detection** | **Yes** | No | No | No | No |
| **CORS Analysis** | **Yes** | No | No | No | No |
| **Auth Header Redaction** | **Yes** | No | No | No | Yes |
| **Sensitive Data Redaction** | **Yes** | No | No | No | Yes |

### Advanced Features

| Feature | Ours | Django | Flask | FastAPI | Spotlight |
|---------|:----:|:------:|:-----:|:-------:|:---------:|
| **Request History** | **Yes** | Yes | No | No | **Yes** |
| **Snapshot Switching** | Basic | **Yes** | No | No | **Yes** |
| **GraphQL Support** | No | No | No | **Yes** | No |
| **WebSocket Support** | No | No | No | No | No |
| **Signals/Events Panel** | **Yes** | **Yes** | No | No | No |
| **Static Files Panel** | No | **Yes** | No | No | No |
| **Alerts Panel** | **Yes** | **Yes** | No | No | **Yes** |
| **AI/MCP Integration** | No | No | No | No | **Yes** |
| **Desktop App** | No | No | No | No | **Yes** |
| **Multi-Service** | No | No | No | No | **Yes** |

---

## Unique Strengths by Tool

### debug-toolbar (Ours)

**Strengths:**
- **True async-first design** using `contextvars` for request-scoped data
- **Full ASGI compliance** without blocking operations
- **Server-Timing header support** (W3C standard)
- **Security-focused**: Header analysis, CORS detection, sensitive data redaction
- **Multiple profiler backends**: cProfile and pyinstrument with flame graphs
- **Cache tracking** for Redis and Memcached with hit/miss stats
- **Advanced SQL analysis**: Duplicate detection, N+1 detection, EXPLAIN plans
- **Memory profiling**: tracemalloc and memray backends
- **Proactive alerts**: Automatic detection of security, performance, and database issues
- **Lifecycle tracking**: Events panel for Litestar hooks and exception handlers
- **Framework-agnostic core** (can support other ASGI frameworks)

**Best For:** Modern async Python applications using Litestar, SQLAlchemy, Redis

---

### Django Debug Toolbar

**Strengths:**
- **Most mature** (10+ years of development)
- **Largest ecosystem** of third-party panels
- **EXPLAIN plan integration** for SQL queries
- **Signals panel** for Django event debugging
- **Static files panel** for asset tracking
- **Alerts panel** for common mistakes (e.g., missing form enctype)
- **Request history** with full snapshot switching

**Best For:** Django applications, teams familiar with Django ecosystem

---

### Flask Debug Toolbar

**Strengths:**
- **Template editor** - Edit templates interactively in browser
- **Profiler dump** - Export profiling data to files
- **Simple integration** with Flask applications

**Best For:** Flask applications needing quick debugging setup

---

### FastAPI Debug Toolbar

**Strengths:**
- **Multi-ORM support**: SQLAlchemy + Tortoise ORM
- **GraphQL/GraphiQL support**
- **Swagger UI integration**
- **FastAPI-native** middleware

**Best For:** FastAPI applications using GraphQL or Tortoise ORM

---

### Sentry Spotlight

**Strengths:**
- **AI/MCP integration** - AI assistants can access telemetry
- **Distributed tracing** across services
- **Desktop app** for dedicated debugging window
- **Multi-service monitoring** in single view
- **Error tracking** with full context
- **User breadcrumbs** for action tracking
- **Sidecar architecture** - doesn't interfere with production

**Best For:** Complex microservice architectures, teams using AI coding assistants, production-like debugging

---

## Feature Gap Analysis

### What We Have That Others Don't

1. **Comprehensive header security analysis** with categorization
2. **CORS header detection and analysis**
3. **Server-Timing HTTP header** for browser DevTools integration
4. **Dual profiler support** (cProfile + pyinstrument switchable)
5. **SQLAlchemy duplicate query detection**
6. **Async-safe cache tracking** for Redis/Memcached
7. **EXPLAIN query plans** for PostgreSQL, SQLite, MySQL, MariaDB
8. **Flame graph visualization** in speedscope format
9. **N+1 query detection** with call stack and fix suggestions
10. **Multi-backend memory profiling** (tracemalloc + memray)
11. **Proactive alerts panel** for security, performance, and database issues

### What We're Missing (Roadmap)

#### Completed Features
- ~~EXPLAIN plan integration for SQL queries~~ Done
- ~~N+1 query detection with call stack~~ Done
- ~~Event/Signal panel for Litestar lifecycle events~~ Done
- ~~Alerts panel for common issues~~ Done
- ~~Memory profiling panel~~ Done
- ~~Flame graph visualization~~ Done

#### Medium Priority (Phase 9)
- **GraphQL panel** for query inspection
- **WebSocket panel** for WS debugging
- **Background tasks panel** (SAQ/Celery)

#### Future Vision (Phase 10+)
- **AI/MCP integration** for AI-assisted debugging
- **Distributed tracing** support (OpenTelemetry)
- **Desktop app/Sidecar** architecture option
- **Multi-framework support** (Starlette, FastAPI adapters)

---

## Migration Guides

### From Django Debug Toolbar

If migrating from Django to Litestar:
- TimerPanel -> TimerPanel (equivalent)
- SQLPanel -> SQLAlchemyPanel (use Advanced-Alchemy)
- HeadersPanel -> HeadersPanel (enhanced with security analysis)
- SettingsPanel -> SettingsPanel (equivalent)
- ProfilingPanel -> ProfilingPanel (enhanced with pyinstrument and flame graphs)
- SignalsPanel -> EventsPanel (Litestar lifecycle hooks and exception handlers)

### From FastAPI Debug Toolbar

- SQLAlchemyPanel -> SQLAlchemyPanel (equivalent, with N+1 detection)
- Default panels -> Core panels (TimerPanel, RequestPanel, etc.)

Added: CachePanel, TemplatesPanel, HeadersPanel (categorized), ProfilingPanel (with flame graphs), AlertsPanel, MemoryPanel, EventsPanel

---

## Performance Comparison

| Metric | Ours | Django | Flask | FastAPI |
|--------|------|--------|-------|---------|
| **Overhead (no panels)** | <1ms | ~2ms | ~1ms | ~1ms |
| **Overhead (all panels)** | ~5-10ms | ~10-20ms | ~5-10ms | ~5ms |
| **Memory usage** | Low | Medium | Low | Low |
| **Async blocking** | None | Yes | Yes | Partial |

*Note: Performance varies by configuration and workload*

---

## Conclusion

**debug-toolbar** excels in:
- Modern async Python applications
- Security-conscious debugging with proactive alerts
- Performance analysis with W3C Server-Timing and flame graphs
- SQLAlchemy query optimization with N+1 detection
- Memory profiling with multiple backends
- Comprehensive lifecycle event tracking

**Choose Django Debug Toolbar** if you need:
- Django-specific features (static files, Django templates)
- Largest plugin ecosystem
- Long-term stability (10+ years)

**Choose Sentry Spotlight** if you need:
- AI-assisted debugging
- Distributed tracing
- Multi-service monitoring
- Production-like debugging environment
