# Recovery Guide: WebSocket Panel Implementation

**Feature**: WebSocket Panel
**Workspace**: `specs/active/websocket-panel/`
**Status**: PRD Complete, Ready for Implementation
**Last Updated**: 2025-11-29

---

## Quick Start

To resume work on this feature:

1. **Read PRD**: `specs/active/websocket-panel/prd.md`
2. **Review Research**: `specs/active/websocket-panel/research/plan.md`
3. **Check Progress**: Review checklist in PRD Section "Implementation Checklist"
4. **Start Implementation**: Begin with Phase 1 (Data Models)

---

## Workspace Structure

```
specs/active/websocket-panel/
├── prd.md                      # Full PRD (8,942 words)
├── research/
│   └── plan.md                 # Research notes (2,247 words)
├── tmp/
│   └── new-patterns.md         # Pattern discoveries during implementation
└── RECOVERY.md                 # This file
```

---

## Implementation Phases

### Phase 1: Data Models (Checkpoint 1)
**Files**: `src/debug_toolbar/core/panels/websocket.py` (partial)
**Tasks**:
- Create `WebSocketMessage` dataclass
- Create `WebSocketConnection` dataclass
- Add helper methods
- Unit tests for data models

### Phase 2: WebSocketPanel Core (Checkpoints 2-3)
**Files**: `src/debug_toolbar/core/panels/websocket.py` (complete)
**Tasks**:
- Create `WebSocketPanel` class
- Implement connection tracking
- Implement statistics generation
- Unit tests for panel logic

### Phase 3: Middleware Integration (Checkpoints 4-7)
**Files**: `src/debug_toolbar/litestar/middleware.py` (modifications)
**Tasks**:
- Add WebSocket scope detection
- Create send/receive wrappers
- Implement message logging
- Integration tests

### Phase 4: Configuration (Checkpoint 8)
**Files**: `src/debug_toolbar/core/config.py` (modifications)
**Tasks**:
- Add 7 WebSocket config fields
- Update docstrings

### Phase 5: Storage Integration (Checkpoint 9)
**Tasks**:
- Verify storage strategy
- Optional: TTL cleanup background task

### Phase 6: UI Template (Checkpoint 10)
**Files**: `templates/panels/websocket.html` (new)
**Tasks**:
- Create HTML template
- Add CSS styling
- Template filters

### Phase 7: Testing (Checkpoints 11-12)
**Files**: Multiple test files
**Tasks**:
- Complete all unit tests
- Complete all integration tests
- Performance benchmarks

### Phase 8: Quality Assurance
**Tasks**:
- Lint, type-check, test coverage
- Code review
- Performance validation

---

## Key Files to Create

1. `src/debug_toolbar/core/panels/websocket.py` (~500 lines)
2. `templates/panels/websocket.html` (~150 lines)
3. `tests/core/panels/test_websocket.py` (~500 lines)
4. `tests/litestar/test_websocket_integration.py` (~400 lines)
5. `tests/performance/test_websocket_performance.py` (~100 lines)

---

## Key Files to Modify

1. `src/debug_toolbar/core/config.py` (+7 lines at line 57)
2. `src/debug_toolbar/litestar/middleware.py` (+200 lines, 3 new methods)
3. `src/debug_toolbar/core/panels/__init__.py` (+1 line export)

---

## Critical Design Decisions

1. **Storage Strategy**: Class-level dict for active connections (not request-scoped)
2. **Thread Safety**: Use `threading.Lock` for connection dict access
3. **Memory Management**: Circular buffer (FIFO) with configurable limits
4. **Error Handling**: Graceful degradation in send/receive wrappers
5. **Performance**: Async-safe, non-blocking tracking

---

## Pattern References

**Similar Panels Studied**:
- LoggingPanel: Handler pattern, lifecycle hooks
- EventsPanel: Metadata collection, runtime recording
- TimerPanel: Instance state tracking
- RequestPanel: Delegate to middleware pattern

**New Patterns**:
- Persistent Connection Pattern
- Hybrid Storage Pattern
- Circular Buffer Pattern
- ASGI Event Wrapper Pattern

---

## Test Coverage Requirements

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: 85%+ coverage
- **Performance**: < 5% overhead
- **Memory**: < 100KB per connection

---

## Configuration Defaults

```python
websocket_tracking_enabled: bool = True
websocket_max_connections: int = 50
websocket_max_messages_per_connection: int = 100
websocket_max_message_size: int = 10240  # 10KB
websocket_binary_preview_size: int = 256
websocket_show_binary_preview: bool = False
websocket_connection_ttl: int = 3600  # 1 hour
```

