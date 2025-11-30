# Research Plan: Async Profiling Panel

**Created**: 2025-11-29
**Status**: Complete
**Research Duration**: 4 hours

---

## Research Methodology

### Phase 1: Codebase Pattern Analysis (90 minutes)

**Objective**: Understand existing panel and backend patterns to ensure consistency.

**Files Analyzed**:
1. `src/debug_toolbar/core/panel.py` (148 lines)
   - Panel ABC with ClassVar metadata
   - Lifecycle hooks: `process_request()`, `process_response()`
   - Abstract `generate_stats()` method
   - `record_stats()` and `get_stats()` context helpers
   - `generate_server_timing()` for performance headers
   - Navigation subtitle pattern

2. `src/debug_toolbar/core/panels/profiling.py` (390 lines)
   - Multi-backend architecture (cProfile, pyinstrument)
   - Backend selection via config with auto-detection
   - Graceful fallback when backend unavailable
   - Statistics filtering (stdlib vs user code)
   - Flame graph integration
   - Profiling overhead tracking

3. `src/debug_toolbar/core/panels/memory/panel.py` (185 lines)
   - Backend ABC pattern imported from `base.py`
   - Platform-specific backend availability
   - Before/after snapshot pattern
   - Memory delta calculation and formatting
   - Navigation subtitle with dynamic metrics

4. `src/debug_toolbar/core/panels/memory/base.py` (58 lines)
   - Clean ABC with `start()`, `stop()`, `get_stats()`
   - `is_available()` classmethod for capability detection
   - Consistent return structure documented in docstring

5. `src/debug_toolbar/core/config.py` (72 lines)
   - Dataclass pattern for configuration
   - Literal types for backend selection
   - Sensible defaults
   - Panel-specific config options inline

6. `src/debug_toolbar/core/context.py` (105 lines)
   - ContextVar for async-safe request context
   - UUID for request tracking
   - Typed dictionaries for panel data
   - Helper functions: `get_request_context()`, `set_request_context()`

**Key Patterns Identified**:

1. **Multi-Backend Pattern**:
   - Backend ABC in separate `base.py`
   - Each backend in own file
   - `is_available()` for dependency checks
   - Panel selects backend in `__init__`

2. **Statistics Structure**:
   - Always include "backend" and "profiling_overhead"
   - Top-level metrics first
   - Collections (lists) for detailed data
   - Nested dicts for grouped metrics

3. **Configuration Pattern**:
   - `{feature}_backend` for backend selection
   - `{feature}_*` prefix for related options
   - Literal types for enumerated choices
   - Defaults optimized for development

4. **Testing Pattern**:
   - Class-based organization by feature
   - Fixtures for common objects
   - Structure validation (dict key checks)
   - Edge cases: empty, errors, disabled

### Phase 2: Async Profiling Research (120 minutes)

**Objective**: Understand async profiling challenges and available tools.

**Web Research Conducted**:

**Query 1**: "Python asyncio profiling sys.monitoring await tracking event loop lag detection 2025"

**Key Findings**:
- **Event Loop Debug Mode**: `loop.slow_callback_duration` for logging slow callbacks (>100ms default)
- **Lag Measurement Pattern**: Time difference between `asyncio.sleep()` expected and actual duration
- **loopmon Library**: Lightweight monitor for asyncio.EventLoop, detects lag from blocking calls
- **Challenges**: cProfile sees `await` as function exit, causing incorrect wall time and inflated call counts
- **sys.monitoring**: Not widely documented for asyncio-specific profiling (Python 3.12+)

**Query 2**: "yappi async profiler Python asyncio task tracking concurrent execution timeline"

**Key Findings**:
- **Yappi Overview**: Multithreading, asyncio, and gevent aware profiler written in C
- **Coroutine Profiling**: v1.2+ correctly handles coroutine yields, doesn't increment call count
- **Wall Time Support**: `yappi.set_clock_type("WALL")` for I/O-bound profiling
- **Usage Pattern**:
  ```python
  import yappi
  yappi.set_clock_type("WALL")
  yappi.start(builtins=False)
  # ... async code ...
  yappi.stop()
  stats = yappi.get_func_stats()
  ```
