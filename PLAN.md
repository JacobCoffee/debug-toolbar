# Async Python Debug Toolbar - Master Plan

**Goal:** The most comprehensive, performant, and feature-rich debug toolbar for ASGI Python applications.

**Last Updated:** 2025-11-30

---

## Current Status: Phase 13 IN PROGRESS - MCP Server

### Test Coverage: 524+ tests passing
### Panels Implemented: 17 panels (15 core + 2 Litestar-specific)
### Latest Merges:
- PR #10 - Alerts Panel (proactive issue detection)
- PR #11 - Flame Graph Visualization
- PR #12 - Multi-Backend Memory Profiling Panel
- PR #13 - N+1 example fix
- PR #14 - Async Profiler Panel
- PR #15 - GraphQL Panel with Strawberry integration
- PR #16 - MCP Server for AI Assistant Integration (in review)

---

## Competitive Analysis Summary

| Feature Category | Our Status | Industry Best |
|-----------------|------------|---------------|
| Core Panels | **17 panels** | Django (15 panels) |
| Async Support | **Best-in-class** | Spotlight (also async) |
| Database Debugging | **Best-in-class** (EXPLAIN + N+1) | Django (EXPLAIN only) |
| Security Features | **Best-in-class** (Alerts Panel) | We lead here |
| Memory Profiling | **Best-in-class** (multi-backend) | None have this depth |
| Flame Graphs | **Complete** | Django (plugin only) |
| Async Profiling | **Best-in-class** (task tracking, blocking detection) | **Unique - nobody else has this** |
| GraphQL Debugging | **Best-in-class** (N+1, resolver timing, Strawberry) | FastAPI (basic only) |
| AI Integration | **In Progress** (PR #16) | Spotlight (MCP) |
| Distributed Tracing | Missing | Spotlight (Sentry) |

---

## Phase Completion Status

### Phase 1-5: COMPLETE ✅

All foundational work complete:
- Core architecture (config, context, storage, panels)
- 17 panels implemented (Timer, Request, Response, Logging, Versions, Routes, SQLAlchemy, Profiling, Headers, Settings, Cache, Templates, Events, Alerts, Memory, AsyncProfiler, GraphQL)
- Litestar integration (middleware, plugin, routes)
- Full UI with history, positioning, resizing, themes
- CI/CD pipelines configured
- 524+ tests passing

### Phase 6: Testing & Documentation 🔄 PARTIAL
- [x] Unit tests (524 tests)
- [x] Integration tests
- [x] CI/CD workflows
- [x] Documentation restructure (PR #6)
- [ ] Performance benchmarks
- [ ] API documentation expansion

### Phase 7: Polish & Release 🔄 IN PROGRESS
- [x] PyPI packaging
- [x] Release automation
- [ ] Documentation completion

### Phase 8: Database Intelligence ✅ COMPLETE
- [x] EXPLAIN Plan Integration (PR #5)
- [x] N+1 Query Detection (PR #8)

### Phase 9: Event & Signal Debugging ✅ COMPLETE
- [x] Litestar Events Panel (PR #9)
- [x] Alerts Panel (PR #10)

### Phase 10: GraphQL & API Debugging ✅ COMPLETE
- [x] GraphQL Panel with Strawberry (PR #15)

### Phase 11: Advanced Profiling ✅ COMPLETE
- [x] Memory Profiling Panel (PR #12)
- [x] Flame Graph Integration (PR #11)
- [x] Async Profiler Panel (PR #14)

### Phase 13: AI & Modern Tooling 🔄 IN PROGRESS
- [x] MCP Server Integration (PR #16 - in review)
  - [x] 10 MCP tools for analysis
  - [x] 10 MCP resources for data access
  - [x] Security utilities for sensitive data redaction
  - [x] CLI entry point (`python -m debug_toolbar.mcp`)
  - [x] Example with shared storage pattern

---

## Next Up

### Immediate (PR #16 merge pending):
1. Merge MCP Server PR
2. Test Claude Code / Cursor integration
3. Add MCP documentation

### Phase 12: Multi-Framework Support
- Starlette adapter
- FastAPI adapter

### Phase 14: Distributed Debugging
- OpenTelemetry integration
- Cross-service tracing

---

## Success Metrics

### Achieved:
- ✅ 17 panels (more than any competitor)
- ✅ Best-in-class async profiling
- ✅ GraphQL debugging
- ✅ MCP server for AI integration

### Remaining:
- Multi-framework support (FastAPI, Starlette)
- OpenTelemetry integration
- 1000+ GitHub stars

---

*This plan positions async-python-debug-toolbar as the definitive debugging solution for modern async Python applications.*
