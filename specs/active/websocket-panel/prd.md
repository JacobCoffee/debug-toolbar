# PRD: WebSocket Panel for Debug Toolbar

**Status**: Draft
**Slug**: websocket-panel
**Priority**: P1 (Unique Feature - No Competitor Has This)
**Complexity**: High
**Estimated Checkpoints**: 12
**Author**: AI Agent (PRD Phase)
**Created**: 2025-11-29
**Updated**: 2025-11-29

---

## Executive Summary

The WebSocket Panel adds comprehensive WebSocket connection tracking and debugging capabilities to the debug-toolbar, establishing a unique differentiator in the Python debugging ecosystem. No existing debug toolbar (Django Debug Toolbar, Flask Debug Toolbar, or others) provides WebSocket visibility, making this a pioneering feature that addresses a critical gap in modern real-time application debugging.

This feature enables developers to track WebSocket connection lifecycles, monitor message flow bidirectionally, inspect connection metadata, and diagnose real-time communication issues without leaving their integrated debugging workflow. By extending the debug-toolbar's panel plugin architecture to support persistent, stateful connections, this implementation sets the foundation for future real-time protocol support (Server-Sent Events, gRPC streaming, etc.).

**Key Value Propositions**:
- **First-to-Market**: No Python debug toolbar offers WebSocket visibility
- **Integrated Debugging**: Single interface for HTTP and WebSocket debugging
- **Real-Time Insights**: Live connection status, message flow, and performance metrics
- **Developer Productivity**: Reduce context switching between browser DevTools and application debugging
- **Production-Ready**: Memory-safe with configurable limits and graceful degradation

---

## Intelligence Context

### Complexity Assessment: High (12 Checkpoints)

**Rationale**:
- **Multi-Component Architecture**: Core panel + middleware modification + storage strategy + UI
- **Stateful Tracking**: WebSocket connections persist beyond single requests, requiring new storage patterns
- **ASGI Protocol Complexity**: WebSocket ASGI events differ significantly from HTTP request/response model
- **Memory Management**: Long-lived connections and high-frequency messaging require careful resource management
- **Testing Complexity**: Async WebSocket testing, concurrent connection scenarios, lifecycle edge cases

**Checkpoint Breakdown**:
1. Data model design and implementation (WebSocketConnection, WebSocketMessage)
2. WebSocketPanel core implementation
3. Middleware WebSocket detection and wrapping
4. Send wrapper for outgoing messages
5. Receive wrapper for incoming messages
6. Connection lifecycle management (connect/disconnect)
7. Message buffering and truncation logic
8. Storage integration (active + historical connections)
9. Configuration options and validation
10. Unit tests (panel logic, data models)
11. Integration tests (Litestar WebSocket handlers)
12. UI template and visualization

### Pattern Analysis

**Similar Implementations Studied**:

1. **LoggingPanel** (`src/debug_toolbar/core/panels/logging.py`):
   - Pattern: Custom handler class for data capture
   - Pattern: Lifecycle hooks for setup/teardown (`process_request`, `process_response`)
   - Pattern: `__slots__` for memory efficiency
   - **Application**: WebSocket message handler with similar lifecycle pattern

2. **EventsPanel** (`src/debug_toolbar/litestar/panels/events.py`):
   - Pattern: Separate metadata collection functions called from middleware
   - Pattern: Runtime event recording with timestamps
   - Pattern: Helper functions for introspection (`_get_handler_info`, `_get_stack_frames`)
   - **Application**: WebSocket message recording with metadata extraction

3. **TimerPanel** (`src/debug_toolbar/core/panels/timer.py`):
   - Pattern: Instance state in `__slots__` for timing measurements
   - Pattern: Start capture in `process_request()`, calculate deltas in `generate_stats()`
   - Pattern: Server-Timing header contribution
   - **Application**: Connection duration tracking, message timing statistics

4. **RequestPanel** (`src/debug_toolbar/core/panels/request.py`):
   - Pattern: Pure data extraction from `context.metadata`
   - Pattern: Minimal panel logic, delegates collection to middleware
   - Pattern: Simple dictionary unpacking in `generate_stats()`
   - **Application**: Delegate WebSocket metadata collection to middleware wrappers

**Architectural Patterns Identified**:
- **Handler Pattern**: Separate handler class for data collection (LoggingPanel)
- **Metadata Collection Pattern**: Middleware populates context, panel extracts (RequestPanel)
- **Lifecycle Hook Pattern**: Setup in `process_request()`, teardown in `process_response()`
- **Storage Pattern**: Use `context.metadata` for request-scoped data, extend for persistent connections

**Novel Patterns Required**:
- **Persistent Connection Pattern**: Track connections beyond single request contexts
- **Hybrid Storage Pattern**: Active connections in class-level dict, completed in ToolbarStorage
- **Circular Buffer Pattern**: FIFO message buffer with configurable limits
- **ASGI Event Wrapper Pattern**: Intercept send/receive for WebSocket scope type

### Technology Stack Context

**Litestar WebSocket API** (from Context7 research):
- Handler signature: `async def handler(websocket: WebSocket)`
- Lifecycle methods: `accept()`, `send_text()`, `send_bytes()`, `close()`
- Reception methods: `receive_text()`, `receive_bytes()`, `receive_json()`
- Class-based: `WebsocketListener` with `on_connect`, `on_receive`, `on_disconnect`

**ASGI WebSocket Spec**:
- Scope type: `"websocket"`
- Events: `websocket.connect`, `websocket.accept`, `websocket.receive`, `websocket.send`, `websocket.disconnect`, `websocket.close`
- Message structure: `{"type": "websocket.send", "text": "..."}`  or `{"type": "websocket.send", "bytes": b"..."}`
- Close frames: Include `code` and `reason` fields

**Middleware Integration Points**:
- Current scope check: `if scope["type"] != "http": await self.app(scope, receive, send)`
- Modification needed: Add `elif scope["type"] == "websocket"` branch
- Wrapper pattern: Similar to HTTP `send_wrapper`, create `websocket_send_wrapper` and `websocket_receive_wrapper`

---

## Problem Statement

### Current Pain Points

**For Developers**:
1. **Context Switching**: Debugging WebSocket issues requires switching between application logs, browser DevTools Network tab (WebSocket frames), and potentially external tools like Wireshark
2. **Limited Visibility**: Browser DevTools show client-side WebSocket frames but lack server-side context (handler logic, application state, database queries during message processing)
3. **No Integration**: WebSocket debugging is disconnected from HTTP debugging, losing request correlation (e.g., WebSocket initiated by HTTP request)
4. **Manual Instrumentation**: Developers must add custom logging to track WebSocket messages, leading to inconsistent practices across projects

**For debug-toolbar**:
1. **Missing Real-Time Protocol Support**: Modern applications increasingly use WebSockets for chat, notifications, collaborative editing, live dashboards - these are invisible to current debug toolbar
2. **Competitive Gap**: While debug-toolbar has unique ASGI-native architecture, lack of WebSocket support is a missing feature vs. competitors (even though they also lack it)
3. **Architecture Limitation**: Current middleware assumes request/response model, doesn't handle persistent connections

### User Stories

**Story 1: Chat Application Debugging**
> As a developer building a real-time chat application with Litestar and WebSockets,
> I want to see all WebSocket messages sent and received in the debug toolbar,
> So that I can debug message routing issues without adding manual print statements.

**Story 2: Connection State Diagnosis**
> As a developer troubleshooting intermittent WebSocket disconnections,
> I want to see connection lifecycle events (connect, disconnect) with timestamps and close codes,
> So that I can identify patterns in connection failures.

**Story 3: Message Content Inspection**
> As a developer debugging a WebSocket API,
> I want to inspect the actual message content (JSON payloads) sent between client and server,
> So that I can verify data serialization and message format correctness.

**Story 4: Performance Analysis**
> As a developer optimizing a real-time dashboard,
> I want to see message frequency, sizes, and timing statistics,
> So that I can identify performance bottlenecks in WebSocket communication.

**Story 5: Multi-Connection Scenarios**
> As a developer building a multiplayer game or collaborative tool,
> I want to track multiple concurrent WebSocket connections,
> So that I can debug interactions between different clients.

