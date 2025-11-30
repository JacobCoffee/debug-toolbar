# Spec: PR #1 - Background Tasks Panel (SAQ Integration)

## Metadata
- **PR Number**: 1
- **Priority**: P1
- **Complexity**: Medium
- **Estimated Files**: 4-6
- **Dependencies**: None
- **Implementation Order**: 5

---

## Problem Statement

Modern async Python applications heavily rely on background task processing for operations like email sending, data processing, and scheduled jobs. SAQ (Simple Async Queue) is a popular async-native task queue built on Redis that integrates well with async frameworks like Litestar.

Currently, there's no visibility into background tasks from the debug toolbar. Developers must check Redis directly or rely on logs to understand task behavior during development.

---

## Goals

1. Track tasks enqueued during a request
2. Display task execution status
3. Show timing and retry information
4. Provide clear association between requests and their spawned tasks

---

## Non-Goals

- Celery/RQ support (future enhancement)
- Real-time task monitoring (polling only)
- Task management (cancel, retry from UI)

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ SAQPanel                                        │
├─────────────────────────────────────────────────┤
│ - Wraps SAQ Queue.enqueue()                    │
│ - Captures task metadata at enqueue time        │
│ - Polls for status during generate_stats()      │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ SAQTaskTracker (context-scoped)                 │
├─────────────────────────────────────────────────┤
│ - Stores enqueued task IDs per request          │
│ - Thread/context-safe via ContextVar            │
└─────────────────────────────────────────────────┘
```

### Integration Pattern

Follow the SQLAlchemy panel pattern:
1. Wrap/patch SAQ Queue at toolbar initialization
2. Store task metadata in context var
3. Query task status at stats generation time

### Files to Create

```python
# src/debug_toolbar/extras/saq/__init__.py
from debug_toolbar.extras.saq.panel import SAQPanel

__all__ = ["SAQPanel"]
```

```python
# src/debug_toolbar/extras/saq/panel.py
class SAQPanel(Panel):
    panel_id = "SAQPanel"
    title = "Background Tasks"
    template = "panels/saq.html"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        # Get tracked tasks from context
        # Poll Redis for current status
        # Return formatted stats
```

### Data Model

```python
@dataclass
class TrackedTask:
    task_id: str
    function_name: str
    queue_name: str
    enqueued_at: float
    status: str  # queued, active, complete, failed, aborted
    started_at: float | None
    completed_at: float | None
    retries: int
    error: str | None
```

---

## Acceptance Criteria

- [ ] Track tasks enqueued via SAQ Queue during request
- [ ] Display task list with status badges
- [ ] Show timing breakdown (queue time, execution time)
- [ ] Handle tasks that complete before response
- [ ] Handle tasks still queued at response time
- [ ] Graceful degradation if Redis unavailable
- [ ] No performance impact when panel disabled
- [ ] 90%+ test coverage
- [ ] Integration test with real SAQ queue

---

## Testing Strategy

### Unit Tests
```python
class TestSAQPanel:
    async def test_tracks_enqueued_task(self):
        """Should capture task when enqueued."""

    async def test_status_polling(self):
        """Should poll Redis for task status."""

    async def test_handles_completed_task(self):
        """Should show completed status and timing."""

    async def test_handles_failed_task(self):
        """Should show error message for failed tasks."""

    async def test_graceful_redis_failure(self):
        """Should handle Redis connection errors."""
```

### Integration Tests
```python
class TestSAQIntegration:
    async def test_full_lifecycle(self):
        """Test enqueue → execute → display cycle."""
```

---

## UI Design

```
┌─────────────────────────────────────────────────┐
│ Background Tasks                          3 tasks│
├─────────────────────────────────────────────────┤
│ ✓ send_email         complete    45ms    0 retry│
│ ⏳ process_report     active     --      0 retry│
│ ⏸ cleanup_temp       queued     --      0 retry│
├─────────────────────────────────────────────────┤
│ Queue: default │ Total: 3 │ Complete: 1         │
└─────────────────────────────────────────────────┘
```

---

## Implementation Notes

1. SAQ tasks have UUIDs accessible via `Job.id`
2. Use `Job.info()` to get current status from Redis
3. SAQ supports multiple queues - track queue name
4. Consider `saq.Queue.sweep()` for stale task cleanup

---

## References

- [SAQ Documentation](https://github.com/tobymao/saq)
- Similar: Django Debug Toolbar Celery Panel
- Pattern: `src/debug_toolbar/extras/advanced_alchemy/panel.py`