---

## Acceptance Criteria Summary

1. Detect WebSocket connections
2. Track connection lifecycle (connect → disconnect)
3. Log text messages (sent/received) with truncation
4. Log binary messages (size only, optional hex preview)
5. Circular buffer for messages (max 100 default)
6. Max connection limit (50 default)
7. Statistics generation (counts, bytes, durations)
8. UI template with connections list and message timeline
9. Configuration options
10. No interference with WebSocket operation
11. Performance < 5% overhead
12. Test coverage 90%+

---

## Next Steps

### To Start Implementation

```bash
# 1. Navigate to project root
cd /home/cody/code/litestar/debug-toolbar

# 2. Ensure dev environment is set up
make dev

# 3. Create new branch
git checkout -b feat/websocket-panel

# 4. Create panel file
touch src/debug_toolbar/core/panels/websocket.py

# 5. Start with data models
# (Copy code from PRD Section "Data Models")
```

### To Test As You Go

```bash
# Run tests for specific file
pytest tests/core/panels/test_websocket.py -v

# Run with coverage
pytest tests/core/panels/test_websocket.py --cov=src/debug_toolbar/core/panels/websocket --cov-report=html

# Run integration tests
pytest tests/litestar/test_websocket_integration.py -v

# Run all tests
make test

# Lint
make lint

# Type check
make type-check
```

---

## Common Issues and Solutions

### Issue 1: Import Errors
**Problem**: Circular imports between middleware and panel
**Solution**: Import WebSocketPanel inside `_handle_websocket()` method, not at module level

### Issue 2: Context Variable Leaks
**Problem**: Context not cleaned up after WebSocket closes
**Solution**: Always use `finally` block to clear context

### Issue 3: Thread Safety
**Problem**: Race conditions in connection dict
**Solution**: Always acquire `_connections_lock` before accessing `_active_connections`

### Issue 4: Memory Growth
**Problem**: Message buffers growing unbounded
**Solution**: Enforce `max_messages` in `WebSocketConnection.add_message()`

### Issue 5: Test Flakiness
**Problem**: Async WebSocket tests timing out
**Solution**: Increase timeout, use `pytest-asyncio` markers, ensure proper cleanup

---

## Resources

### Litestar WebSocket Docs
- Handler examples: `research/plan.md` Section "Litestar WebSocket API Research"
- ASGI spec: `prd.md` Appendix A

### Code Patterns
- Panel pattern: `specs/guides/patterns/README.md`
- Middleware pattern: `src/debug_toolbar/litestar/middleware.py` (HTTP handling)
- Testing pattern: `tests/core/panels/test_logging.py`

### External References
- ASGI WebSocket spec: https://asgi.readthedocs.io/en/latest/specs/www.html#websocket
- WebSocket close codes: https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code
- Litestar docs: https://docs.litestar.dev/latest/usage/websockets.html

---

## Questions/Blockers Log

*Document any questions or blockers encountered during implementation here.*

### Q1: [Example] How to test WebSocket error scenarios?
**A1**: Use `pytest.raises()` with custom WebSocket client that triggers errors

---

## Progress Tracking

Use this section to track completion of checkpoints:

- [ ] Checkpoint 1: Data Models
- [ ] Checkpoint 2: WebSocketPanel Core (tracking)
- [ ] Checkpoint 3: WebSocketPanel Core (stats)
- [ ] Checkpoint 4: Middleware - WebSocket detection
- [ ] Checkpoint 5: Middleware - Send wrapper
- [ ] Checkpoint 6: Middleware - Receive wrapper
- [ ] Checkpoint 7: Middleware - Lifecycle management
- [ ] Checkpoint 8: Configuration
- [ ] Checkpoint 9: Storage integration
- [ ] Checkpoint 10: UI Template
- [ ] Checkpoint 11: Unit Tests
- [ ] Checkpoint 12: Integration Tests

---

## Handoff Notes

When handing off to another agent or resuming after break:

1. **What was completed**: List completed phases/checkpoints
2. **Current work**: What file/test you were working on
3. **Next task**: Specific next task from checklist
4. **Open questions**: Any unresolved design decisions
5. **Test status**: Which tests are passing/failing

---

**Last Session**: 2025-11-29 - PRD Creation Phase
**Next Session**: Implementation Phase 1 - Data Models
**Estimated Remaining Time**: 16-20 hours (expert developer)
