# Async Profiling Panel - Comprehensive Research

**Word Count Target**: 2000+ words
**Date**: 2025-11-29
**Phase**: 11.3 - Advanced Profiling

---

## 1. Executive Summary

The Async Profiling Panel will provide developers with deep visibility into asynchronous Python code execution during request processing. Unlike traditional profilers that struggle with async code, this panel will accurately track task creation, scheduling, await points, blocking call detection, and event loop lag—all critical for debugging modern async ASGI applications.

This research document analyzes existing patterns in the codebase, industry best practices, and technical approaches for implementing async-aware profiling that integrates seamlessly with the debug toolbar's existing architecture.

---

## 2. Problem Statement

### 2.1 The Async Profiling Challenge

Traditional profilers like cProfile have fundamental limitations with asynchronous code:

1. **Await Point Blindness**: cProfile doesn't understand that `await` suspends execution. It treats the entire async function call as a single unit, missing the actual time distribution across await points.

2. **Context Switch Ignorance**: When one coroutine yields to another, standard profilers lose track of which coroutine is actually consuming CPU time.

3. **Wall Time vs CPU Time Confusion**: Async code often waits on I/O. Standard profilers may report very low CPU time while actual wall-clock time is high, making it difficult to identify bottlenecks.

4. **Task Lifecycle Opacity**: Developers can't see when tasks are created, how long they wait to be scheduled, or how they relate to the parent request.

5. **Blocking Call Detection**: Synchronous code running in an async context blocks the entire event loop—a critical performance issue that's hard to detect.

### 2.2 Impact on ASGI Applications

For Litestar and other ASGI frameworks, these issues directly impact:

- **Request latency**: Undetected blocking calls can add hundreds of milliseconds to response times
- **Throughput**: Event loop blocking prevents concurrent request handling
- **Debugging complexity**: Without proper async profiling, developers resort to print statements and guesswork
- **Production issues**: Problems that don't manifest locally become critical in production under load

---

## 3. Industry Analysis

### 3.1 Python Asyncio Debug Mode

Python's built-in asyncio debug mode provides foundational capabilities:

**Enabling Debug Mode:**
```python
# Method 1: Environment variable
PYTHONASYNCIODEBUG=1 python app.py

# Method 2: Runtime
asyncio.run(main(), debug=True)

# Method 3: Loop-level
loop = asyncio.get_event_loop()
loop.set_debug(True)
```

**Debug Mode Features:**
- Thread safety checks for non-threadsafe APIs
- I/O selector timing logging
- Slow callback detection (default: 100ms threshold)
- Configurable via `loop.slow_callback_duration`

**Limitation**: Debug mode logs warnings but doesn't provide structured data for analysis or visualization.

### 3.2 Yappi Profiler

Yappi (Yet Another Python Profiler) introduced coroutine-aware profiling in v1.2:

**Key Capabilities:**
- Correctly tracks wall time across await points
- Distinguishes between yield (suspend) and real function exit
- Supports both wall-clock and CPU time modes
- Works with threads, greenlets, and coroutines

**Usage Example:**
```python
import asyncio
import yappi

async def fetch_data():
    await asyncio.sleep(1.0)  # Simulated I/O
    return "data"

yappi.set_clock_type("WALL")  # or "CPU"
with yappi.run():
    asyncio.run(fetch_data())

yappi.get_func_stats().print_all()
```

**Output shows accurate timing:**
```
name                  ncall  tsub      ttot      tavg
fetch_data            1      0.000001  1.001234  1.001234
```

**Integration Consideration**: Yappi is a mature, C-based profiler that could serve as an optional high-fidelity backend.

### 3.3 Pyinstrument Async Support

Pyinstrument uses contextvars to track async execution context:

- Statistical sampling approach (lower overhead)
- Automatic async context tracking
- Clean output format focused on user code

**Limitation**: Already integrated in ProfilingPanel; async profiling panel should focus on complementary capabilities.

### 3.4 Event Loop Monitoring Approaches

**Custom Task Factory:**
```python
def profiling_task_factory(loop, coro, *, name=None, context=None):
    task = asyncio.Task(coro, loop=loop, name=name, context=context)
    # Record task creation
    creation_time = loop.time()
    task.add_done_callback(lambda t: record_task_complete(t, creation_time))
    return task

loop.set_task_factory(profiling_task_factory)
```

**Event Loop Time Tracking:**
```python
loop = asyncio.get_event_loop()
start = loop.time()
await some_coroutine()
elapsed = loop.time() - start
```

