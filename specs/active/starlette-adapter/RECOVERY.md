# Recovery Guide: Starlette Adapter

**Feature**: Starlette Adapter for Debug Toolbar
**Workspace**: `/home/cody/code/litestar/debug-toolbar/specs/active/starlette-adapter/`
**Status**: PRD Complete, Ready for Implementation

---

## Quick Recovery

If you need to resume work on this feature, start here:

### Current State

✅ **PRD Complete** - Comprehensive PRD with 7,200+ words
✅ **Research Complete** - Pattern analysis, technical validation
✅ **Workspace Created** - Directory structure ready
❌ **Implementation** - Not started
❌ **Testing** - Not started
❌ **Documentation** - Not started

### Next Action

**Start Checkpoint 1**: Middleware & Config Implementation

```bash
# Read the PRD
cat specs/active/starlette-adapter/prd.md

# Review research findings
cat specs/active/starlette-adapter/research/plan.md

# Create first implementation file
touch src/debug_toolbar/starlette/__init__.py
touch src/debug_toolbar/starlette/middleware.py
touch src/debug_toolbar/starlette/config.py
```

---

## Workspace Structure

```
specs/active/starlette-adapter/
├── prd.md                      # ✅ Complete - Full PRD (7,200 words)
├── research/
│   └── plan.md                 # ✅ Complete - Research findings (2,100 words)
├── tmp/
│   └── new-patterns.md         # ⭕ Create during implementation
└── RECOVERY.md                 # ✅ This file
```

---

## Implementation Checklist

Use this to track progress (copy to `tmp/progress.md` when starting):

### Phase 1: Core Implementation (3 checkpoints)

- [ ] **Checkpoint 1: Middleware & Config**
  - [ ] Create `src/debug_toolbar/starlette/__init__.py`
  - [ ] Create `src/debug_toolbar/starlette/middleware.py` (~350 lines)
  - [ ] Create `src/debug_toolbar/starlette/config.py` (~85 lines)
  - [ ] Create `tests/starlette/conftest.py` (fixtures)
  - [ ] Create `tests/starlette/test_config.py`
  - [ ] Create `tests/starlette/test_middleware.py` (basic tests)
  - [ ] Run: `pytest tests/starlette/ -v`

- [ ] **Checkpoint 2: Request/Response Interception**
  - [ ] Implement send wrapper in middleware
  - [ ] Implement HTML injection logic
  - [ ] Implement Server-Timing headers
  - [ ] Add error handling with recovery
  - [ ] Write tests for injection scenarios
  - [ ] Write tests for error handling
  - [ ] Run: `pytest tests/starlette/test_middleware.py -v`

- [ ] **Checkpoint 3: Routes & Storage**
  - [ ] Create `src/debug_toolbar/starlette/routes.py` (~100 lines)
  - [ ] Create `src/debug_toolbar/starlette/panels/__init__.py`
  - [ ] Create `src/debug_toolbar/starlette/panels/routes.py` (~80 lines)
  - [ ] Implement route collection in middleware
  - [ ] Create `tests/starlette/test_routes.py`
  - [ ] Create `tests/starlette/panels/test_routes_panel.py`
  - [ ] Run: `pytest tests/starlette/ -v`

### Phase 2: Integration & Examples (3 checkpoints)

- [ ] **Checkpoint 4: Basic Example**
  - [ ] Create `examples/starlette_basic/app.py` (~150 lines)
  - [ ] Create `examples/starlette_basic/README.md`
  - [ ] Create `examples/starlette_basic/__init__.py`
  - [ ] Manual test: `uvicorn examples.starlette_basic.app:app --reload`
  - [ ] Verify toolbar appears in browser
  - [ ] Test all core panels work

- [ ] **Checkpoint 5: Advanced Example**
  - [ ] Create `examples/starlette_advanced/app.py`
  - [ ] Add Jinja2 template integration
  - [ ] Add SQLAlchemy integration (optional)
  - [ ] Demonstrate Memory and Profiling panels
  - [ ] Create production-like config
  - [ ] Manual testing

- [ ] **Checkpoint 6: Documentation**
  - [ ] Update `README.md` with Starlette section
  - [ ] Add installation instructions
  - [ ] Add usage examples
  - [ ] Document configuration options
  - [ ] Add comparison with Litestar integration

### Phase 3: Quality & Testing (2 checkpoints)

- [ ] **Checkpoint 7: Test Coverage**
  - [ ] Complete all test files (4 total)
  - [ ] Run: `make test-cov`
  - [ ] Verify 90%+ coverage for Starlette modules
  - [ ] Run full suite: `make test` (all 402 + new tests pass)
  - [ ] Write integration tests

- [ ] **Checkpoint 8: Review & Polish**
  - [ ] Run: `make lint` (pass)
  - [ ] Run: `make type-check` (pass)
  - [ ] Code review against patterns
  - [ ] Performance testing
  - [ ] Extract new patterns to `tmp/new-patterns.md`
  - [ ] Final manual testing

---

