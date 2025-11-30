# PRD: Roadmap PR Breakdown

## Metadata
- **Slug**: roadmap-breakdown
- **Complexity**: Meta (planning document)
- **Created**: 2025-11-29
- **Last Updated**: 2025-11-29

---

## Current State Analysis

### Completed Features (from codebase analysis)

| Feature | Status | Evidence |
|---------|--------|----------|
| Core Panels (13) | Complete | Timer, Request, Response, Headers, Logging, Versions, Routes, SQLAlchemy, Profiling, Settings, Cache, Templates, Events |
| Alerts Panel | Complete | `src/debug_toolbar/core/panels/alerts.py` (380 lines, full implementation) |
| Memory Panel | Complete | `src/debug_toolbar/core/panels/memory/` (multi-backend: tracemalloc + memray) |
| Flame Graph | Complete | `src/debug_toolbar/core/panels/flamegraph.py` (speedscope format) |
| N+1 Detection | Complete | SQLAlchemy panel includes N+1 detection |
| EXPLAIN Plans | Complete | SQLAlchemy panel includes EXPLAIN support |
| Events Panel | Complete | `src/debug_toolbar/litestar/panels/events.py` |
| Test Suite | 402 tests | All passing |

### PLAN.md vs Reality Gap

PLAN.md states "305 tests" and marks several features as incomplete that are actually done:
- Phase 9.1 Events Panel: **DONE**
- Alerts Panel: **DONE** (PLAN says "TODO")
- Memory Panel: **DONE** (PLAN says Phase 11)
- Flame Graph: **DONE** (PLAN says Phase 11)

---

## PR Breakdown by Phase

### Phase 9: Event & Signal Debugging

#### PR #1: Background Tasks Panel (SAQ Integration)
**Priority**: P1 (Medium effort, high value for modern async apps)
**Complexity**: Medium
**Estimated Files**: 4-6

```
New Files:
- src/debug_toolbar/extras/saq/__init__.py
- src/debug_toolbar/extras/saq/panel.py
- tests/unit/test_saq_panel.py
- templates/panels/saq.html

Modified Files:
- pyproject.toml (optional dep: saq)
- docs/extras/saq.md
```

**Acceptance Criteria**:
- [ ] Track enqueued tasks during request
- [ ] Show task execution status (pending, running, completed, failed)
- [ ] Display task timing and retry count
- [ ] Integration tests with SAQ queue
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

### Phase 10: GraphQL & API Debugging

#### PR #2: WebSocket Panel
**Priority**: P1 (Unique feature - no competitor has this)
**Complexity**: High
**Estimated Files**: 5-7

```
New Files:
- src/debug_toolbar/core/panels/websocket.py
- tests/unit/test_websocket_panel.py
- templates/panels/websocket.html

Modified Files:
- src/debug_toolbar/litestar/middleware.py (WebSocket detection)
- src/debug_toolbar/core/config.py (WebSocket settings)
```

**Acceptance Criteria**:
- [ ] Track WebSocket connections (open/close)
- [ ] Log messages sent/received with timestamps
- [ ] Display connection state timeline
- [ ] Handle binary and text messages
- [ ] Ping/pong monitoring
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

#### PR #3: GraphQL Panel (Strawberry Integration)
**Priority**: P2 (Matches FastAPI Debug Toolbar)
**Complexity**: Medium
**Estimated Files**: 5-7

```
New Files:
- src/debug_toolbar/extras/strawberry/__init__.py
- src/debug_toolbar/extras/strawberry/panel.py
- src/debug_toolbar/extras/strawberry/extension.py
- tests/unit/test_graphql_panel.py
- templates/panels/graphql.html

Modified Files:
- pyproject.toml (optional dep: strawberry-graphql)
```

**Acceptance Criteria**:
- [ ] Track GraphQL queries and mutations
- [ ] Display resolver timing breakdown
- [ ] Variable inspection
- [ ] Error tracking with stack traces
- [ ] Query complexity analysis (optional)
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

#### PR #4: OpenAPI Integration
**Priority**: P3 (Nice-to-have for API debugging)
**Complexity**: Low
**Estimated Files**: 2-3