**Blocking Detection via Thread:**
```python
import threading

def monitor_blocking(loop, threshold_ms=100):
    last_check = loop.time()

    def check():
        nonlocal last_check
        current = loop.time()
        if (current - last_check) * 1000 > threshold_ms:
            # Potential blocking detected
            log_blocking_warning()
        last_check = current
        loop.call_later(0.01, check)

    loop.call_soon(check)
```

---

## 4. Codebase Pattern Analysis

### 4.1 Multi-Backend Architecture (MemoryPanel Pattern)

The MemoryPanel provides an excellent template for async profiling:

**Directory Structure:**
```
src/debug_toolbar/core/panels/memory/
├── __init__.py           # Exports MemoryPanel
├── panel.py              # Main panel class
├── base.py               # MemoryBackend ABC
├── tracemalloc.py        # TraceMallocBackend
└── memray.py             # MemrayBackend
```

**Abstract Base Class Pattern:**
```python
class MemoryBackend(ABC):
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

**Auto-Selection Logic:**
```python
def _select_backend(self) -> Literal["tracemalloc", "memray"]:
    config_backend = self._get_config("memory_backend", "auto")
    if config_backend == "memray":
        if MemrayBackend.is_available():
            return "memray"
        return "tracemalloc"  # Fallback
    if config_backend == "tracemalloc":
        return "tracemalloc"
    # Auto: prefer memray if available
    return "memray" if MemrayBackend.is_available() else "tracemalloc"
```

### 4.2 Panel Lifecycle Pattern (ProfilingPanel)

**Request/Response Hooks:**
```python
async def process_request(self, context: RequestContext) -> None:
    """Start profiling at request start."""
    start = time.perf_counter()
    # Initialize profiler
    self._profiling_overhead = time.perf_counter() - start

async def process_response(self, context: RequestContext) -> None:
    """Stop profiling at response completion."""
    start = time.perf_counter()
    # Stop profiler
    self._profiling_overhead += time.perf_counter() - start
```

**Statistics Generation:**
```python
async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
    return {
        "backend": self._backend,
        "total_time": total_time,
        "function_calls": total_calls,
        "top_functions": top_functions,
        "profiling_overhead": self._profiling_overhead,
    }
```

### 4.3 Handler Introspection Pattern (EventsPanel)

**Function Information Extraction:**
```python
def _get_handler_info(handler: Callable[..., Any] | None) -> dict[str, Any]:
    func = handler
    if hasattr(handler, "__wrapped__"):
        func = handler.__wrapped__
    if hasattr(handler, "func"):
        func = handler.func

    return {
        "name": getattr(func, "__name__", str(func)),
        "module": getattr(func, "__module__", ""),
        "file": inspect.getfile(func),
        "line": inspect.getsourcelines(func)[1],
        "qualname": getattr(func, "__qualname__", ""),
    }
```

**Stack Frame Capture:**
```python
def _get_stack_frames(skip: int = 2, limit: int = 10) -> list[dict[str, Any]]:
    frames = []
    for frame_info in traceback.extract_stack()[:-skip][-limit:]:
        frames.append({
            "file": frame_info.filename,
            "line": frame_info.lineno,
            "function": frame_info.name,
            "code": frame_info.line or "",
        })
    return frames
```

### 4.4 Testing Patterns

**Mock Toolbar Fixture:**
```python
@pytest.fixture
def mock_toolbar() -> MagicMock:
    toolbar = MagicMock()
    toolbar.config = MagicMock()
    toolbar.config.async_profiler_backend = "auto"
    return toolbar
```

**Panel Lifecycle Tests:**
```python
@pytest.mark.asyncio
async def test_process_request_starts_tracking(
    panel: AsyncProfilerPanel, request_context: RequestContext
) -> None:
    await panel.process_request(request_context)
    assert panel._tracking_active is True
```

---

## 5. Technical Design Decisions

### 5.1 Backend Selection

**Recommended Backends:**

| Backend | Default? | Dependencies | Overhead | Capabilities |
|---------|----------|--------------|----------|--------------|
| TaskFactory | Yes | None (stdlib) | Low | Task creation, timing |
| Yappi | Optional | yappi package | Medium | Full coroutine profiling |

**Rationale**: TaskFactory backend uses only stdlib and provides the most critical information (task lifecycle). Yappi backend offers deeper analysis when installed.

### 5.2 Data Structures

**Task Event:**
```python
@dataclass
class TaskEvent:
    task_id: str
    task_name: str
    event_type: Literal["created", "started", "completed", "cancelled"]
    timestamp: float
    coro_name: str
    parent_task_id: str | None
    stack_frames: list[dict[str, Any]]
```

**Blocking Call Record:**
```python
@dataclass
class BlockingCall:
    timestamp: float
    duration_ms: float
    stack_frames: list[dict[str, Any]]
    function_name: str
    file: str
    line: int
