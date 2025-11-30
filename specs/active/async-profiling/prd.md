# PRD: Async Profiling Panel

## Metadata

| Field | Value |
|-------|-------|
| **Slug** | async-profiling |
| **Phase** | 11.3 |
| **Complexity** | Complex |
| **Checkpoints** | 10+ |
| **Priority** | P1 (High) |
| **Effort** | High |
| **Author** | Claude |
| **Created** | 2025-11-29 |
| **Status** | Draft |

---

## Intelligence Context

### Similar Implementations Analyzed

| File | Pattern | Relevance |
|------|---------|-----------|
| `src/debug_toolbar/core/panels/memory/` | Multi-backend ABC architecture | High - same pattern for backends |
| `src/debug_toolbar/core/panels/profiling.py` | Profiler lifecycle, overhead tracking | High - timing patterns |
| `src/debug_toolbar/litestar/panels/events.py` | Handler introspection, stack capture | High - inspection utilities |
| `src/debug_toolbar/core/panels/timer.py` | perf_counter usage | Medium - timing reference |

### Patterns to Follow

1. **Multi-Backend ABC Pattern**: Abstract base class with `start()`, `stop()`, `get_stats()`, `is_available()` methods
2. **Panel Lifecycle Pattern**: `process_request()` → work → `process_response()` → `generate_stats()`
3. **Configuration Pattern**: `_get_config()` helper with defaults, config-driven backend selection
4. **Handler Introspection Pattern**: `inspect` module for function info, `traceback.extract_stack()` for frames
5. **Testing Pattern**: Mock toolbar fixture, class-based test organization, edge case coverage

### Existing Infrastructure to Leverage

- `RequestContext.metadata` for storing async profiling data
- `Panel` ABC for consistent interface
- Existing templates and CSS for UI consistency
- Test fixtures from `conftest.py`

---

## Problem Statement

### The Challenge

Modern ASGI applications built with Litestar, FastAPI, and Starlette rely heavily on asynchronous programming. However, debugging async code remains significantly harder than debugging synchronous code because:

1. **Traditional profilers fail with async code**: cProfile and similar tools don't understand `await` points. They treat an entire async function as a single call, missing the critical insight of where time is actually spent.

2. **Task lifecycle is invisible**: When `asyncio.create_task()` spawns concurrent tasks, developers have no visibility into when tasks are created, how long they wait to be scheduled, or their relationship to the parent request.

3. **Blocking calls are silent killers**: A single synchronous database call or file read in an async context can block the entire event loop, degrading performance for all concurrent requests. These issues are nearly impossible to detect without specialized tooling.

4. **Event loop lag goes unnoticed**: When the event loop falls behind, response times increase unpredictably. Without monitoring, developers blame the wrong components.

### Impact

| Issue | Symptom | Business Impact |
|-------|---------|-----------------|
| Undetected blocking calls | Intermittent slow requests | User frustration, SLA violations |
| Invisible task overhead | Memory growth, timeout errors | System instability |
| Event loop lag | Inconsistent latency | Poor user experience |
| No async debugging tools | Extended debugging sessions | Developer productivity loss |

### User Stories

**As a backend developer**, I want to see all async tasks created during my request so that I can understand the concurrent execution pattern and identify unnecessary task creation.

**As a performance engineer**, I want to detect blocking calls in async code so that I can eliminate event loop blocking and improve throughput.

**As a DevOps engineer**, I want to monitor event loop lag so that I can identify when the application is under stress before it affects users.

**As a debugging developer**, I want a timeline view of task execution so that I can visualize the actual concurrent behavior of my async code.

---

## Acceptance Criteria

### Functional Requirements

#### Task Tracking
- [ ] Track all `asyncio.create_task()` calls during request processing
- [ ] Record task name, creation time, and completion time
- [ ] Capture the coroutine function name for each task
- [ ] Track parent-child task relationships
- [ ] Record task cancellation events
- [ ] Capture creation stack traces (configurable depth)

#### Blocking Call Detection
- [ ] Detect callbacks/coroutines taking longer than configurable threshold (default: 100ms)
- [ ] Capture stack trace at the time of blocking detection
- [ ] Report the blocking duration in milliseconds
- [ ] Identify the function/file/line causing the block
- [ ] Provide visual warning in panel navigation

