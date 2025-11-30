# WebSocket Panel Research Plan

**Feature**: WebSocket Panel for Debug Toolbar
**Complexity**: High (10+ checkpoints)
**Date**: 2025-11-29

---

## Research Objectives

1. Understand existing panel architecture patterns
2. Analyze Litestar WebSocket implementation
3. Design data models for WebSocket tracking
4. Plan middleware integration strategy
5. Define testing approach for async WebSocket connections

---

## Pattern Analysis

### Similar Panel Implementations

#### 1. LoggingPanel (`src/debug_toolbar/core/panels/logging.py`)

**Key Patterns Identified**:
- Uses custom handler (`ToolbarLoggingHandler`) for data capture
- Implements lifecycle hooks: `process_request()` and `process_response()`
- Handler pattern: Attach during `process_request`, detach during `process_response`
- Stores data in handler instance (`__slots__` for memory efficiency)
- Thread-safe data collection through Python's logging system

**Applicable to WebSocket Panel**:
- Similar handler pattern can track WebSocket messages
- Lifecycle hooks for connection setup/teardown
- Memory management considerations for long-lived connections

#### 2. EventsPanel (`src/debug_toolbar/litestar/panels/events.py`)

**Key Patterns Identified**:
- Helper functions for metadata extraction (`_get_handler_info`, `_get_stack_frames`)
- Separate collection function (`collect_events_metadata`) called from middleware
- Recording function (`record_hook_execution`) for runtime events
- ClassVar metadata for panel configuration
- Comprehensive data model with handler introspection

**Applicable to WebSocket Panel**:
- Separate tracking functions for middleware integration
- Runtime event recording pattern
- Stack frame capture for debugging
- Handler/function introspection utilities

#### 3. TimerPanel (`src/debug_toolbar/core/panels/timer.py`)

**Key Patterns Identified**:
- Instance variables in `__slots__` for timing state
- `process_request()` captures start state
- `generate_stats()` calculates deltas
- Provides `generate_server_timing()` for Server-Timing header
- Simple, focused responsibility

**Applicable to WebSocket Panel**:
- State tracking in panel instance
- Start/end timestamp pattern
- Performance metrics for Server-Timing

#### 4. RequestPanel (`src/debug_toolbar/core/panels/request.py`)

**Key Patterns Identified**:
- Pure data extraction from `context.metadata`
- No lifecycle hooks needed
- Simple dictionary unpacking in `generate_stats()`
- Minimal processing, delegates to middleware

**Applicable to WebSocket Panel**:
- Data should be collected in middleware
- Panel reads from context.metadata
- Keep panel logic simple

---

## Middleware Integration Analysis

### Current Middleware Structure (`src/debug_toolbar/litestar/middleware.py`)

**Observations**:
1. **Scope Type Check**: Line 76 checks `scope["type"] != "http"` - currently skips non-HTTP
2. **Request Context Creation**: Line 88 creates `RequestContext` via `toolbar.process_request()`
3. **Send Wrapper**: Lines 103-114 wrap `send` for response interception
4. **Response State Tracking**: `ResponseState` dataclass (lines 32-42) tracks HTTP response state
5. **Metadata Population**: Lines 232-303 populate request/route metadata
6. **Cleanup**: Line 101 ensures `set_request_context(None)` in finally block

**Required Changes for WebSocket Support**:
1. Add WebSocket scope handling: `if scope["type"] == "websocket"`
2. Create WebSocket-specific wrapper for send/receive
3. Track WebSocket message events
4. Store connection metadata in context
5. Handle WebSocket lifecycle differently (persistent connections)

---

## Litestar WebSocket API Research

### Key Findings from Context7

**WebSocket Handler Patterns**:
1. **Direct Socket Access**: `async def handler(websocket: WebSocket)` receives socket
2. **Lifecycle Methods**: `accept()`, `send_text()`, `send_bytes()`, `close()`
3. **Message Reception**: `receive_text()`, `receive_bytes()`, `receive_json()`
4. **Class-Based Listeners**: `WebsocketListener` with `on_connect`, `on_receive`, `on_disconnect`
5. **Streaming**: Async generators for server-to-client streaming