```
New Files:
- src/debug_toolbar/litestar/panels/openapi.py
- tests/unit/test_openapi_panel.py

Modified Files:
- templates/panels/request.html (add OpenAPI info)
```

**Acceptance Criteria**:
- [ ] Show matched OpenAPI operation ID
- [ ] Display request/response schema from spec
- [ ] Link to API documentation route
- [ ] 90%+ test coverage

**Dependencies**: None (Litestar has built-in OpenAPI)
**Blocked By**: None

---

### Phase 11: Advanced Profiling

#### PR #5: Async Profiling Panel
**Priority**: P1 (Unique for async Python - differentiator)
**Complexity**: High
**Estimated Files**: 6-8

```
New Files:
- src/debug_toolbar/core/panels/async_profiler/__init__.py
- src/debug_toolbar/core/panels/async_profiler/panel.py
- src/debug_toolbar/core/panels/async_profiler/tracker.py
- tests/unit/test_async_profiler.py
- templates/panels/async_profiler.html

Modified Files:
- src/debug_toolbar/core/config.py (async profiling settings)
```

**Acceptance Criteria**:
- [ ] Track async task creation (asyncio.create_task)
- [ ] Concurrent task visualization (timeline)
- [ ] Task switching/scheduling timeline
- [ ] Await point identification and timing
- [ ] Blocking call detection (sync in async context)
- [ ] Event loop lag monitoring
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

**Technical Notes**:
- Use `asyncio.current_task()` and task introspection
- Hook into event loop with custom policy or monitoring
- Consider using `yappi` for async-aware profiling

---

#### PR #6: Flame Graph UI Integration
**Priority**: P2 (Visual profiling enhancement)
**Complexity**: Medium
**Estimated Files**: 4-5

```
New Files:
- static/js/flamegraph.js (d3-flame-graph wrapper)
- templates/panels/flamegraph_viewer.html

Modified Files:
- src/debug_toolbar/core/panels/profiling.py (add UI integration)
- src/debug_toolbar/litestar/routes/handlers.py (flamegraph endpoint)
- templates/panels/profiling.html (add flamegraph button)
```

**Acceptance Criteria**:
- [ ] Interactive SVG visualization using d3-flame-graph
- [ ] Zoom and drill-down support
- [ ] CPU and memory flame graphs (from existing backends)
- [ ] Export to speedscope JSON format
- [ ] 90%+ test coverage for backend

**Dependencies**: PR #5 (can share visualization code)
**Blocked By**: None

**Technical Notes**:
- FlameGraphGenerator already exists, just needs UI
- Consider speedscope embedding or d3-flame-graph

---

### Phase 12: Multi-Framework Support

#### PR #7: Starlette Adapter
**Priority**: P1 (Expands user base significantly)
**Complexity**: Medium
**Estimated Files**: 8-10

```
New Files:
- src/debug_toolbar/starlette/__init__.py
- src/debug_toolbar/starlette/middleware.py
- src/debug_toolbar/starlette/config.py
- src/debug_toolbar/starlette/routes.py
- src/debug_toolbar/starlette/panels/__init__.py
- src/debug_toolbar/starlette/panels/routes.py
- tests/integration/test_starlette_integration.py
- examples/starlette_app.py

Modified Files:
- pyproject.toml (optional dep group)
- docs/frameworks/starlette.md
```

**Acceptance Criteria**:
- [ ] Starlette middleware with toolbar injection
- [ ] Starlette routes panel
- [ ] StarletteDebugToolbarConfig
- [ ] Integration tests with Starlette app
- [ ] Example application
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

#### PR #8: FastAPI Adapter
**Priority**: P1 (Largest ASGI framework user base)
**Complexity**: Low (builds on Starlette)
**Estimated Files**: 4-5

```
New Files:
- src/debug_toolbar/fastapi/__init__.py
- src/debug_toolbar/fastapi/plugin.py
- src/debug_toolbar/fastapi/panels/dependencies.py
- tests/integration/test_fastapi_integration.py
- examples/fastapi_app.py

Modified Files:
- (relies on starlette adapter)
```

