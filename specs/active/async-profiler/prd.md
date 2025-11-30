# PRD: Async Profiling Panel for Debug Toolbar

**Version**: 1.0
**Created**: 2025-11-29
**Status**: Draft
**Priority**: P1 (Highest - Unique Differentiator)

---

## Metadata

| Field | Value |
|-------|-------|
| Slug | `async-profiler` |
| Complexity | Complex |
| Checkpoints | 12 |
| Estimated Effort | 3-4 weeks |
| Python Support | 3.10 - 3.13 |
| Dependencies | Optional: yappi>=1.4.0 |
| Target Version | 0.5.0 |

---

## Intelligence Context

### Similar Implementations Analyzed

This PRD was created after analyzing existing patterns in the debug-toolbar codebase:

1. **ProfilingPanel** (`src/debug_toolbar/core/panels/profiling.py`):
   - Multi-backend architecture (cProfile, pyinstrument)
   - Backend selection via config with auto-detection
   - Graceful fallback when preferred backend unavailable
   - Statistics structure with backend name, overhead tracking
   - Top functions extraction and filtering
   - Server-Timing integration

2. **MemoryPanel** (`src/debug_toolbar/core/panels/memory/panel.py`):
   - Backend ABC pattern (`MemoryBackend`)
   - Separate backend implementations in subdirectory
   - Platform-specific backend availability checks
   - Before/after snapshot pattern
   - Navigation subtitle with dynamic metrics

3. **Panel Base Class** (`src/debug_toolbar/core/panel.py`):
   - ClassVar metadata (panel_id, title, template, has_content)
   - __slots__ for memory efficiency
   - Lifecycle hooks: `process_request()`, `process_response()`
   - Abstract `generate_stats()` method
   - `record_stats()` and `get_stats()` helpers
   - `generate_server_timing()` for performance headers

### Patterns Identified

**Multi-Backend Architecture**:
```python
# Backend ABC with standard interface
class AsyncProfilerBackend(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool: ...
```

**Panel Configuration Pattern**:
```python
# In DebugToolbarConfig
memory_backend: Literal["tracemalloc", "memray", "auto"] = "auto"
profiler_backend: Literal["cprofile", "pyinstrument"] = "cprofile"
profiler_top_functions: int = 50
```

**Statistics Structure Pattern**:
```python
{
    "backend": str,              # Backend name
    "total_time": float,         # Total profiling duration
    "profiling_overhead": float, # Profiling cost in seconds
    "function_calls": int,       # Call count
    "top_functions": list[dict], # Top entries with consistent schema
    "call_tree": str | None,     # Optional detailed view
}
```

**Testing Pattern**:
- Class-based test organization by feature area
- Fixtures: `mock_toolbar`, `profiling_panel`, `request_context`
- Async tests with context cleanup: `set_request_context(None)`
- Structure validation tests (checking dict keys)
- Edge case tests: empty stats, errors, multiple calls, disabled state
- Backend-specific tests with conditional skip decorators

### Key Differences for Async Profiling

Unlike sync profiling (ProfilingPanel) or memory tracking (MemoryPanel), async profiling must handle:

1. **Context Switching Complexity**: Traditional profilers treat `await` as function exit, causing:
   - Incorrect wall time (missing await duration)
   - Inflated call counts (each yield increments)
   - Lost task hierarchy information

2. **Concurrent Execution**: Multiple tasks run simultaneously, requiring:
   - Per-task time accounting
   - Task relationship tracking (parent → children)
   - Timeline visualization of overlapping execution

3. **Event Loop Monitoring**: Need to detect:
   - Loop lag (blocking operations)
   - Slow callbacks (> 100ms)
   - Queue depth and scheduling delays

4. **Asyncio Instrumentation Points**:
   - `asyncio.create_task()` - Task creation
   - Task lifecycle events - Start/complete/cancel
   - Coroutine await boundaries
   - Event loop callback scheduling

---

## Problem Statement

### Current State

Developers building async ASGI applications with Litestar, FastAPI, or other frameworks lack visibility into async-specific performance characteristics. Existing profiling tools have critical limitations:

**ProfilingPanel (cProfile/pyinstrument)**:
- ✗ Treats `await` as function exit, distorting wall time
- ✗ Cannot track concurrent task execution
- ✗ No visibility into event loop health
- ✗ Misses task creation/completion patterns
- ✗ Cannot detect blocking synchronous code in async context

**Standalone Tools (yappi, py-spy, austin)**:
- ✗ Not integrated with request lifecycle
- ✗ Require separate execution and analysis
- ✗ No web UI for results
- ✗ Cannot correlate profiling with specific requests
- ✗ Complex setup and configuration

**Event Loop Debug Mode**:
- ✗ Only logs warnings, no metrics
- ✗ No historical tracking
- ✗ Not request-scoped
- ✗ No task hierarchy visualization

### User Pain Points

1. **Backend Developer** debugging slow API endpoint:
   - "Which async tasks are running concurrently during this request?"
   - "Is my database query blocking the event loop?"
   - "Why is this request taking 2 seconds when my code only has 500ms of work?"

2. **DevOps Engineer** investigating production issues:
   - "Is the event loop getting blocked by synchronous operations?"
   - "How many concurrent tasks are created per request?"
   - "What's the typical event loop lag under load?"

3. **Team Lead** reviewing code quality:
   - "Are we following async best practices?"
   - "Which endpoints create excessive tasks?"
   - "Where are we inadvertently blocking the event loop?"

### Success Criteria

A developer should be able to:
1. Enable async profiling with zero configuration
2. See task creation timeline in the debug toolbar UI
3. Identify blocking calls > 100ms with file/line info
4. Visualize parent-child task relationships
5. Measure event loop lag per request
6. Compare async behavior across requests
7. Export profiling data for deeper analysis

### Competitive Advantage

**No other Python debug toolbar offers async-aware profiling**. This feature would be a unique differentiator for debug-toolbar, making it the go-to choice for async Python web development.

| Feature | debug-toolbar | Django Debug Toolbar | Flask Debug Toolbar |
|---------|--------------|---------------------|-------------------|
| Async profiling | ✓ (this PRD) | ✗ | ✗ |
| Task hierarchy | ✓ | ✗ | ✗ |
| Event loop lag | ✓ | ✗ | ✗ |
| Blocking detection | ✓ | ✗ | ✗ |
| ASGI native | ✓ | ✗ | ✗ |

---

## Acceptance Criteria

### AC1: Multi-Backend Selection with Auto-Detection

**Given** a DebugToolbarConfig with `async_profiler_backend="auto"`
**When** AsyncProfilingPanel initializes
**Then** it selects backends in priority order:
1. YappiBackend (if yappi installed)
2. AsyncMonitorBackend (if Python >= 3.12)
3. EventLoopMonitorBackend (always available)

**Verification**:
```python
def test_backend_auto_selection_with_yappi_available():
    config = DebugToolbarConfig(async_profiler_backend="auto")
    panel = AsyncProfilingPanel(toolbar)
    assert panel._backend_name == "yappi"

def test_backend_auto_selection_without_yappi():
    with patch.dict("sys.modules", {"yappi": None}):
        panel = AsyncProfilingPanel(toolbar)
        if sys.version_info >= (3, 12):
            assert panel._backend_name == "monitoring"
        else:
            assert panel._backend_name == "eventloop"
```

**Success Metrics**:
- Backend selection tests pass on Python 3.10, 3.11, 3.12, 3.13
- Graceful fallback when preferred backend unavailable
- Warning logged when falling back to less capable backend

---

### AC2: Task Creation and Completion Tracking

**Given** an async request handler that creates 5 asyncio tasks
**When** the request completes and stats are generated
**Then** `stats["tasks_created"]` equals 5 and `stats["tasks_completed"]` equals 5

**Example Request**:
```python
async def handler(request):
    tasks = [
        asyncio.create_task(fetch_user(id)) for id in range(5)
    ]
    results = await asyncio.gather(*tasks)
    return {"users": results}
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_tracks_task_creation_count():
    panel = AsyncProfilingPanel(toolbar)
    await panel.process_request(context)

    # Simulate request with known task count
    tasks = [asyncio.create_task(asyncio.sleep(0.01)) for _ in range(5)]
    await asyncio.gather(*tasks)

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    assert stats["tasks_created"] == 5
    assert stats["tasks_completed"] == 5
```