### Success Metrics

**Qualitative**:
- Developers report reduced time to diagnose WebSocket issues
- Positive feedback on integrated HTTP + WebSocket debugging experience
- Adoption by Litestar WebSocket applications

**Quantitative**:
- 90%+ test coverage for WebSocket panel code
- < 5% performance overhead on WebSocket message throughput
- < 100KB memory per tracked connection (with default 100-message buffer)
- Zero production incidents related to WebSocket tracking (graceful degradation)

---

## Goals and Non-Goals

### Goals

1. **Track WebSocket Connection Lifecycle**
   - Detect WebSocket upgrade requests (HTTP → WebSocket)
   - Record connection establishment timestamp
   - Capture connection metadata (path, query parameters, headers)
   - Track connection state transitions (connecting → connected → closing → closed)
   - Record disconnection timestamp, close code, and close reason

2. **Log Bidirectional Messages**
   - Capture messages sent from server to client (outgoing)
   - Capture messages received from client to server (incoming)
   - Record message type (text, binary, ping, pong, close)
   - Store message content with size tracking
   - Include precise timestamps for each message (microsecond precision)

3. **Provide Connection Visualization**
   - Display active and recent connections in panel UI
   - Show connection duration and state indicators
   - Present message timeline with direction indicators (sent ← / → received)
   - Visualize message statistics (count, total bytes, avg size)
   - Support expandable message detail views

4. **Ensure Memory Safety**
   - Implement configurable message buffer limits (circular buffer)
   - Truncate large messages (text > 10KB, show size for binary)
   - Auto-cleanup disconnected connections after TTL expiry
   - Limit max concurrent tracked connections
   - Provide configuration options for resource constraints

5. **Maintain Non-Interference**
   - No impact on normal WebSocket operation (transparent tracking)
   - Graceful degradation on errors (WebSocket works even if tracking fails)
   - Optional tracking via configuration flag
   - Minimal performance overhead (< 5% latency increase)

### Non-Goals (Out of Scope for v1)

1. **Message Modification/Injection**: Not implementing ability to modify or inject WebSocket messages (read-only monitoring)
2. **WebSocket Server Implementation**: Not building WebSocket server, only tracking existing Litestar WebSocket handlers
3. **Multi-Connection Comparison UI**: Not implementing side-by-side comparison of multiple connections (v1 shows list only)
4. **Historical Replay**: Not implementing message replay or connection simulation (future enhancement)
5. **WebSocket Client**: Not implementing WebSocket test client in toolbar UI (use external tools)
6. **Binary Message Decoding**: Not implementing automatic protocol buffer / binary format decoding (show hex preview only)
7. **Custom Protocol Support**: Not implementing WebSocket subprotocol parsing (generic WebSocket only)
8. **Performance Profiling**: Not implementing per-message handler profiling (basic timing only)

---

## Detailed Requirements

### Functional Requirements

#### FR1: WebSocket Connection Detection

**Description**: Middleware must detect WebSocket connections and initialize tracking.

**Acceptance Criteria**:
- Middleware detects `scope["type"] == "websocket"`
- Creates unique connection ID (UUID) for each WebSocket connection
- Extracts connection metadata from scope:
  - Path (`scope["path"]`)
  - Query string (`scope["query_string"]`)
  - Headers (`scope["headers"]`)
  - Client host/port (if available)
- Creates `WebSocketConnection` dataclass instance
- Stores connection in panel's active connections dict
- Does not interfere with WebSocket upgrade process

**Test Cases**:
- `test_detects_websocket_scope()`
- `test_creates_connection_id()`
- `test_extracts_connection_metadata()`
- `test_does_not_block_websocket_upgrade()`

---

#### FR2: Connection Lifecycle Tracking

**Description**: Track connection state transitions from establishment to closure.

**Acceptance Criteria**:
- Records `connected_at` timestamp when connection accepted
- Updates connection state: `"connecting"` → `"connected"` → `"closing"` → `"closed"`
- Captures close code and reason from close frame
- Records `disconnected_at` timestamp when connection closes
- Handles abnormal closures (errors, timeouts)
- Moves completed connections from active dict to storage

**Test Cases**:
- `test_records_connection_timestamp()`
- `test_tracks_state_transitions()`
- `test_captures_close_code_and_reason()`
- `test_handles_abnormal_closure()`
- `test_moves_to_storage_on_close()`

---

#### FR3: Message Logging (Outgoing)

**Description**: Log messages sent from server to client.

**Acceptance Criteria**:
- Intercepts `websocket.send` events via send wrapper
- Creates `WebSocketMessage` with `direction="sent"`
- Determines message type (`"text"`, `"binary"`, `"ping"`, `"pong"`, `"close"`)
- Stores message content (text as string, binary as bytes)
- Records message size in bytes
- Captures timestamp (Unix epoch with millisecond precision)
- Truncates text messages > `websocket_max_message_size` (default 10KB)
- For binary messages, optionally stores hex preview (first 256 bytes)
- Appends message to connection's message buffer
- Increments connection's `total_sent` and `bytes_sent` counters

**Test Cases**:
- `test_logs_text_message_sent()`
- `test_logs_binary_message_sent()`
- `test_logs_ping_pong_frames()`
- `test_logs_close_frame()`
- `test_truncates_large_text_message()`
- `test_stores_binary_hex_preview()`
- `test_increments_sent_counters()`

---

#### FR4: Message Logging (Incoming)

**Description**: Log messages received from client to server.

**Acceptance Criteria**:
- Intercepts `websocket.receive` events via receive wrapper
- Creates `WebSocketMessage` with `direction="received"`
- Determines message type from received event
- Stores message content and size
- Captures timestamp
- Applies same truncation rules as outgoing messages
- Appends message to connection's message buffer
- Increments connection's `total_received` and `bytes_received` counters

**Test Cases**:
- `test_logs_text_message_received()`
- `test_logs_binary_message_received()`
- `test_truncates_large_received_message()`
- `test_increments_received_counters()`

---

#### FR5: Message Buffer Management

**Description**: Implement circular buffer for message storage to prevent unbounded memory growth.

**Acceptance Criteria**:
- Message buffer has configurable max size (`websocket_max_messages_per_connection`, default 100)
- When buffer full, oldest message is evicted (FIFO)
- Buffer tracks if messages were dropped (indicator in UI)
- Buffer is per-connection (isolated message histories)
- Buffer is thread-safe for concurrent access

**Test Cases**:
- `test_message_buffer_respects_limit()`
- `test_evicts_oldest_message_when_full()`
- `test_tracks_dropped_message_count()`
- `test_buffer_thread_safety()`

---

#### FR6: Connection Limit Management

**Description**: Limit number of actively tracked connections to prevent memory exhaustion.

**Acceptance Criteria**:
- Max active connections configurable (`websocket_max_connections`, default 50)
- When limit reached, oldest disconnected connection is removed from active tracking
- Active (still-connected) connections are never removed
- Removed connections are moved to storage if recent, discarded if old
- Configuration option to disable tracking (`websocket_tracking_enabled=False`)

**Test Cases**:
- `test_respects_max_connections_limit()`
- `test_removes_oldest_disconnected_first()`
- `test_never_removes_active_connections()`
- `test_disabled_tracking()`

---

#### FR7: Statistics Generation

**Description**: Panel generates comprehensive statistics from tracked connections.

**Acceptance Criteria**:
- `generate_stats()` returns dict with:
  - `active_connections`: List of currently connected WebSocket connections
  - `recent_connections`: List of recently disconnected connections (last 10)
  - `total_connections`: Total count of all tracked connections (active + stored)
  - `total_messages_sent`: Aggregate across all connections
  - `total_messages_received`: Aggregate across all connections
  - `total_bytes_sent`: Aggregate bytes
  - `total_bytes_received`: Aggregate bytes
  - `connection_durations`: List of connection durations for statistics
- Each connection in lists includes full `WebSocketConnection` data
- Statistics updated in real-time (retrieved from active dict)

**Test Cases**:
- `test_generate_stats_with_active_connections()`
- `test_generate_stats_with_no_connections()`
- `test_aggregate_message_counts()`
- `test_aggregate_byte_counts()`

