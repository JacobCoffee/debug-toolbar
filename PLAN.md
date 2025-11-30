# Async Python Debug Toolbar - Master Plan

**Goal:** The most comprehensive, performant, and feature-rich debug toolbar for ASGI Python applications.

**Last Updated:** 2025-11-30

---

## Current Status: v0.3.0 RELEASED ✅

### Test Coverage: 574+ tests passing
### Panels Implemented: 18 panels (16 core + 2 Litestar-specific)
### Latest Release: v0.3.0 (2025-11-30)
- MCP Server for AI Assistant Integration
- FileToolbarStorage for cross-process data sharing
- Published to PyPI as `litestar-debug-toolbar`

### Recent PRs:
- PR #16 - MCP Server for AI Assistant Integration
- PR #17 - Release v0.3.0 version bump
- PR #18 - Documentation updates (MCP screenshot, API docs)
- PR #19 - WebSocket Panel for real-time connection tracking

---

## Competitive Analysis Summary

| Feature Category | Our Status | Industry Best |
|-----------------|------------|---------------|
| Core Panels | **18 panels** | Django (15 panels) |
| WebSocket Debugging | **Best-in-class** (live tracking, message inspection) | **Unique - nobody else has this** |
| Async Support | **Best-in-class** | Spotlight (also async) |
| Database Debugging | **Best-in-class** (EXPLAIN + N+1) | Django (EXPLAIN only) |
| Security Features | **Best-in-class** (Alerts Panel) | We lead here |
| Memory Profiling | **Best-in-class** (multi-backend) | None have this depth |
| Flame Graphs | **Complete** | Django (plugin only) |
| Async Profiling | **Best-in-class** (task tracking, blocking detection) | **Unique - nobody else has this** |
| GraphQL Debugging | **Best-in-class** (N+1, resolver timing, Strawberry) | FastAPI (basic only) |
| AI Integration | **Best-in-class** (MCP Server) | Spotlight (MCP) |
| Distributed Tracing | Missing | Spotlight (Sentry) |

---

## Phase Completion Status

### Phase 1-5: COMPLETE ✅

All foundational work complete:
- Core architecture (config, context, storage, panels)
- 18 panels implemented (Timer, Request, Response, Logging, Versions, Routes, SQLAlchemy, Profiling, Headers, Settings, Cache, Templates, Events, Alerts, Memory, AsyncProfiler, GraphQL, WebSocket)
- Litestar integration (middleware, plugin, routes)
- Full UI with history, positioning, resizing, themes
- CI/CD pipelines configured
- 574+ tests passing

### Phase 6: Testing & Documentation 🔄 PARTIAL
- [x] Unit tests (524 tests)
- [x] Integration tests
- [x] CI/CD workflows
- [x] Documentation restructure (PR #6)
- [ ] Performance benchmarks
- [ ] API documentation expansion

### Phase 7: Polish & Release ✅ COMPLETE
- [x] PyPI packaging
- [x] Release automation (Sigstore signing, trusted publishers)
- [x] v0.3.0 released to PyPI

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

### Phase 13: AI & Modern Tooling ✅ COMPLETE
- [x] MCP Server Integration (PR #16)
  - [x] 10 MCP tools for analysis
  - [x] 10 MCP resources for data access
  - [x] Security utilities for sensitive data redaction
  - [x] CLI entry point (`python -m debug_toolbar.mcp`)
  - [x] Example with shared storage pattern
  - [x] Claude Code / Cursor integration ready
  - [x] FileToolbarStorage for cross-process data sharing
  - [x] Comprehensive MCP documentation (docs/mcp.md)
  - [x] Screenshot in README and docs

---

## Next Up

### Phase 12: Multi-Framework Support (NEXT)
- [ ] Starlette adapter (core ASGI middleware)
- [ ] FastAPI adapter (builds on Starlette)
- [ ] Framework detection and auto-configuration

### Phase 14: Distributed Debugging
- [ ] OpenTelemetry integration
- [ ] Cross-service request tracing
- [ ] Span correlation

### Phase 6.2: Documentation & Benchmarks
- [ ] Performance benchmarks
- [ ] API documentation expansion
- [ ] Usage guides for each panel

### Phase 10.3: WebSocket Panel ✅ COMPLETE (PR #19)
- [x] WebSocket connection tracking
- [x] Message logging (sent/received with expandable content)
- [x] Connection lifecycle (connect, disconnect, close codes)
- [x] Real-time panel rendering with custom JS
- [x] WebSocket statistics (bytes sent/received, message counts)
- [x] Live updates via WebSocket endpoint (`/_debug_toolbar/ws/live`)
- [x] Event broadcasting to live subscribers
- [x] Max connections enforcement to prevent memory growth
- [x] Example application with Echo and Chat WebSocket demos
- [x] Unit and integration tests (45+ new tests)

---

## Success Metrics

### Achieved:
- ✅ 18 panels (more than any competitor)
- ✅ Best-in-class async profiling
- ✅ GraphQL debugging
- ✅ MCP server for AI integration
- ✅ WebSocket debugging with live updates (unique feature)

### Remaining:
- Multi-framework support (FastAPI, Starlette)
- OpenTelemetry integration
- 1000+ GitHub stars

---

*This plan positions async-python-debug-toolbar as the definitive debugging solution for modern async Python applications.*