**ASGI WebSocket Events** (per ASGI spec):
- `websocket.connect`: Initial connection request
- `websocket.accept`: Server accepts connection
- `websocket.receive`: Message from client
- `websocket.send`: Message to client
- `websocket.disconnect`: Connection closed
- `websocket.close`: Server closes connection

**Message Types**:
- `type: "websocket.send"` with `text` or `bytes` field
- `type: "websocket.receive"` with `text` or `bytes` field
- Close frames include `code` and `reason`

---

## Data Model Design

### Core Data Structures

```python
@dataclass
class WebSocketMessage:
    """Represents a single WebSocket message."""
    direction: Literal["sent", "received"]
    message_type: Literal["text", "binary", "ping", "pong", "close"]
    content: str | bytes | None
    timestamp: float  # Unix timestamp
    size_bytes: int
    truncated: bool = False  # If content was truncated for storage

@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection session."""
    connection_id: str  # UUID
    path: str
    query_string: str
    headers: dict[str, str]
    connected_at: float
    disconnected_at: float | None = None
    close_code: int | None = None
    close_reason: str | None = None
    messages: list[WebSocketMessage] = field(default_factory=list)
    state: Literal["connecting", "connected", "closing", "closed"] = "connecting"

    # Statistics
    total_sent: int = 0
    total_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
```

### Storage Strategy

**Challenge**: WebSocket connections persist beyond single HTTP requests.

**Options**:
1. **Application-Level Storage**: Class-level dict in WebSocketPanel
   - Pro: Simple, all connections visible
   - Con: Memory leak risk for long-running apps

2. **Request Context Storage**: Store in context.metadata per connection
   - Pro: Integrates with existing storage system
   - Con: Connection spans multiple "requests"

3. **Hybrid Approach** (RECOMMENDED):
   - Active connections in class-level dict
   - Completed connections stored in ToolbarStorage
   - Connection ID links requests to WebSocket sessions
   - Configurable retention (max connections, max age)

---

## Memory Management Strategy

### Challenges

1. **Long-Lived Connections**: WebSockets can stay open for hours/days
2. **Message Volume**: High-frequency trading apps might send 1000s msgs/sec
3. **Binary Data**: Large binary messages (file uploads, images)

### Solutions

1. **Message Buffering**:
   - Circular buffer with configurable max size (default: 100 messages)
   - FIFO eviction when buffer full

2. **Content Truncation**:
   - Text messages: Max 10KB, truncate with "..." indicator
   - Binary messages: Store size only, optional hex preview (first 256 bytes)

3. **Connection Limits**:
   - Max active connections tracked: 50 (configurable)
   - Auto-cleanup connections older than 1 hour if disconnected

4. **Opt-In Tracking**:
   - Configuration flag: `websocket_tracking_enabled`
   - Per-connection opt-out via metadata flag

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/core/panels/test_websocket.py`

```python
class TestWebSocketPanel:
    """Unit tests for WebSocketPanel."""

    async def test_panel_metadata(self):
        """Should have correct panel ID and title."""

    async def test_track_connection_open(self):
        """Should record connection establishment."""

    async def test_track_text_message_sent(self):
        """Should log text message sent to client."""

    async def test_track_text_message_received(self):
        """Should log text message received from client."""

    async def test_track_binary_message(self):
        """Should log binary message with size."""

    async def test_message_truncation(self):
        """Should truncate messages over size limit."""

    async def test_message_buffer_limit(self):
        """Should respect max message count."""

    async def test_track_connection_close(self):
        """Should record close code and reason."""

    async def test_connection_state_transitions(self):
        """Should track state: connecting → connected → closing → closed."""

    async def test_generate_stats(self):
        """Should generate statistics from tracked connections."""

    async def test_multiple_connections(self):
        """Should track multiple concurrent connections."""

    async def test_connection_cleanup(self):
        """Should clean up old disconnected connections."""