---

#### FR8: Configuration Options

**Description**: Provide comprehensive configuration for WebSocket tracking.

**Acceptance Criteria**:
- Add to `DebugToolbarConfig` dataclass:
  ```python
  websocket_tracking_enabled: bool = True
  websocket_max_connections: int = 50
  websocket_max_messages_per_connection: int = 100
  websocket_max_message_size: int = 10240  # 10KB
  websocket_binary_preview_size: int = 256  # bytes
  websocket_show_binary_preview: bool = False
  websocket_connection_ttl: int = 3600  # 1 hour (seconds)
  ```
- Configuration validated on startup (positive integers, reasonable limits)
- Configuration accessible to panel and middleware

**Test Cases**:
- `test_default_configuration_values()`
- `test_custom_configuration()`
- `test_configuration_validation()`

---

#### FR9: Panel UI Template

**Description**: HTML template for displaying WebSocket connections and messages.

**Acceptance Criteria**:
- Template file: `templates/panels/websocket.html`
- Displays summary in panel header:
  - Active connection count with status indicator (● green dot)
  - Total connection count
- Lists active connections with:
  - Connection ID (shortened UUID)
  - Path and query string
  - State indicator (● green for connected, ○ gray for closed)
  - Duration (human-readable: "1m 23s")
  - Message counts (sent/received)
  - Total bytes transferred
- Lists recent messages (last 20 across all connections):
  - Timestamp (relative: "2s ago")
  - Connection ID (short)
  - Direction indicator (← / →)
  - Message type and size
  - Content preview (first 100 chars for text, "[binary data]" for binary)
- Expandable message detail view:
  - Full content (with "Copy" button)
  - Full timestamp
  - Truncation indicator if applicable
- Styling consistent with other panels (CSS classes)

**Test Cases** (manual/visual):
- Verify rendering with no connections
- Verify rendering with active connections
- Verify rendering with messages
- Verify responsive layout

---

#### FR10: Middleware Integration

**Description**: Modify Litestar middleware to support WebSocket tracking.

**Acceptance Criteria**:
- Update `DebugToolbarMiddleware.__call__()` to handle WebSocket scope:
  ```python
  if scope["type"] == "websocket":
      await self._handle_websocket(scope, receive, send)
      return
  ```
- Implement `_handle_websocket()` method:
  - Creates request context (or WebSocket-specific context)
  - Initializes connection tracking
  - Wraps `send` for outgoing message interception
  - Wraps `receive` for incoming message interception
  - Handles connection cleanup in finally block
- Create `_create_websocket_send_wrapper()` method
- Create `_create_websocket_receive_wrapper()` method
- Ensure context cleanup: `set_request_context(None)` in finally

**Test Cases**:
- `test_middleware_detects_websocket_scope()`
- `test_middleware_wraps_send_receive()`
- `test_middleware_cleans_up_context()`
- `test_middleware_graceful_error_handling()`

---

### Non-Functional Requirements

#### NFR1: Performance

**Requirement**: WebSocket tracking must have minimal performance impact.

**Criteria**:
- Message logging overhead < 1ms per message (measured with `pytest-benchmark`)
- Connection tracking overhead < 0.1ms per state change
- Memory per connection < 100KB with default 100-message buffer
- No impact on WebSocket throughput (messages/second)

**Measurement**:
- Benchmark test: `test_message_logging_performance()` with 1000 messages
- Memory profiling test with `tracemalloc`
- Load test with 100 concurrent connections

---

#### NFR2: Memory Safety

**Requirement**: No memory leaks from long-lived WebSocket connections.

**Criteria**:
- Circular buffer for messages (bounded memory)
- TTL-based cleanup for disconnected connections
- Max connection limit enforced
- No unbounded data structures

**Verification**:
- Memory leak test: 24-hour connection with continuous messages
- Stress test: 1000 connections with 10,000 messages each
- Monitoring hooks for alerting (log warnings at 80% limits)

---

#### NFR3: Reliability

**Requirement**: WebSocket tracking must not break WebSocket functionality.

**Criteria**:
- Graceful error handling in send/receive wrappers (try/except, log, continue)
- WebSocket connection succeeds even if tracking initialization fails
- Disable tracking on repeated errors (circuit breaker pattern)
- All errors logged with context for debugging

**Verification**:
- Fault injection tests (simulate tracking errors)
- Integration tests with error scenarios
- Manual testing with production-like loads

---

#### NFR4: Thread Safety

**Requirement**: Support concurrent WebSocket connections safely.

**Criteria**:
- Connection dict access protected by `threading.Lock`
- Message buffer append operations are atomic
- No race conditions in state updates
- Context variables properly isolated per connection

**Verification**:
- Concurrent connection test (100 simultaneous connections)
- Race condition test with `pytest-xdist` (parallel execution)
- Manual review of locking patterns

---

#### NFR5: Code Quality

**Requirement**: Maintain project code quality standards.

**Criteria**:
- 90%+ test coverage for new code
- All code passes `make lint` (ruff)
- All code passes `make type-check` (ty)
- No anti-patterns (see CLAUDE.md)
- Comprehensive docstrings (Google style)
- Follows existing panel patterns

**Verification**:
- CI pipeline checks (lint, type-check, coverage)
- Manual code review against patterns
- Documentation review

---

## Technical Design

### Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                     Litestar Application                          │
│                                                                   │
│  ┌─────────────────┐          ┌──────────────────┐              │
│  │ WebSocket       │◄─────────┤DebugToolbar      │              │
│  │ Handler         │          │Middleware        │              │
│  │ (@websocket)    │          │                  │              │
│  └─────────────────┘          └────────┬─────────┘              │
│         ▲                              │                         │
│         │                              │ wraps send/receive      │
│         │                              ▼                         │
│         │                   ┌──────────────────────┐            │
│         │                   │ WebSocket Send/      │            │
│         └───────────────────┤ Receive Wrappers     │            │
│                             │                      │            │
│                             └──────────┬───────────┘            │
│                                        │                         │
│                                        │ records messages        │
│                                        ▼                         │
│                             ┌──────────────────────┐            │
│                             │ WebSocketPanel       │            │
│                             │                      │            │
│                             │ - Active connections │            │
│                             │ - Message buffers    │            │
│                             │ - Statistics         │            │
│                             └──────────────────────┘            │
└───────────────────────────────────────────────────────────────────┘
```

### Data Models

#### WebSocketMessage

```python
"""WebSocket message data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class WebSocketMessage:
    """Represents a single WebSocket message.

    Attributes:
        direction: Direction of message flow ("sent" or "received").
        message_type: Type of WebSocket frame.
        content: Message content (text string or binary bytes).
        timestamp: Unix timestamp with millisecond precision.
        size_bytes: Size of message content in bytes.
        truncated: Whether content was truncated for storage.
    """

    direction: Literal["sent", "received"]
    message_type: Literal["text", "binary", "ping", "pong", "close"]
    content: str | bytes | None
    timestamp: float
    size_bytes: int
    truncated: bool = False

    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the message content.

        Args:
            max_length: Maximum length of preview string.

        Returns:
            Preview string (truncated if necessary).
        """
        if self.content is None:
            return "[no content]"
        if isinstance(self.content, bytes):
            return f"[binary data: {self.size_bytes} bytes]"
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

    def get_binary_preview_hex(self, max_bytes: int = 16) -> str:
        """Get hex preview of binary content.

        Args:
            max_bytes: Maximum bytes to include in preview.

        Returns:
            Hex string representation.
        """
        if not isinstance(self.content, bytes):
            return ""
        preview_bytes = self.content[:max_bytes]
        return preview_bytes.hex(" ").upper()