**Success Metrics**:
- Accurate count for 1-100 tasks
- No double-counting when tasks create other tasks
- Handles cancelled tasks correctly

---

### AC3: Blocking Call Detection

**Given** an async request with blocking synchronous code
**When** a function calls `time.sleep(0.2)` (blocking)
**Then** `stats["blocking_calls"]` contains an entry with:
- Function name
- File path and line number
- Duration >= 0.2 seconds
- Impact classification (warning/critical)

**Example Blocking Code**:
```python
async def slow_handler(request):
    # BAD: Blocks event loop
    time.sleep(0.2)

    # Good async alternative
    await asyncio.sleep(0.2)
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_detects_blocking_synchronous_calls():
    panel = AsyncProfilingPanel(toolbar)
    panel._backend._blocking_threshold = 0.1

    await panel.process_request(context)

    def blocking_function():
        time.sleep(0.2)

    blocking_function()

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    assert len(stats["blocking_calls"]) >= 1
    blocking = stats["blocking_calls"][0]
    assert blocking["duration"] >= 0.2
    assert blocking["function"] == "blocking_function"
    assert "test_async_profiling" in blocking["file"]
    assert blocking["impact"] == "critical"  # > 2x threshold
```

**Success Metrics**:
- Detects calls > `async_profiler_blocking_threshold` (default: 0.1s)
- Accurate file/line information
- < 1% false positive rate (async calls not flagged as blocking)

---

### AC4: Event Loop Lag Measurement

**Given** a request with event loop blocking
**When** profiling completes
**Then** `stats["event_loop_lag"]` reports lag in seconds
**And** lag includes min/avg/max/p95 metrics

**Calculation Method**:
```python
# Measure scheduling delay
expected_delay = 0.010  # 10ms sleep
start = time.perf_counter()
await asyncio.sleep(expected_delay)
actual_delay = time.perf_counter() - start
lag = actual_delay - expected_delay
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_measures_event_loop_lag():
    panel = AsyncProfilingPanel(toolbar)
    await panel.process_request(context)

    # Introduce blocking to create lag
    def block():
        time.sleep(0.05)

    await asyncio.get_event_loop().run_in_executor(None, block)
    await asyncio.sleep(0.01)  # Should be delayed

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    assert "event_loop_lag" in stats
    assert stats["event_loop_lag"]["max"] > 0
    assert stats["event_loop_lag"]["avg"] >= 0
```

**Success Metrics**:
- Lag detection within 1ms accuracy
- Reports lag even for sub-millisecond delays
- Does not report lag when event loop healthy

---

### AC5: Task Hierarchy Visualization

**Given** a parent task that creates 2 child tasks
**When** profiling completes
**Then** `stats["task_hierarchy"]` shows parent-child relationships

**Example Task Structure**:
```python
async def parent_task():
    child1 = asyncio.create_task(child_task("A"))
    child2 = asyncio.create_task(child_task("B"))
    await asyncio.gather(child1, child2)

async def child_task(name):
    await asyncio.sleep(0.01)
```

**Expected Hierarchy**:
```json
{
  "task_id": "140234567890",
  "name": "parent_task",
  "parent": null,
  "duration": 0.012,
  "children": [
    {
      "task_id": "140234567891",
      "name": "child_task",
      "parent": "140234567890",
      "duration": 0.010,
      "children": []
    },
    {
      "task_id": "140234567892",
      "name": "child_task",
      "parent": "140234567890",
      "duration": 0.010,
      "children": []
    }
  ]
}
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_tracks_task_hierarchy():
    panel = AsyncProfilingPanel(toolbar)
    await panel.process_request(context)

    async def child():
        await asyncio.sleep(0.01)

    async def parent():
        c1 = asyncio.create_task(child())
        c2 = asyncio.create_task(child())
        await asyncio.gather(c1, c2)

    await parent()

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    hierarchy = stats["task_hierarchy"]
    assert len(hierarchy) == 1  # One root task
    assert len(hierarchy[0]["children"]) == 2
    assert all(c["parent"] == hierarchy[0]["task_id"] for c in hierarchy[0]["children"])
```

**Success Metrics**:
- Correctly identifies parent-child relationships
- Handles nested task creation (3+ levels deep)
- Tracks up to `async_profiler_max_tasks` (default: 100)

---

### AC6: Await Point Analysis

**Given** an async function with multiple await calls
**When** profiling completes
**Then** `stats["await_points"]` aggregates await behavior by function

**Example Function**:
```python
async def fetch_user_data(user_id):
    user = await db.fetch_user(user_id)      # Await #1
    profile = await db.fetch_profile(user_id) # Await #2
    posts = await db.fetch_posts(user_id)    # Await #3
    return combine(user, profile, posts)
```

**Expected Stats**:
```json
{
  "function": "fetch_user_data",
  "file": "handlers.py",
  "line": 42,
  "await_count": 3,
  "total_wait_time": 0.150,
  "avg_wait_time": 0.050
}
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_tracks_await_points():
    panel = AsyncProfilingPanel(toolbar)
    await panel.process_request(context)

    async def multi_await():
        await asyncio.sleep(0.01)
        await asyncio.sleep(0.02)
        await asyncio.sleep(0.03)

    await multi_await()

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    await_points = stats["await_points"]
    func = next(a for a in await_points if a["function"] == "multi_await")
    assert func["await_count"] == 3
    assert func["total_wait_time"] > 0.06
```

**Success Metrics**:
- Accurate await counting per function
- Correlates time spent waiting with specific functions
- Helps identify I/O bottlenecks

---

### AC7: Zero-Overhead When Disabled

**Given** AsyncProfilingPanel with `enabled=False`
**When** a request is processed
**Then** profiling overhead < 0.001 seconds (1ms)

**Verification**:
```python
@pytest.mark.asyncio
async def test_minimal_overhead_when_disabled():
    panel = AsyncProfilingPanel(toolbar)
    panel.enabled = False

    start = time.perf_counter()
    await panel.process_request(context)

    # Simulate typical request
    await asyncio.gather(*[asyncio.sleep(0.01) for _ in range(10)])

    await panel.process_response(context)
    elapsed = time.perf_counter() - start

    # Overhead should be negligible
    assert elapsed < 0.101  # 10 x 10ms + < 1ms overhead
```

**Success Metrics**:
- Disabled panel adds < 1ms per request
- No memory leaks when disabled
- Backend profiler not initialized when disabled

---

### AC8: Navigation Subtitle Display

**Given** profiling stats with 3 blocking calls
**When** `get_nav_subtitle()` is called
**Then** returns human-readable summary

**Examples**:
- 3 blocking calls: `"3 blocking"`
- No blocking, 2ms lag: `"Lag: 2ms"`
- No issues: `"OK"`
- 1 blocking, 5ms lag: `"1 blocking, 5ms lag"`

**Verification**:
```python
def test_nav_subtitle_with_blocking_calls():
    panel = AsyncProfilingPanel(toolbar)
    panel._blocking_count = 3
    panel._event_loop_lag = 0.0
    assert panel.get_nav_subtitle() == "3 blocking"

def test_nav_subtitle_with_lag():
    panel = AsyncProfilingPanel(toolbar)
    panel._blocking_count = 0
    panel._event_loop_lag = 0.002
    assert panel.get_nav_subtitle() == "Lag: 2ms"
```

**Success Metrics**:
- Clear, concise summaries
- Highlights most critical issue first
- Updates after each request

---

### AC9: Server-Timing Header Integration

**Given** completed async profiling
**When** `generate_server_timing()` is called
**Then** returns dict with timing metrics

**Expected Metrics**:
```python
{
    "async_profiling": 0.005,      # Profiling overhead
    "event_loop_lag": 0.002,       # Max lag
    "task_creation": 0.001,        # Task creation overhead
}
```

**Verification**:
```python
@pytest.mark.asyncio
async def test_server_timing_integration():
    panel = AsyncProfilingPanel(toolbar)
    await panel.process_request(context)
    await asyncio.sleep(0.01)
    await panel.process_response(context)

    stats = await panel.generate_stats(context)
    context.store_panel_data("AsyncProfilingPanel", "profiling_overhead", stats["profiling_overhead"])
    context.store_panel_data("AsyncProfilingPanel", "event_loop_lag", stats["event_loop_lag"]["max"])

    timing = panel.generate_server_timing(context)

    assert "async_profiling" in timing
    assert "event_loop_lag" in timing
    assert all(isinstance(v, float) for v in timing.values())
```

