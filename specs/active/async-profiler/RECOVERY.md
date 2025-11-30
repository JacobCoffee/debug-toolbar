# Session Recovery Guide: Async Profiler

**Feature**: Async Profiling Panel for debug-toolbar
**Workspace**: `/home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/`
**Status**: PRD Complete, Ready for Implementation
**Last Updated**: 2025-11-29

---

## Quick Context

This feature adds async-aware profiling to the debug-toolbar, providing visibility into:
- Asyncio task creation and lifecycle
- Event loop lag and blocking detection
- Task hierarchy (parent → children)
- Await point analysis

**Why it matters**: No other Python debug toolbar has async profiling. This is a unique differentiator.

---

## Workspace Structure

```
specs/active/async-profiler/
├── prd.md              # Comprehensive PRD (3200+ words)
├── research/
│   └── plan.md         # Research notes and findings (2000+ words)
├── tmp/
│   └── new-patterns.md # Pattern discoveries (create during implementation)
└── RECOVERY.md         # This file
```

---

## What's Been Done

### Research Phase (Complete)
- [x] Analyzed existing panel patterns (ProfilingPanel, MemoryPanel)
- [x] Researched async profiling tools (yappi, sys.monitoring, loopmon)
- [x] Studied testing patterns (90%+ coverage strategy)
- [x] Designed multi-backend architecture
- [x] Identified risks and mitigations

### PRD Phase (Complete)
- [x] 12 detailed acceptance criteria
- [x] Technical approach with code examples
- [x] Backend implementations (yappi, monitoring, eventloop)
- [x] TaskTracker utility design
- [x] Testing strategy (108 tests planned)
- [x] UI/template design
- [x] Implementation phases (4 weeks)

### Key Decisions Made

1. **Multi-backend architecture**: yappi → monitoring → eventloop (auto-select)
2. **Task tracking**: Monkey-patch `asyncio.create_task()`
3. **Statistics schema**: Rich common schema with optional fields
4. **Configuration**: Inline in DebugToolbarConfig with `async_profiler_` prefix
5. **Complexity**: High (12 checkpoints)

---

## Current State

**Phase**: PRD Complete
**Next Step**: Begin Phase 1 implementation (Foundation)

**Files Created**:
- `/home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/prd.md`
- `/home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/research/plan.md`
- `/home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/RECOVERY.md`

**Files to Create** (Implementation):
1. `src/debug_toolbar/core/panels/async_profiling/__init__.py`
2. `src/debug_toolbar/core/panels/async_profiling/panel.py`
3. `src/debug_toolbar/core/panels/async_profiling/base.py`
4. `src/debug_toolbar/core/panels/async_profiling/yappi.py`
5. `src/debug_toolbar/core/panels/async_profiling/monitoring.py`
6. `src/debug_toolbar/core/panels/async_profiling/eventloop.py`
7. `src/debug_toolbar/core/panels/async_profiling/task_tracker.py`
8. `tests/unit/test_async_profiling_panel.py`
9. `tests/unit/async_profiling/test_*.py` (4 backend test files)
10. `tests/integration/test_async_profiling_integration.py`

**Files to Modify**:
1. `src/debug_toolbar/core/config.py` - Add async profiler config
2. `pyproject.toml` - Add yappi optional dependency

---

## How to Resume

### If Continuing Implementation

**Step 1**: Review PRD
```bash
cd /home/cody/code/litestar/debug-toolbar
cat specs/active/async-profiler/prd.md
```

**Step 2**: Create implementation branch
```bash
git checkout -b feat/async-profiler
```

**Step 3**: Start Phase 1 (Foundation)
- Read: "Implementation Phases > Phase 1" in PRD
- Create: Backend ABC and EventLoopBackend
- Test: Basic functionality

**Step 4**: Follow checkpoints
```
Phase 1 (Week 1):
[ ] 1. Backend ABC definition
[ ] 2. EventLoopMonitorBackend
[ ] 3. AsyncProfilingPanel skeleton
[ ] 4. Basic tests

Phase 2 (Week 2):
[ ] 5. YappiBackend implementation
[ ] 6. Blocking detection
[ ] 7. Integration tests

Phase 3 (Week 3):
[ ] 8. TaskTracker utility
[ ] 9. Task hierarchy
[ ] 10. MonitoringBackend (3.12+)

Phase 4 (Week 4):
[ ] 11. Template/UI
[ ] 12. Documentation
```

### If Reviewing for Approval

**What to check**:
1. Does PRD align with project goals?
2. Is complexity assessment accurate (12 checkpoints)?
3. Are acceptance criteria measurable?
4. Is testing strategy adequate (90%+ coverage)?
5. Are risks identified and mitigated?

