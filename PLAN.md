# Async Python Debug Toolbar - Master Plan

**Goal:** The most comprehensive, performant, and feature-rich debug toolbar for ASGI Python applications.

**Last Updated:** 2025-11-30

---

## Current Status: Phase 11 COMPLETE - Advanced Profiling ✅

### Test Coverage: 406+ tests passing
### Panels Implemented: 16 panels (14 core + 2 Litestar-specific)
### Latest Merges:
- PR #10 - Alerts Panel (proactive issue detection)
- PR #11 - Flame Graph Visualization
- PR #12 - Multi-Backend Memory Profiling Panel
- PR #13 - N+1 example fix
- PR #14 - Async Profiler Panel (in review)

---

## Competitive Analysis Summary

| Feature Category | Our Status | Industry Best |
|-----------------|------------|---------------|
| Core Panels | **16 panels** | Django (15 panels) |
| Async Support | **Best-in-class** | Spotlight (also async) |
| Database Debugging | **Best-in-class** (EXPLAIN + N+1) | Django (EXPLAIN only) |
| Security Features | **Best-in-class** (Alerts Panel) | We lead here |
| Memory Profiling | **Best-in-class** (multi-backend) | None have this depth |
| Flame Graphs | **Complete** | Django (plugin only) |
| Async Profiling | **Best-in-class** (task tracking, blocking detection) | **Unique - nobody else has this** |
| AI Integration | Missing | Spotlight (MCP) |
| Distributed Tracing | Missing | Spotlight (Sentry) |

---

## Phase Completion Status

### Phase 1-5: COMPLETE ✅

All foundational work complete:
- Core architecture (config, context, storage, panels)
- 16 panels implemented (Timer, Request, Response, Logging, Versions, Routes, SQLAlchemy, Profiling, Headers, Settings, Cache, Templates, Events, Alerts, Memory, AsyncProfiler)
- Litestar integration (middleware, plugin, routes)
- Full UI with history, positioning, resizing, themes
- CI/CD pipelines configured
- 406+ tests passing

### Phase 5 UI Features (Just Completed):
- Dark/light theme toggle with localStorage persistence
- Toolbar positioning (left/right/top/bottom)
- Resizable toolbar with drag handles
- Panel expand/collapse animations (CSS transitions)
- Standalone history/detail pages with theme support
- SQLAlchemy auto-attach to all engines
- Routes panel with app route collection
- Improved nested data rendering (objects/arrays)