**Success Metrics**:
- Metrics appear in Server-Timing response header
- Values accurate to microsecond precision
- Compatible with browser DevTools timing panel

---

### AC10: Configuration via DebugToolbarConfig

**Given** DebugToolbarConfig with async profiler options
**When** AsyncProfilingPanel initializes
**Then** configuration is applied correctly

**Configuration Options**:
```python
@dataclass
class DebugToolbarConfig:
    # ... existing config ...

    # Async profiling config
    async_profiler_backend: Literal["yappi", "monitoring", "eventloop", "auto"] = "auto"
    async_profiler_track_tasks: bool = True
    async_profiler_detect_blocking: bool = True
    async_profiler_blocking_threshold: float = 0.1  # seconds
    async_profiler_max_tasks: int = 100
```

**Verification**:
```python
def test_respects_config_options():
    config = DebugToolbarConfig(
        async_profiler_backend="yappi",
        async_profiler_blocking_threshold=0.05,
        async_profiler_max_tasks=50,
    )
    panel = AsyncProfilingPanel(toolbar_with_config(config))

    assert panel._backend_name == "yappi"
    assert panel._blocking_threshold == 0.05
    assert panel._max_tasks == 50
```

**Success Metrics**:
- All config options honored
- Sensible defaults for zero-config usage
- Type checking via typing.Literal

---

### AC11: Statistics Structure Consistency

**Given** any backend
**When** `generate_stats()` is called
**Then** all backends return consistent schema

**Required Keys**:
```python
{
    "backend": str,                    # Backend name
    "profiling_overhead": float,       # Profiling cost (seconds)
    "tasks_created": int,              # Total tasks created
    "tasks_completed": int,            # Total tasks completed
    "event_loop_lag": {                # Event loop lag stats
        "min": float,
        "avg": float,
        "max": float,
        "p95": float,
    },
    "blocking_calls": list[dict],      # Blocking operations
    "task_hierarchy": list[dict],      # Task tree structure
    "await_points": list[dict],        # Await analysis
    "top_async_functions": list[dict], # Top functions by time
}
```

**Verification**:
```python
@pytest.mark.parametrize("backend", ["yappi", "eventloop"])
async def test_stats_schema_consistent(backend):
    panel = create_panel_with_backend(backend)
    await panel.process_request(context)
    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    # Validate schema
    assert "backend" in stats
    assert "profiling_overhead" in stats
    assert "tasks_created" in stats
    assert "event_loop_lag" in stats
    assert isinstance(stats["event_loop_lag"], dict)
    assert all(k in stats["event_loop_lag"] for k in ["min", "avg", "max", "p95"])
```

**Success Metrics**:
- All backends return same keys
- Type consistency across backends
- Graceful handling of unavailable data (empty lists, zero values)

---

### AC12: Error Handling and Resilience

**Given** backend raises exception during profiling
**When** request completes
**Then** panel returns empty stats and logs warning

**Error Scenarios**:
1. Backend initialization fails
2. Task tracking raises exception
3. Event loop instrumentation conflicts
4. Memory limit exceeded

**Verification**:
```python
@pytest.mark.asyncio
async def test_handles_backend_start_error():
    panel = AsyncProfilingPanel(toolbar)
    with patch.object(panel._backend, "start", side_effect=RuntimeError("Test error")):
        await panel.process_request(context)
        # Should not raise, should log warning

@pytest.mark.asyncio
async def test_returns_empty_stats_on_error():
    panel = AsyncProfilingPanel(toolbar)
    panel._backend = None  # Simulate backend failure

    stats = await panel.generate_stats(context)

    assert stats["backend"] == "none"
    assert stats["tasks_created"] == 0
    assert stats["blocking_calls"] == []
```

**Success Metrics**:
- No exceptions propagate to application
- Warnings logged with error details
- Empty/default stats returned on error
- Panel can recover after error

---

## Technical Approach

### Architecture Overview

```
AsyncProfilingPanel
├── Backend Selection (auto/manual)
│   ├── YappiBackend (preferred)
│   ├── AsyncMonitorBackend (Python 3.12+)
│   └── EventLoopMonitorBackend (fallback)
├── Lifecycle Hooks
│   ├── process_request() → backend.start()
│   ├── process_response() → backend.stop()
│   └── generate_stats() → backend.get_stats()
├── Task Tracking
│   ├── TaskTracker utility
│   ├── Task creation hooks
│   └── Hierarchy construction
└── Data Aggregation
    ├── Blocking call detection
    ├── Await point analysis
    └── Event loop lag calculation
```

### Backend Interface

**Abstract Base Class**:
```python
"""Base class for async profiler backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AsyncProfilerBackend(ABC):
    """Abstract base class for async profiling backends.

    Backends are responsible for profiling async code execution,
    tracking task lifecycle, and detecting event loop issues.
    """

    @abstractmethod
    def start(self) -> None:
        """Begin async profiling.

        Called at request start to initialize profiling state.
        Should be lightweight (< 1ms).
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """End async profiling.

        Called at request end to finalize profiling data.
        Should capture final state before cleanup.
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Retrieve async profiling statistics.

        Returns:
            Dictionary containing:
                - backend: str - Backend name
                - profiling_overhead: float - Profiling cost (seconds)
                - tasks_created: int - Total tasks created
                - tasks_completed: int - Total tasks completed
                - event_loop_lag: dict - Lag statistics (min/avg/max/p95)
                - blocking_calls: list[dict] - Blocking operations detected
                - task_hierarchy: list[dict] - Task tree structure
                - await_points: list[dict] - Await analysis
                - top_async_functions: list[dict] - Top functions by time
        """
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend is available.

        Returns:
            True if backend can be used (dependencies installed,
            Python version compatible), False otherwise.
        """
        ...
```

### YappiBackend Implementation

**Primary backend using yappi library**:

```python
"""Yappi backend for async profiling."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from debug_toolbar.core.panels.async_profiling.base import AsyncProfilerBackend

if TYPE_CHECKING:
    import yappi

logger = logging.getLogger(__name__)


class YappiBackend(AsyncProfilerBackend):
    """Async profiling backend using yappi.

    Yappi (Yet Another Python Profiler) is coroutine-aware and correctly
    handles async/await context switches, making it ideal for async profiling.

    Features:
        - Accurate wall time for coroutines
        - Correct call counts (doesn't increment on yield)
        - Per-task statistics
        - Low overhead (< 5% in most cases)
    """

    __slots__ = (
        "_stats",
        "_start_time",
        "_task_stats",
        "_blocking_threshold",
        "_max_tasks",
    )

    def __init__(self, blocking_threshold: float = 0.1, max_tasks: int = 100) -> None:
        """Initialize yappi backend.

        Args:
            blocking_threshold: Minimum duration (seconds) to consider a call blocking.
            max_tasks: Maximum number of tasks to track.
        """
        self._stats: yappi.YFuncStats | None = None
        self._start_time: float = 0.0
        self._task_stats: list[dict[str, Any]] = []
        self._blocking_threshold = blocking_threshold
        self._max_tasks = max_tasks

    def start(self) -> None:
        """Start yappi profiling."""
        try:
            import yappi

            yappi.set_clock_type("WALL")  # Wall time for I/O profiling
            yappi.clear_stats()  # Clear any previous profiling data
            yappi.start(builtins=False)  # Don't profile builtins
            self._start_time = time.perf_counter()

        except ImportError:
            logger.warning("yappi not installed, async profiling unavailable")
            raise
        except Exception as e:
            logger.warning("Failed to start yappi profiling: %s", e)
            raise

    def stop(self) -> None:
        """Stop yappi profiling."""
        try:
            import yappi

            yappi.stop()
            self._stats = yappi.get_func_stats()

        except Exception as e:
            logger.warning("Failed to stop yappi profiling: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """Extract statistics from yappi."""
        if self._stats is None:
            return self._empty_stats()

        overhead = time.perf_counter() - self._start_time

        # Extract function statistics
        top_functions = self._extract_top_functions()
        blocking_calls = self._extract_blocking_calls()
        await_points = self._extract_await_points()

        # Task statistics (if yappi provides threading stats)
        tasks_created = self._count_tasks_created()
        tasks_completed = self._count_tasks_completed()

        # Event loop lag (estimated from scheduling delays)
        event_loop_lag = self._calculate_event_loop_lag()

        return {
            "backend": "yappi",
            "profiling_overhead": overhead,
            "tasks_created": tasks_created,
            "tasks_completed": tasks_completed,
            "event_loop_lag": event_loop_lag,
            "blocking_calls": blocking_calls,
            "task_hierarchy": [],  # TODO: Implement via TaskTracker
            "await_points": await_points,
            "top_async_functions": top_functions,
        }

    def _extract_top_functions(self) -> list[dict[str, Any]]:
        """Extract top async functions by cumulative time."""
        if self._stats is None:
            return []

        functions = []
        for stat in self._stats:
            # Filter to async functions (coroutines)
            if not self._is_coroutine(stat):
                continue

            functions.append({
                "function": stat.name,
                "file": stat.module,
                "line": stat.lineno,
                "calls": stat.ncall,
                "total_time": stat.ttot,
                "cumulative_time": stat.tsub,
                "per_call": stat.tavg,
            })

        # Sort by cumulative time, return top results
        functions.sort(key=lambda x: x["cumulative_time"], reverse=True)
        return functions[:50]

    def _extract_blocking_calls(self) -> list[dict[str, Any]]:
        """Identify blocking synchronous calls in async context."""
        if self._stats is None:
            return []

        blocking = []
        for stat in self._stats:
            # Skip async functions
            if self._is_coroutine(stat):
                continue

            # Check if call duration exceeds threshold
            if stat.tavg >= self._blocking_threshold:
                impact = "critical" if stat.tavg >= self._blocking_threshold * 2 else "warning"

                blocking.append({
                    "function": stat.name,
                    "file": stat.module,
                    "line": stat.lineno,
                    "duration": stat.tavg,
                    "calls": stat.ncall,
                    "total_time": stat.ttot,
                    "impact": impact,
                })

        blocking.sort(key=lambda x: x["duration"], reverse=True)
        return blocking

    def _extract_await_points(self) -> list[dict[str, Any]]:
        """Analyze await behavior by function."""
        # This requires correlating coroutine yields with function calls
        # Simplified implementation - actual would need deeper yappi integration
        return []

    def _count_tasks_created(self) -> int:
        """Count asyncio tasks created during profiling."""
        # Would need TaskTracker integration
        return 0

    def _count_tasks_completed(self) -> int:
        """Count asyncio tasks completed during profiling."""
        return 0

    def _calculate_event_loop_lag(self) -> dict[str, float]:
        """Calculate event loop lag statistics."""
        # Would need event loop instrumentation
        return {
            "min": 0.0,
            "avg": 0.0,
            "max": 0.0,
            "p95": 0.0,
        }

    def _is_coroutine(self, stat: Any) -> bool:
        """Check if function stat represents a coroutine."""
        # Coroutines have special naming in yappi
        return "coroutine" in str(stat.name).lower() or stat.name.startswith("async ")

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure."""
        return {
            "backend": "yappi",
            "profiling_overhead": 0.0,
            "tasks_created": 0,
            "tasks_completed": 0,
            "event_loop_lag": {
                "min": 0.0,
                "avg": 0.0,
                "max": 0.0,
                "p95": 0.0,
            },
            "blocking_calls": [],
            "task_hierarchy": [],
            "await_points": [],
            "top_async_functions": [],
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check if yappi is installed and available."""
        try:
            import yappi  # noqa: F401
            return True
        except ImportError:
            return False
```

### EventLoopMonitorBackend Implementation

**Fallback backend using asyncio sleep for lag detection**:

```python
"""Event loop monitoring backend (fallback)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from debug_toolbar.core.panels.async_profiling.base import AsyncProfilerBackend

logger = logging.getLogger(__name__)


class EventLoopMonitorBackend(AsyncProfilerBackend):
    """Minimal async profiling using event loop lag detection.

    This backend doesn't require any dependencies and works on all
    Python versions. It provides basic event loop health monitoring
    but lacks detailed profiling capabilities.

    Features:
        - Event loop lag measurement
        - Basic task counting via asyncio introspection
        - Very low overhead (< 0.5%)
        - Always available

    Limitations:
        - No function-level profiling
        - Cannot detect blocking calls precisely
        - No await point analysis
    """

    __slots__ = (
        "_start_time",
        "_lag_samples",
        "_tasks_before",
        "_tasks_after",
    )

    def __init__(self) -> None:
        """Initialize event loop monitor backend."""
        self._start_time: float = 0.0
        self._lag_samples: list[float] = []
        self._tasks_before: int = 0
        self._tasks_after: int = 0

    def start(self) -> None:
        """Begin event loop monitoring."""
        self._start_time = time.perf_counter()
        self._lag_samples = []

        # Count current tasks
        try:
            loop = asyncio.get_running_loop()
            self._tasks_before = len(asyncio.all_tasks(loop))
        except RuntimeError:
            self._tasks_before = 0

    def stop(self) -> None:
        """End event loop monitoring."""
        try:
            loop = asyncio.get_running_loop()
            self._tasks_after = len(asyncio.all_tasks(loop))
        except RuntimeError:
            self._tasks_after = 0

    def get_stats(self) -> dict[str, Any]:
        """Get event loop monitoring statistics."""
        overhead = time.perf_counter() - self._start_time

        # Calculate lag statistics
        if self._lag_samples:
            lag_min = min(self._lag_samples)
            lag_max = max(self._lag_samples)
            lag_avg = sum(self._lag_samples) / len(self._lag_samples)
            lag_p95 = sorted(self._lag_samples)[int(len(self._lag_samples) * 0.95)]
        else:
            lag_min = lag_max = lag_avg = lag_p95 = 0.0

        # Task count delta (rough estimate)
        tasks_created = max(0, self._tasks_after - self._tasks_before)

        return {
            "backend": "eventloop",
            "profiling_overhead": overhead,
            "tasks_created": tasks_created,
            "tasks_completed": tasks_created,  # Assumption: all complete
            "event_loop_lag": {
                "min": lag_min,
                "avg": lag_avg,
                "max": lag_max,
                "p95": lag_p95,
            },
            "blocking_calls": [],  # Not available
            "task_hierarchy": [],  # Not available
            "await_points": [],    # Not available
            "top_async_functions": [],  # Not available
        }

    async def measure_lag(self) -> float:
        """Measure current event loop lag.

        Returns:
            Lag in seconds (difference between expected and actual sleep time).
        """
        expected = 0.010  # 10ms
        start = time.perf_counter()
        await asyncio.sleep(expected)
        actual = time.perf_counter() - start
        lag = max(0, actual - expected)
        self._lag_samples.append(lag)
        return lag

    @classmethod
    def is_available(cls) -> bool:
        """Event loop monitor is always available."""
        return True
```

### TaskTracker Utility

**Tracks asyncio task lifecycle and hierarchy**:

```python
"""Task tracking utility for async profiling."""

from __future__ import annotations

import asyncio
import weakref
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class TaskInfo:
    """Information about a tracked asyncio task."""

    task_id: int
    name: str
    coro_name: str
    parent_id: int | None
    created_at: float
    completed_at: float | None = None
    cancelled: bool = False
    exception: Exception | None = None
    children: list[int] = field(default_factory=list)


class TaskTracker:
    """Tracks asyncio task creation and lifecycle.

    Uses weak references to avoid preventing task garbage collection.
    Instruments asyncio.create_task() to capture task creation.
    """

    __slots__ = (
        "_tasks",
        "_max_tasks",
        "_task_count",
        "_original_create_task",
    )

    def __init__(self, max_tasks: int = 100) -> None:
        """Initialize task tracker.

        Args:
            max_tasks: Maximum number of tasks to track (prevents memory exhaustion).
        """
        self._tasks: dict[int, TaskInfo] = {}
        self._max_tasks = max_tasks
        self._task_count = 0
        self._original_create_task: Any = None

    def start(self) -> None:
        """Begin tracking task creation."""
        # Monkey-patch asyncio.create_task
        self._original_create_task = asyncio.create_task
        asyncio.create_task = self._instrumented_create_task  # type: ignore[assignment]

    def stop(self) -> None:
        """Stop tracking and restore original create_task."""
        if self._original_create_task:
            asyncio.create_task = self._original_create_task  # type: ignore[assignment]
            self._original_create_task = None

    def _instrumented_create_task(self, coro, *, name=None, context=None):
        """Instrumented version of asyncio.create_task."""
        # Create task using original function
        if context is not None:
            task = self._original_create_task(coro, name=name, context=context)
        else:
            task = self._original_create_task(coro, name=name)

        # Track the task if under limit
        if self._task_count < self._max_tasks:
            self._track_task(task)

        return task

    def _track_task(self, task: asyncio.Task) -> None:
        """Record task information."""
        task_id = id(task)
        parent_id = self._get_current_task_id()

        info = TaskInfo(
            task_id=task_id,
            name=task.get_name(),
            coro_name=task.get_coro().__qualname__,
            parent_id=parent_id,
            created_at=time.time(),
        )

        self._tasks[task_id] = info
        self._task_count += 1

        # Add to parent's children list
        if parent_id and parent_id in self._tasks:
            self._tasks[parent_id].children.append(task_id)

        # Add completion callback
        task.add_done_callback(self._task_done_callback)

    def _task_done_callback(self, task: asyncio.Task) -> None:
        """Called when task completes."""
        task_id = id(task)
        if task_id in self._tasks:
            info = self._tasks[task_id]
            info.completed_at = time.time()
            info.cancelled = task.cancelled()

            if not task.cancelled():
                try:
                    task.result()
                except Exception as e:
                    info.exception = e

    def _get_current_task_id(self) -> int | None:
        """Get ID of current running task."""
        try:
            current = asyncio.current_task()
            return id(current) if current else None
        except RuntimeError:
            return None

    def get_hierarchy(self) -> list[dict[str, Any]]:
        """Build task hierarchy tree.

        Returns:
            List of root tasks with nested children.
        """
        # Find root tasks (no parent)
        roots = [info for info in self._tasks.values() if info.parent_id is None]

        return [self._build_task_node(info) for info in roots]

    def _build_task_node(self, info: TaskInfo) -> dict[str, Any]:
        """Recursively build task hierarchy node."""
        duration = 0.0
        if info.completed_at:
            duration = info.completed_at - info.created_at

        node = {
            "task_id": str(info.task_id),
            "name": info.name,
            "coro": info.coro_name,
            "parent": str(info.parent_id) if info.parent_id else None,
            "duration": duration,
            "cancelled": info.cancelled,
            "children": [],
        }

        # Add child nodes
        for child_id in info.children:
            if child_id in self._tasks:
                child_node = self._build_task_node(self._tasks[child_id])
                node["children"].append(child_node)

        return node

    def get_stats(self) -> dict[str, int]:
        """Get task statistics.

        Returns:
            Dictionary with task counts.
        """
        completed = sum(1 for t in self._tasks.values() if t.completed_at)
        cancelled = sum(1 for t in self._tasks.values() if t.cancelled)

        return {
            "tasks_created": self._task_count,
            "tasks_completed": completed,
            "tasks_cancelled": cancelled,
            "tasks_with_errors": sum(1 for t in self._tasks.values() if t.exception),
        }
```

### AsyncProfilingPanel Main Class

**Panel implementation following established patterns**:

```python
"""Async profiling panel for asyncio performance analysis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from debug_toolbar.core.panel import Panel
from debug_toolbar.core.panels.async_profiling.base import AsyncProfilerBackend
from debug_toolbar.core.panels.async_profiling.eventloop import EventLoopMonitorBackend
from debug_toolbar.core.panels.async_profiling.yappi import YappiBackend

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

logger = logging.getLogger(__name__)


class AsyncProfilingPanel(Panel):
    """Panel for profiling async/asyncio performance.

    Provides insights into async code execution including:
    - Task creation and lifecycle
    - Event loop lag and blocking detection
    - Await point analysis
    - Task hierarchy visualization

    Supports multiple profiling backends:
    - yappi: Full-featured async profiler (requires yappi package)
    - monitoring: Python 3.12+ sys.monitoring API (native)
    - eventloop: Basic event loop lag detection (always available)

    Configure via toolbar config:
        async_profiler_backend: "yappi" | "monitoring" | "eventloop" | "auto"
        async_profiler_track_tasks: bool (default: True)
        async_profiler_detect_blocking: bool (default: True)
        async_profiler_blocking_threshold: float (default: 0.1 seconds)
        async_profiler_max_tasks: int (default: 100)
    """

    panel_id: ClassVar[str] = "AsyncProfilingPanel"
    title: ClassVar[str] = "Async Profiling"
    template: ClassVar[str] = "panels/async_profiling.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Async"

    __slots__ = (
        "_backend",
        "_backend_name",
        "_track_tasks",
        "_detect_blocking",
        "_blocking_threshold",
        "_max_tasks",
        "_blocking_count",
        "_event_loop_lag",
    )

    def __init__(self, toolbar: DebugToolbar) -> None:
        """Initialize async profiling panel.

        Args:
            toolbar: The parent DebugToolbar instance.
        """
        super().__init__(toolbar)
        self._backend_name = self._select_backend()
        self._backend = self._create_backend(self._backend_name)
        self._track_tasks = self._get_config("async_profiler_track_tasks", True)
        self._detect_blocking = self._get_config("async_profiler_detect_blocking", True)
        self._blocking_threshold = self._get_config("async_profiler_blocking_threshold", 0.1)
        self._max_tasks = self._get_config("async_profiler_max_tasks", 100)
        self._blocking_count = 0
        self._event_loop_lag = 0.0

    def _select_backend(self) -> Literal["yappi", "monitoring", "eventloop"]:
        """Determine which profiling backend to use.

        Returns:
            Name of selected backend.
        """
        config_backend = self._get_config("async_profiler_backend", "auto")

        # Explicit backend selection
        if config_backend == "yappi":
            if YappiBackend.is_available():
                return "yappi"
            logger.info("yappi requested but not available, falling back to auto selection")

        # TODO: Add monitoring backend check for Python 3.12+
        # if config_backend == "monitoring":
        #     if sys.version_info >= (3, 12) and AsyncMonitorBackend.is_available():
        #         return "monitoring"

        if config_backend == "eventloop":
            return "eventloop"

        # Auto selection: yappi > monitoring > eventloop
        if YappiBackend.is_available():
            return "yappi"

        # TODO: Check for monitoring backend
        # if sys.version_info >= (3, 12):
        #     return "monitoring"

        return "eventloop"

    def _create_backend(self, backend_name: str) -> AsyncProfilerBackend:
        """Create backend instance.

        Args:
            backend_name: Name of backend to create.

        Returns:
            Configured backend instance.
        """
        if backend_name == "yappi":
            return YappiBackend(
                blocking_threshold=self._blocking_threshold,
                max_tasks=self._max_tasks,
            )

        # TODO: Add monitoring backend
        # if backend_name == "monitoring":
        #     return AsyncMonitorBackend(...)

        return EventLoopMonitorBackend()

    def _get_config(self, key: str, default: Any) -> Any:
        """Get configuration value from toolbar config.

        Args:
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value.
        """
        config = getattr(self._toolbar, "config", None)
        if config is None:
            return default
        return getattr(config, key, default)

    async def process_request(self, context: RequestContext) -> None:
        """Start profiling at request start.

        Args:
            context: The current request context.
        """
        if not self.enabled:
            return

        try:
            self._backend.start()
        except Exception as e:
            logger.warning("Failed to start async profiling: %s", e)
            self.enabled = False

    async def process_response(self, context: RequestContext) -> None:
        """Stop profiling at request end.

        Args:
            context: The current request context.
        """
        if not self.enabled:
            return

        try:
            self._backend.stop()
        except Exception as e:
            logger.warning("Failed to stop async profiling: %s", e)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate async profiling statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary of profiling statistics.
        """
        if not self.enabled or self._backend is None:
            return self._empty_stats()

        try:
            stats = self._backend.get_stats()

            # Cache values for nav subtitle
            self._blocking_count = len(stats.get("blocking_calls", []))
            self._event_loop_lag = stats.get("event_loop_lag", {}).get("max", 0.0)

            return stats
        except Exception as e:
            logger.warning("Failed to generate async profiling stats: %s", e)
            return self._empty_stats()

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "backend": "none",
            "profiling_overhead": 0.0,
            "tasks_created": 0,
            "tasks_completed": 0,
            "event_loop_lag": {
                "min": 0.0,
                "avg": 0.0,
                "max": 0.0,
                "p95": 0.0,
            },
            "blocking_calls": [],
            "task_hierarchy": [],
            "await_points": [],
            "top_async_functions": [],
        }

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data.

        Args:
            context: The current request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {
            "async_profiling": stats.get("profiling_overhead", 0.0),
            "event_loop_lag": stats.get("event_loop_lag", {}).get("max", 0.0),
        }

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle showing async issues.

        Returns:
            Human-readable subtitle (e.g., "3 blocking, 5ms lag").
        """
        parts = []

        if self._blocking_count > 0:
            parts.append(f"{self._blocking_count} blocking")

        if self._event_loop_lag > 0.001:  # > 1ms
            lag_ms = int(self._event_loop_lag * 1000)
            parts.append(f"Lag: {lag_ms}ms")

        if not parts:
            return "OK"

        return ", ".join(parts)
```

