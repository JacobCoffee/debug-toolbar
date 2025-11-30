# Spec: PR #5 - Async Profiling Panel

## Metadata
- **PR Number**: 5
- **Priority**: P1
- **Complexity**: High
- **Estimated Files**: 6-8
- **Dependencies**: None
- **Implementation Order**: 1 (First priority - unique differentiator)

---

## Problem Statement

Async Python applications have unique performance characteristics that traditional profilers don't capture well:
- Task concurrency and scheduling
- Await points where execution yields
- Blocking sync code in async context
- Event loop latency

No existing debug toolbar provides async-aware profiling. This is our primary differentiator for the async Python ecosystem.

---

## Goals

1. Track asyncio task creation during request
2. Visualize concurrent task execution timeline
3. Identify await points and their durations
4. Detect blocking sync code in async context
5. Monitor event loop lag

---

## Non-Goals

- Replace cProfile/pyinstrument (complement them)
- Support trio/curio (asyncio only for v1)
- Production monitoring (development tool only)

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ AsyncProfilerPanel                              │
├─────────────────────────────────────────────────┤
│ - Coordinates profiling components              │
│ - Generates timeline visualization              │
│ - Calculates concurrency metrics                │
└─────────────────────────────────────────────────┘
         │
    ┌────┴────┬─────────────┬─────────────┐
    ▼         ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Task    │ │ Await   │ │ Blocking│ │ Event   │
│ Tracker │ │ Tracker │ │ Detector│ │ Loop    │
│         │ │         │ │         │ │ Monitor │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Task Tracking

Hook into `asyncio.create_task()` to capture task creation:

```python
import asyncio
from functools import wraps

_original_create_task = asyncio.create_task

def patched_create_task(coro, *, name=None, context=None):
    task = _original_create_task(coro, name=name, context=context)
    # Record task creation
    AsyncTaskTracker.record_task_created(task)
    # Add done callback for completion tracking
    task.add_done_callback(AsyncTaskTracker.record_task_done)
    return task
```

### Await Point Detection

Use `sys.settrace` or `sys.monitoring` (Python 3.12+) to detect await points:

```python
# Python 3.12+ approach
import sys.monitoring as sm

def await_callback(code, instruction_offset, awaitable):
    # Record await start
    pass

sm.register_callback(sm.events.PY_AWAIT, await_callback)
```

For Python < 3.12, use frame inspection with settrace.

### Blocking Detection

Monitor event loop responsiveness:

```python
async def blocking_detector():
    """Detect when event loop is blocked."""
    threshold_ms = 100  # Configurable
    while True:
        start = time.perf_counter()
        await asyncio.sleep(0)  # Yield to event loop
        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > threshold_ms:
            # Event loop was blocked
            AsyncBlockingTracker.record_block(elapsed)
```

### Files to Create

```
src/debug_toolbar/core/panels/async_profiler/
├── __init__.py
├── panel.py           # AsyncProfilerPanel
├── task_tracker.py    # Task creation/completion tracking
├── await_tracker.py   # Await point detection
├── blocking_detector.py  # Sync-in-async detection
└── event_loop_monitor.py # Event loop lag monitoring
```

### Data Model

```python
@dataclass
class TrackedTask:
    task_id: str
    name: str
    coro_name: str
    created_at: float
    started_at: float | None
    completed_at: float | None
    cancelled: bool
    exception: str | None
    parent_task_id: str | None  # For task hierarchy

@dataclass
class AwaitPoint:
    task_id: str
    awaitable_name: str
    file: str
    line: int
    started_at: float
    resumed_at: float
    duration_ms: float

@dataclass
class BlockingEvent:
    detected_at: float
    duration_ms: float
    stack_trace: list[str]

@dataclass
class EventLoopMetrics:
    avg_lag_ms: float
    max_lag_ms: float
    samples: int
```

---

## Acceptance Criteria