**Decision needed**:
- [ ] Approve PRD → Proceed to implementation
- [ ] Request changes → Document feedback in `prd.md`
- [ ] Defer → Document reason and timeline

### If Context Switched

**Quick refresh**:
1. Read: "Problem Statement" section in PRD
2. Read: "Acceptance Criteria" (AC1-AC12) in PRD
3. Read: "Technical Approach > Architecture Overview" in PRD
4. Review: `research/plan.md` for background

**Key concepts**:
- **Async profiling challenge**: Traditional profilers treat `await` as function exit
- **Solution**: Yappi (coroutine-aware) with multi-backend fallback
- **Unique value**: No other debug toolbar has this
- **Complexity**: High (asyncio internals, multi-backend, visualization)

---

## Key Files Reference

### PRD (`prd.md`)
- **Lines 1-100**: Metadata, intelligence context, problem statement
- **Lines 100-500**: Acceptance criteria (AC1-AC12)
- **Lines 500-1200**: Technical approach (backends, task tracker, panel)
- **Lines 1200-1400**: Files to create, testing strategy
- **Lines 1400-1600**: Data models, UI design
- **Lines 1600-1800**: Dependencies, phases, risks
- **Lines 1800-end**: Documentation, comparison, examples

### Research Plan (`research/plan.md`)
- **Lines 1-200**: Research methodology (5 phases)
- **Lines 200-400**: Codebase pattern analysis
- **Lines 400-600**: Async profiling research (web sources)
- **Lines 600-800**: Testing pattern analysis
- **Lines 800-1000**: Technical deep dives (yappi, event loop lag)
- **Lines 1000-1200**: Design decisions
- **Lines 1200-end**: Implementation strategy, open questions

---

## Common Questions

### Q: What makes this high complexity?
**A**: Multi-backend architecture + asyncio internals + task hierarchy tracking + visualization. Requires deep async knowledge.

### Q: Why yappi over sys.monitoring?
**A**: Yappi works on 3.10+, sys.monitoring only 3.12+. We use both with auto-selection.

### Q: How does task tracking work?
**A**: Monkey-patch `asyncio.create_task()` to intercept creation, add completion callback, build hierarchy.

### Q: What's the testing strategy?
**A**: 108 tests total: 40 panel, 60 backends, 8 integration. Target 90%+ coverage. Use conditional skips for optional backends.

### Q: How long will implementation take?
**A**: 3-4 weeks with phased approach:
- Week 1: Foundation (eventloop backend)
- Week 2: Yappi integration
- Week 3: Advanced features (task tracking)
- Week 4: UI and polish

### Q: What are the main risks?
**A**:
1. Yappi state isolation (concurrent requests)
2. Event loop instrumentation side effects
3. Performance overhead
Mitigations documented in PRD.

---

## Pattern References

### Panel Pattern
See: `src/debug_toolbar/core/panel.py`
- ClassVar metadata
- Lifecycle hooks
- `generate_stats()` abstract method

### Multi-Backend Pattern
See: `src/debug_toolbar/core/panels/memory/`
- Backend ABC in `base.py`
- Each backend in own file
- `is_available()` classmethod
- Panel selects backend in `__init__`

### Testing Pattern
See: `tests/unit/test_profiling_panel.py`
- Class-based organization
- Fixtures for common objects
- Structure validation
- Edge cases (empty, errors, disabled)

---

## Next Steps (Priority Order)

1. **Immediate**: Review and approve PRD
2. **Phase 1**: Implement backend ABC and EventLoopBackend
3. **Phase 2**: Integrate yappi
4. **Phase 3**: Add task tracking
5. **Phase 4**: Build UI

---

## Contact Info

**Feature Owner**: TBD
**Reviewer**: TBD
**Slack Channel**: TBD
**GitHub Issue**: TBD

---

## Appendix: Command Reference

### View PRD
```bash
cat /home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/prd.md
```

### View Research
```bash
cat /home/cody/code/litestar/debug-toolbar/specs/active/async-profiler/research/plan.md
```

### Start Implementation
```bash
cd /home/cody/code/litestar/debug-toolbar
git checkout -b feat/async-profiler
mkdir -p src/debug_toolbar/core/panels/async_profiling
touch src/debug_toolbar/core/panels/async_profiling/__init__.py
```

### Run Tests
```bash
make test                    # All tests
make test-fast              # Unit tests only
make test-cov               # With coverage
pytest tests/unit/test_async_profiling_panel.py  # Specific test
```

### Check Code Quality
```bash
make lint                   # Run ruff
make type-check            # Run ty
make fmt                   # Format code
```

---

**Remember**: This is a P1 feature with unique value. Take time to implement correctly following patterns. 90%+ test coverage is required.