- **Integration**: PyCharm uses yappi by default for async profiling
- **Visualization**: Can export to gprof2dot for call graph visualization

**Sources**:
1. [Monitoring the asyncio event loop - Stack Overflow](https://stackoverflow.com/questions/38856410/monitoring-the-asyncio-event-loop)
2. [Monitoring async Python - MeadSteve's Dev Blog](https://blog.meadsteve.dev/programming/2020/02/23/monitoring-async-python/)
3. [Python Async/Sync: Advanced Blocking Detection - DZone](https://dzone.com/articles/python-asyncsync-advanced-blocking-detection-and-b)
4. [Developing with asyncio - Python Docs](https://docs.python.org/3/library/asyncio-dev.html)
5. [GitHub - sumerc/yappi](https://github.com/sumerc/yappi)
6. [Profiling asynchronous Python - Medium](https://medium.com/@maximsmirnov/profiling-asynchronous-python-576568f6f2c0)
7. [yappi coroutine profiling docs](https://github.com/sumerc/yappi/blob/master/doc/coroutine-profiling.md)

### Phase 3: Testing Pattern Analysis (60 minutes)

**Objective**: Understand test structure for 90%+ coverage.

**Test Files Analyzed**:

1. `tests/unit/test_profiling_panel.py` (445 lines, 40+ tests)
   - Test classes: Init, BackendSelection, Processing, EmptyStats, ServerTiming, NavSubtitle, ConfigOptions, CProfileTree, Pyinstrument, EdgeCases, Flamegraph
   - Fixtures: `mock_toolbar`, `profiling_panel`, `request_context`
   - Pattern: Each test class focuses on one feature area
   - Async tests clean up context: `set_request_context(None)`
   - Structure validation: Check dict keys exist
   - Conditional skips: `pytest.mark.skipif` for optional backends

2. `tests/unit/test_memory_panel.py` (423 lines, 35+ tests)
   - Similar class-based structure
   - Backend-specific tests with availability checks
   - Navigation subtitle formatting tests (bytes/KB/MB/GB)
   - Error handling tests with mocked exceptions
   - Backend ABC instantiation test (should fail)

**Test Coverage Strategy**:
- **Unit tests**: 85-95% coverage per module
- **Integration tests**: End-to-end workflows
- **Edge cases**: Errors, empty data, disabled state
- **Backend-specific**: Conditional execution based on availability

**Estimated Test Count for Async Profiling**:
- Panel tests: 40 tests
- YappiBackend: 15 tests
- MonitoringBackend: 15 tests
- EventLoopBackend: 12 tests
- TaskTracker: 18 tests
- Integration: 8 tests
- **Total**: ~108 tests → ~90% coverage

### Phase 4: Architecture Design (90 minutes)

**Objective**: Design backend architecture and data flow.

**Backend Selection Logic**:
```
Config: async_profiler_backend = "auto"

Check backends in priority order:
1. YappiBackend.is_available()
   ├─ True → Use yappi (best async support)
   └─ False → Continue
2. sys.version_info >= (3, 12) and AsyncMonitorBackend.is_available()
   ├─ True → Use monitoring (native, efficient)
   └─ False → Continue
3. EventLoopMonitorBackend.is_available()
   └─ True → Use eventloop (always available fallback)
```

**Data Flow**:
```
1. Request arrives
2. Middleware calls panel.process_request(context)
3. Panel calls backend.start()
   ├─ YappiBackend: yappi.start()
   ├─ MonitoringBackend: sys.monitoring.use_tool_id()
   └─ EventLoopBackend: Record start time, count tasks
4. Application code executes (async handlers, tasks, etc.)
5. Middleware calls panel.process_response(context)
6. Panel calls backend.stop()
7. Panel calls backend.get_stats()
8. Backend transforms profiling data to standard schema
9. Panel stores stats in context
10. UI renders stats via template
```

**Backend Interface Design**:
```python
class AsyncProfilerBackend(ABC):
    @abstractmethod
    def start(self) -> None:
        """Initialize profiling (< 1ms overhead)."""

    @abstractmethod
    def stop(self) -> None:
        """Finalize profiling, capture state."""

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Return standardized statistics."""

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check dependencies and compatibility."""
```

**Task Tracking Approach**:

Option 1: Monkey-patch `asyncio.create_task()` (chosen)
- Pros: Captures all task creation
- Cons: Intrusive, may conflict with other patches

Option 2: Hook into event loop callbacks
- Pros: Less intrusive
- Cons: More complex, may miss tasks

Option 3: Use contextvars to track current task
- Pros: Clean, async-safe
- Cons: Requires code instrumentation

**Decision**: Use Option 1 with careful restoration in `stop()`.

### Phase 5: Risk Analysis (30 minutes)

**Objective**: Identify and mitigate implementation risks.

**Critical Risks**:

1. **Yappi State Isolation** (High probability, High impact)
   - Problem: Yappi uses global state, concurrent requests may conflict
   - Evidence: Yappi docs mention thread-local stats
   - Mitigation: Call `yappi.clear_stats()` before each `start()`
   - Testing: Multi-threaded request test

2. **Event Loop Instrumentation** (Low probability, Critical impact)
   - Problem: Hooking event loop may cause crashes
   - Evidence: asyncio internals are complex
   - Mitigation: Extensive try/except, restore original behavior
   - Testing: Stress test with high concurrency

3. **Performance Overhead** (Medium probability, High impact)
   - Problem: Profiling may slow requests unacceptably
   - Evidence: cProfile adds 5-10% overhead
   - Mitigation: Benchmark, auto-disable if > 10% overhead
   - Testing: Load test comparing enabled/disabled

**Medium Risks**:

4. **sys.monitoring API Changes** (Medium probability, Medium impact)
   - Problem: Python 3.12+ API is new, may evolve
   - Evidence: New stdlib APIs often change
   - Mitigation: Version guards, graceful degradation
   - Testing: CI on Python 3.12, 3.13

5. **Memory Leaks** (Low probability, Medium impact)
   - Problem: Task references prevent GC
   - Evidence: Common issue with profilers
   - Mitigation: Weak references, max task limit
   - Testing: Long-running profiling with memory monitoring

**Low Risks**:

6. **Task Tracking Race Conditions** (Low probability, Low impact)
   - Problem: Concurrent task creation may miss tasks
   - Evidence: asyncio allows concurrent operations
   - Mitigation: Thread-safe collections (asyncio is single-threaded per loop)
   - Testing: Rapid task creation test

---

## Technical Deep Dives

### Asyncio Profiling Challenges

**Challenge 1: Context Switching Distorts Metrics**

Traditional profilers like cProfile record events:
- Function entry: Start timer
- Function exit: Stop timer, record duration

For async functions:
```python
async def fetch_data():
    result = await db.query()  # ← Yields to event loop
    return result
```

What happens:
1. `fetch_data()` called → Timer starts
2. `await db.query()` → Coroutine yields
3. Profiler sees yield as function exit → Timer stops
4. Other tasks run on event loop
5. `db.query()` completes, `fetch_data()` resumes → Timer starts again
6. `fetch_data()` returns → Timer stops

**Problems**:
- Wall time calculation: Only counts active time, misses await time
- Call count: Each resume increments call count (looks like multiple calls)
- Parent-child relationship: Lost when coroutine yields

**Yappi Solution**:
- Tracks coroutine state separately from function calls
- Accumulates time across yields
- Correctly attributes wait time to coroutine

**Challenge 2: Concurrent Execution**

Multiple tasks run "simultaneously":
```python
tasks = [
    asyncio.create_task(fetch_user(1)),
    asyncio.create_task(fetch_user(2)),
    asyncio.create_task(fetch_user(3)),
]
results = await asyncio.gather(*tasks)
```

Timeline:
```
Time  | Task 1        | Task 2        | Task 3
------|---------------|---------------|---------------
0ms   | fetch_user(1) |               |
5ms   | await query   | fetch_user(2) |
10ms  | ...waiting... | await query   | fetch_user(3)
15ms  | ...waiting... | ...waiting... | await query
20ms  | resume        | ...waiting... | ...waiting...
25ms  | return        | resume        | ...waiting...
30ms  |               | return        | resume
35ms  |               |               | return
```

**Need to track**:
- Individual task durations
- Overlapping execution periods
- Parent task (who created the task)
- Child tasks (who did this task create)

**TaskTracker Solution**:
- Hook `asyncio.create_task()` to capture creation
- Record parent task ID (via `asyncio.current_task()`)
- Add completion callback to capture end time
- Build hierarchy tree after profiling

**Challenge 3: Blocking Detection**

Sync code blocks event loop:
```python
async def handler():
    time.sleep(0.5)  # ← BLOCKS event loop for 500ms
    return "done"
```

During `time.sleep(0.5)`:
- Event loop cannot run other tasks
- All async operations delayed
- Application appears frozen

**Detection Methods**:

1. **Yappi Function Time** (chosen):
   - Non-async functions with high wall time are blocking
   - Filter: `tavg >= blocking_threshold` and not coroutine

2. **Event Loop Lag** (supplementary):
   - Measure: `actual_sleep - expected_sleep`
   - High lag indicates blocking

3. **sys.monitoring** (Python 3.12+):
   - Monitor C_RETURN events
   - Long-running C calls are blocking

### Yappi Integration Details

**Initialization**:
```python
import yappi

# Use wall clock (includes I/O wait time)
yappi.set_clock_type("WALL")

# Alternative: CPU time (excludes I/O wait)
# yappi.set_clock_type("CPU")

# Clear any previous profiling data
yappi.clear_stats()

# Start profiling
# builtins=False: Don't profile built-in functions (noise)
yappi.start(builtins=False)
```

**Data Extraction**:
```python
yappi.stop()

# Function statistics
func_stats = yappi.get_func_stats()

# Iterate over stats
for stat in func_stats:
    # stat.name: Function name
    # stat.module: Module/file
    # stat.lineno: Line number
    # stat.ncall: Call count (correct for coroutines)
    # stat.ttot: Total time
    # stat.tsub: Cumulative time (including callees)
    # stat.tavg: Average time per call
    print(f"{stat.name}: {stat.ttot:.3f}s ({stat.ncall} calls)")

# Thread statistics (for task tracking)
thread_stats = yappi.get_thread_stats()
```

**Filtering Coroutines**:
```python
def is_coroutine(stat):
    # Yappi marks coroutines in function name
    # Example: "<coroutine 'fetch_data'>"
    return "coroutine" in str(stat.name).lower()

coroutines = [s for s in func_stats if is_coroutine(s)]
sync_funcs = [s for s in func_stats if not is_coroutine(s)]
```

**Detecting Blocking**:
```python
def find_blocking_calls(func_stats, threshold=0.1):
    blocking = []
    for stat in func_stats:
        # Skip async functions
        if is_coroutine(stat):
            continue

        # Check average call time
        if stat.tavg >= threshold:
            blocking.append({
                "function": stat.name,
                "file": stat.module,
                "line": stat.lineno,
                "duration": stat.tavg,
                "calls": stat.ncall,
            })

    return sorted(blocking, key=lambda x: x["duration"], reverse=True)
```

### Event Loop Lag Measurement

**Concept**: Measure scheduling delay

**Implementation**:
```python
import asyncio
import time

async def measure_lag():
    samples = []

    for _ in range(10):
        expected_delay = 0.010  # 10ms

        start = time.perf_counter()
        await asyncio.sleep(expected_delay)
        actual_delay = time.perf_counter() - start

        lag = actual_delay - expected_delay
        samples.append(max(0, lag))  # Lag can't be negative

        # Small delay between measurements
        await asyncio.sleep(0.001)

    return {
        "min": min(samples),
        "avg": sum(samples) / len(samples),
        "max": max(samples),
        "p95": sorted(samples)[int(len(samples) * 0.95)],
    }
```

**Interpretation**:
- `lag < 1ms`: Event loop healthy
- `1ms ≤ lag < 10ms`: Minor contention
- `10ms ≤ lag < 100ms`: Significant blocking
- `lag ≥ 100ms`: Critical blocking

**Integration**:
- Run lag measurement periodically during request
- Store samples, calculate stats at end
- Report max lag as primary metric

### Task Hierarchy Construction

**Goal**: Build parent → children tree

**Data Structure**:
```python
@dataclass
class TaskInfo:
    task_id: int              # id(task)
    name: str                 # task.get_name()
    coro_name: str            # task.get_coro().__qualname__
    parent_id: int | None     # Parent task ID
    created_at: float         # time.time()
    completed_at: float | None
    cancelled: bool
    exception: Exception | None
    children: list[int]       # Child task IDs
```

**Instrumentation**:
```python
# Store original create_task
_original_create_task = asyncio.create_task

def _instrumented_create_task(coro, *, name=None, context=None):
    # Create task normally
    task = _original_create_task(coro, name=name)

    # Capture parent task
    try:
        current = asyncio.current_task()
        parent_id = id(current) if current else None
    except RuntimeError:
        parent_id = None

    # Record task info
    task_tracker.record_task(
        task_id=id(task),
        name=task.get_name(),
        parent_id=parent_id,
        created_at=time.time(),
    )

    # Add completion callback
    task.add_done_callback(lambda t: task_tracker.mark_complete(id(t)))

    return task

# Monkey-patch
asyncio.create_task = _instrumented_create_task
```

**Hierarchy Reconstruction**:
```python
def build_hierarchy(tasks: dict[int, TaskInfo]) -> list[dict]:
    # Find root tasks (no parent)
    roots = [t for t in tasks.values() if t.parent_id is None]

    def build_node(info: TaskInfo) -> dict:
        return {
            "task_id": str(info.task_id),
            "name": info.name,
            "duration": info.completed_at - info.created_at if info.completed_at else 0,
            "children": [
                build_node(tasks[child_id])
                for child_id in info.children
                if child_id in tasks
            ],
        }

    return [build_node(root) for root in roots]
```

---

## Design Decisions

### Decision 1: Backend Architecture

**Options Considered**:
1. Single backend (yappi only)
2. Multi-backend with manual selection
3. Multi-backend with auto-selection (chosen)

**Rationale**:
- Follows existing pattern from ProfilingPanel and MemoryPanel
- Provides graceful degradation (yappi → monitoring → eventloop)
- Allows future backend additions without breaking changes
- Gives users flexibility to choose based on needs

**Trade-offs**:
- More complex implementation
- More code to test
- Better user experience and compatibility

### Decision 2: Task Tracking Method

**Options Considered**:
1. Monkey-patch `asyncio.create_task()` (chosen)
2. Use sys.monitoring callbacks
3. Parse asyncio debug output

**Rationale**:
- Monkey-patching captures all task creation
- Works on all Python versions (3.10+)
- Simple to implement and restore
- sys.monitoring only available on 3.12+

**Trade-offs**:
- Intrusive (modifies stdlib)
- Potential conflicts with other patches
- Most reliable and compatible solution

### Decision 3: Statistics Schema

**Options Considered**:
1. Backend-specific schemas (flexible but inconsistent)
2. Minimal common schema (consistent but limited)
3. Rich common schema with optional fields (chosen)

**Rationale**:
- Template needs consistent structure
- Allows backends to provide best-effort data
- Missing data → empty lists/zero values
- Follows pattern from existing panels

**Schema**:
```python
{
    # Required fields (all backends)
    "backend": str,
    "profiling_overhead": float,

    # Best-effort fields (populate if possible)
    "tasks_created": int,
    "tasks_completed": int,
    "event_loop_lag": dict,  # min/avg/max/p95
    "blocking_calls": list,
    "task_hierarchy": list,
    "await_points": list,
    "top_async_functions": list,
}
```

### Decision 4: Configuration Approach

**Options Considered**:
1. Separate AsyncProfilingConfig class
2. Inline in DebugToolbarConfig (chosen)
3. Environment variables

**Rationale**:
- Follows pattern from memory_backend, profiler_backend
- Single config object easier for users
- Type checking via Literal types
- Clear naming with `async_profiler_` prefix

**Config Options**:
```python
async_profiler_backend: Literal["yappi", "monitoring", "eventloop", "auto"] = "auto"
async_profiler_track_tasks: bool = True
async_profiler_detect_blocking: bool = True
async_profiler_blocking_threshold: float = 0.1
async_profiler_max_tasks: int = 100
```

### Decision 5: UI Approach

**Options Considered**:
1. JSON dump (minimal)
2. Tables only (simple)
3. Tables + timeline visualization (chosen)

**Rationale**:
- Timeline shows concurrent execution (unique value)
- Tables for detailed analysis
- Follows pattern from ProfilingPanel (flame graph)
- Differentiates from standalone tools

**Sections**:
1. Summary metrics (tasks, lag, overhead)
2. Blocking calls table (sortable)
3. Task hierarchy tree (collapsible)
4. Timeline visualization (Gantt chart)
5. Await analysis table

---

## Implementation Strategy

### Phase 1: Foundation (Week 1)

**Goal**: Working panel with basic functionality

**Tasks**:
1. Create directory structure
2. Define AsyncProfilerBackend ABC
3. Implement EventLoopMonitorBackend (simplest)
4. Create AsyncProfilingPanel skeleton
5. Add config options to DebugToolbarConfig
6. Write unit tests for ABC and EventLoop backend
7. Document backend interface

**Deliverable**: Panel works with eventloop backend, tests pass

### Phase 2: Yappi Integration (Week 2)

**Goal**: Full-featured profiling

**Tasks**:
1. Implement YappiBackend
2. Function profiling and filtering
3. Blocking call detection
4. Top async functions extraction
5. Write unit tests for Yappi backend
6. Add yappi to optional dependencies
7. Document configuration and usage

**Deliverable**: Yappi backend provides rich profiling data

### Phase 3: Advanced Features (Week 3)

**Goal**: Task tracking and hierarchy

**Tasks**:
1. Implement TaskTracker utility
2. Integrate with YappiBackend
3. Task hierarchy construction
4. Await point analysis
5. Implement AsyncMonitorBackend (Python 3.12+)
6. Write integration tests
7. Document advanced features

**Deliverable**: Complete async profiling capabilities

### Phase 4: UI & Polish (Week 4, first half)

**Goal**: Production-ready feature

**Tasks**:
1. Create template
2. Implement timeline visualization (JavaScript)
3. Navigation subtitle
4. Server-Timing integration
5. Write user guide
6. Create example applications
7. Final testing and polish

**Deliverable**: Ready for release

---

## Open Questions

### Resolved

1. **Q**: Should we use yappi or sys.monitoring as primary backend?
   **A**: Yappi for 3.10-3.11, both for 3.12+, auto-select with fallback

2. **Q**: How to track task hierarchy without global state?
   **A**: Monkey-patch `asyncio.create_task()`, restore in `stop()`

3. **Q**: What's acceptable profiling overhead?
   **A**: < 5% for yappi, < 1% for eventloop, < 0.001s when disabled

4. **Q**: How to handle concurrent requests with yappi global state?
   **A**: Call `yappi.clear_stats()` before each `start()`

### Pending Implementation

1. **Q**: Can yappi provide await point analysis?
   **A**: TBD - May need custom instrumentation or settle for task-level only

2. **Q**: How to integrate with existing ProfilingPanel?
   **A**: TBD - Separate panels or combined? Probably separate for clarity

3. **Q**: Should we persist profiling data across requests?
   **A**: TBD - Storage pattern exists, but may not be needed for v1

---

## Success Criteria

### Functional
- [ ] All acceptance criteria pass
- [ ] Works on Python 3.10, 3.11, 3.12, 3.13
- [ ] All backends functional
- [ ] 90%+ test coverage

### Performance
- [ ] < 5% overhead (yappi)
- [ ] < 1% overhead (eventloop)
- [ ] < 0.001s overhead when disabled

### Usability
- [ ] Zero-config works out of box
- [ ] Clear error messages
- [ ] Intuitive UI
- [ ] Complete documentation

### Quality
- [ ] All lints pass
- [ ] All type checks pass
- [ ] No anti-patterns
- [ ] Pattern compliance

---

## Conclusion

This research establishes a solid foundation for implementing the Async Profiling Panel. The design:

1. **Follows established patterns** from ProfilingPanel and MemoryPanel
2. **Leverages proven tools** (yappi) with graceful fallbacks
3. **Addresses unique async challenges** (context switching, concurrency, blocking)
4. **Provides unique value** not available in other debug toolbars
5. **Maintains high quality** (90%+ coverage, type safety, docs)

The implementation is feasible within 3-4 weeks with the phased approach, and the risk mitigation strategies address the main concerns.

**Recommendation**: Proceed with implementation following the 4-phase plan.
