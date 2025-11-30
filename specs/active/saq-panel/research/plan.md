# SAQ Panel - Research Plan

**Date**: 2025-11-29
**Agent**: PRD Agent (Intelligent Edition)
**Feature**: SAQ Background Tasks Panel
**Complexity**: Medium (8 checkpoints)

---

## Executive Summary

This document captures the pattern recognition and research phase for the SAQ (Simple Async Queue) Background Tasks Panel feature. The panel will track background tasks enqueued during HTTP requests, providing visibility into async job execution, timing, and lifecycle status.

---

## Pattern Recognition Phase

### Similar Implementations Analyzed

1. **SQLAlchemy Panel** (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)
   - **Pattern**: Event listener wrapping for external library integration
   - **Key Insights**:
     - Uses global `_tracker` instance with contextvar-safe state management
     - Event listeners attached at panel initialization via `_setup_event_listeners()`
     - Global listeners pattern with `_setup_global_listeners()` for auto-discovery
     - Request lifecycle integration via `process_request()` and `process_response()`
     - Comprehensive tracking with hash generation for duplicate detection
     - Stack trace capture for origin tracking (with performance considerations)
     - Deferred execution support (EXPLAIN queries via separate endpoint)
   - **Applicable to SAQ**: Same pattern for wrapping `Queue.enqueue()` calls

2. **Timer Panel** (`src/debug_toolbar/core/panels/timer.py`)
   - **Pattern**: Simple lifecycle hooks for timing
   - **Key Insights**:
     - Stores start state in instance variables (`__slots__`)
     - Uses `process_request()` to capture start time
     - Uses `generate_stats()` to calculate elapsed time
     - Contributes to `Server-Timing` headers via `generate_server_timing()`
   - **Applicable to SAQ**: Track task enqueue timing

3. **Panel Base Class** (`src/debug_toolbar/core/panel.py`)
   - **Pattern**: ABC with ClassVar metadata
   - **Key Insights**:
     - `panel_id`, `title`, `template`, `has_content` as ClassVar
     - `generate_stats()` is the primary data collection method
     - `record_stats()` and `get_stats()` for context interaction
     - Optional lifecycle hooks: `process_request()`, `process_response()`
   - **Applicable to SAQ**: Standard panel structure

### Architecture Patterns Identified

1. **Tracker Pattern** (from SQLAlchemy Panel):
   ```python
   class TaskTracker:
       def __init__(self):
           self.tasks = []
           self._enabled = False

       def start(self) -> None:
           self._enabled = True

       def stop(self) -> None:
           self._enabled = False
   ```

2. **Monkey Patching Pattern** (for Queue.enqueue wrapping):
   ```python
   _original_enqueue = None

   async def _wrapped_enqueue(self, *args, **kwargs):
       # Track before
       job = await _original_enqueue(self, *args, **kwargs)
       # Track after
       return job
   ```

3. **Request Context Integration**:
   ```python
   async def process_request(self, context: RequestContext) -> None:
       _tracker.start()

   async def process_response(self, context: RequestContext) -> None:
       _tracker.stop()
   ```

---

## SAQ API Research

### Official Documentation Analysis

