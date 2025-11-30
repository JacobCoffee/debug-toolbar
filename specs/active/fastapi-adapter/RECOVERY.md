# Session Recovery Guide: FastAPI Adapter

**Feature**: FastAPI Adapter for Debug Toolbar
**Slug**: `fastapi-adapter`
**Status**: PRD Complete, Ready for Implementation
**Last Updated**: 2025-11-29

---

## Quick Context

This feature adds FastAPI framework support to the debug-toolbar project. The unique value proposition is the **Dependency Injection Panel** that tracks FastAPI's dependency resolution, caching behavior, and timing.

**Complexity**: Simple (6 checkpoints)
**Key Dependency**: Starlette adapter (prerequisite)

---

## Workspace Structure

```
specs/active/fastapi-adapter/
├── prd.md                    # Complete PRD (~5,800 words)
├── research/
│   └── plan.md              # Research notes (~2,400 words)
├── tmp/
│   └── new-patterns.md      # For pattern discovery during implementation
└── RECOVERY.md              # This file
```

---

## Current State

### Completed
- [x] Research phase complete
- [x] PRD written and comprehensive
- [x] Patterns analyzed (Litestar integration, Events panel)
- [x] Architecture decisions documented
- [x] Testing strategy defined
- [x] Example application designed
- [x] Workspace created

### In Progress
- [ ] None (waiting for implementation phase)

### Blocked
- [ ] Starlette adapter completion (prerequisite)

---

## Key Files Reference

### PRD Location
`/home/cody/code/litestar/debug-toolbar/specs/active/fastapi-adapter/prd.md`

**Sections to review**:
- **Acceptance Criteria** (page 8-10): Detailed requirements
- **Technical Approach** (page 11-18): Implementation guide
- **Files to Create** (page 19-20): Complete file list
- **Testing Strategy** (page 16-17): Coverage targets

### Research Location
`/home/cody/code/litestar/debug-toolbar/specs/active/fastapi-adapter/research/plan.md`

**Key sections**:
- **Research Questions** (page 2-7): FastAPI DI internals
- **Pattern Analysis** (page 7-9): Litestar patterns to reuse
- **Architecture Decisions** (page 9-10): Why we chose this approach

---

## Implementation Checklist

When ready to implement, follow these phases:

### Phase 1: Foundation (Checkpoint 1-2)
- [ ] Verify Starlette adapter is complete
- [ ] Create file structure: `src/debug_toolbar/fastapi/`
- [ ] Implement `FastAPIDebugToolbarConfig`
- [ ] Write config unit tests
- [ ] **Goal**: Config tested and working

### Phase 2: Middleware (Checkpoint 2-3)
- [ ] Implement `DebugToolbarMiddleware` (wraps Starlette)
- [ ] Add DI tracking hooks
- [ ] Implement `setup_debug_toolbar()` helper
- [ ] Write middleware unit tests
- [ ] **Goal**: Middleware integrates with FastAPI

### Phase 3: DI Panel (Checkpoint 3)
- [ ] Implement `DependencyInjectionPanel` class
- [ ] Implement helper functions:
  - `collect_dependency_metadata()`
  - `record_dependency_resolution()`
  - `_get_dependency_info()`
- [ ] Write DI panel unit tests
- [ ] **Goal**: Panel displays dependency data

### Phase 4: Testing (Checkpoint 4)
- [ ] Create integration test suite
- [ ] Test with various dependency patterns
- [ ] Test cache behavior
- [ ] Test nested dependencies
- [ ] Verify 90%+ coverage
- [ ] **Goal**: All tests passing, coverage met

### Phase 5: Example (Checkpoint 5)
- [ ] Create `examples/fastapi_basic/` directory
- [ ] Implement `main.py` with FastAPI app
- [ ] Implement `dependencies.py` with example dependencies
- [ ] Add README and requirements.txt
- [ ] Test example app runs correctly
- [ ] **Goal**: Working example demonstrating DI panel

### Phase 6: Documentation (Checkpoint 6)
- [ ] Update main README with FastAPI support
- [ ] Write integration guide: `docs/integrations/fastapi.md`
- [ ] Write DI panel guide: `docs/panels/dependency-injection.md`
- [ ] Extract patterns to pattern library
- [ ] Code review
- [ ] **Goal**: Feature complete and documented

---

## Critical Decisions

### Decision 1: Middleware Strategy
**What**: Wrap Starlette middleware, add DI tracking hooks
**Why**: Maximum code reuse, FastAPI built on Starlette
**See**: `research/plan.md`, "AD-1: Middleware Strategy"

### Decision 2: DI Tracking Approach
**What**: Middleware-level inspection using `route.dependant`
**Why**: Non-invasive, version-stable, uses public APIs
**Alternative**: Monkey-patch `solve_dependencies` (too fragile)
**See**: `research/plan.md`, "AD-2: DI Tracking Approach"

### Decision 3: Panel Scope
**What**: DI panel only in v1
**Why**: Clear value prop, manageable scope
**Deferred**: OpenAPI panel, Pydantic validation panel
**See**: `research/plan.md`, "AD-3: Panel Scope"

---

## Key Patterns to Follow

### 1. Config Inheritance Pattern
```python
@dataclass
class FastAPIDebugToolbarConfig(DebugToolbarConfig):
    exclude_paths: Sequence[str] = field(default_factory=lambda: [...])
    track_dependency_injection: bool = True

    def __post_init__(self) -> None:
        # Auto-register DI panel if tracking enabled
```
**Reference**: `src/debug_toolbar/litestar/config.py`