```

### Integration Tests

**Test File**: `tests/litestar/test_websocket_integration.py`

```python
class TestWebSocketIntegration:
    """Integration tests with Litestar app."""

    async def test_websocket_handler_tracking(self):
        """Should track messages in real WebSocket handler."""

    async def test_websocket_connect_lifecycle(self):
        """Should track connect → accept → disconnect."""

    async def test_websocket_bidirectional_messages(self):
        """Should track messages in both directions."""

    async def test_websocket_close_codes(self):
        """Should capture close codes (1000, 1001, etc.)."""

    async def test_websocket_with_query_params(self):
        """Should capture query parameters from connection."""

    async def test_websocket_headers(self):
        """Should capture connection headers."""

    async def test_multiple_concurrent_websockets(self):
        """Should handle multiple simultaneous connections."""

    async def test_websocket_error_handling(self):
        """Should gracefully handle WebSocket errors."""
```

### Test Fixtures

```python
@pytest.fixture
def websocket_panel(toolbar):
    """WebSocketPanel instance."""
    from debug_toolbar.core.panels.websocket import WebSocketPanel
    return WebSocketPanel(toolbar)

@pytest.fixture
async def mock_websocket_scope():
    """Mock ASGI WebSocket scope."""
    return {
        "type": "websocket",
        "path": "/ws/test",
        "query_string": b"token=abc123",
        "headers": [(b"host", b"localhost")],
    }
```

---

## UI/UX Design

### Panel Display Structure

```
┌──────────────────────────────────────────────────────┐
│ WebSocket                         2 active, 5 total  │
├──────────────────────────────────────────────────────┤
│ Connection #1: /ws/chat          ● Connected (1m 23s)│
│ ├─ Messages: 45 sent, 67 received (2.3 KB total)    │
│ └─ Query: ?room=general&user=alice                   │
├──────────────────────────────────────────────────────┤
│ Connection #2: /ws/notifications ● Connected (2m 41s)│
│ ├─ Messages: 3 sent, 128 received (15.2 KB total)   │
│ └─ Query: ?user=alice                                │
├──────────────────────────────────────────────────────┤
│ Recent Activity:                                     │
│ ├─ 00:02:41.234 → #2 text (123 bytes)               │
│ ├─ 00:02:39.012 ← #1 {"type": "message", ...}       │
│ ├─ 00:02:38.456 → #1 {"type": "ack"}                │
│ ├─ 00:02:35.789 ← #2 binary (4.2 KB)                │
│ └─ [Load More...]                                    │
└──────────────────────────────────────────────────────┘
```

### Connection Detail View (Expandable)

```
Connection: f3a7b2c1-... (shortened UUID)
Path: /ws/chat
State: Connected ●
Duration: 1m 23s
Connected: 2025-11-29 14:23:45.123

Statistics:
- Messages Sent: 45 (1.2 KB)
- Messages Received: 67 (1.1 KB)
- Total Messages: 112
- Avg Message Size: 20 bytes

Message Timeline:
┌────────────────────────────────────────────────┐
│ 00:01:23.456 ← text (234 bytes)               │
│ {"type": "message", "content": "Hello..."}     │
│ [Copy] [View Full]                             │
├────────────────────────────────────────────────┤
│ 00:01:23.123 → text (45 bytes)                 │
│ {"type": "ack", "id": 123}                     │
│ [Copy] [View Full]                             │
└────────────────────────────────────────────────┘
```

---

## Configuration Options

### New Config Fields

```python
@dataclass
class DebugToolbarConfig:
    # ... existing fields ...

    # WebSocket tracking
    websocket_tracking_enabled: bool = True
    websocket_max_connections: int = 50
    websocket_max_messages_per_connection: int = 100
    websocket_max_message_size: int = 10240  # 10KB
    websocket_binary_preview_size: int = 256  # bytes
    websocket_show_binary_preview: bool = False
    websocket_connection_ttl: int = 3600  # 1 hour (seconds)