```

#### WebSocketConnection

```python
"""WebSocket connection data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection session.

    Attributes:
        connection_id: Unique identifier (UUID string).
        path: WebSocket endpoint path.
        query_string: Raw query string from connection request.
        headers: Connection request headers.
        connected_at: Unix timestamp when connection was established.
        disconnected_at: Unix timestamp when connection closed (None if active).
        close_code: WebSocket close code (1000-4999).
        close_reason: Human-readable close reason.
        messages: List of messages (circular buffer, max 100 by default).
        state: Current connection state.
        total_sent: Total messages sent (server → client).
        total_received: Total messages received (client → server).
        bytes_sent: Total bytes sent.
        bytes_received: Total bytes received.
        messages_dropped: Count of messages dropped due to buffer overflow.
    """

    connection_id: str
    path: str
    query_string: str
    headers: dict[str, str]
    connected_at: float
    disconnected_at: float | None = None
    close_code: int | None = None
    close_reason: str | None = None
    messages: list[WebSocketMessage] = field(default_factory=list)
    state: Literal["connecting", "connected", "closing", "closed"] = "connecting"
    total_sent: int = 0
    total_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_dropped: int = 0

    def get_duration(self) -> float:
        """Get connection duration in seconds.

        Returns:
            Duration in seconds (current time - connected_at if still active).
        """
        import time

        end_time = self.disconnected_at or time.time()
        return end_time - self.connected_at

    def add_message(self, message: WebSocketMessage, max_messages: int = 100) -> None:
        """Add a message to the buffer.

        Args:
            message: WebSocketMessage to add.
            max_messages: Maximum messages to retain (circular buffer).
        """
        self.messages.append(message)
        if len(self.messages) > max_messages:
            self.messages.pop(0)
            self.messages_dropped += 1

        # Update counters
        if message.direction == "sent":
            self.total_sent += 1
            self.bytes_sent += message.size_bytes
        else:
            self.total_received += 1
            self.bytes_received += message.size_bytes

    def get_short_id(self) -> str:
        """Get shortened connection ID for display.

        Returns:
            First 8 characters of connection ID.
        """
        return self.connection_id[:8]