**Acceptance Criteria**:
- [ ] FastAPI plugin/middleware
- [ ] Dependency injection panel
- [ ] FastAPIDebugToolbarConfig
- [ ] Integration tests
- [ ] Example with FastAPI features
- [ ] 90%+ test coverage

**Dependencies**: PR #7 (Starlette adapter)
**Blocked By**: PR #7

---

### Phase 13: AI & Modern Tooling

#### PR #9: MCP Server Integration
**Priority**: P2 (Unique differentiator - AI debugging)
**Complexity**: High
**Estimated Files**: 8-10

```
New Files:
- src/debug_toolbar/mcp/__init__.py
- src/debug_toolbar/mcp/server.py
- src/debug_toolbar/mcp/tools.py
- src/debug_toolbar/mcp/resources.py
- tests/unit/test_mcp_server.py
- docs/integrations/mcp.md
- examples/mcp_integration.py

Modified Files:
- pyproject.toml (mcp dependency)
- src/debug_toolbar/core/storage.py (expose for MCP)
```

**Acceptance Criteria**:
- [ ] Implement Model Context Protocol server
- [ ] Tool: Get request history
- [ ] Tool: Get query analysis
- [ ] Tool: Get performance bottlenecks
- [ ] Tool: Get error context
- [ ] Resource: Current request data
- [ ] Cursor IDE integration docs
- [ ] Claude Code integration docs
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

#### PR #10: Export & Share
**Priority**: P3 (Team collaboration)
**Complexity**: Low
**Estimated Files**: 3-4

```
New Files:
- src/debug_toolbar/core/export.py
- tests/unit/test_export.py

Modified Files:
- src/debug_toolbar/litestar/routes/handlers.py (export endpoints)
- templates/toolbar.html (export button)
```

**Acceptance Criteria**:
- [ ] Export debug session to JSON
- [ ] Export to HAR format
- [ ] Import previous sessions
- [ ] Share link generation (optional)
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

### Phase 14: Distributed Debugging

#### PR #11: OpenTelemetry Integration
**Priority**: P2 (Industry standard tracing)
**Complexity**: High
**Estimated Files**: 6-8

```
New Files:
- src/debug_toolbar/otel/__init__.py
- src/debug_toolbar/otel/exporter.py
- src/debug_toolbar/otel/span_processor.py
- src/debug_toolbar/core/panels/otel.py
- tests/unit/test_otel_integration.py

Modified Files:
- pyproject.toml (opentelemetry deps)
- src/debug_toolbar/core/context.py (trace context)
```

**Acceptance Criteria**:
- [ ] OTLP exporter for debug data
- [ ] Trace context propagation
- [ ] Span visualization in panel
- [ ] Integration with Jaeger/Zipkin
- [ ] 90%+ test coverage

**Dependencies**: None
**Blocked By**: None

---

### Phase 15: Polish & Documentation

#### PR #12: Performance Benchmarks
**Priority**: P2 (Required for release)
**Complexity**: Low
**Estimated Files**: 3-4

```
New Files:
- benchmarks/benchmark_overhead.py
- benchmarks/benchmark_panels.py
- benchmarks/README.md

Modified Files:
- docs/performance.md
- Makefile (benchmark target)
```

**Acceptance Criteria**:
- [ ] Measure baseline request overhead
- [ ] Measure per-panel overhead
- [ ] Establish performance budgets
- [ ] CI integration for regression detection
- [ ] Documentation of results

**Dependencies**: None
**Blocked By**: None

---

#### PR #13: Documentation Completion
**Priority**: P1 (Required for release)
**Complexity**: Low
**Estimated Files**: 8-12

```
New/Modified Files:
- docs/api/panels.md
- docs/api/config.md
- docs/guides/creating-panels.md
- docs/guides/framework-integration.md
- docs/examples/*.md
- README.md (usage examples)
```

**Acceptance Criteria**:
- [ ] Complete API documentation
- [ ] Panel creation guide
- [ ] Framework integration guides
- [ ] Usage examples for each panel
- [ ] Troubleshooting guide

