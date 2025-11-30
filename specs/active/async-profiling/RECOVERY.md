# Async Profiling Panel - Recovery Guide

## Quick Resume

```bash
# Resume implementation
/implement async-profiling
```

---

## Intelligence Context

### Feature Overview
- **Name**: Async Profiling Panel
- **Phase**: 11.3 - Advanced Profiling
- **Complexity**: Complex (10+ checkpoints)
- **Slug**: async-profiling

### Key Patterns to Follow
1. **Multi-backend ABC** (like MemoryPanel): `base.py` with abstract class
2. **Panel lifecycle**: `process_request()` → `process_response()` → `generate_stats()`
3. **Config-driven**: `_get_config()` helper with defaults
4. **Handler introspection**: `inspect` module patterns from EventsPanel

### Reference Files
- `src/debug_toolbar/core/panels/memory/` - Directory structure pattern
- `src/debug_toolbar/core/panels/profiling.py` - Profiler lifecycle
- `src/debug_toolbar/litestar/panels/events.py` - Stack capture

---

## Current Progress

### PRD Phase: COMPLETE ✅

| Checkpoint | Status | Notes |
|------------|--------|-------|
| 0. Bootstrap | ✅ | Patterns loaded |
| 1. Pattern Recognition | ✅ | 4 similar implementations analyzed |
| 2. Workspace Creation | ✅ | `specs/active/async-profiling/` |
| 3. Intelligent Analysis | ✅ | Web research completed |
| 4. Research | ✅ | 2000+ words |
| 5. Write PRD | ✅ | `prd.md` created |
| 6. Task Breakdown | ✅ | 17 tasks defined |
| 7. Recovery Guide | ✅ | This file |
| 8. Git Verification | Pending | Check no src/ changes |

### Implementation Phase: NOT STARTED

| Task | Status | Files |
|------|--------|-------|
| 1. Base Classes | Pending | `base.py`, `models.py` |
| 2. TaskFactoryBackend | Pending | `taskfactory.py` |
| 3. AsyncProfilerPanel | Pending | `panel.py` |
| 4. BlockingCallDetector | Pending | `detector.py` |
| 5. EventLoopLagMonitor | Pending | `detector.py` |
| 6. Integrate Detection | Pending | `panel.py` |
| 7. Add Config Options | Pending | `config.py` |
| 8. Wire Configuration | Pending | Multiple |
| 9. Timeline Generation | Pending | `timeline.py` |
| 10. Panel Template | Pending | `async_profiler.html` |
| 11. Export Panel | Pending | `__init__.py` files |
| 12. Backend Tests | Pending | `test_async_profiler_panel.py` |
| 13. Detection Tests | Pending | `test_async_profiler_panel.py` |
| 14. Panel Tests | Pending | `test_async_profiler_panel.py` |
| 15. YappiBackend | Pending | `yappi_backend.py` |
| 16. Yappi Tests | Pending | `test_async_profiler_panel.py` |
| 17. Documentation | Pending | Various |

---

## How to Continue

### From PRD Phase (Current)
1. Complete Checkpoint 8: Verify no src/ changes
2. Run `/implement async-profiling`

### From Implementation Phase
1. Read `specs/active/async-profiling/tasks.md`
2. Check which task was last completed
3. Continue with next task in sequence

### From Testing Phase
1. Run `make test` to see failures
2. Fix failing tests
3. Check coverage with `make test-cov`

---

## Key Technical Decisions

### Backend Selection
- **Default**: TaskFactoryBackend (stdlib, no deps)
- **Optional**: YappiBackend (requires `yappi` package)
- **Selection**: Config-driven with auto fallback

### Blocking Detection Approach
- Uses asyncio debug mode
- Sets `loop.slow_callback_duration`
- Captures via exception handler

### Event Loop Monitoring
- Scheduled callbacks at 10ms intervals
- Measures actual vs expected delay
- Reports max lag and samples

### Timeline Visualization
- Pure HTML/CSS Gantt chart
- No external JS libraries
- Color-coded task states

---

## Workspace Files

```
specs/active/async-profiling/
├── prd.md              # Full requirements document
├── tasks.md            # 17-task breakdown
├── RECOVERY.md         # This file
├── research/
│   └── plan.md         # Research notes
├── tmp/
│   └── new-patterns.md # Patterns to extract
└── patterns/           # (empty - for extracted patterns)
```

---

## Quality Checklist

Before marking any task complete:
- [ ] Code follows patterns from reference files
- [ ] No `Optional[T]` (use `T | None`)
- [ ] Has `from __future__ import annotations`
- [ ] Tests use class-based organization
- [ ] Context vars cleaned up in tests
- [ ] No unnecessary comments

Before marking implementation complete:
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] Coverage >90%
- [ ] Template renders correctly

---

## Troubleshooting

### Event Loop Access Issues
```python
# Use asyncio.get_running_loop() inside async context
loop = asyncio.get_running_loop()

# NOT asyncio.get_event_loop() which is deprecated
```

### Task Factory Restoration
```python
# Always restore in finally or try/except
def stop(self) -> None:
    if self._loop and self._original_factory is not None:
        self._loop.set_task_factory(self._original_factory)
```

### Testing Async Code
```python
@pytest.mark.asyncio
async def test_async_function(self) -> None:
    # Always use asyncio fixtures
    loop = asyncio.get_running_loop()
    ...
```

---

## Contact

For questions about this implementation:
1. Check `CLAUDE.md` for project conventions
2. Check `specs/guides/patterns/` for patterns
3. Check similar panels for reference

---

*Last Updated: 2025-11-29*