## Key Files to Reference

### Primary Implementation References

1. **Pattern Source**: `src/debug_toolbar/litestar/middleware.py`
   - ResponseState pattern
   - Send wrapper implementation
   - HTML injection logic
   - Error handling

2. **Config Pattern**: `src/debug_toolbar/litestar/config.py`
   - Dataclass structure
   - `should_show_toolbar()` logic
   - Panel registration

3. **Routes Pattern**: `src/debug_toolbar/litestar/routes/handlers.py`
   - Framework-agnostic rendering functions
   - Can import directly: `_render_request_row`, `get_toolbar_css`, etc.

4. **Panel Pattern**: `src/debug_toolbar/litestar/panels/routes.py`
   - Panel ABC implementation
   - Stats generation
   - Metadata collection

### Testing References

1. **Test Fixtures**: `tests/litestar/conftest.py`
   - Adapt for Starlette TestClient
   - Config fixtures
   - Toolbar fixtures

2. **Test Patterns**: `tests/litestar/test_middleware.py`
   - Middleware initialization tests
   - Injection tests
   - Error handling tests

### Documentation References

1. **Starlette Docs**: https://starlette.dev/middleware/
   - Pure ASGI middleware pattern
   - Type annotations
   - Request/Response API

2. **Pattern Library**: `specs/guides/patterns/README.md`
   - Code style (PEP 604, future annotations)
   - Testing patterns
   - Type handling

---

## Critical Implementation Notes

### 1. Use Pure ASGI Middleware

❌ **Don't use**:
```python
from starlette.middleware.base import BaseHTTPMiddleware

class DebugToolbarMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # DON'T DO THIS - has contextvars issues
```

✅ **Do use**:
```python
from starlette.types import ASGIApp, Scope, Receive, Send, Message

class DebugToolbarMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Pure ASGI pattern - recommended
```

**Rationale**: See `research/plan.md` - BaseHTTPMiddleware has known issues.

---

### 2. Reuse Framework-Agnostic Rendering

✅ **Do import and reuse**:
```python
from debug_toolbar.litestar.routes.handlers import (
    _render_request_row,
    _render_panel_content,
    get_toolbar_css,
    get_toolbar_js,
)
```

These functions have **zero framework dependencies** - they return pure HTML strings.

**Impact**: Saves ~400 lines of duplicate code.

---

### 3. ResponseState Pattern

✅ **Critical for race-condition-free state**:
```python
async def __call__(self, scope, receive, send):
    state = ResponseState()  # Per-request instance

    async def send_wrapper(message):
        nonlocal state  # Closure captures per-request state
        # Safe to modify state here
        await send(message)

    await self.app(scope, receive, send_wrapper)
```

**Don't use** `self.state` (shared across requests).

---

### 4. Error Recovery Pattern

✅ **Always send response on error**:
```python
try:
    await self.app(scope, receive, send_wrapper)
except Exception:
    # Cleanup: send buffered response if started but not sent
    if state.started and not state.headers_sent:
        await self._send_buffered_response(send, state)
    raise  # Re-raise after cleanup
finally:
    set_request_context(None)  # Always cleanup context
```

**Critical**: Prevents broken connections.

---

## Common Pitfalls

### Pitfall 1: Forgetting to Filter Non-HTTP Requests

❌ **Wrong**:
```python
async def __call__(self, scope, receive, send):
    # Process all requests - breaks WebSocket!
    await self.app(scope, receive, send)
```

✅ **Correct**:
```python
async def __call__(self, scope, receive, send):
    if scope["type"] != "http":
        await self.app(scope, receive, send)
        return
    # Only process HTTP requests
```

---

### Pitfall 2: Not Cleaning Up Context

❌ **Wrong**:
```python
async def __call__(self, scope, receive, send):
    context = await self.toolbar.process_request()
    await self.app(scope, receive, send)
    # Context leaks to next request!
```

✅ **Correct**:
```python
async def __call__(self, scope, receive, send):
    context = await self.toolbar.process_request()
    try:
        await self.app(scope, receive, send)
    finally:
        set_request_context(None)  # Always cleanup
```

---

### Pitfall 3: Blocking on Response Body

❌ **Wrong**:
```python
async def send_wrapper(message):
    if message["type"] == "http.response.body":
        body = message["body"]
        # Process immediately - breaks streaming!
```

✅ **Correct**:
```python
async def send_wrapper(message):
    if message["type"] == "http.response.body":
        state.body_chunks.append(message.get("body", b""))

        if not message.get("more_body", False):
            # Only process when complete
            await self._inject_and_send(send, state)
            return

    await send(message)
```

---

## Testing Strategy

### Unit Tests (~600 lines total)

1. **`test_config.py`** (~150 lines):
   - Config defaults
   - `should_show_toolbar()` logic
   - Path/pattern exclusion
   - Callback override

2. **`test_middleware.py`** (~250 lines):
   - Middleware initialization
   - Request interception
   - HTML injection
   - Server-Timing headers
   - Error handling
   - Excluded paths
   - Non-HTML responses

