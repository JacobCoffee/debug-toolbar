# ADR-003: Storage and Context Management

## Status

Accepted

## Date

2025-11-26

## Context

The debug toolbar needs to:

1. Store panel data during request processing (request-scoped)
2. Persist toolbar data for historical viewing (application-scoped)
3. Support concurrent requests without data leakage
4. Bound memory usage to prevent leaks

### Requirements

- Thread-safe storage for concurrent requests
- Async-compatible context propagation
- LRU eviction for bounded memory
- Fast O(1) access patterns
- No external dependencies (in-memory only)

### Options Considered

#### Request Context Options

**Option A: Thread-local storage**
```python
import threading
_local = threading.local()
```
- Pros: Simple, well-understood
- Cons: Doesn't work with async (coroutines share threads)

**Option B: Context variables (contextvars)**
```python
from contextvars import ContextVar
_ctx: ContextVar[dict] = ContextVar("toolbar_ctx")
```
- Pros: Works with async, copy-on-write semantics
- Cons: Slightly more complex API

**Option C: Request object attachment**
```python
request.state.debug_toolbar = {...}
```
- Pros: Framework-native pattern
- Cons: Framework-specific, needs adapter per framework

#### Storage Options

**Option A: Simple dict with manual cleanup**
```python
_storage: dict[str, dict] = {}
```
- Pros: Simple
- Cons: Unbounded growth, manual eviction needed

**Option B: LRU cache**
```python
from functools import lru_cache
# Or custom OrderedDict-based LRU
```
- Pros: Bounded, automatic eviction
- Cons: Thread safety concerns with OrderedDict

**Option C: External cache (Redis)**
```python
import redis
```
- Pros: Distributed, persistent
- Cons: External dependency, overkill for debug tool

## Decision

### Request Context: Context Variables (Option B)

We will use Python's `contextvars` module for request-scoped data:

```python
# async_debug_toolbar/context.py
from contextvars import ContextVar
from typing import TypedDict

class RequestContext(TypedDict):
    request_id: str
    scope: dict
    panels_data: dict[str, Any]
    start_time: float | None
    end_time: float | None

_request_context: ContextVar[RequestContext | None] = ContextVar(
    "debug_toolbar_context",
    default=None,
)

def get_request_context() -> RequestContext | None:
    return _request_context.get()

def set_request_context(ctx: RequestContext) -> None:
    _request_context.set(ctx)
```

**Rationale:**
- Native async support via copy-on-write semantics
- Each coroutine gets isolated context
- No risk of data leakage between concurrent requests
- Standard library, no dependencies

### Application Storage: Thread-safe LRU OrderedDict (Option B)

We will implement a custom thread-safe LRU storage:

```python
# async_debug_toolbar/storage.py
from collections import OrderedDict
import threading

class ToolbarStorage:
    def __init__(self, max_size: int = 50):
        self._max_size = max_size
        self._data: OrderedDict[str, ToolbarRecord] = OrderedDict()
        self._lock = threading.RLock()

    def store(self, request_id: str, data: dict) -> None:
        with self._lock:
            if request_id in self._data:
                self._data.move_to_end(request_id)
            self._data[request_id] = ToolbarRecord(...)

            while len(self._data) > self._max_size:
                self._data.popitem(last=False)  # Evict oldest

    def get(self, request_id: str) -> ToolbarRecord | None:
        with self._lock:
            record = self._data.get(request_id)
            if record:
                self._data.move_to_end(request_id)  # LRU update
            return record
```

**Rationale:**
- OrderedDict provides O(1) operations with ordering
- RLock ensures thread safety for concurrent access
- LRU eviction bounds memory usage
- No external dependencies

## Data Flow

```
Request Start
    │
    ▼
┌─────────────────────────────────────────┐
│ set_request_context({                   │
│     request_id: "abc-123",              │
│     scope: {...},                       │
│     panels_data: {},                    │
│     start_time: time.perf_counter(),    │
│ })                                      │
└─────────────────────────────────────────┘
    │
    ▼
Panel.process_request()
    │
    ▼
[Application Processing]
    │
    ▼
Panel.process_response()
    │
    ├─► panel.record_stats({...})
    │       │
    │       ▼
    │   ctx["panels_data"]["timer"] = stats
    │
    ▼
┌─────────────────────────────────────────┐
│ storage.store(                          │
│     request_id="abc-123",               │
│     data=ctx["panels_data"]             │
│ )                                       │
│                                         │
│ [LRU eviction if needed]                │
└─────────────────────────────────────────┘
    │
    ▼
clear_request_context()
```

## Consequences

### Positive

1. **Async Safety**: Contextvars work correctly with asyncio
2. **Thread Safety**: Storage protected by RLock
3. **Bounded Memory**: LRU ensures max N requests stored
4. **Zero Dependencies**: All stdlib components
5. **Fast Access**: O(1) for all operations

### Negative

1. **In-Memory Only**: Lost on restart (acceptable for debug tool)
2. **Per-Process**: Not shared across workers (acceptable)
3. **Lock Contention**: Possible under extreme load (mitigated by fast operations)

### Memory Analysis

```
Per-request context: ~5 KB average
  - request_id: 36 bytes (UUID)
  - scope reference: 8 bytes
  - panels_data: ~5 KB (varies by panels)

Storage with 50 requests: ~250 KB
  - Plus ToolbarRecord overhead: ~50 KB
  - Total: ~300 KB

Maximum memory usage: ~500 KB (with overhead)
```

## Context Manager API

For clean lifecycle management:

```python
class RequestContextManager:
    def __init__(self, ctx: RequestContext):
        self._ctx = ctx
        self._token = None

    async def __aenter__(self) -> RequestContext:
        self._token = _request_context.set(self._ctx)
        return self._ctx

    async def __aexit__(self, *args) -> None:
        if self._token:
            _request_context.reset(self._token)
```

Usage in middleware:

```python
async def __call__(self, scope, receive, send):
    ctx = RequestContext(
        request_id=str(uuid.uuid4()),
        scope=scope,
        panels_data={},
        start_time=None,
        end_time=None,
    )

    async with RequestContextManager(ctx):
        await self.app(scope, receive, send)
```

## References

- [PEP 567 - Context Variables](https://peps.python.org/pep-0567/)
- [Python contextvars documentation](https://docs.python.org/3/library/contextvars.html)
- [OrderedDict implementation](https://docs.python.org/3/library/collections.html#collections.OrderedDict)