---

## Files to Create

### Core Implementation (7 files)

1. **src/debug_toolbar/core/panels/async_profiling/__init__.py**
   ```python
   """Async profiling panel and backends."""

   from debug_toolbar.core.panels.async_profiling.panel import AsyncProfilingPanel

   __all__ = ["AsyncProfilingPanel"]
   ```

2. **src/debug_toolbar/core/panels/async_profiling/panel.py**
   - Main `AsyncProfilingPanel` class (shown above)
   - ~300 lines

3. **src/debug_toolbar/core/panels/async_profiling/base.py**
   - `AsyncProfilerBackend` ABC (shown above)
   - ~60 lines

4. **src/debug_toolbar/core/panels/async_profiling/yappi.py**
   - `YappiBackend` implementation (shown above)
   - ~250 lines

5. **src/debug_toolbar/core/panels/async_profiling/monitoring.py**
   - `AsyncMonitorBackend` for Python 3.12+ (sys.monitoring)
   - ~300 lines
   - TODO: Implementation details

6. **src/debug_toolbar/core/panels/async_profiling/eventloop.py**
   - `EventLoopMonitorBackend` (shown above)
   - ~150 lines

7. **src/debug_toolbar/core/panels/async_profiling/task_tracker.py**
   - `TaskTracker` utility (shown above)
   - ~200 lines

### Tests (6 files)

1. **tests/unit/test_async_profiling_panel.py**
   - Main panel tests
   - ~500 lines
   - Classes: TestInit, TestBackendSelection, TestLifecycle, TestStats, TestServerTiming, TestNavSubtitle

2. **tests/unit/async_profiling/test_yappi_backend.py**
   - YappiBackend tests
   - ~300 lines
   - Requires yappi installed

3. **tests/unit/async_profiling/test_monitoring_backend.py**
   - AsyncMonitorBackend tests
   - ~300 lines
   - Skip if Python < 3.12

4. **tests/unit/async_profiling/test_eventloop_backend.py**
   - EventLoopMonitorBackend tests
   - ~200 lines

5. **tests/unit/async_profiling/test_task_tracker.py**
   - TaskTracker tests
   - ~300 lines

6. **tests/integration/test_async_profiling_integration.py**
   - End-to-end async profiling tests
   - ~400 lines
   - Real async patterns, blocking detection, hierarchy

### Configuration (2 files to modify)

1. **src/debug_toolbar/core/config.py**
   - Add async profiler config options:
   ```python
   async_profiler_backend: Literal["yappi", "monitoring", "eventloop", "auto"] = "auto"
   async_profiler_track_tasks: bool = True
   async_profiler_detect_blocking: bool = True
   async_profiler_blocking_threshold: float = 0.1
   async_profiler_max_tasks: int = 100
   ```

2. **pyproject.toml**
   - Add optional dependency:
   ```toml
   [project.optional-dependencies]
   async-profiling = ["yappi>=1.4.0"]
   ```

### Templates (1 file)

1. **src/debug_toolbar/templates/panels/async_profiling.html**
   - UI for async profiling results
   - ~400 lines
   - Sections: Summary, Blocking Calls, Task Hierarchy, Timeline, Await Analysis

---

## Testing Strategy

### Coverage Target: 90%+

**Unit Tests** (~90 tests total):

1. **Panel Tests** (test_async_profiling_panel.py) - 40 tests:
   - Initialization (8 tests)
   - Backend selection (6 tests)
   - Request/response lifecycle (8 tests)
   - Statistics generation (12 tests)
   - Server-Timing (3 tests)
   - Navigation subtitle (5 tests)
   - Error handling (8 tests)

2. **Backend Tests** (60 tests):
   - YappiBackend (15 tests)
   - MonitoringBackend (15 tests)
   - EventLoopBackend (12 tests)
   - TaskTracker (18 tests)

3. **Integration Tests** (8 tests):
   - Real async request profiling
   - Blocking call detection
   - Task hierarchy construction
   - Concurrent task handling
   - Error propagation
   - Multi-request profiling

### Test Patterns

**Unit Test Example**:
```python
@pytest.mark.asyncio
async def test_detects_blocking_calls():
    """Should detect synchronous blocking in async context."""
    panel = AsyncProfilingPanel(mock_toolbar)
    await panel.process_request(context)

    # Intentional blocking
    time.sleep(0.2)

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    assert len(stats["blocking_calls"]) > 0
    assert stats["blocking_calls"][0]["duration"] >= 0.2
    assert stats["blocking_calls"][0]["impact"] == "critical"
```

**Integration Test Example**:
```python
@pytest.mark.asyncio
async def test_profiles_real_async_application():
    """Should profile actual async web request."""
    app = create_test_app_with_toolbar()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/async-endpoint")

    # Extract profiling data from toolbar
    toolbar_data = extract_toolbar_data(response)
    async_stats = toolbar_data["async_profiling"]

    assert async_stats["tasks_created"] > 0
    assert async_stats["event_loop_lag"]["max"] < 0.1
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Test async profiling
  run: |
    uv pip install -e ".[async-profiling]"
    pytest tests/unit/test_async_profiling_panel.py
    pytest tests/unit/async_profiling/
    pytest tests/integration/test_async_profiling_integration.py

- name: Test Python 3.12 monitoring backend
  if: matrix.python-version == '3.12'
  run: |
    pytest tests/unit/async_profiling/test_monitoring_backend.py
```

---

## Data Models

### TaskInfo

```python
@dataclass
class TaskInfo:
    """Information about an asyncio task."""
    task_id: int
    name: str
    coro_name: str
    parent_id: int | None
    created_at: float
    completed_at: float | None = None
    cancelled: bool = False
    exception: Exception | None = None
    children: list[int] = field(default_factory=list)
```

### BlockingCall

```python
TypedDict for blocking call info:
{
    "function": str,      # Function name
    "file": str,          # File path
    "line": int,          # Line number
    "duration": float,    # Call duration (seconds)
    "calls": int,         # Number of calls
    "total_time": float,  # Total time across all calls
    "impact": "warning" | "critical",  # Severity
}
```

### EventLoopLag

```python
TypedDict for lag statistics:
{
    "min": float,   # Minimum lag (seconds)
    "avg": float,   # Average lag
    "max": float,   # Maximum lag
    "p95": float,   # 95th percentile lag
}
```

### AwaitPoint

```python
TypedDict for await analysis:
{
    "function": str,         # Function name
    "file": str,             # File path
    "line": int,             # Line number
    "await_count": int,      # Number of await calls
    "total_wait_time": float,  # Total time waiting
    "avg_wait_time": float,    # Average wait time per await
}
```

### AsyncFunction

```python
TypedDict for top async functions:
{
    "function": str,          # Function name
    "file": str,              # File path
    "line": int,              # Line number
    "calls": int,             # Call count
    "total_time": float,      # Total execution time
    "cumulative_time": float, # Cumulative time including children
    "per_call": float,        # Average time per call
}
```

---

## UI/UX Design

### Template Structure

**panels/async_profiling.html**:

```html
<div class="async-profiling-panel">
  <!-- Summary Section -->
  <div class="summary">
    <div class="metric">
      <span class="label">Backend</span>
      <span class="value">{{ stats.backend }}</span>
    </div>
    <div class="metric">
      <span class="label">Tasks Created</span>
      <span class="value">{{ stats.tasks_created }}</span>
    </div>
    <div class="metric">
      <span class="label">Tasks Completed</span>
      <span class="value">{{ stats.tasks_completed }}</span>
    </div>
    <div class="metric">
      <span class="label">Loop Lag (max)</span>
      <span class="value">{{ stats.event_loop_lag.max|ms }}</span>
    </div>
  </div>

  <!-- Blocking Calls Table -->
  <section class="blocking-calls">
    <h3>Blocking Calls ({{ stats.blocking_calls|length }})</h3>
    <table class="sortable">
      <thead>
        <tr>
          <th>Function</th>
          <th>File:Line</th>
          <th>Duration</th>
          <th>Calls</th>
          <th>Impact</th>
        </tr>
      </thead>
      <tbody>
        {% for call in stats.blocking_calls %}
        <tr class="impact-{{ call.impact }}">
          <td>{{ call.function }}</td>
          <td>{{ call.file }}:{{ call.line }}</td>
          <td>{{ call.duration|ms }}</td>
          <td>{{ call.calls }}</td>
          <td><span class="badge">{{ call.impact }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>

  <!-- Task Hierarchy Tree -->
  <section class="task-hierarchy">
    <h3>Task Hierarchy</h3>
    <div class="tree">
      {% for task in stats.task_hierarchy %}
        {% include "partials/task_node.html" with task=task %}
      {% endfor %}
    </div>
  </section>

  <!-- Timeline Visualization -->
  <section class="timeline">
    <h3>Task Timeline</h3>
    <div id="task-timeline" class="timeline-chart"></div>
  </section>

  <!-- Await Analysis -->
  <section class="await-analysis">
    <h3>Await Points</h3>
    <table>
      <thead>
        <tr>
          <th>Function</th>
          <th>File:Line</th>
          <th>Await Count</th>
          <th>Total Wait</th>
          <th>Avg Wait</th>
        </tr>
      </thead>
      <tbody>
        {% for point in stats.await_points %}
        <tr>
          <td>{{ point.function }}</td>
          <td>{{ point.file }}:{{ point.line }}</td>
          <td>{{ point.await_count }}</td>
          <td>{{ point.total_wait_time|ms }}</td>
          <td>{{ point.avg_wait_time|ms }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
</div>
```

### JavaScript for Timeline

```javascript
// Render Gantt-style timeline of concurrent tasks
function renderTaskTimeline(tasks) {
  const timeline = document.getElementById('task-timeline');
  const svg = d3.select(timeline).append('svg');

  // Calculate time scale
  const minTime = d3.min(tasks, t => t.created_at);
  const maxTime = d3.max(tasks, t => t.completed_at || t.created_at);
  const timeScale = d3.scaleLinear()
    .domain([minTime, maxTime])
    .range([0, 800]);

  // Render task bars
  tasks.forEach((task, i) => {
    const x = timeScale(task.created_at);
    const width = timeScale(task.completed_at || maxTime) - x;

    svg.append('rect')
      .attr('x', x)
      .attr('y', i * 25)
      .attr('width', width)
      .attr('height', 20)
      .attr('class', task.cancelled ? 'cancelled' : 'completed')
      .attr('title', task.name);
  });
}
```

---

## Security & Privacy Considerations

### Sensitive Data Exposure

**Risk**: Task names and function arguments may contain PII (user IDs, email, etc.)

**Mitigation**:
1. Never log function arguments (only names)
2. Strip absolute paths to relative paths
3. Redact task names matching patterns:
   ```python
   async_profiler_redact_patterns: list[str] = [
       r"user_\d+",
       r"email=[\w@.]+",
       r"token=[a-zA-Z0-9]+",
   ]
   ```
4. Add config option to disable task name tracking entirely

### Performance DoS

**Risk**: Profiling overhead could be weaponized to slow down application

**Mitigation**:
1. Default: disabled in production (check `DEBUG` env var)
2. Max tasks limit prevents memory exhaustion
3. Auto-disable if overhead exceeds threshold (10% of request time)
4. Rate limit profiling endpoint access (via show_toolbar_callback)

### Resource Cleanup

**Risk**: Task references prevent garbage collection, causing memory leaks

**Mitigation**:
1. Use weak references in TaskTracker
2. Clear all profiling state after each request
3. Timeout for long-running profiling (max 60 seconds)
4. Limit max tracked tasks (default: 100)

---

## Dependencies & Compatibility

### Required Dependencies
- None (EventLoopMonitorBackend works with stdlib only)

### Optional Dependencies
- **yappi >= 1.4.0** (for YappiBackend)
  - License: MIT
  - Supports: Python 3.10-3.13, all platforms
  - Install: `pip install debug-toolbar[async-profiling]`

### Python Version Support

| Python | EventLoop | Yappi | Monitoring | Recommendation |
|--------|-----------|-------|------------|---------------|
| 3.10   | ✓         | ✓     | ✗          | Install yappi |
| 3.11   | ✓         | ✓     | ✗          | Install yappi |
| 3.12   | ✓         | ✓     | ✓          | Use yappi or monitoring |
| 3.13   | ✓         | ✓     | ✓          | Use yappi or monitoring |

### Platform Compatibility
- **Linux**: All backends
- **macOS**: All backends
- **Windows**: All backends (yappi supports Windows)

### Framework Compatibility
- **Litestar**: Full support (primary target)
- **FastAPI**: Full support via standalone usage
- **Starlette**: Full support via standalone usage
- **Quart**: Full support (asyncio-based)
- **Sanic**: Compatible (asyncio-based)

---

## Implementation Phases

### Phase 1: Foundation (Checkpoints 1-4)
**Duration**: 1 week

**Deliverables**:
- [ ] Backend ABC definition
- [ ] EventLoopMonitorBackend implementation
- [ ] AsyncProfilingPanel skeleton
- [ ] Basic lifecycle integration
- [ ] Unit tests for ABC and EventLoop backend
- [ ] Documentation: Backend interface

**Success Criteria**:
- Panel can be instantiated
- Event loop lag detection works
- Tests achieve 85%+ coverage for Phase 1 code

### Phase 2: Yappi Integration (Checkpoints 5-7)
**Duration**: 1 week

**Deliverables**:
- [ ] YappiBackend implementation
- [ ] Function profiling
- [ ] Blocking call detection
- [ ] Top async functions extraction
- [ ] Unit tests for Yappi backend
- [ ] Documentation: Configuration guide

**Success Criteria**:
- Yappi backend accurately profiles async code
- Blocking calls > threshold detected
- Tests achieve 90%+ coverage for Yappi code

### Phase 3: Advanced Features (Checkpoints 8-10)
**Duration**: 1 week

**Deliverables**:
- [ ] TaskTracker utility
- [ ] Task hierarchy construction
- [ ] Await point analysis
- [ ] AsyncMonitorBackend (Python 3.12+)
- [ ] Integration tests
- [ ] Documentation: Interpreting results

**Success Criteria**:
- Task hierarchy correctly captures parent-child relationships
- Integration tests pass on all Python versions
- Full feature parity across backends (where possible)

### Phase 4: UI & Polish (Checkpoints 11-12)
**Duration**: 0.5 weeks

**Deliverables**:
- [ ] Template implementation
- [ ] Timeline visualization (JavaScript)
- [ ] Navigation subtitle
- [ ] Server-Timing integration
- [ ] User guide documentation
- [ ] Example applications

**Success Criteria**:
- UI clearly presents profiling data
- Timeline visualization shows concurrent execution
- Documentation complete and clear
- Ready for production use

---

## Success Metrics

### Functional Metrics
- [ ] 90%+ test coverage
- [ ] All 12 acceptance criteria pass
- [ ] Works on Python 3.10, 3.11, 3.12, 3.13
- [ ] All backends functional (yappi, eventloop, monitoring)
- [ ] Zero crashes in error scenarios