3. **`test_routes.py`** (~100 lines):
   - Route handlers
   - History page
   - Detail page
   - JSON API
   - Static files

4. **`test_routes_panel.py`** (~100 lines):
   - Route collection
   - Stats generation
   - Various route types
   - Matched route detection

### Manual Testing Checklist

```bash
# 1. Start example app
uvicorn examples.starlette_basic.app:app --reload

# 2. Open browser: http://localhost:8000

# 3. Verify:
- [ ] Toolbar appears on right side
- [ ] Can move toolbar (left/right/top/bottom)
- [ ] All core panels load
- [ ] Routes panel shows app routes
- [ ] Click panel buttons - details appear
- [ ] History page works: http://localhost:8000/_debug_toolbar/
- [ ] Detail page works (click request ID)
- [ ] Server-Timing header present (DevTools Network tab)
- [ ] No toolbar on /_debug_toolbar/ paths
- [ ] JSON responses have no toolbar

# 4. Test error handling:
- [ ] Trigger 404 - toolbar still appears
- [ ] Trigger 500 - toolbar still appears
- [ ] Check logs - no errors from toolbar
```

---

## Performance Benchmarks

Run these before/after to measure overhead:

```bash
# Benchmark without toolbar
ab -n 1000 -c 10 http://localhost:8000/

# Benchmark with toolbar (excluded path)
ab -n 1000 -c 10 http://localhost:8000/api/status

# Target: <5ms overhead for excluded paths
# Target: <20ms overhead for HTML injection
```

---

## Quick Commands

```bash
# Development setup
make dev

# Run Starlette tests only
pytest tests/starlette/ -v

# Run with coverage
pytest tests/starlette/ --cov=src/debug_toolbar/starlette --cov-report=html

# Run all tests (including existing 402)
make test

# Type checking
make type-check

# Linting
make lint

# Auto-fix linting
make lint-fix

# Manual testing
uvicorn examples.starlette_basic.app:app --reload
```

---

## Dependencies

### Required (add to pyproject.toml)

```toml
[project.optional-dependencies]
starlette = [
    "starlette>=0.27.0",
]
```

### For Examples

```bash
pip install uvicorn[standard]  # ASGI server
pip install jinja2              # Templates (advanced example)
```

---

## Completion Criteria

✅ Feature is complete when:

1. **All checkpoints passed** (8 of 8)
2. **Test coverage ≥90%** for Starlette modules
3. **All tests pass** (402 existing + ~100 new)
4. **Quality gates pass**:
   - `make lint` - no errors
   - `make type-check` - no errors
5. **Manual testing complete**:
   - Basic example runs
   - Toolbar appears and functions
   - All panels work
6. **Documentation updated**:
   - README has Starlette section
   - Examples documented
7. **Pattern extraction**:
   - New patterns documented in `tmp/new-patterns.md`

---

## Help & Resources

### If Stuck on Implementation

1. **Read research plan**: `specs/active/starlette-adapter/research/plan.md`
2. **Compare with Litestar**: `src/debug_toolbar/litestar/middleware.py`
3. **Check Starlette docs**: https://starlette.dev/middleware/
4. **Review PRD**: `specs/active/starlette-adapter/prd.md` (Section: Technical Approach)

### If Tests Failing

1. **Check fixtures**: Compare with `tests/litestar/conftest.py`
2. **Review test patterns**: `tests/litestar/test_middleware.py`
3. **Verify cleanup**: `set_request_context(None)` in finally blocks
4. **Check async markers**: `@pytest.mark.asyncio` on async tests

### If Type Errors

1. **Import types**: `from starlette.types import ASGIApp, Scope, Receive, Send, Message`
2. **Add future annotations**: `from __future__ import annotations` at top
3. **Use PEP 604**: `T | None` instead of `Optional[T]`
4. **TYPE_CHECKING imports**: For circular dependencies

---

## Session Recovery Template

Copy this when resuming work:

```markdown
## Session: [Date]

**Starting Point**: [Checkpoint number or task]

**Goals for Session**:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Files Modified**:
- [ ] file1.py
- [ ] file2.py

**Tests Run**:
- [ ] pytest tests/starlette/ -v
- [ ] make test
- [ ] make lint

**Issues Encountered**:
- Issue 1: [description] - Solution: [...]

**Next Session**:
- Start with: [...]
```

---

## Contact / Handoff Notes

If handing off to another developer:

1. **Start here**: Read PRD (`prd.md`) - skip to "Technical Approach" section
2. **Understand patterns**: Read research plan (`research/plan.md`)
3. **Reference implementation**: Study `src/debug_toolbar/litestar/middleware.py`
4. **Run existing tests**: `make test` - verify baseline
5. **Create first file**: Follow Checkpoint 1 checklist above

**Estimated Time**: 8-12 hours for experienced developer (all checkpoints)

---

**Last Updated**: 2025-11-29
**Status**: Ready for Implementation
**Confidence**: 93% (High)