### Phase 6: Testing & Documentation 🔄 PARTIAL
- [x] Unit tests (283 tests)
- [x] Integration tests
- [x] CI/CD workflows
- [x] Documentation restructure (PR #6)
- [x] Index page improvements (PR #7)
- [x] Comparison page added
- [ ] Performance benchmarks
- [ ] API documentation (Sphinx content expansion)
- [ ] More usage examples

### Phase 7: Polish & Release 🔄 IN PROGRESS

- [ ] Security audit
- [ ] Performance benchmarks
- [x] PyPI packaging
- [x] Release automation
- [ ] Documentation completion

### Phase 8: Database Intelligence ✅ COMPLETE
- [x] EXPLAIN Plan Integration (PR #5)
- [x] N+1 Query Detection (PR #8)

### Phase 9: Event & Signal Debugging ✅ COMPLETE
- [x] Litestar Events Panel (PR #9)
- [x] Alerts Panel (PR #10)
- [ ] Background Tasks Panel (SAQ integration) - deferred

### Phase 11: Advanced Profiling ✅ COMPLETE
- [x] Memory Profiling Panel with multi-backend (PR #12)
- [x] Flame Graph Integration (PR #11)
- [x] Async Profiler Panel (PR #14) - task tracking, blocking detection, event loop monitoring

---

## Roadmap to Superiority

### Phase 8: Database Intelligence ✅ COMPLETE

**Goal:** Best-in-class database debugging for async Python

#### 8.1 EXPLAIN Plan Integration ✅ COMPLETE (PR #5)
```
Priority: HIGH
Effort: Medium
Value: Matches Django's key feature
```
- [x] Add EXPLAIN button to SQLAlchemy queries
- [x] Support PostgreSQL EXPLAIN (BUFFERS, FORMAT TEXT)
- [x] Support SQLite EXPLAIN QUERY PLAN
- [x] Support MySQL EXPLAIN
- [x] Support MariaDB EXPLAIN
- [x] Visual query plan display (modal with formatted output)
- [x] Parameter substitution for EXPLAIN execution
- [ ] Cost estimation highlighting (future enhancement)

#### 8.2 N+1 Query Detection ✅ COMPLETE (PR #8)
```
Priority: HIGH
Effort: Medium
Value: Unique selling point for ORMs
```
- [x] Track query patterns during request
- [x] Detect repeated similar queries (N+1 pattern)
- [x] Capture call stack for each query
- [x] Group queries by origin
- [x] Provide fix suggestions
- [x] Add warning badge to panel nav

#### 8.3 Query Optimization Hints
```
Priority: MEDIUM
Effort: Low
Value: Developer experience
```
- [ ] Missing index detection
- [ ] Full table scan warnings
- [ ] Suggest query improvements
- [ ] Link to relevant documentation

---

### Phase 9: Event & Signal Debugging

**Goal:** Complete visibility into application lifecycle

#### 9.1 Litestar Events Panel ✅ COMPLETE (PR #9)
```
Priority: HIGH
Effort: Medium
Value: Matches Django signals panel
```
- [x] Track lifecycle events (startup, shutdown)
- [x] Track request lifecycle (before_request, after_request, after_response)
- [x] Track exception handlers
- [x] Show registered handlers per event
- [x] Execution timing per handler
- [x] Handler call stack

#### 9.2 Background Tasks Panel
```
Priority: MEDIUM
Effort: Medium
Value: Modern async apps need this
```
- [ ] SAQ (Simple Async Queue) integration
- [ ] Track enqueued tasks
- [ ] Task execution status
- [ ] Task timing and retries
- [ ] Optional: Celery/RQ support

#### 9.3 Alerts Panel ✅ COMPLETE (PR #10)
```
Priority: MEDIUM
Effort: Low
Value: Proactive issue detection
```
- [x] Missing CSRF protection warnings
- [x] Insecure cookie settings
- [x] Debug mode in apparent production
- [x] Missing security headers
- [x] Large response body warnings
- [x] Slow query threshold alerts
- [x] N+1 query alerts

---

### Phase 10: GraphQL & API Debugging

**Goal:** First-class API debugging support

#### 10.1 GraphQL Panel
```
Priority: MEDIUM
Effort: Medium
Value: Matches FastAPI Debug Toolbar
```
- [ ] Strawberry GraphQL integration
- [ ] Query/mutation tracking
- [ ] Resolver timing breakdown
- [ ] Variable inspection
- [ ] Error tracking
- [ ] Query complexity analysis

#### 10.2 OpenAPI Integration
```
Priority: LOW
Effort: Low
Value: Nice-to-have for API debugging
```
- [ ] Show matched OpenAPI operation
- [ ] Request/response schema validation
- [ ] Link to API documentation

#### 10.3 WebSocket Panel
```
Priority: MEDIUM
Effort: High
Value: Unique - no competitor has this
```
- [ ] WebSocket connection tracking
- [ ] Message logging (sent/received)
- [ ] Connection state timeline
- [ ] Ping/pong monitoring
- [ ] Binary/text message inspection

---

### Phase 11: Advanced Profiling

**Goal:** Deepest performance insights available

#### 11.1 Memory Profiling Panel ✅ COMPLETE (PR #12)
```
Priority: HIGH
Effort: High
Value: Unique comprehensive feature - no competitor has this depth
```

**Multi-Backend Architecture** (like ProfilingPanel's cProfile/pyinstrument):

| Backend | Strengths | Limitations |
|---------|-----------|-------------|
| **tracemalloc** (stdlib) | Low overhead, cross-platform, no deps | Python-only allocations |
| **memray** (bloomberg) | Native C tracking, flame graphs, detailed stacks | Linux/macOS only, file-based |

**Implementation:**
- [x] `MemoryBackend` abstract base class
- [x] `TraceMallocBackend` - stdlib, default, works everywhere
  - [x] Snapshot at request start/end
  - [x] Top allocations by file/line
  - [x] Allocation diff (what grew during request)
  - [x] Peak memory tracking
- [x] `MemrayBackend` - optional, deep analysis
  - [x] Native extension tracking (SQLAlchemy C code, numpy, etc.)
  - [x] Full call stack with C frames
  - [x] Temp file management + cleanup
  - [x] Flame graph data generation
- [x] Auto-selection: memray if available + Linux/macOS, else tracemalloc
- [x] Configuration: `memory_backend: Literal["tracemalloc", "memray", "auto"]`

**Panel Features:**
- [x] Memory usage per request (before/after/delta)
- [x] Top N memory allocations with source location
- [x] Object allocation tracking by type
- [x] Memory leak detection hints (objects that keep growing)
- [x] Peak memory reporting
- [x] Memory flame graph (memray backend)

#### 11.2 Flame Graph Integration ✅ COMPLETE (PR #11)
```
Priority: HIGH
Effort: Medium
Value: Visual profiling (Django has this as plugin)
```

**Multi-Source Flame Graphs:**
- [x] Generate from cProfile data (CPU profiling)
- [x] Generate from memray data (memory profiling)
- [x] Interactive SVG visualization (d3-flame-graph or speedscope format)
- [x] Zoom and drill-down support
- [ ] Compare across requests (diff flame graphs)
- [ ] Export to speedscope JSON format

#### 11.3 Async Profiler Panel ✅ COMPLETE (PR #14)
```
Priority: HIGH
Effort: High
Value: Unique for async Python - nobody else has this
```

**Implementation:**
- [x] `AsyncProfilerBackend` abstract base class
- [x] `TaskFactoryBackend` - custom task factory hook
  - [x] Track async task creation (asyncio.create_task)
  - [x] Task completion/cancellation/error tracking
  - [x] Parent task relationship tracking
  - [x] Stack trace capture at task creation
  - [x] SQLAlchemy greenlet compatibility
- [x] `BlockingCallDetector` - asyncio debug mode integration
  - [x] Custom exception handler for slow callback warnings
  - [x] Configurable threshold (default 100ms)
  - [x] Automatic recording with source location
- [x] `EventLoopLagMonitor` - scheduled callback monitoring
  - [x] Detects when event loop falls behind
  - [x] Configurable sample interval and threshold
  - [x] Max lag tracking

**Panel Features:**
- [x] Concurrent task visualization (timeline view)
- [x] Task status badges (completed, cancelled, error, running)
- [x] Blocking call detection (sync code in async context)
- [x] Event loop lag monitoring
- [x] Summary statistics (total/completed/cancelled/error tasks)
- [x] Server-Timing header integration
- [x] XSS-safe rendering (validated and escaped)

---

### Phase 12: Multi-Framework Support

**Goal:** Framework-agnostic debug toolbar

#### 12.1 Starlette Adapter
```
Priority: HIGH
Effort: Medium
Value: Expands user base significantly
```
- [ ] Starlette middleware
- [ ] Starlette routes panel
- [ ] StarletteDebugToolbarConfig
- [ ] Example application

#### 12.2 FastAPI Adapter
```
Priority: HIGH
Effort: Low (builds on Starlette)
Value: Largest ASGI framework user base
```
- [ ] FastAPI plugin
- [ ] Dependency injection panel
- [ ] FastAPIDebugToolbarConfig
- [ ] Example with FastAPI features

#### 12.3 Quart Adapter
```
Priority: LOW
Effort: Medium
Value: Flask-like async framework
```
- [ ] Quart middleware
- [ ] QuartDebugToolbarConfig

---

### Phase 13: AI & Modern Tooling

**Goal:** AI-assisted debugging (Spotlight-level innovation)

#### 13.1 MCP Server Integration
```
Priority: HIGH
Effort: High
Value: Unique differentiator - AI debugging
```
- [ ] Implement Model Context Protocol server
- [ ] Expose debug data to AI assistants
- [ ] Cursor IDE integration
- [ ] Claude Code integration
- [ ] Tool definitions for:
  - Get request history
  - Get query analysis
  - Get performance bottlenecks
  - Get error context

#### 13.2 Export & Share
```
Priority: MEDIUM
Effort: Low
Value: Team collaboration
```
- [ ] Export debug session to JSON
- [ ] Export to HAR format
- [ ] Share link generation
- [ ] Import previous sessions

#### 13.3 Comparison Mode
```
Priority: LOW
Effort: Medium
Value: Performance regression detection
```
- [ ] Compare two requests side-by-side
- [ ] Highlight differences
- [ ] Track performance over time
- [ ] Baseline comparison

---

### Phase 14: Distributed Debugging

**Goal:** Microservice-ready debugging (Spotlight-level)

#### 14.1 OpenTelemetry Integration
```
Priority: HIGH
Effort: High
Value: Industry standard tracing
```
- [ ] OTLP exporter for debug data
- [ ] Trace context propagation
- [ ] Span visualization
- [ ] Integration with Jaeger/Zipkin

#### 14.2 Cross-Service Tracing
```
Priority: MEDIUM
Effort: High
Value: Microservice debugging
```
- [ ] HTTP client tracing (httpx, aiohttp)
- [ ] Trace ID propagation
- [ ] Service map visualization
- [ ] Latency breakdown by service

#### 14.3 Sidecar Mode
```
Priority: LOW
Effort: Very High
Value: Production-like debugging
```
- [ ] Standalone sidecar process
- [ ] Multi-application aggregation
- [ ] Persistent storage backend
- [ ] Remote debugging support

---

### Phase 15: Enterprise Features

**Goal:** Production-grade tooling

#### 15.1 Access Control
```
Priority: MEDIUM
Effort: Medium
Value: Enterprise security
```
- [ ] Role-based panel access
- [ ] Sensitive data masking levels
- [ ] Audit logging
- [ ] SSO integration

#### 15.2 Performance Budgets
```
Priority: MEDIUM
Effort: Low
Value: CI/CD integration
```
- [ ] Define performance thresholds
- [ ] Fail CI on budget exceeded
- [ ] Track budgets over time
- [ ] Slack/webhook notifications

#### 15.3 Plugin Marketplace
```
Priority: LOW
Effort: Medium
Value: Community ecosystem
```
- [ ] Plugin registration system
- [ ] Community panel repository
- [ ] Plugin documentation
- [ ] Version compatibility

---

## Implementation Priority Matrix

### Must Have (Phase 8-9) ✅ ALL COMPLETE
| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| ~~EXPLAIN plans~~ | ~~Medium~~ | ~~High~~ | ✅ DONE |
| ~~N+1 detection~~ | ~~Medium~~ | ~~High~~ | ✅ DONE |
| ~~Events panel~~ | ~~Medium~~ | ~~High~~ | ✅ DONE |
| ~~Alerts panel~~ | ~~Low~~ | ~~Medium~~ | ✅ DONE (PR #10) |
| ~~Flame graphs~~ | ~~Medium~~ | ~~High~~ | ✅ DONE (PR #11) |

### Should Have (Phase 10-11)
| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| GraphQL panel | Medium | Medium | **P1** |
| ~~Memory profiling (tracemalloc + memray)~~ | ~~High~~ | ~~High~~ | ✅ DONE (PR #12) |
| WebSocket panel | High | Medium | **P2** |
| ~~Async profiling~~ | ~~High~~ | ~~High~~ | ✅ DONE (PR #14) |

### Nice to Have (Phase 12-13)
| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| FastAPI adapter | Low | High | **P2** |
| Starlette adapter | Medium | High | **P2** |
| MCP integration | High | High | **P3** |
| Export/share | Low | Medium | **P3** |

### Future Vision (Phase 14-15)
| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| OpenTelemetry | High | High | **P3** |
| Cross-service tracing | High | Medium | **P4** |
| Sidecar mode | Very High | Medium | **P4** |
| Plugin marketplace | Medium | Medium | **P4** |

---

## Competitive Advantages Target

### vs Django Debug Toolbar
- [x] Async-first (they're WSGI)
- [x] Server-Timing header
- [x] Security header analysis
- [x] EXPLAIN plans (match them) ✅
- [x] Signals panel equivalent (Events Panel) ✅
- [x] Memory profiling (they don't have multi-backend) ✅
- [x] Flame graphs built-in (they need plugin) ✅

### vs Flask Debug Toolbar
- [x] Async support
- [x] More panels (15 vs ~10)
- [x] Better profiling (flame graphs, memory)
- [ ] Template editor (consider)

### vs FastAPI Debug Toolbar
- [x] More comprehensive panels (15 vs ~8)
- [x] Cache tracking
- [x] Better profiling (memory, flame graphs)
- [x] N+1 detection
- [ ] GraphQL support (match them)
- [ ] Tortoise ORM (maybe)

### vs Sentry Spotlight
- [x] Lighter weight
- [x] No external dependencies
- [x] Deeper memory profiling (memray support)
- [ ] AI/MCP integration (match them)
- [ ] Distributed tracing (match them)

---

## Success Metrics

### Phase 8-9 Complete When: ✅ ACHIEVED
- ~~EXPLAIN plans work for PostgreSQL, SQLite, MySQL~~ ✅ PR #5
- ~~N+1 queries auto-detected with 90%+ accuracy~~ ✅ PR #8
- ~~Events panel tracks lifecycle hooks~~ ✅ PR #9
- ~~Alerts panel provides proactive issue detection~~ ✅ PR #10
- Performance overhead < 15ms with all features enabled (needs benchmarking)

### Phase 11 Complete When: ✅ ACHIEVED
- ~~Memory profiling with multi-backend support~~ ✅ PR #12
- ~~Flame graph visualization integrated~~ ✅ PR #11
- ~~Async profiling tracks task creation/scheduling~~ ✅ PR #14

### Phase 10 Complete When:
- GraphQL queries fully inspectable
- WebSocket connections tracked end-to-end

### Phase 13 Complete When:
- MCP server passes Claude/Cursor integration tests
- Debug sessions exportable/importable
- Multi-framework support (Litestar, FastAPI, Starlette)

### Ultimate Success:
- Default choice for ASGI debugging
- 1000+ GitHub stars
- Used by 10+ major Litestar projects
- Community-contributed panels ecosystem

---

## File Structure (Current + Projected)

```
src/debug_toolbar/
├── core/                      # Framework-agnostic core
│   ├── panels/
│   │   ├── alerts.py          # ✅ Phase 9 - COMPLETE
│   │   ├── async_profiler/    # ✅ Phase 11 - COMPLETE (PR #14)
│   │   │   ├── __init__.py
│   │   │   ├── panel.py       # AsyncProfilerPanel
│   │   │   ├── base.py        # AsyncProfilerBackend ABC
│   │   │   ├── taskfactory.py # TaskFactoryBackend (stdlib, default)
│   │   │   ├── detector.py    # BlockingCallDetector, EventLoopLagMonitor
│   │   │   ├── timeline.py    # Timeline visualization generation
│   │   │   └── models.py      # Data models (TaskEvent, BlockingCall, etc.)
│   │   ├── graphql.py         # Phase 10 - pending
│   │   ├── memory/            # ✅ Phase 11 - COMPLETE
│   │   │   ├── __init__.py
│   │   │   ├── panel.py       # MemoryPanel
│   │   │   ├── base.py        # MemoryBackend ABC
│   │   │   ├── tracemalloc_backend.py # TraceMallocBackend (stdlib, default)
│   │   │   └── memray_backend.py      # MemrayBackend (optional, Linux/macOS)
│   │   └── websocket.py       # Phase 10 - pending
│   ├── mcp/                   # Phase 13 - pending
│   │   ├── server.py
│   │   └── tools.py
│   └── otel/                  # Phase 14 - pending
│       └── exporter.py
├── litestar/                  # ✅ Litestar adapter - COMPLETE
│   └── panels/
│       ├── events.py          # ✅ Phase 9 - COMPLETE
│       └── routes.py          # ✅ COMPLETE
├── starlette/                 # Phase 12 - pending
├── fastapi/                   # Phase 12 - pending
└── extras/
    ├── advanced_alchemy/      # ✅ COMPLETE
    ├── strawberry/            # Phase 10 - pending
    └── saq/                   # Phase 9 - deferred
```

---

## Resources & References

### Competitor Documentation
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Flask Debug Toolbar](https://flask-debugtoolbar.readthedocs.io/)
- [FastAPI Debug Toolbar](https://fastapi-debug-toolbar.domake.io/)
- [Sentry Spotlight](https://spotlightjs.com/)

### Standards & Protocols
- [Server-Timing Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Server-Timing)
- [OpenTelemetry](https://opentelemetry.io/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

### Related Projects
- [pyinstrument](https://github.com/joerick/pyinstrument) - Statistical profiler
- [py-spy](https://github.com/benfred/py-spy) - Sampling profiler, flame graphs
- [tracemalloc](https://docs.python.org/3/library/tracemalloc.html) - Stdlib memory tracking
- [memray](https://github.com/bloomberg/memray) - Bloomberg's memory profiler (native + Python)
- [pytest-memray](https://github.com/bloomberg/pytest-memray) - Memory testing in CI
- [scalene](https://github.com/plasma-umass/scalene) - CPU + memory + GPU profiler
- [fil-profile](https://github.com/pythonspeed/filprofiler) - Memory profiler for data pipelines
- [speedscope](https://github.com/jlfwong/speedscope) - Flame graph visualizer

---

*This plan positions async-python-debug-toolbar as the definitive debugging solution for modern async Python applications.*