### Performance Metrics
- [ ] < 5% overhead with yappi backend
- [ ] < 1% overhead with eventloop backend
- [ ] < 0.001s overhead when disabled
- [ ] Handles 100 concurrent tasks without slowdown
- [ ] Memory usage < 50MB for 100 tasks

### Usability Metrics
- [ ] Zero-config setup (works with defaults)
- [ ] Clear blocking call identification (file:line)
- [ ] Intuitive UI (no user training needed)
- [ ] < 5 seconds to identify performance issue

### Quality Metrics
- [ ] All lints pass (ruff)
- [ ] All type checks pass (ty)
- [ ] No anti-patterns (PEP 604, future annotations)
- [ ] Documentation complete (API + user guide)

---

## Risk Assessment

### High-Risk Items

1. **Yappi Integration Complexity** (Probability: Medium, Impact: High)
   - Risk: Yappi's threading model may conflict with request-scoped profiling
   - Mitigation: Isolate yappi state, clear stats before each session
   - Contingency: Fall back to eventloop backend

2. **Event Loop Instrumentation Side Effects** (Probability: Low, Impact: Critical)
   - Risk: Hooking event loop may cause application crashes
   - Mitigation: Try/except in all callbacks, restore original behavior
   - Contingency: Disable async profiling if errors detected

3. **Performance Overhead** (Probability: Medium, Impact: High)
   - Risk: Profiling may slow production apps unacceptably
   - Mitigation: Auto-disable if overhead > 10%, default disabled in prod
   - Contingency: Recommend yappi only in development

### Medium-Risk Items

4. **sys.monitoring API Instability** (Probability: Medium, Impact: Medium)
   - Risk: Python 3.12+ API may change
   - Mitigation: Version guards, extensive error handling
   - Contingency: Skip monitoring backend on affected versions

5. **Task Tracking Race Conditions** (Probability: Low, Impact: Medium)
   - Risk: Concurrent task creation may skip/double-count tasks
   - Mitigation: Thread-safe collections, contextvars
   - Contingency: Document known limitations

6. **Memory Leaks** (Probability: Low, Impact: Medium)
   - Risk: Task references prevent GC
   - Mitigation: Weak references, max task limit, cleanup
   - Contingency: Add memory monitoring, lower default max_tasks

---

## Documentation Requirements

### API Documentation
- [ ] AsyncProfilingPanel docstring (Google style)
- [ ] All backend classes with Args/Returns
- [ ] Configuration options in DebugToolbarConfig
- [ ] Public methods with type hints

### User Guide
- [ ] Installation (with yappi extra)
- [ ] Configuration examples
- [ ] Interpreting profiling results
- [ ] Understanding blocking calls
- [ ] Task hierarchy visualization
- [ ] Performance tuning tips
- [ ] Troubleshooting common issues

### Developer Guide
- [ ] Adding new backends
- [ ] Backend ABC interface
- [ ] Task tracker internals
- [ ] Testing patterns
- [ ] Contributing guidelines

### Examples
- [ ] Basic async profiling setup
- [ ] Detecting blocking operations
- [ ] Optimizing task creation
- [ ] Custom backend implementation

---

## Comparison with Alternatives

### debug-toolbar vs Standalone Tools

| Feature | debug-toolbar async | yappi standalone | py-spy | austin |
|---------|-------------------|------------------|--------|--------|
| ASGI integration | ✓ | ✗ | ✗ | ✗ |
| Request-scoped | ✓ | ✗ | ✗ | ✗ |
| Task hierarchy | ✓ | ✗ | ✗ | ✗ |
| Event loop lag | ✓ | ✗ | ✗ | ✗ |
| Zero config | ✓ | ✗ | ✗ | ✗ |
| Web UI | ✓ | ✗ | ✗ | ✗ |
| Blocking detection | ✓ | Partial | ✓ | ✓ |
| Timeline viz | ✓ | ✗ | ✗ | ✗ |
| Python 3.10+ | ✓ | ✓ | ✓ | ✓ |

### Unique Value Proposition

**AsyncProfilingPanel is the only async profiler that:**
1. Integrates seamlessly with ASGI request lifecycle
2. Provides web UI for profiling results
3. Correlates profiling with specific HTTP requests
4. Tracks asyncio task creation and hierarchy
5. Detects event loop blocking in real-time
6. Requires zero configuration for basic usage

This makes it a **unique differentiator** for the debug-toolbar project and positions it as the premier debugging tool for async Python web applications.

---

## References

### Research Sources

- [Monitoring the asyncio event loop - Stack Overflow](https://stackoverflow.com/questions/38856410/monitoring-the-asyncio-event-loop)
- [Monitoring async Python - MeadSteve's Dev Blog](https://blog.meadsteve.dev/programming/2020/02/23/monitoring-async-python/)
- [Python Async/Sync: Advanced Blocking Detection - DZone](https://dzone.com/articles/python-asyncsync-advanced-blocking-detection-and-b)
- [Developing with asyncio - Python Docs](https://docs.python.org/3/library/asyncio-dev.html)
- [GitHub - sumerc/yappi - Yet Another Python Profiler](https://github.com/sumerc/yappi)
- [Profiling asynchronous Python - Medium](https://medium.com/@maximsmirnov/profiling-asynchronous-python-576568f6f2c0)
- [yappi coroutine profiling docs](https://github.com/sumerc/yappi/blob/master/doc/coroutine-profiling.md)

### Codebase Patterns

- `src/debug_toolbar/core/panel.py` - Panel ABC pattern
- `src/debug_toolbar/core/panels/profiling.py` - Multi-backend profiling
- `src/debug_toolbar/core/panels/memory/panel.py` - Backend selection pattern
- `src/debug_toolbar/core/panels/memory/base.py` - Backend ABC pattern
- `tests/unit/test_profiling_panel.py` - Testing patterns
- `tests/unit/test_memory_panel.py` - Backend testing patterns

---

## Appendix: Code Examples

### Example 1: Basic Usage

```python
from litestar import Litestar
from debug_toolbar import DebugToolbarConfig
from debug_toolbar.litestar import DebugToolbarPlugin

config = DebugToolbarConfig(
    extra_panels=["debug_toolbar.core.panels.async_profiling.AsyncProfilingPanel"],
    async_profiler_backend="auto",
    async_profiler_detect_blocking=True,
    async_profiler_blocking_threshold=0.1,
)

app = Litestar(
    route_handlers=[...],
    plugins=[DebugToolbarPlugin(config=config)],
)
```

### Example 2: Detecting Blocking Calls

```python
import asyncio
import time

async def bad_handler():
    # BAD: Blocks event loop for 200ms
    time.sleep(0.2)
    return {"status": "done"}

async def good_handler():
    # GOOD: Uses async sleep
    await asyncio.sleep(0.2)
    return {"status": "done"}

# AsyncProfilingPanel will detect time.sleep(0.2) as blocking
# and show it in the "Blocking Calls" section with:
# - Function: bad_handler
# - Duration: 0.2s
# - Impact: critical (> 2x threshold)
```

### Example 3: Task Hierarchy

```python
async def parent_task():
    """Creates child tasks - hierarchy will be visualized."""
    results = await asyncio.gather(
        child_task("A"),
        child_task("B"),
        child_task("C"),
    )
    return results

async def child_task(name: str):
    await asyncio.sleep(0.1)
    return f"Result {name}"

# AsyncProfilingPanel will show:
# parent_task (0.1s)
# ├── child_task (0.1s)
# ├── child_task (0.1s)
# └── child_task (0.1s)
```

### Example 4: Custom Backend

```python
from debug_toolbar.core.panels.async_profiling.base import AsyncProfilerBackend

class CustomBackend(AsyncProfilerBackend):
    """Custom profiling backend."""

    def start(self) -> None:
        self._start_time = time.time()
        # Initialize custom profiling

    def stop(self) -> None:
        self._end_time = time.time()
        # Finalize profiling

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": "custom",
            "profiling_overhead": self._end_time - self._start_time,
            # ... other stats
        }

    @classmethod
    def is_available(cls) -> bool:
        return True  # Always available

# Use in config:
config = DebugToolbarConfig(
    async_profiler_backend="custom",
)
```

---

**End of PRD**

**Next Steps**:
1. Review and approve PRD
2. Begin Phase 1 implementation (Foundation)
3. Create tracking issues for each checkpoint
4. Schedule weekly progress reviews
