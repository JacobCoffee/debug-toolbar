# Debug Toolbar Implementation Roadmap

**Created**: 2025-11-29
**Status**: Active
**Test Count**: 402 (all passing)

---

## Executive Summary

This roadmap breaks down the remaining PLAN.md work into 13 manageable PRs, ordered by priority and dependencies. The codebase is more mature than PLAN.md indicates - several "TODO" items are already complete.

### Already Complete (Not in PLAN.md)
- Alerts Panel (full implementation)
- Memory Panel (multi-backend: tracemalloc + memray)
- Flame Graph generator (speedscope format)

---

## Implementation Order

### Tier 1: Core Differentiation (Do First)

| Order | PR | Title | Priority | Effort | Unique Value |
|-------|-----|-------|----------|--------|--------------|
| **1** | PR #5 | [Async Profiling Panel](specs/pr05-async-profiler.md) | P1 | High | No competitor has this |
| **2** | PR #2 | [WebSocket Panel](specs/pr02-websocket-panel.md) | P1 | High | Unique feature |
| **3** | PR #7 | [Starlette Adapter](specs/pr07-starlette-adapter.md) | P1 | Medium | 10x user base expansion |

### Tier 2: Framework Expansion

| Order | PR | Title | Priority | Effort | Value |
|-------|-----|-------|----------|--------|-------|
| **4** | PR #8 | [FastAPI Adapter](specs/pr08-fastapi-adapter.md) | P1 | Low | Largest ASGI user base |
| **5** | PR #1 | [SAQ Panel](specs/pr01-saq-panel.md) | P1 | Medium | Modern async apps |
| **6** | PR #6 | Flame Graph UI | P2 | Medium | Visual appeal |

### Tier 3: Ecosystem Integration

| Order | PR | Title | Priority | Effort | Value |
|-------|-----|-------|----------|--------|-------|
| **7** | PR #3 | [GraphQL Panel](specs/pr03-graphql-panel.md) | P2 | Medium | Competitor parity |
| **8** | PR #9 | [MCP Server](specs/pr09-mcp-server.md) | P2 | High | AI integration |
| **9** | PR #11 | [OpenTelemetry](specs/pr11-opentelemetry.md) | P2 | High | Enterprise appeal |

### Tier 4: Polish & Release

| Order | PR | Title | Priority | Effort | Value |
|-------|-----|-------|----------|--------|-------|
| **10** | PR #12 | Performance Benchmarks | P2 | Low | Release confidence |
| **11** | PR #13 | Documentation | P1 | Low | Required for adoption |
| **12** | PR #10 | Export/Share | P3 | Low | Team collaboration |
| **13** | PR #4 | OpenAPI Integration | P3 | Low | Nice-to-have |

---

## Dependency Graph

```
              ┌─────────────────────────────────────┐
              │ PR #7: Starlette Adapter            │
              └─────────────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────────────┐
              │ PR #8: FastAPI Adapter              │
              └─────────────────────────────────────┘

         All Feature PRs
              │
              ▼
┌─────────────────────────────────────┐
│ PR #13: Documentation               │
└─────────────────────────────────────┘
```

**Note**: Most PRs are independent and can be worked in parallel.

---

## Timeline Estimates

| Milestone | PRs | Focus |
|-----------|-----|-------|
| **M1** | #5, #2 | Unique differentiators |
| **M2** | #7, #8 | Multi-framework support |
| **M3** | #1, #3, #6 | Extended panels |
| **M4** | #9, #11 | Integrations |
| **M5** | #12, #13, #10, #4 | Polish & release |

---

## Risk Assessment

| PR | Risk | Mitigation |
|----|------|------------|
| PR #5 (Async) | High - Event loop hooks | Prototype first |
| PR #2 (WebSocket) | Medium - Litestar API | Study existing middleware |
| PR #9 (MCP) | Medium - Spec evolving | Pin version |
| PR #11 (OTEL) | Medium - Large API | Scope carefully |

---

## Success Metrics

### Per-PR
- 90%+ test coverage
- All existing tests pass
- Documentation complete

### Project-Level
- Multi-framework support (Litestar, Starlette, FastAPI)
- Unique features (async profiling, WebSocket)
- AI integration (MCP)
- 1000+ GitHub stars

---

## Spec Files

Detailed specifications for each PR:

```
specs/active/roadmap-breakdown/
├── prd.md                              # Master PRD
├── ROADMAP.md                          # This file
└── specs/
    ├── pr01-saq-panel.md               # Background tasks
    ├── pr02-websocket-panel.md         # WebSocket tracking
    ├── pr03-graphql-panel.md           # GraphQL/Strawberry
    ├── pr05-async-profiler.md          # Async profiling
    ├── pr07-starlette-adapter.md       # Starlette support
    ├── pr08-fastapi-adapter.md         # FastAPI support
    ├── pr09-mcp-server.md              # MCP integration
    └── pr11-opentelemetry.md           # OTEL integration
```

---

## How to Use

1. **Pick a PR**: Start with highest priority available
2. **Read spec**: Review detailed specification
3. **Implement**: Follow patterns in existing code
4. **Test**: Achieve 90%+ coverage
5. **Document**: Update docs as needed

### Command Flow

```bash
# Read the spec
cat specs/active/roadmap-breakdown/specs/pr05-async-profiler.md

# Implement
/implement async-profiler

# Test
make test-cov

# Review
/review async-profiler
```

---

## PLAN.md Updates Needed

The main PLAN.md file should be updated to reflect:

1. **Test count**: 402 (not 305)
2. **Alerts Panel**: COMPLETE
3. **Memory Panel**: COMPLETE (multi-backend)
4. **Flame Graph**: COMPLETE (generator)
5. **Phase markers**: Several items done

Consider archiving completed phases and focusing on remaining work.
