# Async Profiling Panel - Task Breakdown

## Complexity: COMPLEX (10+ checkpoints)

This breakdown follows the complexity level with detailed, dependency-aware tasks.

---

## Phase 1: Foundation (Tasks 1-3)

### Task 1: Create Directory Structure and Base Classes

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/__init__.py`
- `src/debug_toolbar/core/panels/async_profiler/base.py`
- `src/debug_toolbar/core/panels/async_profiler/models.py`

**Details:**
1. Create `async_profiler/` directory under `core/panels/`
2. Implement `AsyncProfilerBackend` ABC with abstract methods:
   - `start(loop: AbstractEventLoop) -> None`
   - `stop() -> None`
   - `get_stats() -> dict[str, Any]`
   - `is_available() -> bool` (classmethod)
3. Create data models:
   - `TaskEvent` dataclass
   - `BlockingCall` dataclass
   - `LagSample` dataclass
4. Create `__init__.py` with placeholder export

**Dependencies:** None

---

### Task 2: Implement TaskFactoryBackend

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/taskfactory.py`

**Details:**
1. Implement `TaskFactoryBackend(AsyncProfilerBackend)`
2. `start()`: Save original task factory, install profiling factory
3. `_profiling_task_factory()`: Create task, record TaskEvent, add done callback
4. `stop()`: Restore original task factory
5. `get_stats()`: Return collected task events
6. Add `_get_stack_frames()` utility function (from EventsPanel pattern)

**Dependencies:** Task 1

---

### Task 3: Implement Basic AsyncProfilerPanel

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/panel.py`

**Details:**
1. Create `AsyncProfilerPanel(Panel)` class
2. Implement class variables: `panel_id`, `title`, `template`, etc.
3. Implement `__init__()` with backend selection
4. Implement `process_request()`: Start backend
5. Implement `process_response()`: Stop backend
6. Implement `generate_stats()`: Return basic task stats
7. Implement `get_nav_subtitle()`: Show task count

**Dependencies:** Task 2

---

## Phase 2: Detection Features (Tasks 4-6)

### Task 4: Implement BlockingCallDetector

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/detector.py`

**Details:**
1. Create `BlockingCallDetector` class
2. `install(loop)`: Enable debug mode, set slow_callback_duration
3. Capture slow callback events via exception handler or logging
4. `uninstall()`: Restore original settings
5. `get_stats()`: Return blocking call records with stack traces

**Dependencies:** Task 1

---

### Task 5: Implement EventLoopLagMonitor

**Files to modify:**
- `src/debug_toolbar/core/panels/async_profiler/detector.py`

**Details:**
1. Create `EventLoopLagMonitor` class
2. `start(loop)`: Schedule periodic lag checks
3. `_check_lag()`: Compare expected vs actual callback time
4. Record `LagSample` when lag exceeds threshold
5. `stop()`: Stop monitoring
6. `get_stats()`: Return samples and max_lag_ms

**Dependencies:** Task 1

---

### Task 6: Integrate Detection into Panel

**Files to modify:**
- `src/debug_toolbar/core/panels/async_profiler/panel.py`

**Details:**
1. Add `_blocking_detector` and `_lag_monitor` to panel
2. Update `process_request()`: Install detectors
3. Update `process_response()`: Uninstall detectors
4. Update `generate_stats()`: Include detection stats
5. Update `get_nav_subtitle()`: Show warning badge if blocking detected

**Dependencies:** Tasks 4, 5

---

## Phase 3: Configuration (Tasks 7-8)

### Task 7: Add Configuration Options

**Files to modify:**
- `src/debug_toolbar/core/config.py`

**Details:**
1. Add async profiler configuration options:
   - `async_profiler_backend: Literal["taskfactory", "yappi", "auto"]`
   - `async_blocking_threshold_ms: float`
   - `async_enable_blocking_detection: bool`
   - `async_enable_event_loop_monitoring: bool`
   - `async_event_loop_lag_threshold_ms: float`
   - `async_capture_task_stacks: bool`
   - `async_max_stack_depth: int`
2. Add defaults for all options

**Dependencies:** Task 3

---

### Task 8: Wire Configuration to Panel

**Files to modify:**
- `src/debug_toolbar/core/panels/async_profiler/panel.py`
- `src/debug_toolbar/core/panels/async_profiler/detector.py`

**Details:**
1. Add `_get_config()` helper to panel
2. Use config values in backend selection
3. Use config values for detector thresholds
4. Use config values for stack capture settings
5. Add conditional feature enabling based on config

**Dependencies:** Task 7

---

## Phase 4: Visualization (Tasks 9-11)

