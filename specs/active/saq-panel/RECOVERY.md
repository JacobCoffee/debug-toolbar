# Session Recovery Guide: SAQ Panel

**Feature**: SAQ Background Tasks Panel
**Slug**: `saq-panel`
**Status**: PRD Complete, Awaiting Implementation
**Last Updated**: 2025-11-29

---

## Quick Resume

### Current State

✅ **PRD Phase Complete**
- Comprehensive PRD created (7,800+ words)
- Research plan documented (2,400+ words)
- Pattern analysis complete (3 similar implementations studied)
- Technical approach defined
- All 8 checkpoints identified

🔲 **Implementation Phase** - Not Started
🔲 **Testing Phase** - Not Started
🔲 **Review Phase** - Not Started

### Next Action

If resuming this work, say:

```
/implement saq-panel
```

This will start the implementation phase using the PRD as specification.

---

## Project Context

### What is This Feature?

A debug toolbar panel that automatically tracks background tasks enqueued via SAQ (Simple Async Queue) during HTTP requests. Provides visibility into:
- Task count and timing
- Function names and arguments
- Scheduled vs immediate tasks
- N+1 task pattern detection
- Call stack origins

### Why It Matters

Modern async apps use background task queues extensively. Developers currently have zero visibility into tasks spawned during requests, making debugging and optimization difficult. This panel solves that with zero-config automatic tracking.

### Priority: P1 (High)

Modern async applications increasingly rely on background tasks. This panel addresses a critical gap in debugging capabilities.

---

## Files Created

### Workspace Files

All files in: `/home/cody/code/litestar/debug-toolbar/specs/active/saq-panel/`

1. **prd.md** (7,800 words)
   - Complete product requirements document
   - Technical architecture and design
   - Acceptance criteria (Must/Should/Could Have)
   - Implementation plan with 8 checkpoints
   - Testing strategy (90%+ coverage target)
   - UI mockups and examples

2. **research/plan.md** (2,400 words)
   - Pattern recognition from 3 similar implementations
   - SAQ API research and documentation
   - Technical approach evaluation
   - Risk assessment
   - Open questions and decisions

3. **RECOVERY.md** (this file)
   - Session continuity guide
   - Quick reference for resuming work

### Source Files

None yet (implementation not started).

Will create:
- `src/debug_toolbar/extras/saq/__init__.py`
- `src/debug_toolbar/extras/saq/tracker.py`
- `src/debug_toolbar/extras/saq/panel.py`

### Test Files

None yet (implementation not started).

Will create:
- `tests/unit/test_saq_panel.py`
- `tests/integration/test_saq_integration.py`

---

## Key Decisions Made

### 1. Monkey Patching Approach

**Decision**: Use monkey patching to wrap `Queue.enqueue()` method.

**Rationale**:
- Zero-config user experience (no code changes)
- Follows pattern from SQLAlchemy panel
- Works with any Queue instance automatically

**Alternative Rejected**: Custom Queue subclass (worse UX, requires code changes)

**Implementation Detail**: Store original method reference, restore on cleanup.

---

### 2. Tracker Pattern

**Decision**: Use global `_tracker` singleton with start/stop lifecycle.

**Rationale**:
- Proven pattern from SQLAlchemy panel
- Request-scoped via `process_request()` / `process_response()`
- Thread-safe via contextvar integration

**Pattern Reference**: `src/debug_toolbar/extras/advanced_alchemy/panel.py:338`

---

### 3. Stack Capture Enabled by Default

**Decision**: Enable call stack capture by default.

**Rationale**:
- Debug toolbar is for development (overhead acceptable)
- High value for debugging (identify task origin)
- Can be disabled: `SAQPanel(toolbar, capture_stacks=False)`

**Performance Impact**: ~0.5ms per task (acceptable for dev)

---

### 4. Status Refresh Deferred to Phase 3

**Decision**: Make real-time job status refresh optional (P2 priority).

**Rationale**:
- Core value is tracking enqueued tasks (metadata only)
- Status refresh requires API endpoint + Redis queries
- Reduces initial scope
- Can be added later without breaking changes

---

### 5. Track enqueue() Only

**Decision**: Only track `Queue.enqueue()`, not `apply()` or `map()`.

**Rationale**:
- `apply()` executes inline (not a background task)
- `map()` internally calls `enqueue()` (already tracked)
- Simplifies implementation

---

## Implementation Checkpoints (8 Total)

- [ ] 1. TaskTracker implementation with enqueue tracking
- [ ] 2. Queue.enqueue() monkey patching with original preservation
- [ ] 3. SAQPanel class with lifecycle hooks
- [ ] 4. generate_stats() with task aggregation
- [ ] 5. Unit tests (TaskTracker, wrapping, panel) - 90%+ coverage
- [ ] 6. Integration tests with real/mock Queue
- [ ] 7. Optional status refresh endpoint
- [ ] 8. Documentation and pattern extraction

---

## Pattern References

### Similar Implementations Studied

1. **SQLAlchemy Panel** (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)
   - 588 lines
   - Event listener wrapping pattern
   - Global `_tracker` with request-scoped state
   - N+1 detection via pattern hashing
   - Stack capture with library frame filtering