**Dependencies**: All feature PRs
**Blocked By**: None (can be done incrementally)

---

## Priority Order (Recommended Implementation Sequence)

### Tier 1: Core Differentiation (Do First)
| Order | PR | Priority | Effort | Rationale |
|-------|-----|----------|--------|-----------|
| 1 | PR #5: Async Profiling | P1 | High | Unique differentiator, no competitor has this |
| 2 | PR #2: WebSocket Panel | P1 | High | Unique feature, growing demand |
| 3 | PR #7: Starlette Adapter | P1 | Medium | Expands user base 10x |

### Tier 2: Framework Expansion (Critical for Adoption)
| Order | PR | Priority | Effort | Rationale |
|-------|-----|----------|--------|-----------|
| 4 | PR #8: FastAPI Adapter | P1 | Low | Largest ASGI user base, builds on #7 |
| 5 | PR #1: SAQ Panel | P1 | Medium | Modern async apps need this |
| 6 | PR #6: Flame Graph UI | P2 | Medium | Visual appeal, builds on existing code |

### Tier 3: Ecosystem Integration
| Order | PR | Priority | Effort | Rationale |
|-------|-----|----------|--------|-----------|
| 7 | PR #3: GraphQL Panel | P2 | Medium | Matches competitor feature |
| 8 | PR #9: MCP Server | P2 | High | AI integration, unique value |
| 9 | PR #11: OpenTelemetry | P2 | High | Industry standard, enterprise appeal |

### Tier 4: Polish & Release
| Order | PR | Priority | Effort | Rationale |
|-------|-----|----------|--------|-----------|
| 10 | PR #12: Benchmarks | P2 | Low | Required for release confidence |
| 11 | PR #13: Documentation | P1 | Low | Required for adoption |
| 12 | PR #10: Export/Share | P3 | Low | Nice-to-have for teams |
| 13 | PR #4: OpenAPI Integration | P3 | Low | Nice-to-have enhancement |

---

## Dependency Graph

```
PR #7 (Starlette) ──► PR #8 (FastAPI)

All Feature PRs ──► PR #13 (Documentation)

PR #5 (Async Profiling) ─┬─► PR #6 (Flame Graph UI)
                         │
PR existing (Memory) ────┘
```

---

## Risk Assessment

| PR | Risk Level | Mitigation |
|----|------------|------------|
| PR #5 (Async Profiling) | High | Prototype first, may need event loop hooks |
| PR #2 (WebSocket) | Medium | Litestar WebSocket API complexity |
| PR #9 (MCP) | Medium | MCP spec evolving, version pin needed |
| PR #11 (OpenTelemetry) | Medium | API surface large, scope carefully |

---

## Success Metrics

### Phase Completion Criteria

**Phase 10 Complete When:**
- WebSocket connections tracked end-to-end
- GraphQL queries fully inspectable
- Memory profiling adds < 5% overhead (already done)

**Phase 12 Complete When:**
- Starlette and FastAPI adapters working
- 3+ integration tests per framework
- Example apps for each

**Phase 13 Complete When:**
- MCP server passes Claude/Cursor integration tests
- Debug sessions exportable/importable

### Ultimate Success:
- Default choice for ASGI debugging
- 1000+ GitHub stars
- Used by 10+ major Litestar/FastAPI projects
- Community-contributed panels

---

## Notes

### PLAN.md Updates Needed

The PLAN.md file is outdated. It should be updated to reflect:
1. Test count is now 402 (not 305)
2. Alerts Panel is COMPLETE
3. Memory Panel with multi-backend is COMPLETE
4. Flame Graph generator is COMPLETE
5. Phase 9.3 Alerts is DONE

### Patterns Observed

From analyzing existing panels:
- All panels extend `Panel` ABC
- Use `ClassVar` for panel metadata
- Implement `generate_stats()` as async method
- Optional lifecycle hooks: `process_request()`, `process_response()`
- Use `__slots__` for instance attributes
- Templates in `templates/panels/`
- Tests use fixtures from `conftest.py`