Sources:
- [GitHub - tobymao/saq](https://github.com/tobymao/saq)
- [SAQ 0.26.0 documentation](https://saq-py.readthedocs.io/en/latest/)
- [Getting Started Guide](https://saq-py.readthedocs.io/en/latest/getting_started.html)

### Key API Points

#### Queue Class
```python
from saq import Queue

queue = Queue.from_url("redis://localhost")
```

#### Job Enqueuing
```python
# Basic enqueue
job = await queue.enqueue("function_name", arg1=value1)

# Scheduled job
job = await queue.enqueue("function_name", scheduled=time.time() + 10)

# Job with timeout
job = await queue.enqueue("function_name", timeout=300)

# Job with retries
job = await queue.enqueue("function_name", retries=3)
```

#### Job Class Attributes (Critical for Tracking)
Based on SAQ source inspection and documentation:
- `job.id` - UUID/str identifier
- `job.key` - Redis key for the job
- `job.function` - Function name/callable
- `job.kwargs` - Job keyword arguments
- `job.scheduled` - Scheduled execution timestamp
- `job.started` - Execution start timestamp
- `job.completed` - Completion timestamp
- `job.retries` - Number of retries configured
- `job.attempts` - Number of attempts made
- `job.status` - Current status (queued, active, complete, failed, aborted)
- `job.error` - Error message if failed
- `job.result` - Job result if completed
- `job.timeout` - Timeout in seconds
- `job.ttl` - Time to live in seconds
- `job.queue` - Reference to parent Queue

#### Job Methods
```python
await job.refresh(timeout=1)  # Refresh from Redis
await job.abort(error="reason")  # Abort job
await job.finish(result=value)  # Mark as finished
await job.retry(error="reason")  # Retry job
await job.update()  # Update in Redis
```

### Integration Points

1. **Enqueue Interception**: Wrap `Queue.enqueue()` method
2. **Job Metadata**: Capture at enqueue time (don't need to query Redis during request)
3. **Status Refresh**: Optional async endpoint to fetch current status from Redis
4. **Multiple Queue Support**: Track multiple Queue instances if present

---

## Technical Approach

### Component Design

#### 1. TaskTracker Class
Mirrors SQLAlchemy's QueryTracker pattern:
- Stores enqueued tasks during request lifecycle
- Tracks: function name, arguments, enqueue time, job ID, scheduled time
- Optional: capture call stack for task origin

#### 2. Queue Wrapping Strategy
Two approaches considered:

**Approach A: Monkey Patching** (SELECTED)
```python
_original_enqueue = None

def _setup_queue_tracking():
    global _original_enqueue
    if _original_enqueue is None:
        from saq import Queue
        _original_enqueue = Queue.enqueue
        Queue.enqueue = _wrapped_enqueue
```

**Pros**:
- Works with any Queue instance automatically
- No user code changes required
- Follows SQLAlchemy panel pattern

**Cons**:
- Monkey patching has risks
- May conflict with other libraries

**Approach B: Custom Queue Subclass**
```python
class TrackedQueue(Queue):
    async def enqueue(self, *args, **kwargs):
        job = await super().enqueue(*args, **kwargs)
        _tracker.track_job(job)
        return job
```

**Pros**:
- Cleaner, more explicit
- No monkey patching

**Cons**:
- Requires user to use TrackedQueue instead of Queue
- Less discoverable

**Decision**: Approach A (monkey patching) for consistency with SQLAlchemy panel and zero-config UX.

#### 3. Data Model

```python
@dataclass
class TrackedTask:
    """Represents a tracked background task."""
    job_id: str
    function_name: str
    kwargs: dict[str, Any]
    enqueued_at: float
    enqueue_duration_ms: float
    scheduled: float | None
    timeout: int | None
    retries: int | None
    queue_name: str
    stack: list[dict[str, Any]]  # Call stack if enabled
```

#### 4. Panel Implementation

```python
class SAQPanel(Panel):
    panel_id: ClassVar[str] = "SAQPanel"
    title: ClassVar[str] = "Background Tasks"
    template: ClassVar[str] = "panels/saq.html"

    async def process_request(self, context: RequestContext) -> None:
        _tracker.start()

    async def process_response(self, context: RequestContext) -> None:
        _tracker.stop()

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        tasks = list(_tracker.tasks)
        return {
            "tasks": tasks,
            "task_count": len(tasks),
            "scheduled_count": sum(1 for t in tasks if t.scheduled),
            "total_enqueue_time_ms": sum(t.enqueue_duration_ms for t in tasks),
        }
```

---

## Files to Create

### Core Implementation
1. `src/debug_toolbar/extras/saq/__init__.py`
2. `src/debug_toolbar/extras/saq/panel.py` (main implementation, ~600 lines)
3. `src/debug_toolbar/extras/saq/tracker.py` (TaskTracker class, ~200 lines)

### Configuration
4. Update `src/debug_toolbar/core/config.py` to document SAQ panel in docstring

### Testing
5. `tests/unit/test_saq_panel.py` (comprehensive unit tests, ~400 lines)
6. `tests/integration/test_saq_integration.py` (integration tests, ~200 lines)

### Documentation
7. Update project README with SAQ panel example
8. Create `docs/panels/saq.md` with usage guide

---

## Testing Strategy

### Unit Tests (90%+ coverage target)

1. **TaskTracker Tests**:
   - Initial state verification
   - Start/stop lifecycle
   - Task recording with various job configurations
   - Stack capture (if enabled)
   - Serialization of complex arguments

2. **Queue Wrapping Tests**:
   - Mock Queue.enqueue() calls
   - Verify original functionality preserved
   - Verify tracking occurs when enabled
   - Verify no tracking when disabled
   - Multiple queue instance handling

3. **Panel Tests**:
   - panel_id, title, template metadata
   - generate_stats() with various task scenarios
   - Empty state (no tasks)
   - Multiple tasks with different configurations
   - Scheduled vs immediate tasks
   - Statistics calculations

4. **Integration Tests**:
   - Real Redis connection (optional, with skipif)
   - Real SAQ Queue instance
   - Enqueue actual jobs
   - Verify tracking data matches job data
   - Context cleanup

### Fixtures Required

```python
@pytest.fixture
def task_tracker() -> TaskTracker:
    return TaskTracker()

@pytest.fixture
def mock_toolbar() -> MagicMock:
    return MagicMock(spec=["config"])

@pytest.fixture
def saq_panel(mock_toolbar: MagicMock) -> SAQPanel:
    return SAQPanel(mock_toolbar)

@pytest.fixture
def mock_queue():
    # Mock saq.Queue instance
    pass

@pytest.fixture
async def redis_queue():
    # Real Redis-backed queue for integration tests
    # Use pytest.skip if Redis not available
    pass
```

---

## Risk Assessment

### Technical Risks

1. **Monkey Patching Risk**: Medium
   - **Mitigation**: Store original method, restore on cleanup, comprehensive tests

2. **Performance Overhead**: Low-Medium
   - **Mitigation**: Minimal tracking overhead (just metadata capture), no Redis queries during request

3. **SAQ Version Compatibility**: Medium
   - **Mitigation**: Document supported versions (0.24+), test against multiple versions

4. **Multiple Queue Instances**: Low
   - **Mitigation**: Tracker stores queue name/identifier for correlation

### Implementation Risks

1. **Import Failure**: Low
   - **Mitigation**: Graceful degradation if SAQ not installed (same as SQLAlchemy panel)

2. **Async Complexity**: Low
   - **Mitigation**: Follow existing async panel patterns

---

## Performance Considerations

### Tracking Overhead
- **Per-task overhead**: ~0.1-0.5ms (metadata capture only)
- **No Redis queries**: All data captured at enqueue time
- **Stack capture**: Optional, can be disabled for high-traffic scenarios

### Memory Usage
- **Per-task**: ~1-2KB (depends on argument size)
- **Max tasks per request**: Unlikely to exceed 50-100 in normal usage
- **Cleanup**: Tasks cleared after request completion

---

## Open Questions

1. **Job Status Refresh**: Should panel provide endpoint to refresh job status from Redis?
   - **Decision**: Yes, optional AJAX endpoint similar to EXPLAIN queries in SQLAlchemy panel
   - **Implementation**: Separate API endpoint `/api/saq/job/<job_id>/status`

2. **Multiple Queue Tracking**: How to identify different queues?
   - **Decision**: Use Queue.name if available, otherwise use `id(queue)` as identifier

3. **Argument Serialization**: How to handle non-JSON-serializable arguments?
   - **Decision**: Follow SQLAlchemy panel pattern: `str()` fallback, truncate long values

4. **Stack Capture**: Always enabled or opt-in?
   - **Decision**: Enabled by default (like SQLAlchemy), can be disabled via panel init

---

## Dependencies

### Required
- `saq >= 0.24.0` (optional dependency, graceful degradation)
- `redis-py >= 4.2.0` (transitive dependency via SAQ)

### Testing
- `pytest-asyncio` (already in project)
- `fakeredis` (for unit tests without real Redis)

---

## Success Criteria

1. Zero-config integration: Panel auto-discovers Queue usage
2. Tracks all enqueued tasks during request lifecycle
3. Displays task metadata: function, arguments, scheduled time, retries
4. Optional status refresh from Redis
5. Performance overhead < 1ms per task
6. 90%+ test coverage
7. Pattern compliance with existing panels
8. No breaking changes to SAQ API

---

## References

### External
- [SAQ Documentation](https://saq-py.readthedocs.io/en/latest/)
- [SAQ GitHub](https://github.com/tobymao/saq)

### Internal
- `src/debug_toolbar/extras/advanced_alchemy/panel.py` - SQLAlchemy panel pattern
- `src/debug_toolbar/core/panel.py` - Panel ABC
- `src/debug_toolbar/core/context.py` - RequestContext
- `specs/guides/patterns/README.md` - Pattern library

---

## Next Steps

1. Review this research plan
2. Create comprehensive PRD (3200+ words)
3. Create RECOVERY.md for session continuity
4. Await approval before implementation phase