2. **Timer Panel** (`src/debug_toolbar/core/panels/timer.py`)
   - 74 lines
   - Simple lifecycle hooks
   - Instance state in `__slots__`
   - Server-Timing contribution

3. **Panel Base Class** (`src/debug_toolbar/core/panel.py`)
   - 148 lines
   - ABC with ClassVar metadata
   - Abstract `generate_stats()`
   - Optional lifecycle hooks

### Patterns to Follow

- **Type Hints**: PEP 604 (`T | None`), future annotations
- **Docstrings**: Google style with Args/Returns
- **Testing**: Class-based, async fixtures, context cleanup
- **Error Handling**: Graceful degradation for missing dependencies

---

## External Dependencies

### Required (Runtime)

- `saq >= 0.24.0` (optional, graceful degradation)
- `redis-py >= 4.2.0` (transitive via saq)

### Required (Testing)

- `pytest-asyncio` (already in project)
- `fakeredis >= 2.0.0` (optional, for tests without Redis)

### Documentation References

- [SAQ Official Docs](https://saq-py.readthedocs.io/en/latest/)
- [SAQ GitHub](https://github.com/tobymao/saq)
- [Getting Started Guide](https://saq-py.readthedocs.io/en/latest/getting_started.html)

---

## Technical Deep Dive

### Architecture Overview

```
Request Start
    ↓
SAQPanel.process_request()
    ↓
_tracker.start() → Clear tasks, set enabled=True
    ↓
[User code calls queue.enqueue()]
    ↓
_wrapped_enqueue() intercepts
    ↓
_original_enqueue() executes → Returns Job
    ↓
_tracker.track_job(job, duration) → Store metadata
    ↓
[More enqueue calls...]
    ↓
SAQPanel.process_response()
    ↓
_tracker.stop() → Set enabled=False
    ↓
SAQPanel.generate_stats()
    ↓
Convert tasks to dict
Detect N+1 patterns
Calculate summary stats
    ↓
Render panel UI
```

### Data Model

```python
@dataclass
class TrackedTask:
    job_id: str                      # SAQ job UUID
    function_name: str               # Function to execute
    kwargs: dict[str, Any]           # Serialized arguments
    enqueued_at: float               # Unix timestamp
    enqueue_duration_ms: float       # Overhead in ms
    scheduled: float | None          # Scheduled time (optional)
    timeout: int | None              # Timeout in seconds
    retries: int | None              # Retry count
    ttl: int | None                  # Time to live
    queue_id: str                    # Queue identifier
    stack: list[dict[str, Any]]      # Call stack frames
    pattern_hash: str                # For N+1 detection
```

### Key Algorithms

#### N+1 Detection

1. Group tasks by `pattern_hash` (function name hash)
2. Within each pattern group, group by `origin_key` (call stack hash)
3. If count >= threshold (default: 3), flag as N+1
4. Sort by count descending
5. Generate fix suggestion

**Threshold**: 3 tasks (configurable)

**Example**:
- Same function enqueued 5 times from `handlers.py:45`
- Flagged as N+1
- Suggestion: "Consider batching with queue.map()"

#### Stack Capture

1. Use `traceback.extract_stack()`
2. Filter frames:
   - Skip library frames (saq, debug_toolbar, asyncio, pytest)
   - Skip site-packages
3. Extract: file, line, function, code
4. Limit to 5 most relevant frames (last 5 after filtering)

**Performance**: ~0.5ms per task

---

## Testing Strategy

### Coverage Target: >= 90%

### Unit Test Structure

```python
# tests/unit/test_saq_panel.py

class TestTaskTracker:
    # 10 tests: start, stop, track_job, serialization, stack capture

class TestQueueWrapping:
    # 7 tests: setup, restore, wrapping behavior, error handling

class TestSAQPanel:
    # 15 tests: metadata, lifecycle, generate_stats, N+1 detection
```

### Integration Tests

```python
# tests/integration/test_saq_integration.py

# Real Queue with fakeredis
# Full lifecycle test
# Multiple queue test
```

### Key Test Fixtures

```python
@pytest.fixture
def task_tracker() -> TaskTracker
    # Fresh tracker with cleanup

@pytest.fixture
def mock_job()
    # Mock SAQ Job object

@pytest.fixture
def saq_panel(mock_toolbar)
    # Panel instance

@pytest.fixture
def context()
    # RequestContext with cleanup
```

---

## Performance Targets

### Overhead

- **Per-task overhead**: < 1ms
  - Metadata capture: ~0.1ms
  - Serialization: ~0.2ms
  - Stack capture: ~0.5ms (if enabled)

- **Total overhead**: 10-20% of actual enqueue time
  - Actual Redis enqueue: 1-5ms
  - Panel overhead: 0.3-0.8ms
  - **Ratio**: Acceptable for debug toolbar

### Memory

- **Per-task**: ~1-2KB
- **Typical request**: 10 tasks = 20KB
- **Heavy request**: 50 tasks = 100KB
- **Cleanup**: Cleared after each request

### Scalability

- Safe for production (if needed)
- Consider disabling stack capture in high-traffic
- No cross-request accumulation

---

## UI Mockup Summary

### Panel Header
```
Background Tasks | 12 tasks (8 immediate, 4 scheduled) | 45.2ms total
```

### Summary Section
- Total tasks
- Immediate vs scheduled breakdown
- Total enqueue time
- Average per task

### N+1 Warnings
- Function name and count
- Origin (file:line in function)
- Suggestion (batch with queue.map())

### Task List
For each task:
- Job ID
- Function name
- Arguments (truncated)
- Timing
- Configuration (retries, timeout, ttl)
- Origin (call stack)
- Optional: Refresh Status button (P2)

---

## Common Pitfalls to Avoid

### 1. Forgetting Context Cleanup in Tests

**Problem**: Context vars leak between tests.

**Solution**: Always cleanup in fixtures:
```python
@pytest.fixture
def context():
    ctx = RequestContext()
    set_request_context(ctx)
    yield ctx
    set_request_context(None)  # ← Critical
```

### 2. Using Optional[T] Instead of T | None

**Problem**: PEP 604 is project standard.

**Solution**: Use `T | None` everywhere, add `from __future__ import annotations`.

### 3. Missing TYPE_CHECKING Guards

**Problem**: Circular imports.

**Solution**:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saq import Job  # Only for type checking
```

### 4. Forgetting to Restore Original Method

**Problem**: Monkey patch leaks into other tests.

**Solution**: Store `_original_enqueue`, provide `_remove_queue_wrapping()`.

### 5. Infinite Recursion in Wrapper

**Problem**: Calling wrapped method from wrapper.

**Solution**: Call `_original_enqueue` (stored reference), not `Queue.enqueue`.

---

## FAQ

### Q: What if SAQ is not installed?

**A**: Panel gracefully degrades. `_setup_queue_wrapping()` catches ImportError, returns False. Panel shows "SAQ not available" message.

### Q: Does this work with multiple Queue instances?

**A**: Yes. Tracker stores `queue_id` (queue name or id(queue)) for each task.

### Q: What about custom enqueue methods?

**A**: Not tracked. Only standard `Queue.enqueue()` is wrapped. Custom methods need explicit wrapping.

### Q: Can I disable stack capture?

**A**: Yes. `SAQPanel(toolbar, capture_stacks=False)`.

### Q: What's the performance impact?

**A**: ~0.3-0.8ms per task. Negligible for development. Can disable stack capture for better performance.

### Q: Can I use this in production?

**A**: Yes, but not recommended. Debug toolbar is for development. If needed, disable stack capture.

---

## Resources

### Internal Code References

- SQLAlchemy Panel: `src/debug_toolbar/extras/advanced_alchemy/panel.py`
- Panel ABC: `src/debug_toolbar/core/panel.py`
- Request Context: `src/debug_toolbar/core/context.py`
- Pattern Library: `specs/guides/patterns/README.md`

### External Documentation

- SAQ Docs: https://saq-py.readthedocs.io/en/latest/
- SAQ GitHub: https://github.com/tobymao/saq
- Redis-py Docs: https://redis-py.readthedocs.io/

### Testing References

- Existing panel tests: `tests/unit/test_sqlalchemy_panel.py`
- Pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/

---

## Resuming Work

### If Implementing

1. Read PRD: `specs/active/saq-panel/prd.md`
2. Read research: `specs/active/saq-panel/research/plan.md`
3. Run: `/implement saq-panel`
4. Follow checkpoints 1-8

### If Testing

1. Ensure implementation complete (checkpoints 1-4)
2. Read testing strategy in PRD
3. Create fixtures in `tests/conftest.py`
4. Write unit tests (checkpoint 5)
5. Write integration tests (checkpoint 6)
6. Verify coverage: `make test-cov`

### If Reviewing

1. Verify all checkpoints complete
2. Run quality gates:
   - `make test` (all pass)
   - `make lint` (no errors)
   - `make type-check` (no errors)
3. Check coverage >= 90%
4. Extract patterns to `specs/guides/patterns/`
5. Update CLAUDE.md if needed

---

## Status Summary

| Phase | Status | Next Action |
|-------|--------|-------------|
| **PRD** | ✅ Complete | Read and approve PRD |
| **Implementation** | 🔲 Not Started | Run `/implement saq-panel` |
| **Testing** | 🔲 Not Started | Create test files |
| **Review** | 🔲 Not Started | Run quality gates |
| **Documentation** | 🔲 Not Started | Write docs/panels/saq.md |

---

**Last Updated**: 2025-11-29
**Complexity**: Medium (8 checkpoints)
**Estimated Total Time**: 6-9 hours
**Priority**: P1 (High)

---

## Command Reference

```bash
# Resume implementation
/implement saq-panel

# Run tests
make test
make test-cov
pytest tests/unit/test_saq_panel.py -v

# Quality checks
make lint
make type-check
make fmt

# View coverage
coverage report --include="src/debug_toolbar/extras/saq/*"
```

---

**Ready to Resume**: Yes
**Blocking Issues**: None
**Dependencies Met**: Yes (SAQ is optional)