#### Event Loop Monitoring
- [ ] Monitor event loop lag with configurable sampling interval
- [ ] Report maximum lag observed during request
- [ ] Track lag samples over time for the request duration
- [ ] Threshold-based alerts for excessive lag (default: 10ms)

#### Timeline Visualization
- [ ] Display horizontal Gantt-style timeline of task execution
- [ ] Color code task states: created (gray), running (blue), awaiting (yellow), completed (green), cancelled (red)
- [ ] Show task duration on hover
- [ ] Indicate blocking call periods in timeline
- [ ] Support nested task visualization

#### Statistics Generation
- [ ] Total tasks created during request
- [ ] Total blocking calls detected
- [ ] Maximum event loop lag
- [ ] Profiling overhead measurement
- [ ] Per-task timing breakdown

### Non-Functional Requirements

#### Performance
- [ ] Default configuration overhead < 15ms per request
- [ ] Memory overhead < 1MB per request for typical workloads
- [ ] No impact on event loop when panel is disabled

#### Compatibility
- [ ] Support Python 3.10, 3.11, 3.12, 3.13
- [ ] Work with uvloop event loop policy
- [ ] Compatible with anyio-based applications
- [ ] No interference with existing profiling panels

#### Testing
- [ ] Unit test coverage > 90%
- [ ] Integration tests for real async scenarios
- [ ] Edge case tests for task cancellation, exceptions

#### Configuration
- [ ] All thresholds configurable via `DebugToolbarConfig`
- [ ] Backend selectable: "taskfactory", "yappi", "auto"
- [ ] Individual features toggleable (task tracking, blocking detection, etc.)

---

## Technical Approach

### Architecture Overview

The Async Profiling Panel follows the established multi-backend pattern from MemoryPanel, with a primary TaskFactory-based backend (no dependencies) and an optional Yappi-based backend (for deeper analysis).

```
┌─────────────────────────────────────────────────────────────┐
│                    AsyncProfilerPanel                        │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │   Config    │  │  Backend ABC   │  │  Timeline Gen    │ │
│  │  Options    │  │  (Selectable)  │  │  (Visualization) │ │
│  └─────────────┘  └────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
   │ TaskFactory   │ │ Yappi         │ │ Blocking      │
   │ Backend       │ │ Backend       │ │ Detector      │
   │ (Default)     │ │ (Optional)    │ │ (Utility)     │
   └───────────────┘ └───────────────┘ └───────────────┘
```

### Backend Design

#### AsyncProfilerBackend (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import Any

