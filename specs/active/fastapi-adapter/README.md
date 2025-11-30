# FastAPI Adapter - Feature Workspace

**Status**: PRD Complete, Ready for Implementation
**Priority**: P1 (Largest ASGI user base)
**Complexity**: Simple (6 checkpoints)
**Created**: 2025-11-29

---

## Quick Links

- **PRD**: `prd.md` (~4,950 words)
- **Research**: `research/plan.md` (~2,260 words)
- **Recovery Guide**: `RECOVERY.md`
- **New Patterns**: `tmp/new-patterns.md`

---

## Feature Summary

Adds FastAPI framework support to debug-toolbar with a unique **Dependency Injection Panel** that tracks:
- Dependency resolution and caching
- Dependency tree hierarchy
- Resolution timing
- Cache hit rates

**Key Differentiator**: FastAPI's DI system tracking - no other debug toolbar offers this.

---

## Next Steps

1. **Wait for prerequisite**: Starlette adapter must be complete
2. **Review PRD**: Read `prd.md` for full requirements
3. **Start implementation**: Follow 6 checkpoints in RECOVERY.md
4. **Target timeline**: ~15 working days

---

## Files Structure

```
specs/active/fastapi-adapter/
├── README.md                 # This file
├── prd.md                    # Complete PRD (5,800 words)
├── RECOVERY.md               # Session recovery guide
├── research/
│   └── plan.md              # Research notes (2,400 words)
└── tmp/
    └── new-patterns.md      # Pattern discovery during implementation
```

---

## Key Decisions

1. **Middleware Strategy**: Wrap Starlette middleware, add DI hooks
2. **DI Tracking**: Middleware-level inspection, non-invasive
3. **Panel Scope**: DI panel only in v1, defer OpenAPI/Pydantic panels

See `research/plan.md` for detailed rationale.

---

## Acceptance Criteria Highlights

- FastAPIDebugToolbarConfig with framework-specific options
- Middleware integration via `app.add_middleware()`
- DependencyInjectionPanel showing cache status and timing
- 90%+ test coverage
- Example app with realistic dependencies
- Integration guide and documentation

See `prd.md` section "Acceptance Criteria" for complete list.

---

## Testing Strategy

- **Unit tests**: Config, middleware, panel (~57 tests)
- **Integration tests**: Real FastAPI app (~13 tests)
- **Coverage target**: 90%+ overall
- **Performance target**: <5% overhead

See `prd.md` section "Testing Strategy" for details.

---

## Dependencies

**Required**:
- Starlette adapter (prerequisite)
- FastAPI >= 0.100.0
- Starlette >= 0.27.0

**Optional** (for examples):
- Uvicorn
- SQLAlchemy

---

## Timeline Estimate

- Week 1: Foundation and setup
- Week 2: Core features and testing
- Week 3: Polish and documentation

**Total**: ~15 working days

---

## Contact

**Feature Owner**: [Your Name]
**Status**: Ready for implementation
**Last Updated**: 2025-11-29
