# Spec: PR #2 - WebSocket Panel

## Metadata
- **PR Number**: 2
- **Priority**: P1
- **Complexity**: High
- **Estimated Files**: 5-7
- **Dependencies**: None
- **Implementation Order**: 2

---

## Problem Statement

WebSocket connections are increasingly common in modern web applications for real-time features like chat, notifications, and live updates. Currently, there's no debug toolbar that provides visibility into WebSocket connections - this is a unique differentiator opportunity.

Developers debugging WebSocket issues must rely on browser DevTools or external tools like Wireshark, losing the integrated debugging experience.

---

## Goals

1. Track WebSocket connection lifecycle (connect, disconnect)
2. Log messages sent and received with timestamps
3. Display connection state timeline
4. Support both text and binary messages
5. Monitor ping/pong for connection health

---

## Non-Goals

- Message modification/injection
- Multiple concurrent connection comparison (v1)
- WebSocket server implementation

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ WebSocketPanel                                  │
├─────────────────────────────────────────────────┤
│ - Tracks active connections                     │
│ - Stores message history per connection         │
│ - Generates timeline visualization data         │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ WebSocketTracker                                │
├─────────────────────────────────────────────────┤
│ - Per-connection message buffer                 │
│ - State change timestamps                       │
│ - Configurable message limit                    │
└─────────────────────────────────────────────────┘
```

### Litestar WebSocket Integration

Litestar provides WebSocket handlers via `@websocket()` decorator. The middleware needs to detect WebSocket upgrades and wrap the connection.

```python
# Detection in middleware
if scope["type"] == "websocket":
    # Wrap WebSocket with tracking
```

### Files to Create/Modify

```python
# src/debug_toolbar/core/panels/websocket.py
class WebSocketPanel(Panel):
    panel_id = "WebSocketPanel"
    title = "WebSocket"
    template = "panels/websocket.html"

    # Track connections across the application
    _connections: ClassVar[dict[str, WebSocketConnection]] = {}
```

```python
# Middleware modification for WebSocket detection
# src/debug_toolbar/litestar/middleware.py
async def __call__(self, scope, receive, send):
    if scope["type"] == "websocket":
        # Create tracked WebSocket wrapper
```

### Data Model

```python
@dataclass
class WebSocketMessage:
    direction: Literal["sent", "received"]
    message_type: Literal["text", "binary", "ping", "pong", "close"]
    content: str | bytes
    timestamp: float
    size_bytes: int

@dataclass
class WebSocketConnection:
    connection_id: str
    path: str
    connected_at: float
    disconnected_at: float | None
    close_code: int | None
    close_reason: str | None
    messages: list[WebSocketMessage]
    state: Literal["connecting", "open", "closing", "closed"]
```

---

## Acceptance Criteria

- [ ] Detect WebSocket upgrade requests
- [ ] Track connection open/close with timestamps
- [ ] Log text messages (truncated if > 10KB)
- [ ] Log binary messages (show size, optionally hex preview)
- [ ] Record ping/pong frames
- [ ] Display close codes and reasons
- [ ] Timeline visualization of connection lifecycle
- [ ] Message direction indicators (sent/received)
- [ ] Configurable message buffer size
- [ ] No interference with normal WebSocket operation
- [ ] 90%+ test coverage

---

## Testing Strategy

### Unit Tests
```python
class TestWebSocketPanel:
    async def test_tracks_connection_open(self):
        """Should record connection establishment."""

    async def test_tracks_text_message(self):
        """Should log text messages with content."""

    async def test_tracks_binary_message(self):
        """Should log binary messages with size."""

    async def test_truncates_large_messages(self):
        """Should truncate messages over size limit."""

    async def test_tracks_close_code(self):
        """Should record close code and reason."""

    async def test_message_buffer_limit(self):
        """Should respect max message count."""
```

### Integration Tests
```python
class TestWebSocketIntegration:
    async def test_full_lifecycle(self):
        """Test connect → message → close cycle."""

    async def test_concurrent_connections(self):
        """Test multiple simultaneous connections."""
```

---

## UI Design

```
┌─────────────────────────────────────────────────┐
│ WebSocket                              1 active │
├─────────────────────────────────────────────────┤
│ Connection: /ws/chat                            │
│ Status: ● Open (2.3s)                          │
│ Messages: 15 sent, 23 received                  │
├─────────────────────────────────────────────────┤
│ Timeline:                                       │
│ ├─ 00:00.000 Connected                         │
│ ├─ 00:00.050 → {"type": "auth", ...}          │
│ ├─ 00:00.123 ← {"type": "welcome", ...}       │
│ ├─ 00:01.234 → {"type": "subscribe", ...}     │
│ ├─ 00:01.456 ← {"type": "data", ...}          │
│ └─ ...                                         │
├─────────────────────────────────────────────────┤
│ → Sent  ← Received  ◉ System                   │
└─────────────────────────────────────────────────┘
```

---

## Configuration

```python
@dataclass
class DebugToolbarConfig:
    # ... existing ...
    websocket_max_messages: int = 100
    websocket_max_message_size: int = 10240  # 10KB
    websocket_show_binary_preview: bool = False
```

---

## Implementation Notes

1. WebSocket connections persist beyond single requests
2. Need connection ID strategy (UUID per connection)
3. Consider memory management for long-lived connections
4. Binary messages: show hex preview option
5. Handle connection errors gracefully

---

## References

- [Litestar WebSocket Docs](https://docs.litestar.dev/latest/usage/websockets.html)
- [WebSocket Close Codes](https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code)
- No direct competitor reference (unique feature)