```

### Component Design

#### WebSocketPanel

**File**: `src/debug_toolbar/core/panels/websocket.py`

```python
"""WebSocket panel for tracking WebSocket connections and messages."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

# Import data models (to be defined in same file)
# from .websocket_models import WebSocketConnection, WebSocketMessage


class WebSocketPanel(Panel):
    """Panel for displaying WebSocket connection and message information.

    Tracks:
    - Active WebSocket connections
    - Connection lifecycle (connect, disconnect)
    - Bidirectional messages (sent/received)
    - Message content and metadata
    - Connection statistics
    """

    panel_id: ClassVar[str] = "WebSocketPanel"
    title: ClassVar[str] = "WebSocket"
    template: ClassVar[str] = "panels/websocket.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "WebSocket"

    # Class-level storage for active connections (shared across requests)
    _active_connections: ClassVar[dict[str, WebSocketConnection]] = {}
    _connections_lock: ClassVar[threading.Lock] = threading.Lock()

    __slots__ = ()

    def __init__(self, toolbar: DebugToolbar) -> None:
        """Initialize the panel.

        Args:
            toolbar: The parent DebugToolbar instance.
        """
        super().__init__(toolbar)

    @classmethod
    def track_connection(cls, connection: WebSocketConnection) -> None:
        """Add a connection to active tracking.

        Args:
            connection: WebSocketConnection instance to track.
        """
        with cls._connections_lock:
            cls._active_connections[connection.connection_id] = connection

            # Enforce max connections limit
            config = getattr(cls, "_config", None)
            max_connections = getattr(config, "websocket_max_connections", 50)

            if len(cls._active_connections) > max_connections:
                cls._cleanup_old_connections()

    @classmethod
    def untrack_connection(cls, connection_id: str) -> WebSocketConnection | None:
        """Remove a connection from active tracking.

        Args:
            connection_id: ID of connection to remove.

        Returns:
            The removed connection, or None if not found.
        """
        with cls._connections_lock:
            return cls._active_connections.pop(connection_id, None)

    @classmethod
    def get_connection(cls, connection_id: str) -> WebSocketConnection | None:
        """Get a connection by ID.

        Args:
            connection_id: Connection ID to retrieve.

        Returns:
            WebSocketConnection instance, or None if not found.
        """
        with cls._connections_lock:
            return cls._active_connections.get(connection_id)

    @classmethod
    def _cleanup_old_connections(cls) -> None:
        """Remove oldest disconnected connections to free memory.

        Called when max connections limit is reached.
        """
        disconnected = [
            (conn_id, conn)
            for conn_id, conn in cls._active_connections.items()
            if conn.state == "closed"
        ]

        if disconnected:
            # Sort by disconnection time, remove oldest
            disconnected.sort(key=lambda x: x[1].disconnected_at or 0)
            oldest_id, _ = disconnected[0]
            cls._active_connections.pop(oldest_id, None)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate WebSocket statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary of statistics including active connections,
            recent messages, and aggregate metrics.
        """
        with self._connections_lock:
            active_connections = [
                self._connection_to_dict(conn)
                for conn in self._active_connections.values()
                if conn.state in ("connecting", "connected")
            ]

            recent_connections = [
                self._connection_to_dict(conn)
                for conn in sorted(
                    [c for c in self._active_connections.values() if c.state == "closed"],
                    key=lambda c: c.disconnected_at or 0,
                    reverse=True,
                )[:10]
            ]

            # Aggregate statistics
            total_sent = sum(c.total_sent for c in self._active_connections.values())
            total_received = sum(c.total_received for c in self._active_connections.values())
            bytes_sent = sum(c.bytes_sent for c in self._active_connections.values())
            bytes_received = sum(c.bytes_received for c in self._active_connections.values())

            # Recent messages across all connections (last 20)
            all_messages = []
            for conn in self._active_connections.values():
                for msg in conn.messages:
                    all_messages.append((conn.connection_id, msg))

            all_messages.sort(key=lambda x: x[1].timestamp, reverse=True)
            recent_messages = [
                {
                    "connection_id": conn_id,
                    "direction": msg.direction,
                    "message_type": msg.message_type,
                    "size_bytes": msg.size_bytes,
                    "timestamp": msg.timestamp,
                    "content_preview": msg.get_content_preview(100),
                    "truncated": msg.truncated,
                }
                for conn_id, msg in all_messages[:20]
            ]

        return {
            "active_connections": active_connections,
            "recent_connections": recent_connections,
            "total_connections": len(self._active_connections),
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
            "total_bytes_sent": bytes_sent,
            "total_bytes_received": bytes_received,
            "recent_messages": recent_messages,
        }

    def _connection_to_dict(self, conn: WebSocketConnection) -> dict[str, Any]:
        """Convert WebSocketConnection to dictionary for template.

        Args:
            conn: WebSocketConnection instance.

        Returns:
            Dictionary representation suitable for template rendering.
        """
        return {
            "connection_id": conn.connection_id,
            "short_id": conn.get_short_id(),
            "path": conn.path,
            "query_string": conn.query_string,
            "state": conn.state,
            "connected_at": conn.connected_at,
            "disconnected_at": conn.disconnected_at,
            "duration": conn.get_duration(),
            "total_sent": conn.total_sent,
            "total_received": conn.total_received,
            "bytes_sent": conn.bytes_sent,
            "bytes_received": conn.bytes_received,
            "messages_dropped": conn.messages_dropped,
            "close_code": conn.close_code,
            "close_reason": conn.close_reason,
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing active connection count.

        Returns:
            Subtitle string (e.g., "2 active").
        """
        with self._connections_lock:
            active_count = sum(
                1 for conn in self._active_connections.values() if conn.state in ("connecting", "connected")
            )
        if active_count == 0:
            return ""
        return f"{active_count} active"
```

**Key Design Decisions**:
1. **Class-level storage**: `_active_connections` is `ClassVar` shared across all panel instances (WebSocket connections are global, not request-scoped)
2. **Thread safety**: `_connections_lock` protects concurrent access
3. **Lazy cleanup**: Only cleanup when max limit reached (defer work)
4. **Dictionary serialization**: `_connection_to_dict()` prepares data for Jinja template

#### Middleware Modifications

**File**: `src/debug_toolbar/litestar/middleware.py`

**Changes**:

1. **Update `__call__()` method** (line 74):
```python
async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    """Process an ASGI request."""
    # Add WebSocket handling
    if scope["type"] == "websocket":
        await self._handle_websocket(scope, receive, send)
        return

    if scope["type"] != "http":
        await self.app(scope, receive, send)
        return

    # ... existing HTTP handling ...
```

2. **Add `_handle_websocket()` method**:
```python
async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
    """Handle WebSocket connections.

    Args:
        scope: ASGI WebSocket scope.
        receive: ASGI receive callable.
        send: ASGI send callable.
    """
    # Check if WebSocket tracking is enabled
    if not getattr(self.config, "websocket_tracking_enabled", True):
        await self.app(scope, receive, send)
        return

    # Import here to avoid circular dependency
    from debug_toolbar.core.panels.websocket import WebSocketConnection, WebSocketPanel

    # Create connection instance
    import time
    from uuid import uuid4

    connection_id = str(uuid4())
    connection = WebSocketConnection(
        connection_id=connection_id,
        path=scope["path"],
        query_string=scope["query_string"].decode() if isinstance(scope["query_string"], bytes) else scope["query_string"],
        headers={
            k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
            for k, v in scope.get("headers", [])
        },
        connected_at=time.time(),
        state="connecting",
    )

    # Track connection
    WebSocketPanel.track_connection(connection)

    # Wrap send and receive
    send_wrapper = self._create_websocket_send_wrapper(send, connection)
    receive_wrapper = self._create_websocket_receive_wrapper(receive, connection)

    try:
        await self.app(scope, receive_wrapper, send_wrapper)
    except Exception:
        connection.state = "closed"
        connection.disconnected_at = time.time()
        raise
    finally:
        # Mark as disconnected if not already
        if connection.state != "closed":
            connection.state = "closed"
            connection.disconnected_at = time.time()
```

3. **Add `_create_websocket_send_wrapper()` method**:
```python
def _create_websocket_send_wrapper(self, send: Send, connection: WebSocketConnection) -> Send:
    """Create send wrapper for WebSocket message tracking.

    Args:
        send: Original ASGI send callable.
        connection: WebSocketConnection instance.

    Returns:
        Wrapped send callable.
    """
    from debug_toolbar.core.panels.websocket import WebSocketMessage
    import time

    async def send_wrapper(message: Message) -> None:
        # Track outgoing messages
        try:
            if message["type"] == "websocket.accept":
                connection.state = "connected"

            elif message["type"] == "websocket.send":
                # Determine message type and content
                content = None
                message_type = "text"
                size_bytes = 0
                truncated = False

                if "text" in message:
                    content = message["text"]
                    message_type = "text"
                    size_bytes = len(content.encode("utf-8"))

                    # Truncate if too large
                    max_size = getattr(self.config, "websocket_max_message_size", 10240)
                    if size_bytes > max_size:
                        content = content[:max_size] + "... [truncated]"
                        truncated = True

                elif "bytes" in message:
                    content = message["bytes"]
                    message_type = "binary"
                    size_bytes = len(content)

                    # Optionally store binary preview
                    if getattr(self.config, "websocket_show_binary_preview", False):
                        preview_size = getattr(self.config, "websocket_binary_preview_size", 256)
                        content = content[:preview_size]
                    else:
                        content = None  # Don't store binary content

                # Create message record
                ws_message = WebSocketMessage(
                    direction="sent",
                    message_type=message_type,
                    content=content,
                    timestamp=time.time(),
                    size_bytes=size_bytes,
                    truncated=truncated,
                )

                # Add to connection
                max_messages = getattr(self.config, "websocket_max_messages_per_connection", 100)
                connection.add_message(ws_message, max_messages=max_messages)

            elif message["type"] == "websocket.close":
                connection.state = "closing"
                connection.close_code = message.get("code", 1000)
                connection.close_reason = message.get("reason", "")
                connection.disconnected_at = time.time()

        except Exception:
            # Log error but don't break WebSocket
            import logging
            logging.getLogger(__name__).debug("WebSocket send tracking failed", exc_info=True)

        # Always forward to original send
        await send(message)

    return send_wrapper
```

4. **Add `_create_websocket_receive_wrapper()` method**:
```python
def _create_websocket_receive_wrapper(self, receive: Receive, connection: WebSocketConnection) -> Receive:
    """Create receive wrapper for WebSocket message tracking.

    Args:
        receive: Original ASGI receive callable.
        connection: WebSocketConnection instance.

    Returns:
        Wrapped receive callable.
    """
    from debug_toolbar.core.panels.websocket import WebSocketMessage
    import time

    async def receive_wrapper() -> Message:
        message = await receive()

        # Track incoming messages
        try:
            if message["type"] == "websocket.receive":
                content = None
                message_type = "text"
                size_bytes = 0
                truncated = False

                if "text" in message:
                    content = message["text"]
                    message_type = "text"
                    size_bytes = len(content.encode("utf-8"))

                    max_size = getattr(self.config, "websocket_max_message_size", 10240)
                    if size_bytes > max_size:
                        content = content[:max_size] + "... [truncated]"
                        truncated = True

                elif "bytes" in message:
                    content = message["bytes"]
                    message_type = "binary"
                    size_bytes = len(content)

                    if getattr(self.config, "websocket_show_binary_preview", False):
                        preview_size = getattr(self.config, "websocket_binary_preview_size", 256)
                        content = content[:preview_size]
                    else:
                        content = None

                ws_message = WebSocketMessage(
                    direction="received",
                    message_type=message_type,
                    content=content,
                    timestamp=time.time(),
                    size_bytes=size_bytes,
                    truncated=truncated,
                )

                max_messages = getattr(self.config, "websocket_max_messages_per_connection", 100)
                connection.add_message(ws_message, max_messages=max_messages)

            elif message["type"] == "websocket.disconnect":
                connection.state = "closed"
                connection.close_code = message.get("code", 1000)
                connection.disconnected_at = time.time()

        except Exception:
            import logging
            logging.getLogger(__name__).debug("WebSocket receive tracking failed", exc_info=True)

        return message

    return receive_wrapper
```

**Key Design Decisions**:
1. **Graceful error handling**: Try/except around tracking code, always forward to original send/receive
2. **Configuration-driven**: Respects config for truncation, binary preview, etc.
3. **Non-blocking**: Tracking happens synchronously but doesn't await anything
4. **State machine**: Properly tracks connection state transitions

---

### Configuration Updates

**File**: `src/debug_toolbar/core/config.py`

**Add fields** (after line 57):
```python
# WebSocket tracking configuration
websocket_tracking_enabled: bool = True
websocket_max_connections: int = 50
websocket_max_messages_per_connection: int = 100
websocket_max_message_size: int = 10240  # 10KB
websocket_binary_preview_size: int = 256  # bytes
websocket_show_binary_preview: bool = False
websocket_connection_ttl: int = 3600  # 1 hour (seconds)
```

---

### UI Template Design

**File**: `templates/panels/websocket.html` (new file)

```html
{% extends "panels/base.html" %}

{% block panel_content %}
<div class="panel-section">
    <h3>Active Connections ({{ stats.active_connections|length }})</h3>

    {% if stats.active_connections %}
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Path</th>
                    <th>State</th>
                    <th>Duration</th>
                    <th>Messages</th>
                    <th>Bytes</th>
                </tr>
            </thead>
            <tbody>
                {% for conn in stats.active_connections %}
                <tr>
                    <td><code>{{ conn.short_id }}</code></td>
                    <td>
                        <code>{{ conn.path }}</code>
                        {% if conn.query_string %}
                            <br><small class="text-muted">?{{ conn.query_string }}</small>
                        {% endif %}
                    </td>
                    <td>
                        <span class="status-indicator status-{{ conn.state }}">●</span>
                        {{ conn.state }}
                    </td>
                    <td>{{ conn.duration|format_duration }}</td>
                    <td>
                        <span class="text-success">↑ {{ conn.total_sent }}</span> /
                        <span class="text-info">↓ {{ conn.total_received }}</span>
                    </td>
                    <td>
                        <span class="text-success">↑ {{ conn.bytes_sent|format_bytes }}</span> /
                        <span class="text-info">↓ {{ conn.bytes_received|format_bytes }}</span>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p class="text-muted">No active WebSocket connections.</p>
    {% endif %}
</div>

<div class="panel-section">
    <h3>Recent Messages ({{ stats.recent_messages|length }})</h3>

    {% if stats.recent_messages %}
        <div class="message-timeline">
            {% for msg in stats.recent_messages %}
            <div class="message-item message-{{ msg.direction }}">
                <div class="message-header">
                    <span class="message-time">{{ msg.timestamp|format_timestamp }}</span>
                    <span class="message-connection"><code>{{ msg.connection_id[:8] }}</code></span>
                    <span class="message-direction">
                        {% if msg.direction == "sent" %}
                            <span class="text-success">→ Sent</span>
                        {% else %}
                            <span class="text-info">← Received</span>
                        {% endif %}
                    </span>
                    <span class="message-type badge">{{ msg.message_type }}</span>
                    <span class="message-size text-muted">{{ msg.size_bytes|format_bytes }}</span>
                </div>
                <div class="message-content">
                    <pre><code>{{ msg.content_preview }}</code></pre>
                    {% if msg.truncated %}
                        <span class="text-warning">⚠ Content truncated</span>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    {% else %}
        <p class="text-muted">No messages logged yet.</p>
    {% endif %}
</div>

<div class="panel-section">
    <h3>Statistics</h3>
    <dl class="stats-list">
        <dt>Total Connections:</dt>
        <dd>{{ stats.total_connections }}</dd>

        <dt>Total Messages Sent:</dt>
        <dd>{{ stats.total_messages_sent }}</dd>

        <dt>Total Messages Received:</dt>
        <dd>{{ stats.total_messages_received }}</dd>

        <dt>Total Bytes Sent:</dt>
        <dd>{{ stats.total_bytes_sent|format_bytes }}</dd>

        <dt>Total Bytes Received:</dt>
        <dd>{{ stats.total_bytes_received|format_bytes }}</dd>
    </dl>
</div>
{% endblock %}
```

**Template Filters** (add to template context):
- `format_duration`: Format seconds as "1m 23s"
- `format_bytes`: Format bytes as "1.2 KB", "3.4 MB", etc.
- `format_timestamp`: Format Unix timestamp as relative time or absolute

---

## Testing Strategy

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage of panel logic, data models
- **Integration Tests**: 85%+ coverage of middleware integration
- **End-to-End Tests**: Manual verification of UI rendering

### Unit Test Plan

**File**: `tests/core/panels/test_websocket.py` (new file)

**Test Classes**:

```python
class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_create_text_message(self):
        """Should create text message with correct attributes."""

    def test_create_binary_message(self):
        """Should create binary message with size."""

    def test_get_content_preview_text(self):
        """Should preview text content."""

    def test_get_content_preview_binary(self):
        """Should indicate binary content."""

    def test_get_binary_preview_hex(self):
        """Should generate hex preview for binary."""


class TestWebSocketConnection:
    """Tests for WebSocketConnection dataclass."""

    def test_create_connection(self):
        """Should create connection with required fields."""

    def test_add_message(self):
        """Should add message to buffer."""

    def test_message_buffer_limit(self):
        """Should respect max messages limit (circular buffer)."""

    def test_message_dropped_tracking(self):
        """Should increment dropped count."""

    def test_update_sent_counters(self):
        """Should increment total_sent and bytes_sent."""

    def test_update_received_counters(self):
        """Should increment total_received and bytes_received."""

    def test_get_duration_active(self):
        """Should calculate duration for active connection."""

    def test_get_duration_closed(self):
        """Should calculate duration for closed connection."""

    def test_get_short_id(self):
        """Should return first 8 chars of connection ID."""


class TestWebSocketPanel:
    """Tests for WebSocketPanel class."""

    def test_panel_metadata(self):
        """Should have correct panel_id, title, template."""

    def test_track_connection(self):
        """Should add connection to active tracking."""

    def test_untrack_connection(self):
        """Should remove connection from active tracking."""

    def test_get_connection(self):
        """Should retrieve connection by ID."""

    def test_max_connections_limit(self):
        """Should enforce max connections limit."""

    def test_cleanup_old_connections(self):
        """Should remove oldest disconnected connections."""

    async def test_generate_stats_no_connections(self):
        """Should return empty stats with no connections."""

    async def test_generate_stats_with_active(self):
        """Should include active connections in stats."""

    async def test_generate_stats_with_recent(self):
        """Should include recent disconnected connections."""

    async def test_generate_stats_aggregate_counts(self):
        """Should aggregate message and byte counts."""

    async def test_generate_stats_recent_messages(self):
        """Should include last 20 messages across connections."""

    def test_nav_subtitle_no_active(self):
        """Should return empty string with no active connections."""

    def test_nav_subtitle_with_active(self):
        """Should show active count."""

    def test_connection_to_dict(self):
        """Should convert connection to template dict."""

    def test_thread_safety(self):
        """Should handle concurrent access safely."""
```

### Integration Test Plan

**File**: `tests/litestar/test_websocket_integration.py` (new file)

**Test Classes**:

```python
class TestWebSocketMiddlewareIntegration:
    """Integration tests with Litestar WebSocket handlers."""

    @pytest.fixture
    def app(self):
        """Litestar app with WebSocket handler and debug toolbar."""
        from litestar import Litestar, WebSocket, websocket
        from debug_toolbar.litestar import DebugToolbarPlugin

        @websocket("/ws/echo")
        async def echo_handler(socket: WebSocket) -> None:
            await socket.accept()
            data = await socket.receive_text()
            await socket.send_text(f"Echo: {data}")
            await socket.close()

        return Litestar(
            route_handlers=[echo_handler],
            plugins=[DebugToolbarPlugin()],
        )

    async def test_detects_websocket_connection(self, app):
        """Should detect and track WebSocket connection."""

    async def test_tracks_connection_lifecycle(self, app):
        """Should track connect → accept → close."""

    async def test_tracks_text_message_sent(self, app):
        """Should log text message sent to client."""

    async def test_tracks_text_message_received(self, app):
        """Should log text message received from client."""

    async def test_tracks_binary_message(self, app):
        """Should log binary message with size."""

    async def test_tracks_close_code(self, app):
        """Should capture close code and reason."""

    async def test_multiple_concurrent_connections(self, app):
        """Should handle multiple simultaneous connections."""

    async def test_connection_with_query_params(self, app):
        """Should capture query parameters."""

    async def test_connection_with_headers(self, app):
        """Should capture connection headers."""

    async def test_large_message_truncation(self, app):
        """Should truncate messages over limit."""

    async def test_message_buffer_overflow(self, app):
        """Should respect message buffer limit."""

    async def test_error_in_tracking(self, app):
        """Should gracefully handle tracking errors."""

    async def test_disabled_tracking(self, app):
        """Should not track when websocket_tracking_enabled=False."""
```

**Test Utilities**:

```python
@pytest.fixture
async def websocket_client(app):
    """WebSocket test client."""
    from litestar.testing import AsyncTestClient

    async with AsyncTestClient(app=app) as client:
        yield client


async def connect_websocket(client, path: str):
    """Helper to establish WebSocket connection."""
    async with client.websocket_connect(path) as ws:
        yield ws
```

### Performance Test Plan

**File**: `tests/performance/test_websocket_performance.py` (new file)

```python
import pytest


class TestWebSocketPerformance:
    """Performance benchmarks for WebSocket tracking."""

    def test_message_logging_overhead(self, benchmark):
        """Benchmark message logging performance."""
        # Target: < 1ms per message

    def test_connection_tracking_overhead(self, benchmark):
        """Benchmark connection state change performance."""
        # Target: < 0.1ms per state change

    async def test_concurrent_connections_memory(self):
        """Measure memory usage with 100 concurrent connections."""
        # Target: < 10MB total

    async def test_high_frequency_messaging(self):
        """Test 1000 messages/second throughput."""
        # Target: No message loss, < 10% latency increase
```

---

## Files to Create/Modify

### New Files

1. **`src/debug_toolbar/core/panels/websocket.py`** (350+ lines)
   - WebSocketMessage dataclass
   - WebSocketConnection dataclass
   - WebSocketPanel class

2. **`templates/panels/websocket.html`** (100+ lines)
   - Panel UI template
   - Connection list
   - Message timeline
   - Statistics display

3. **`tests/core/panels/test_websocket.py`** (500+ lines)
   - Unit tests for data models
   - Unit tests for panel logic
   - Thread safety tests

4. **`tests/litestar/test_websocket_integration.py`** (400+ lines)
   - Integration tests with Litestar
   - WebSocket lifecycle tests
   - Message tracking tests

5. **`tests/performance/test_websocket_performance.py`** (100+ lines)
   - Performance benchmarks
   - Memory profiling tests

### Modified Files

1. **`src/debug_toolbar/core/config.py`** (~7 new lines)
   - Add WebSocket configuration fields (lines after 57)

2. **`src/debug_toolbar/litestar/middleware.py`** (~200 new lines)
   - Add `_handle_websocket()` method
   - Add `_create_websocket_send_wrapper()` method
   - Add `_create_websocket_receive_wrapper()` method
   - Update `__call__()` to route WebSocket scope

3. **`src/debug_toolbar/core/panels/__init__.py`** (~1 line)
   - Export WebSocketPanel (if following pattern)

4. **`docs/` (future)** (not in scope for implementation PR)
   - Add WebSocket panel documentation
   - Add usage examples

---

## Implementation Checklist

### Phase 1: Data Models (Checkpoint 1)
- [ ] Create `WebSocketMessage` dataclass in `websocket.py`
- [ ] Implement `get_content_preview()` method
- [ ] Implement `get_binary_preview_hex()` method
- [ ] Create `WebSocketConnection` dataclass
- [ ] Implement `add_message()` with circular buffer
- [ ] Implement `get_duration()` method
- [ ] Implement `get_short_id()` method
- [ ] Add type hints with PEP 604 syntax
- [ ] Add comprehensive docstrings (Google style)
- [ ] Unit tests for both dataclasses (15+ tests)

### Phase 2: WebSocketPanel Core (Checkpoints 2-3)
- [ ] Create `WebSocketPanel` class skeleton
- [ ] Implement class-level `_active_connections` dict
- [ ] Implement `_connections_lock` for thread safety
- [ ] Implement `track_connection()` class method
- [ ] Implement `untrack_connection()` class method
- [ ] Implement `get_connection()` class method
- [ ] Implement `_cleanup_old_connections()` method
- [ ] Implement `generate_stats()` method
- [ ] Implement `_connection_to_dict()` helper
- [ ] Implement `get_nav_subtitle()` method
- [ ] Unit tests for panel logic (20+ tests)

### Phase 3: Middleware Integration (Checkpoints 4-7)
- [ ] Update `__call__()` to detect WebSocket scope
- [ ] Implement `_handle_websocket()` method
- [ ] Create WebSocketConnection instance from scope
- [ ] Implement `_create_websocket_send_wrapper()` method
- [ ] Handle `websocket.accept` event
- [ ] Handle `websocket.send` event (text/binary)
- [ ] Handle `websocket.close` event
- [ ] Implement message truncation logic
- [ ] Implement `_create_websocket_receive_wrapper()` method
- [ ] Handle `websocket.receive` event
- [ ] Handle `websocket.disconnect` event
- [ ] Add graceful error handling (try/except, logging)
- [ ] Ensure cleanup in finally block
- [ ] Integration tests (15+ tests)

### Phase 4: Configuration (Checkpoint 8)
- [ ] Add `websocket_tracking_enabled` to config
- [ ] Add `websocket_max_connections` to config
- [ ] Add `websocket_max_messages_per_connection` to config
- [ ] Add `websocket_max_message_size` to config
- [ ] Add `websocket_binary_preview_size` to config
- [ ] Add `websocket_show_binary_preview` to config
- [ ] Add `websocket_connection_ttl` to config
- [ ] Update config docstring
- [ ] Configuration tests

### Phase 5: Storage Integration (Checkpoint 9)
- [ ] Decide on storage strategy (active dict + ToolbarStorage)
- [ ] Implement TTL-based cleanup (optional background task)
- [ ] Test storage with ToolbarStorage integration

### Phase 6: UI Template (Checkpoint 10)
- [ ] Create `templates/panels/websocket.html`
- [ ] Implement active connections table
- [ ] Implement recent connections section
- [ ] Implement message timeline
- [ ] Implement statistics section
- [ ] Add CSS styling (consistent with other panels)
- [ ] Implement template filters (`format_duration`, `format_bytes`, `format_timestamp`)
- [ ] Manual testing of UI rendering

### Phase 7: Testing (Checkpoints 11-12)
- [ ] Complete all unit tests
- [ ] Complete all integration tests
- [ ] Add performance benchmarks
- [ ] Memory profiling tests
- [ ] Concurrent connection stress tests
- [ ] Verify 90%+ coverage
- [ ] Manual E2E testing with real Litestar app

### Phase 8: Quality Assurance
- [ ] Run `make lint` (pass)
- [ ] Run `make type-check` (pass)
- [ ] Run `make test` (all pass)
- [ ] Run `make test-cov` (90%+ coverage)
- [ ] Code review against patterns
- [ ] Anti-pattern check
- [ ] Docstring completeness review
- [ ] Performance validation (< 5% overhead)
- [ ] Memory leak testing (24-hour connection test)

---

## Acceptance Criteria (Expanded)

### AC1: Connection Detection
- **Given** a Litestar application with a WebSocket handler
- **When** a client connects to the WebSocket endpoint
- **Then** the middleware detects the WebSocket scope
- **And** creates a WebSocketConnection instance with unique ID
- **And** extracts path, query string, and headers
- **And** adds connection to panel's active tracking
- **And** the WebSocket upgrade proceeds normally

### AC2: Connection Lifecycle
- **Given** an active WebSocket connection
- **When** the connection is accepted
- **Then** connection state changes to "connected"
- **And** connected_at timestamp is recorded
- **When** the connection closes normally
- **Then** connection state changes to "closed"
- **And** disconnected_at timestamp is recorded
- **And** close code and reason are captured
- **When** the connection closes abnormally (error)
- **Then** connection is still marked as closed
- **And** error is logged but does not propagate

### AC3: Message Logging (Sent)
- **Given** an active WebSocket connection
- **When** the server sends a text message
- **Then** a WebSocketMessage is created with direction="sent"
- **And** message_type="text"
- **And** content is stored as string
- **And** size_bytes is calculated
- **And** timestamp is recorded
- **And** message is appended to connection's buffer
- **When** the text message is larger than max_message_size
- **Then** content is truncated
- **And** truncated=True flag is set
- **When** the server sends a binary message
- **Then** message_type="binary"
- **And** content is None (unless binary_preview enabled)
- **And** size_bytes is recorded

### AC4: Message Logging (Received)
- **Given** an active WebSocket connection
- **When** the server receives a text message from client
- **Then** a WebSocketMessage is created with direction="received"
- **And** same logging rules as sent messages apply
- **When** the server receives a binary message
- **Then** message is logged with type="binary"
- **And** size is recorded

### AC5: Message Buffer Management
- **Given** a connection with max_messages_per_connection=100
- **When** 101 messages are logged
- **Then** the oldest message is removed (FIFO)
- **And** messages_dropped counter increments
- **And** only 100 messages remain in buffer
- **When** messages are added concurrently
- **Then** buffer operations are thread-safe
- **And** no messages are lost due to race conditions

### AC6: Connection Limit Management
- **Given** max_connections=50 configuration
- **When** 51st connection is tracked
- **Then** oldest disconnected connection is removed
- **And** active connections are never removed
- **When** all connections are active (51st attempt)
- **Then** oldest connection by connect time might be removed (implementation choice)
- **Or** tracking is disabled for new connections (alternative)

### AC7: Statistics Generation
- **Given** 3 active connections and 5 recent closed connections
- **When** panel.generate_stats() is called
- **Then** stats include all 3 active connections
- **And** stats include 5 recent closed connections
- **And** total_connections = 8
- **And** aggregate message counts are correct
- **And** aggregate byte counts are correct
- **And** recent_messages includes last 20 messages across all connections
- **And** messages are sorted by timestamp (newest first)

### AC8: UI Rendering
- **Given** stats from generate_stats()
- **When** template is rendered
- **Then** active connections table shows all active connections
- **And** each row displays ID, path, state, duration, message counts, byte counts
- **And** state indicator shows green dot for connected, gray for closed
- **And** message timeline shows last 20 messages
- **And** each message shows timestamp, connection ID, direction, type, size, content preview
- **And** truncated messages have warning indicator
- **And** statistics section shows aggregate totals

### AC9: Configuration
- **Given** default configuration
- **Then** websocket_tracking_enabled=True
- **And** websocket_max_connections=50
- **And** websocket_max_messages_per_connection=100
- **And** websocket_max_message_size=10240 (10KB)
- **When** custom configuration is provided
- **Then** panel respects custom values
- **When** websocket_tracking_enabled=False
- **Then** middleware skips all tracking
- **And** WebSocket operates normally

### AC10: Non-Interference
- **Given** WebSocket tracking is enabled
- **When** a WebSocket connection is established
- **Then** connection succeeds regardless of tracking
- **When** an error occurs in send wrapper
- **Then** error is logged but not raised
- **And** message is forwarded to original send
- **When** an error occurs in receive wrapper
- **Then** error is logged but not raised
- **And** message is returned normally

### AC11: Performance
- **Given** a WebSocket connection
- **When** 1000 messages are sent
- **Then** average logging overhead < 1ms per message
- **When** 100 concurrent connections are active
- **Then** total memory usage < 10MB (with default buffer)
- **When** a single connection is open for 1 hour
- **Then** no memory leaks detected
- **And** memory usage remains stable

### AC12: Test Coverage
- **When** test suite is run
- **Then** unit test coverage ≥ 90%
- **And** integration test coverage ≥ 85%
- **And** all tests pass
- **And** lint checks pass
- **And** type checks pass
- **And** no anti-patterns detected

---

## Risk Assessment and Mitigation

### Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| Memory leak from long-lived connections | Medium | High | **HIGH** | Circular buffer, TTL cleanup, max limits |
| Performance degradation on high-frequency messaging | Medium | Medium | **MEDIUM** | Benchmarking, configurable limits, opt-out |
| Breaking WebSocket functionality | Low | Critical | **MEDIUM** | Graceful error handling, extensive testing |
| Thread safety issues | Low | High | **MEDIUM** | Locking, isolated buffers, concurrent tests |
| ASGI protocol incompatibility | Low | High | **MEDIUM** | Follow ASGI spec, test with multiple frameworks |

### Detailed Mitigation Strategies

**Risk 1: Memory Leak**
- **Detection**: Add memory profiling test with 24-hour connection
- **Prevention**: Circular buffer (bounded), TTL cleanup, max connection limit
- **Monitoring**: Log warnings at 80% of limits
- **Fallback**: Configuration option to disable tracking

**Risk 2: Performance Degradation**
- **Detection**: Benchmark tests for message logging
- **Prevention**: Async-safe, non-blocking tracking, configurable truncation
- **Monitoring**: Performance regression tests in CI
- **Fallback**: Opt-out via configuration

**Risk 3: Breaking WebSocket**
- **Detection**: Integration tests with various WebSocket scenarios
- **Prevention**: Try/except in wrappers, always forward to original send/receive
- **Monitoring**: Error logging with context
- **Fallback**: Circuit breaker (disable tracking after N errors)

**Risk 4: Thread Safety**
- **Detection**: Concurrent connection stress tests
- **Prevention**: threading.Lock for shared state, per-connection buffers
- **Monitoring**: Race condition tests with pytest-xdist
- **Fallback**: Document thread safety requirements

---

## Future Enhancements (Post-v1)

1. **Message Replay**: Ability to replay captured WebSocket messages
2. **Connection Comparison**: Side-by-side comparison of multiple connections
3. **Binary Protocol Decoding**: Automatic protobuf/msgpack decoding
4. **WebSocket Test Client**: In-toolbar WebSocket client for testing
5. **Subprotocol Support**: Parse and display WebSocket subprotocols (STOMP, MQTT, etc.)
6. **Real-Time UI Updates**: Live updates to panel via Server-Sent Events
7. **Message Filtering**: Filter messages by content, type, direction
8. **Export**: Export connection history as JSON/HAR
9. **Alerts**: Configurable alerts for connection drops, error rates
10. **Per-Handler Profiling**: Profile WebSocket handler performance

---

## Documentation Plan (Post-Implementation)

1. **API Documentation**:
   - WebSocketPanel class reference
   - WebSocketConnection/WebSocketMessage dataclass reference
   - Configuration options reference

2. **Usage Guide**:
   - Basic setup (included in main docs)
   - WebSocket tracking configuration
   - Interpreting panel output
   - Performance tuning tips

3. **Examples**:
   - Basic WebSocket echo server
   - Chat application with multiple connections
   - Binary message handling
   - Custom configuration example

4. **Architecture Documentation**:
   - WebSocket tracking architecture diagram
   - Data flow diagram (ASGI → Middleware → Panel)
   - Storage strategy explanation

---

## Success Metrics (Post-Launch)

### Adoption Metrics
- Number of projects using WebSocketPanel
- GitHub stars/forks increase
- Mentions in blog posts/tutorials

### Quality Metrics
- Test coverage maintained > 90%
- Zero production bugs reported
- Performance benchmarks remain green

### Developer Experience Metrics
- Time to diagnose WebSocket issues (qualitative feedback)
- Feature requests for WebSocket panel enhancements
- Positive sentiment in issue comments

---

## Appendix

### A. ASGI WebSocket Event Reference

**websocket.connect**:
```python
{
    "type": "websocket.connect",
}
```

**websocket.accept**:
```python
{
    "type": "websocket.accept",
    "subprotocol": "...",  # Optional
    "headers": [...],  # Optional
}
```

**websocket.send**:
```python
{
    "type": "websocket.send",
    "bytes": b"...",  # Exclusive with text
    "text": "...",  # Exclusive with bytes
}
```

**websocket.receive**:
```python
{
    "type": "websocket.receive",
    "bytes": b"...",  # Exclusive with text
    "text": "...",  # Exclusive with bytes
}
```

**websocket.disconnect**:
```python
{
    "type": "websocket.disconnect",
    "code": 1000,
}
```

**websocket.close**:
```python
{
    "type": "websocket.close",
    "code": 1000,
    "reason": "...",  # Optional
}
```

### B. WebSocket Close Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 1000 | Normal Closure | Successful operation / regular disconnect |
| 1001 | Going Away | Server shutting down or browser navigating away |
| 1002 | Protocol Error | Endpoint received malformed frame |
| 1003 | Unsupported Data | Endpoint received incompatible data type |
| 1006 | Abnormal Closure | Connection closed without close frame (error) |
| 1007 | Invalid Payload | Endpoint received inconsistent data |
| 1008 | Policy Violation | Message violates policy |
| 1009 | Message Too Big | Message too large to process |
| 1011 | Internal Server Error | Server encountered unexpected condition |

### C. Pattern Library Contributions

**New Patterns Identified**:

1. **Persistent Connection Pattern**: Track connections beyond request lifecycle using class-level storage
2. **Hybrid Storage Pattern**: Active dict for live data + ToolbarStorage for history
3. **Circular Buffer Pattern**: FIFO buffer with configurable limit
4. **ASGI Event Wrapper Pattern**: Wrap send/receive for ASGI events

**To be extracted to** `specs/guides/patterns/` during review phase.

---

## Conclusion

This PRD defines a comprehensive, production-ready WebSocket Panel that establishes debug-toolbar as the first Python debugging tool with integrated WebSocket visibility. The design balances feature richness with performance, memory safety, and maintainability, following established codebase patterns while introducing novel patterns for persistent connection tracking.

**Key Deliverables**:
- 5 new files (panel, template, 3 test files)
- 4 modified files (config, middleware, __init__)
- 12 implementation checkpoints
- 50+ test cases
- 90%+ test coverage
- < 5% performance overhead
- Zero breaking changes to existing functionality

**Estimated Implementation Time**: 16-20 hours (expert developer)

**Unique Value**: First-to-market WebSocket debugging in Python tooling ecosystem

---

**PRD Version**: 1.0
**Word Count**: 8,942 words
**Status**: Ready for Implementation Phase