```

**Event Loop Lag Sample:**
```python
@dataclass
class LagSample:
    timestamp: float
    expected_delta: float
    actual_delta: float
    lag_ms: float
```

### 5.3 Configuration Options

```python
# In DebugToolbarConfig
async_profiler_backend: Literal["taskfactory", "yappi", "auto"] = "auto"
async_blocking_threshold_ms: float = 100.0
async_slow_callback_threshold_ms: float = 50.0
async_enable_event_loop_monitoring: bool = True
async_event_loop_lag_threshold_ms: float = 10.0
async_track_task_creation: bool = True
async_capture_task_stacks: bool = True
async_max_stack_depth: int = 10
async_max_timeline_events: int = 1000
```

### 5.4 Timeline Visualization

**Approach**: Pure HTML/CSS Gantt-style chart (no external JS libraries)

**Features:**
- Horizontal timeline showing request duration
- Task bars showing start/end times
- Color coding: running (blue), awaiting (yellow), completed (green), cancelled (red)
- Hover tooltips with task details
- Expand/collapse for nested tasks

---

## 6. Implementation Strategy

### 6.1 File Structure

```
src/debug_toolbar/core/panels/async_profiler/
├── __init__.py           # Exports AsyncProfilerPanel
├── panel.py              # Main AsyncProfilerPanel class
├── base.py               # AsyncProfilerBackend ABC
├── taskfactory.py        # TaskFactoryBackend (default)
├── yappi_backend.py      # YappiBackend (optional)
├── detector.py           # BlockingCallDetector
├── models.py             # TaskEvent, BlockingCall, LagSample
└── timeline.py           # Timeline data processing
```

### 6.2 Integration Points

**Middleware Integration:**
```python
# In debug_toolbar/litestar/middleware.py
async def __call__(self, scope, receive, send):
    if self.toolbar_enabled:
        # Get async profiler panel
        panel = self.get_panel("AsyncProfilerPanel")
        if panel and panel.enabled:
            # Install monitoring before request
            panel.install_monitoring()
        try:
            await self.app(scope, receive, send)
        finally:
            if panel and panel.enabled:
                panel.uninstall_monitoring()
```

**Context Storage:**
```python
context.metadata["async_profiling"] = {
    "tasks": [],
    "blocking_calls": [],
    "event_loop_lag": [],
    "timeline_events": [],
    "summary": {
        "total_tasks": 0,
        "blocking_calls_count": 0,
        "max_lag_ms": 0.0,
    },
}
```

### 6.3 Testing Strategy

**Unit Tests (90%+ coverage):**
- Backend selection and fallback
- Task event recording
- Blocking detection thresholds
- Timeline event generation
- Statistics calculation

**Integration Tests:**
- Real async request with concurrent tasks
- Task cancellation scenarios
- Blocking call simulation
- Event loop lag detection

---

## 7. Risk Analysis

### 7.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Event loop interference | Medium | High | Minimal hooks, thorough testing |
| Performance overhead | Medium | Medium | Configurable tracking levels |
| Yappi unavailable | Low | Low | Graceful fallback to TaskFactory |
| Python version differences | Low | Medium | Test across 3.10-3.13 |

### 7.2 Compatibility Considerations

- asyncio API stable since Python 3.7
- Task factory API stable
- Yappi supports Python 3.6+
- No breaking changes expected

---

## 8. Success Criteria

1. **Task Tracking**: Accurately track 100% of tasks created during request
2. **Blocking Detection**: Detect blocking calls >100ms with <10% false positives
3. **Event Loop Monitoring**: Measure lag with <1ms precision
4. **Performance**: <15ms overhead with default settings
5. **Test Coverage**: >90% for all modules
6. **Documentation**: Complete API documentation and usage examples

---

## 9. References

### Documentation
- [Python asyncio Development](https://docs.python.org/3/library/asyncio-dev.html)
- [Yappi Coroutine Profiling](https://github.com/sumerc/yappi/blob/master/doc/coroutine-profiling.md)
- [Profiling Asyncio Code](https://roguelynn.com/words/asyncio-profiling/)

### Related Research
- [Monitoring the asyncio event loop - Stack Overflow](https://stackoverflow.com/questions/38856410/monitoring-the-asyncio-event-loop)
- [Profiling Asynchronous Python - Medium](https://medium.com/@maximsmirnov/profiling-asynchronous-python-576568f6f2c0)

### Existing Patterns
- `src/debug_toolbar/core/panels/memory/` - Multi-backend architecture
- `src/debug_toolbar/core/panels/profiling.py` - Profiler lifecycle
- `src/debug_toolbar/litestar/panels/events.py` - Handler introspection

---

**Word Count**: ~2,400 words