### 2. Metadata Collection Pattern
```python
def collect_dependency_metadata(app: FastAPI, context: RequestContext) -> None:
    """Initialize dependency metadata structure."""
    context.metadata["dependencies"] = {...}

def record_dependency_resolution(...) -> None:
    """Record a dependency resolution event."""
```
**Reference**: `src/debug_toolbar/litestar/panels/events.py`

### 3. Panel Statistics Pattern
```python
async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
    dependencies_data = context.metadata.get("dependencies", {})
    # Compute stats from raw metadata
    return {...}
```
**Reference**: `src/debug_toolbar/litestar/panels/events.py`

---

## Testing Targets

- **Config**: 95%+ coverage
- **Middleware**: 90%+ coverage
- **DI Panel**: 95%+ coverage
- **Overall**: 90%+ coverage

**Test Files**:
- `tests/unit/test_fastapi_config.py` (~15 tests)
- `tests/unit/test_fastapi_middleware.py` (~12 tests)
- `tests/unit/test_dependency_injection_panel.py` (~20 tests)
- `tests/integration/test_fastapi_integration.py` (~8 tests)

---

## Common Issues & Solutions

### Issue: "Cannot import FastAPI"
**Solution**: Add FastAPI to dependencies
```bash
uv add fastapi
```

### Issue: "Starlette adapter not found"
**Solution**: Wait for/implement Starlette adapter first
**Check**: `src/debug_toolbar/starlette/` exists

### Issue: "DI tracking overhead too high"
**Solution**:
1. Make tracking optional: `track_dependency_injection=False`
2. Benchmark and optimize hot paths
3. Consider caching dependency info at startup

### Issue: "Circular dependency detected"
**Solution**: Implement cycle detection in tree builder
```python
def build_tree(dep, visited=None):
    visited = visited or set()
    if dep in visited:
        return {"error": "Circular dependency"}
    visited.add(dep)
    # ...
```

---

## File Locations

### Implementation Files
```
src/debug_toolbar/fastapi/
├── __init__.py
├── config.py
├── middleware.py
├── setup.py
└── panels/
    ├── __init__.py
    └── dependencies.py
```

### Test Files
```
tests/unit/
├── test_fastapi_config.py
├── test_fastapi_middleware.py
└── test_dependency_injection_panel.py

tests/integration/
└── test_fastapi_integration.py
```

### Example Files
```
examples/fastapi_basic/
├── main.py
├── dependencies.py
├── requirements.txt
└── README.md
```

### Documentation Files
```
docs/integrations/fastapi.md
docs/panels/dependency-injection.md
```

---

## Code Standards Reminder

**Critical**:
- [ ] `from __future__ import annotations` at top of every file
- [ ] Use `T | None`, not `Optional[T]`
- [ ] ClassVar for panel metadata
- [ ] TYPE_CHECKING for type-only imports
- [ ] Google-style docstrings
- [ ] Clean up context vars in tests: `set_request_context(None)`

**Quality Gates**:
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] 90%+ coverage

---

## Resources

### External Documentation
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI Advanced Dependencies](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)
- [Starlette Middleware](https://www.starlette.io/middleware/)

### Research Sources (from PRD)
- [FastAPI Dependency Injection: Beyond The Basics](https://dev.turmansolutions.ai/2025/08/26/fastapi-dependency-injection-beyond-the-basics/)
- [FastAPI Dependency Caching](https://www.compilenrun.com/docs/framework/fastapi/fastapi-dependency-injection/fastapi-dependency-caching/)
- [Understanding FastAPI's Built-In Dependency Injection](https://developer-service.blog/understading-fastapis-built-in-dependency-injection/)
- [Inside FastAPI's Routing Core](https://zalt.me/blog/2025/10/inside-fastapi-routing)

### Internal References
- Litestar integration: `src/debug_toolbar/litestar/`
- Events panel: `src/debug_toolbar/litestar/panels/events.py`
- Core panel base: `src/debug_toolbar/core/panel.py`
- Pattern library: `specs/guides/patterns/README.md`

---

## Next Steps

When resuming this feature:

1. **Check prerequisite**: Is Starlette adapter complete?
   ```bash
   ls src/debug_toolbar/starlette/
   ```

2. **Read PRD**: Review acceptance criteria and technical approach
   ```bash
   cat specs/active/fastapi-adapter/prd.md
   ```

3. **Start with config**: Easiest entry point
   ```bash
   touch src/debug_toolbar/fastapi/config.py
   touch tests/unit/test_fastapi_config.py
   ```

4. **Run tests continuously**:
   ```bash
   make test-fast  # Unit tests only
   make test-cov   # With coverage
   ```

5. **Follow checkpoints**: 6 checkpoints, ~15 working days estimated

---

## Success Criteria

### Functional
- [ ] FastAPI app can integrate debug toolbar in <5 lines of code
- [ ] DI panel shows all resolved dependencies with cache status
- [ ] Example app runs and demonstrates DI tracking

### Quality
- [ ] 90%+ test coverage
- [ ] All quality gates pass
- [ ] No anti-patterns in code

### Performance
- [ ] <5% overhead with DI tracking enabled
- [ ] 0% overhead when toolbar disabled

### Documentation
- [ ] Integration guide complete
- [ ] Example app has README
- [ ] API docs generated

---

## Contact & Questions

**Feature Owner**: [Your Name]
**Reviewers**: Core maintainers
**Slack/Discord**: [Project channel]

**Questions to ask**:
1. Is Starlette adapter ready? Who's working on it?
2. Any changes to core panel architecture?
3. Performance budget still <5% overhead?

---

**Last Updated**: 2025-11-29
**Status**: Ready for Implementation
**Next Action**: Wait for Starlette adapter OR start parallel with mock adapter