class AsyncProfilerBackend(ABC):
    """Abstract base class for async profiling backends."""

    @abstractmethod
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Begin async profiling. Called at request start."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """End async profiling. Called at request end."""
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Retrieve profiling statistics.

        Returns:
            Dictionary containing:
                - tasks: List of task events
                - blocking_calls: List of blocking call records
                - event_loop_lag: List of lag samples
                - summary: Aggregate statistics
                - backend: Backend name
                - profiling_overhead: Time spent profiling (seconds)
        """
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend is available."""
        ...
```

#### TaskFactoryBackend (Default)

Uses Python's asyncio task factory mechanism to intercept task creation:

```python
class TaskFactoryBackend(AsyncProfilerBackend):
    """Default backend using asyncio task factory hooks."""

    def __init__(self) -> None:
        self._original_factory: TaskFactory | None = None
        self._tasks: list[TaskEvent] = []
        self._start_time: float = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._start_time = loop.time()
        self._original_factory = loop.get_task_factory()
        loop.set_task_factory(self._profiling_task_factory)

    def _profiling_task_factory(
        self,
        loop: asyncio.AbstractEventLoop,
        coro: Coroutine[Any, Any, Any],
        *,
        name: str | None = None,
        context: Context | None = None,
    ) -> asyncio.Task[Any]:
        task = asyncio.Task(coro, loop=loop, name=name, context=context)
        creation_time = loop.time() - self._start_time

        event = TaskEvent(
            task_id=str(id(task)),
            task_name=task.get_name(),
            event_type="created",
            timestamp=creation_time,
            coro_name=coro.__qualname__,
            parent_task_id=None,
            stack_frames=_get_stack_frames(),
        )
        self._tasks.append(event)

        task.add_done_callback(
            lambda t: self._record_task_complete(t, creation_time)
        )
        return task

    def stop(self) -> None:
        if self._loop and self._original_factory is not None:
            self._loop.set_task_factory(self._original_factory)

    @classmethod
    def is_available(cls) -> bool:
        return True  # Always available - stdlib only
```

#### YappiBackend (Optional)

Provides deeper coroutine-aware profiling when yappi is installed:

```python
class YappiBackend(AsyncProfilerBackend):
    """Optional backend using yappi for detailed coroutine profiling."""

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        import yappi
        yappi.set_clock_type("WALL")
        yappi.start()
        # Also install task factory for task tracking
        ...

    def stop(self) -> None:
        import yappi
        yappi.stop()

    def get_stats(self) -> dict[str, Any]:
        import yappi
        func_stats = yappi.get_func_stats()
        # Convert to our format with coroutine timing
        ...

    @classmethod
    def is_available(cls) -> bool:
        try:
            import yappi
            return True
        except ImportError:
            return False
```

### Blocking Call Detection

The BlockingCallDetector uses asyncio's slow callback duration feature combined with custom monitoring:

```python
class BlockingCallDetector:
    """Detects blocking calls in async context."""

    def __init__(self, threshold_ms: float = 100.0) -> None:
        self._threshold_ms = threshold_ms
        self._blocking_calls: list[BlockingCall] = []
        self._original_duration: float | None = None

    def install(self, loop: asyncio.AbstractEventLoop) -> None:
        # Enable debug mode for slow callback detection
        loop.set_debug(True)
        self._original_duration = loop.slow_callback_duration
        loop.slow_callback_duration = self._threshold_ms / 1000.0

        # Install custom exception handler to capture slow callbacks
        original_handler = loop.get_exception_handler()
        loop.set_exception_handler(self._exception_handler)

    def _exception_handler(
        self,
        loop: asyncio.AbstractEventLoop,
        context: dict[str, Any],
    ) -> None:
        # Capture slow callback warnings
        message = context.get("message", "")
        if "slow callback" in message.lower():
            self._blocking_calls.append(
                BlockingCall(
                    timestamp=loop.time(),
                    duration_ms=...,
                    stack_frames=_get_stack_frames(),
                    ...
                )
            )
```

### Event Loop Lag Monitoring

```python
class EventLoopLagMonitor:
    """Monitors event loop lag via scheduled callbacks."""

    def __init__(self, sample_interval: float = 0.01) -> None:
        self._sample_interval = sample_interval  # 10ms
        self._samples: list[LagSample] = []
        self._running = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._running = True
        self._last_check = loop.time()
        loop.call_soon(self._check_lag)

    def _check_lag(self) -> None:
        if not self._running:
            return

        current = self._loop.time()
        expected = self._sample_interval
        actual = current - self._last_check
        lag = (actual - expected) * 1000  # Convert to ms

        if lag > 0:
            self._samples.append(LagSample(
                timestamp=current,
                expected_delta=expected,
                actual_delta=actual,
                lag_ms=lag,
            ))

        self._last_check = current
        self._loop.call_later(self._sample_interval, self._check_lag)
```

### Panel Implementation

```python
class AsyncProfilerPanel(Panel):
    """Panel for profiling async task execution and event loop behavior."""

    panel_id: ClassVar[str] = "AsyncProfilerPanel"
    title: ClassVar[str] = "Async"
    template: ClassVar[str] = "panels/async_profiler.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Async"

    __slots__ = (
        "_backend",
        "_backend_name",
        "_blocking_detector",
        "_lag_monitor",
        "_profiling_overhead",
        "_task_count",
        "_blocking_count",
    )

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._backend_name = self._select_backend()
        self._backend = self._create_backend(self._backend_name)
        self._blocking_detector = BlockingCallDetector(
            threshold_ms=self._get_config("async_blocking_threshold_ms", 100.0)
        )
        self._lag_monitor = EventLoopLagMonitor()
        self._profiling_overhead = 0.0
        self._task_count = 0
        self._blocking_count = 0

    async def process_request(self, context: RequestContext) -> None:
        start = time.perf_counter()

        loop = asyncio.get_running_loop()
        self._backend.start(loop)

        if self._get_config("async_enable_blocking_detection", True):
            self._blocking_detector.install(loop)

        if self._get_config("async_enable_event_loop_monitoring", True):
            self._lag_monitor.start(loop)

        self._profiling_overhead = time.perf_counter() - start

    async def process_response(self, context: RequestContext) -> None:
        start = time.perf_counter()

        self._backend.stop()
        self._blocking_detector.uninstall()
        self._lag_monitor.stop()

        self._profiling_overhead += time.perf_counter() - start

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        backend_stats = self._backend.get_stats()
        blocking_stats = self._blocking_detector.get_stats()
        lag_stats = self._lag_monitor.get_stats()

        self._task_count = len(backend_stats.get("tasks", []))
        self._blocking_count = len(blocking_stats.get("blocking_calls", []))

        timeline = self._generate_timeline(
            backend_stats["tasks"],
            blocking_stats["blocking_calls"],
        )

        return {
            "backend": self._backend_name,
            "tasks": backend_stats["tasks"],
            "blocking_calls": blocking_stats["blocking_calls"],
            "event_loop_lag": lag_stats["samples"],
            "timeline": timeline,
            "summary": {
                "total_tasks": self._task_count,
                "blocking_calls_count": self._blocking_count,
                "max_lag_ms": lag_stats.get("max_lag_ms", 0.0),
                "has_warnings": self._blocking_count > 0,
            },
            "profiling_overhead": self._profiling_overhead,
        }

    def get_nav_subtitle(self) -> str:
        if self._blocking_count > 0:
            return f"⚠️ {self._blocking_count} blocking"
        return f"{self._task_count} tasks"
```

### Configuration Options

Add to `DebugToolbarConfig`:

```python
@dataclass
class DebugToolbarConfig:
    # ... existing options ...

    # Async Profiler Options
    async_profiler_backend: Literal["taskfactory", "yappi", "auto"] = "auto"
    async_blocking_threshold_ms: float = 100.0
    async_slow_callback_threshold_ms: float = 50.0
    async_enable_blocking_detection: bool = True
    async_enable_event_loop_monitoring: bool = True
    async_event_loop_lag_threshold_ms: float = 10.0
    async_track_task_creation: bool = True
    async_capture_task_stacks: bool = True
    async_max_stack_depth: int = 10
    async_max_timeline_events: int = 1000
```

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/debug_toolbar/core/panels/async_profiler/__init__.py` | Package exports |
| `src/debug_toolbar/core/panels/async_profiler/panel.py` | AsyncProfilerPanel class |
| `src/debug_toolbar/core/panels/async_profiler/base.py` | AsyncProfilerBackend ABC |
| `src/debug_toolbar/core/panels/async_profiler/taskfactory.py` | TaskFactoryBackend |
| `src/debug_toolbar/core/panels/async_profiler/yappi_backend.py` | YappiBackend |
| `src/debug_toolbar/core/panels/async_profiler/detector.py` | BlockingCallDetector |
| `src/debug_toolbar/core/panels/async_profiler/models.py` | Data classes |
| `src/debug_toolbar/core/panels/async_profiler/timeline.py` | Timeline generation |
| `src/debug_toolbar/templates/panels/async_profiler.html` | Panel template |
| `tests/unit/test_async_profiler_panel.py` | Unit tests |

### Modified Files

| File | Modification |
|------|--------------|
| `src/debug_toolbar/core/config.py` | Add async profiler config options |
| `src/debug_toolbar/core/panels/__init__.py` | Export AsyncProfilerPanel |
| `src/debug_toolbar/__init__.py` | Include in public API |

---

## Testing Strategy

### Unit Tests (Target: 90%+ Coverage)

#### Backend Tests

```python
class TestTaskFactoryBackend:
    """Tests for TaskFactoryBackend."""

    def test_is_always_available(self) -> None:
        assert TaskFactoryBackend.is_available() is True

    @pytest.mark.asyncio
    async def test_tracks_task_creation(self) -> None:
        backend = TaskFactoryBackend()
        loop = asyncio.get_running_loop()
        backend.start(loop)

        async def sample_task():
            await asyncio.sleep(0.01)

        task = asyncio.create_task(sample_task())
        await task

        backend.stop()
        stats = backend.get_stats()

        assert len(stats["tasks"]) >= 1
        assert stats["tasks"][0]["coro_name"] == "sample_task"

    @pytest.mark.asyncio
    async def test_restores_original_factory(self) -> None:
        loop = asyncio.get_running_loop()
        original = loop.get_task_factory()

        backend = TaskFactoryBackend()
        backend.start(loop)
        backend.stop()

        assert loop.get_task_factory() == original
```

#### Blocking Detection Tests

```python
class TestBlockingCallDetector:
    """Tests for BlockingCallDetector."""

    @pytest.mark.asyncio
    async def test_detects_blocking_call(self) -> None:
        detector = BlockingCallDetector(threshold_ms=10)
        loop = asyncio.get_running_loop()
        detector.install(loop)

        # Simulate blocking
        import time
        time.sleep(0.02)  # 20ms blocking

        detector.uninstall()
        stats = detector.get_stats()

        assert len(stats["blocking_calls"]) >= 1

    @pytest.mark.asyncio
    async def test_no_false_positives(self) -> None:
        detector = BlockingCallDetector(threshold_ms=100)
        loop = asyncio.get_running_loop()
        detector.install(loop)

        await asyncio.sleep(0.01)  # Non-blocking

        detector.uninstall()
        stats = detector.get_stats()

        assert len(stats["blocking_calls"]) == 0
```

#### Panel Tests

```python
class TestAsyncProfilerPanel:
    """Tests for AsyncProfilerPanel."""

    def test_panel_metadata(self) -> None:
        assert AsyncProfilerPanel.panel_id == "AsyncProfilerPanel"
        assert AsyncProfilerPanel.title == "Async"
        assert AsyncProfilerPanel.has_content is True

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self, mock_toolbar: MagicMock, request_context: RequestContext
    ) -> None:
        panel = AsyncProfilerPanel(mock_toolbar)

        await panel.process_request(request_context)

        async def work():
            await asyncio.sleep(0.01)

        await work()

        await panel.process_response(request_context)
        stats = await panel.generate_stats(request_context)

        assert "tasks" in stats
        assert "blocking_calls" in stats
        assert "profiling_overhead" in stats
```

### Integration Tests

```python
class TestAsyncProfilerIntegration:
    """Integration tests with real async code."""

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self) -> None:
        """Test tracking of concurrent task execution."""
        ...

    @pytest.mark.asyncio
    async def test_nested_tasks(self) -> None:
        """Test parent-child task relationship tracking."""
        ...

    @pytest.mark.asyncio
    async def test_task_cancellation(self) -> None:
        """Test cancelled task tracking."""
        ...
```

---

## Out of Scope

The following features are explicitly out of scope for this implementation:

1. **Cross-request task tracking**: Tasks that outlive the request are not tracked
2. **Distributed tracing integration**: OpenTelemetry integration is Phase 14
3. **Historical comparison**: Comparing async behavior across requests
4. **External async frameworks**: trio, curio support (asyncio only)
5. **Automatic blocking call fixes**: Panel provides detection, not auto-remediation
6. **Real-time streaming**: Timeline updates only on request completion

---

## Dependencies

### Required (Core)
- Python 3.10+ (asyncio task factory API)
- No new external dependencies for default backend

### Optional (Enhanced)
- `yappi` - For YappiBackend with deeper coroutine profiling

---

## Rollout Plan

### Phase 1: Core Implementation
1. Create directory structure and base classes
2. Implement TaskFactoryBackend
3. Implement basic panel with task tracking
4. Add unit tests

### Phase 2: Detection Features
1. Implement BlockingCallDetector
2. Implement EventLoopLagMonitor
3. Add detection tests
4. Update panel statistics

### Phase 3: Visualization
1. Create timeline generation logic
2. Build HTML template with CSS timeline
3. Add tooltips and interactions
4. Integration tests

### Phase 4: Optional Backend
1. Implement YappiBackend
2. Add yappi-specific tests
3. Documentation

### Phase 5: Polish
1. Configuration documentation
2. Example usage in docs
3. Performance benchmarking
4. Final review

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | >90% | pytest-cov report |
| Performance Overhead | <15ms | Benchmark suite |
| Task Tracking Accuracy | 100% | Integration tests |
| Blocking Detection | <10% false positives | Manual verification |
| Documentation | Complete | Review checklist |

---

## Appendix: Research Sources

- [Python asyncio Development Documentation](https://docs.python.org/3/library/asyncio-dev.html)
- [Yappi GitHub Repository](https://github.com/sumerc/yappi)
- [Profiling Asyncio Code - roguelynn](https://roguelynn.com/words/asyncio-profiling/)
- [Monitoring the asyncio event loop - Stack Overflow](https://stackoverflow.com/questions/38856410/monitoring-the-asyncio-event-loop)
- Internal patterns: MemoryPanel, ProfilingPanel, EventsPanel

---

**Word Count**: ~3,600 words