### Task 9: Implement Timeline Generation

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/timeline.py`

**Details:**
1. Create `generate_timeline()` function
2. Convert task events to timeline format
3. Calculate relative positions and durations
4. Include blocking call periods
5. Handle overlapping tasks
6. Return timeline-ready data structure

**Dependencies:** Task 3

---

### Task 10: Create Panel Template

**Files to create:**
- `src/debug_toolbar/templates/panels/async_profiler.html`

**Details:**
1. Create HTML structure for panel content
2. Add summary section (total tasks, blocking calls, max lag)
3. Add task list with expandable details
4. Add blocking calls section with stack traces
5. Add timeline visualization (CSS-based Gantt chart)
6. Add appropriate styling consistent with other panels

**Dependencies:** Task 9

---

### Task 11: Export Panel from Package

**Files to modify:**
- `src/debug_toolbar/core/panels/async_profiler/__init__.py`
- `src/debug_toolbar/core/panels/__init__.py`
- `src/debug_toolbar/__init__.py`

**Details:**
1. Export `AsyncProfilerPanel` from async_profiler package
2. Add to panels `__init__.py` exports
3. Add to main package `__init__.py`
4. Ensure panel is discoverable

**Dependencies:** Task 10

---

## Phase 5: Testing (Tasks 12-14)

### Task 12: Unit Tests - Backends

**Files to create:**
- `tests/unit/test_async_profiler_panel.py`

**Details:**
1. Test `TaskFactoryBackend.is_available()`
2. Test task creation tracking
3. Test task completion tracking
4. Test factory restoration after stop
5. Test edge cases (no tasks, cancelled tasks)

**Dependencies:** Tasks 1-3

---

### Task 13: Unit Tests - Detection

**Files to modify:**
- `tests/unit/test_async_profiler_panel.py`

**Details:**
1. Test `BlockingCallDetector` initialization
2. Test blocking call detection with artificial delay
3. Test no false positives for fast code
4. Test `EventLoopLagMonitor` sampling
5. Test threshold configuration

**Dependencies:** Tasks 4-6

---

### Task 14: Unit Tests - Panel

**Files to modify:**
- `tests/unit/test_async_profiler_panel.py`

**Details:**
1. Test panel metadata (panel_id, title, etc.)
2. Test full panel lifecycle
3. Test `generate_stats()` structure
4. Test `get_nav_subtitle()` with/without warnings
5. Test configuration integration
6. Test backend selection and fallback

**Dependencies:** Tasks 7-11

---

## Phase 6: Optional Backend (Tasks 15-16)

### Task 15: Implement YappiBackend

**Files to create:**
- `src/debug_toolbar/core/panels/async_profiler/yappi_backend.py`

**Details:**
1. Create `YappiBackend(AsyncProfilerBackend)`
2. `is_available()`: Check yappi import
3. `start()`: Configure and start yappi with WALL clock
4. `stop()`: Stop yappi profiling
5. `get_stats()`: Convert yappi stats to our format
6. Include coroutine-specific timing data

**Dependencies:** Task 2

---

### Task 16: Add Yappi Tests

**Files to modify:**
- `tests/unit/test_async_profiler_panel.py`

**Details:**
1. Test `YappiBackend.is_available()` with mock
2. Test yappi integration when available
3. Test fallback when yappi unavailable
4. Skip tests when yappi not installed

**Dependencies:** Task 15

---

## Phase 7: Documentation (Task 17)

### Task 17: Update Documentation

**Files to modify:**
- `docs/` (if exists)
- `README.md` (panel list)

**Details:**
1. Add Async Profiler to panel documentation
2. Document configuration options
3. Add usage examples
4. Document yappi optional dependency
5. Add troubleshooting section

**Dependencies:** All previous tasks

---

## Task Dependency Graph

```
Task 1 (Base)
    ├── Task 2 (TaskFactory)
    │       └── Task 3 (Panel)
    │               ├── Task 7 (Config)
    │               │       └── Task 8 (Wire Config)
    │               ├── Task 9 (Timeline)
    │               │       └── Task 10 (Template)
    │               │               └── Task 11 (Export)
    │               └── Task 12 (Tests - Backend)
    │
    ├── Task 4 (Blocking)
    │       └── Task 6 (Integrate)
    │               └── Task 13 (Tests - Detection)
    │
    ├── Task 5 (Lag Monitor)
    │       └── Task 6 (Integrate)
    │
    └── Task 15 (Yappi)
            └── Task 16 (Yappi Tests)

Task 14 (Tests - Panel) depends on: 7, 8, 9, 10, 11
Task 17 (Docs) depends on: All
```

---

## Estimated Implementation Order

1. **Sprint 1**: Tasks 1, 2, 3 (Foundation)
2. **Sprint 2**: Tasks 4, 5, 6 (Detection)
3. **Sprint 3**: Tasks 7, 8 (Configuration)
4. **Sprint 4**: Tasks 9, 10, 11 (Visualization)
5. **Sprint 5**: Tasks 12, 13, 14 (Testing)
6. **Sprint 6**: Tasks 15, 16, 17 (Optional + Docs)

---

## Quality Gates

Before marking implementation complete:

- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Coverage >90% for new modules
- [ ] No anti-patterns (per CLAUDE.md)
- [ ] Template renders correctly
- [ ] Config options documented