```

---

## Implementation Risks & Mitigations

### Risk 1: Memory Leaks from Long-Lived Connections

**Mitigation**:
- Circular buffer for messages
- TTL-based cleanup for disconnected connections
- Max connection limit
- Monitoring hooks for alerting

### Risk 2: Performance Impact on High-Frequency Messaging

**Mitigation**:
- Optional tracking (config flag)
- Sampling mode (track every Nth message)
- Async message logging (non-blocking)
- Message truncation

### Risk 3: ASGI Middleware Complexity

**Mitigation**:
- Separate WebSocket wrapper class
- Extensive integration tests
- Graceful degradation on errors
- Logging for debugging

### Risk 4: Thread Safety with Concurrent Connections

**Mitigation**:
- Use threading.Lock for connection dict access
- Async-safe data structures
- Per-connection message buffers (no shared state)

---

## Dependencies

### Internal Dependencies
- `debug_toolbar.core.panel.Panel` - Base class
- `debug_toolbar.core.context.RequestContext` - Context storage
- `debug_toolbar.litestar.middleware.DebugToolbarMiddleware` - Middleware integration

### External Dependencies
- `litestar.connection.WebSocket` - WebSocket handling
- ASGI spec compliance (websocket events)

### No New External Packages Required

---

## Performance Benchmarks

### Target Performance

- **Message Logging Overhead**: < 1ms per message
- **Memory per Connection**: < 100KB (with 100 message buffer)
- **Memory per Message**: ~200 bytes (metadata) + content
- **Connection Tracking Overhead**: < 0.1ms per state change

### Measurement Plan

1. Benchmark message logging with `pytest-benchmark`
2. Memory profiling with `tracemalloc`
3. Concurrent connection stress test (100+ connections)
4. High-frequency message test (1000 msgs/sec)

---

## Alternative Approaches Considered

### 1. WebSocket Proxy Pattern

**Description**: Intercept at ASGI layer with full proxy.

**Pros**: Complete visibility, no Litestar dependency
**Cons**: Complex, high performance overhead, reimplements WebSocket logic

**Decision**: Rejected - Too complex for MVP

### 2. Litestar Plugin Hook

**Description**: Use Litestar's plugin system to wrap WebSocket handlers.

**Pros**: Clean integration, framework-aware
**Cons**: Litestar-specific, doesn't work for generic ASGI

**Decision**: Future consideration for Litestar-specific features

### 3. Decorator-Based Tracking

**Description**: `@track_websocket` decorator for handlers.

**Pros**: Explicit opt-in, simple
**Cons**: Manual, easy to forget, doesn't track framework internals

**Decision**: Rejected - Doesn't meet auto-tracking goal

---

## Success Criteria

1. **Functionality**: All acceptance criteria met
2. **Performance**: < 5% overhead on WebSocket operations
3. **Testing**: 90%+ code coverage, all integration tests pass
4. **Documentation**: Comprehensive docstrings, usage examples
5. **Code Quality**: Passes lint, type checks, no anti-patterns
6. **Usability**: Clear UI, actionable information for debugging

---

## Next Steps

1. Implement `WebSocketConnection` and `WebSocketMessage` dataclasses
2. Create `WebSocketPanel` with basic structure
3. Modify middleware to detect and wrap WebSocket scope
4. Implement message tracking in send/receive wrappers
5. Add connection lifecycle management
6. Create unit tests for panel logic
7. Create integration tests with Litestar WebSocket handlers
8. Design and implement HTML template
9. Add configuration options
10. Write documentation and examples

---

## Research Completion

**Total Research Time**: 2 hours
**Patterns Identified**: 4 similar panels, 2 middleware patterns
**External API Research**: Litestar WebSocket API, ASGI WebSocket spec
**Data Models Designed**: 2 core dataclasses
**Test Strategy**: 20+ test cases planned
**Word Count**: 2,247 words

**Status**: ✅ Complete - Ready for PRD finalization