- [ ] Track all tasks created via asyncio.create_task()
- [ ] Show task hierarchy (parent → child relationships)
- [ ] Display concurrent task timeline
- [ ] Identify await points with durations > threshold
- [ ] Detect blocking calls > 100ms (configurable)
- [ ] Calculate event loop lag metrics
- [ ] Timeline visualization with zoom
- [ ] Export timeline data as JSON
- [ ] No significant overhead when disabled
- [ ] Python 3.10+ support
- [ ] 90%+ test coverage

---

## Testing Strategy

### Unit Tests
```python
class TestAsyncProfilerPanel:
    async def test_tracks_created_task(self):
        """Should record task creation."""

    async def test_tracks_task_completion(self):
        """Should record task completion time."""

    async def test_tracks_cancelled_task(self):
        """Should handle task cancellation."""

    async def test_detects_await_point(self):
        """Should identify await points."""

    async def test_detects_blocking_call(self):
        """Should detect sync blocking code."""

    async def test_measures_event_loop_lag(self):
        """Should calculate loop latency."""

class TestTaskTracker:
    async def test_task_hierarchy(self):
        """Should track parent-child relationships."""

    async def test_concurrent_tasks(self):
        """Should handle many concurrent tasks."""
```

### Integration Tests
```python
class TestAsyncProfilerIntegration:
    async def test_real_request_profiling(self):
        """Profile actual Litestar request with async ops."""
```

---

## UI Design

```
┌─────────────────────────────────────────────────┐
│ Async Profiler                     12 tasks     │
├─────────────────────────────────────────────────┤
│ Event Loop Lag: avg 2.3ms, max 15.2ms          │
│ Blocking Events: 1 (⚠ 150ms block detected)    │
├─────────────────────────────────────────────────┤
│ Task Timeline (0-250ms):                        │
│ ├─ request_handler ███████████████████████ 245ms│
│ │  ├─ fetch_user ████████░░░░░░░░░░░░░░░ 85ms  │
│ │  ├─ fetch_posts ░░░░████████░░░░░░░░░░ 90ms  │
│ │  └─ send_email  ░░░░░░░░░░░░████████░░ 70ms  │
├─────────────────────────────────────────────────┤
│ Await Points (>10ms):                           │
│ • fetch_user:23 - await session.execute() 45ms │
│ • fetch_posts:15 - await session.execute() 38ms│
├─────────────────────────────────────────────────┤
│ ⚠ Blocking Detected:                           │
│ • api/handlers.py:45 - time.sleep(0.15) 150ms  │
└─────────────────────────────────────────────────┘
```

---

## Configuration

```python
@dataclass
class DebugToolbarConfig:
    # ... existing ...
    async_profiling_enabled: bool = True
    async_await_threshold_ms: float = 10.0
    async_blocking_threshold_ms: float = 100.0
    async_max_tasks: int = 1000
    async_event_loop_sample_rate_ms: float = 10.0
```

---

## Implementation Notes

1. **Performance**: Use sampling for event loop monitoring
2. **Compatibility**: Different approaches for Python 3.10-3.11 vs 3.12+
3. **Task Names**: Use `asyncio.current_task().get_name()`
4. **Stack Traces**: Capture on blocking detection for debugging
5. **Memory**: Limit tracked tasks to prevent memory growth

### Python Version Handling

```python
import sys

if sys.version_info >= (3, 12):
    # Use sys.monitoring for await tracking
    from .await_tracker_312 import AwaitTracker
else:
    # Use settrace fallback
    from .await_tracker_legacy import AwaitTracker
```

---

## References

- [asyncio Task documentation](https://docs.python.org/3/library/asyncio-task.html)
- [sys.monitoring (Python 3.12+)](https://docs.python.org/3/library/sys.monitoring.html)
- [yappi async profiler](https://github.com/sumerc/yappi) - inspiration for approach
- Pattern: `src/debug_toolbar/core/panels/profiling.py`
