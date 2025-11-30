"""WebSocket debugging panel for tracking WebSocket connections and messages."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal
from uuid import uuid4

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext

__all__ = ["WebSocketMessage", "WebSocketConnection", "WebSocketPanel"]

EventCallback = Callable[[dict[str, Any]], None]


@dataclass(slots=True)
class WebSocketMessage:
    """Represents a single WebSocket message (sent or received).

    Attributes:
        direction: Whether the message was sent or received.
        message_type: The type of WebSocket frame.
        content: The message payload (text, bytes, or None for control frames).
        timestamp: Unix timestamp in seconds with millisecond precision.
        size_bytes: Size of the message payload in bytes.
        truncated: Whether the content was truncated to meet size limits.
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
            max_length: Maximum length of the preview string.

        Returns:
            A preview string, truncated if necessary. Binary data is shown as hex.
        """
        if self.content is None:
            return "<no content>"

        if isinstance(self.content, bytes):
            return self.get_binary_preview_hex(max_bytes=max_length // 2)

        preview = str(self.content)
        if len(preview) > max_length:
            return preview[:max_length] + "..."
        return preview

    def get_binary_preview_hex(self, max_bytes: int = 16) -> str:
        """Get a hexadecimal preview of binary message content.

        Args:
            max_bytes: Maximum number of bytes to display.

        Returns:
            Hexadecimal representation of the binary data.
        """
        if not isinstance(self.content, bytes):
            return "<not binary>"

        preview_bytes = self.content[:max_bytes]
        hex_str = preview_bytes.hex(" ", 1)

        if len(self.content) > max_bytes:
            return f"{hex_str}... ({len(self.content)} bytes total)"
        return hex_str


@dataclass(slots=True)
class WebSocketConnection:
    """Represents a WebSocket connection with its lifecycle and messages.

    Attributes:
        connection_id: Unique identifier for the connection (UUID).
        path: WebSocket endpoint path.
        query_string: Query string from the connection request.
        headers: HTTP headers from the WebSocket handshake.
        connected_at: Unix timestamp when connection was established.
        disconnected_at: Unix timestamp when connection was closed (None if still open).
        close_code: WebSocket close code (RFC 6455).
        close_reason: Human-readable close reason.
        messages: List of messages exchanged on this connection.
        state: Current connection state.
        total_sent: Count of messages sent.
        total_received: Count of messages received.
        bytes_sent: Total bytes sent.
        bytes_received: Total bytes received.
        messages_dropped: Count of messages dropped due to buffer limits.
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

    @staticmethod
    def generate_id() -> str:
        """Generate a unique connection ID.

        Returns:
            A UUID string for the connection.
        """
        return str(uuid4())

    def get_duration(self) -> float:
        """Calculate the connection duration in seconds.

        Returns:
            Duration in seconds. Returns time since connection if still open.
        """
        import time

        end_time = self.disconnected_at if self.disconnected_at is not None else time.time()
        return end_time - self.connected_at

    def add_message(self, message: WebSocketMessage, max_messages: int = 100) -> None:
        """Add a message to the connection, enforcing message buffer limits.

        Args:
            message: The WebSocket message to add.
            max_messages: Maximum number of messages to retain per connection.
        """
        self.messages.append(message)

        if message.direction == "sent":
            self.total_sent += 1
            self.bytes_sent += message.size_bytes
        else:
            self.total_received += 1
            self.bytes_received += message.size_bytes

        if len(self.messages) > max_messages:
            self.messages.pop(0)
            self.messages_dropped += 1

    def get_short_id(self) -> str:
        """Get a shortened version of the connection ID for display.

        Returns:
            First 8 characters of the connection ID.
        """
        return self.connection_id[:8]


class WebSocketPanel(Panel):
    """Panel for displaying WebSocket connection and message information."""

    panel_id: ClassVar[str] = "WebSocketPanel"
    title: ClassVar[str] = "WebSocket"
    template: ClassVar[str] = "panels/websocket.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "WebSocket"

    _active_connections: ClassVar[dict[str, WebSocketConnection]] = {}
    _connections_lock: ClassVar[threading.Lock] = threading.Lock()
    _live_subscribers: ClassVar[set[asyncio.Queue[str]]] = set()
    _subscribers_lock: ClassVar[threading.Lock] = threading.Lock()

    __slots__ = ()

    @classmethod
    def subscribe(cls) -> asyncio.Queue[str]:
        """Subscribe to live WebSocket panel updates.

        Returns:
            An asyncio.Queue that will receive JSON-encoded event messages.
        """
        queue: asyncio.Queue[str] = asyncio.Queue()
        with cls._subscribers_lock:
            cls._live_subscribers.add(queue)
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue[str]) -> None:
        """Unsubscribe from live updates.

        Args:
            queue: The queue to remove from subscribers.
        """
        with cls._subscribers_lock:
            cls._live_subscribers.discard(queue)

    @classmethod
    def _broadcast_event(cls, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all live subscribers.

        Args:
            event_type: Type of event (connection, message, disconnect).
            data: Event data to broadcast.
        """
        with cls._subscribers_lock:
            if not cls._live_subscribers:
                return
            subscribers = set(cls._live_subscribers)

        message = json.dumps({"type": event_type, "data": data})
        dead_queues = []
        for queue in subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:  # noqa: PERF203 - queue cleanup in loop is fine
                dead_queues.append(queue)

        if dead_queues:
            with cls._subscribers_lock:
                for queue in dead_queues:
                    cls._live_subscribers.discard(queue)

    @classmethod
    def track_connection(cls, connection: WebSocketConnection, ttl: int = 3600, max_connections: int = 50) -> None:
        """Track a new WebSocket connection.

        Args:
            connection: The connection to track.
            ttl: Time-to-live in seconds for disconnected connections. Defaults to 3600.
            max_connections: Maximum connections to track. Oldest are dropped when exceeded.
        """
        with cls._connections_lock:
            cls._active_connections[connection.connection_id] = connection
            cls._cleanup_old_connections(ttl)
            cls._enforce_connection_limit(max_connections)

        cls._broadcast_event(
            "connection",
            {
                "connection_id": connection.connection_id,
                "short_id": connection.get_short_id(),
                "path": connection.path,
                "state": connection.state,
                "connected_at": connection.connected_at,
            },
        )

    @classmethod
    def broadcast_message(cls, connection_id: str, message: WebSocketMessage) -> None:
        """Broadcast a message event to live subscribers.

        Args:
            connection_id: The connection ID the message belongs to.
            message: The WebSocket message that was sent/received.
        """
        cls._broadcast_event(
            "message",
            {
                "connection_id": connection_id,
                "direction": message.direction,
                "type": message.message_type,
                "size": message.size_bytes,
                "preview": message.get_content_preview(),
                "timestamp": message.timestamp,
            },
        )

    @classmethod
    def broadcast_state_change(cls, connection_id: str, state: str, close_code: int | None = None) -> None:
        """Broadcast a connection state change to live subscribers.

        Args:
            connection_id: The connection ID.
            state: New connection state.
            close_code: WebSocket close code if applicable.
        """
        cls._broadcast_event(
            "state_change",
            {
                "connection_id": connection_id,
                "state": state,
                "close_code": close_code,
            },
        )

    @classmethod
    def untrack_connection(cls, connection_id: str) -> None:
        """Remove a connection from tracking.

        Args:
            connection_id: The ID of the connection to remove.
        """
        with cls._connections_lock:
            if connection_id in cls._active_connections:
                connection = cls._active_connections[connection_id]
                import time

                connection.disconnected_at = time.time()

    @classmethod
    def get_connection(cls, connection_id: str) -> WebSocketConnection | None:
        """Get a tracked connection by ID.

        Args:
            connection_id: The connection ID to look up.

        Returns:
            The connection if found, None otherwise.
        """
        with cls._connections_lock:
            return cls._active_connections.get(connection_id)

    @classmethod
    def _cleanup_old_connections(cls, ttl: int = 3600) -> None:
        """Remove old disconnected connections based on TTL.

        Args:
            ttl: Time-to-live in seconds for disconnected connections. Defaults to 3600.
        """
        import time

        current_time = time.time()
        to_remove = []

        for conn_id, conn in cls._active_connections.items():
            if conn.disconnected_at is not None:
                age = current_time - conn.disconnected_at
                if age > ttl:
                    to_remove.append(conn_id)

        for conn_id in to_remove:
            del cls._active_connections[conn_id]

    @classmethod
    def _enforce_connection_limit(cls, max_connections: int) -> None:
        """Enforce maximum connection limit by dropping oldest connections.

        Drops disconnected connections first (oldest first), then active if needed.

        Args:
            max_connections: Maximum number of connections to retain.
        """
        if len(cls._active_connections) <= max_connections:
            return

        connections = list(cls._active_connections.values())
        disconnected = sorted(
            [c for c in connections if c.disconnected_at is not None],
            key=lambda c: c.disconnected_at or 0,
        )
        active = sorted(
            [c for c in connections if c.disconnected_at is None],
            key=lambda c: c.connected_at,
        )

        to_remove = []
        excess = len(cls._active_connections) - max_connections

        for conn in disconnected:
            if len(to_remove) >= excess:
                break
            to_remove.append(conn.connection_id)

        for conn in active:
            if len(to_remove) >= excess:
                break
            to_remove.append(conn.connection_id)

        for conn_id in to_remove:
            del cls._active_connections[conn_id]

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate WebSocket statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary containing WebSocket statistics.
        """
        with self._connections_lock:
            connections = list(self._active_connections.values())

        active_connections = [c for c in connections if c.state in ("connecting", "connected")]
        closed_connections = [c for c in connections if c.state == "closed"]

        total_messages_sent = sum(c.total_sent for c in connections)
        total_messages_received = sum(c.total_received for c in connections)
        total_bytes_sent = sum(c.bytes_sent for c in connections)
        total_bytes_received = sum(c.bytes_received for c in connections)

        return {
            "active_connections": [self._connection_to_dict(c) for c in active_connections],
            "closed_connections": [self._connection_to_dict(c) for c in closed_connections],
            "total_active": len(active_connections),
            "total_closed": len(closed_connections),
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
        }

    @staticmethod
    def _connection_to_dict(conn: WebSocketConnection) -> dict[str, Any]:
        """Convert a WebSocketConnection to a dictionary.

        Args:
            conn: The connection to convert.

        Returns:
            Dictionary representation of the connection.
        """
        return {
            "connection_id": conn.connection_id,
            "short_id": conn.get_short_id(),
            "path": conn.path,
            "query_string": conn.query_string,
            "headers": conn.headers,
            "connected_at": conn.connected_at,
            "disconnected_at": conn.disconnected_at,
            "close_code": conn.close_code,
            "close_reason": conn.close_reason,
            "state": conn.state,
            "duration": conn.get_duration(),
            "total_sent": conn.total_sent,
            "total_received": conn.total_received,
            "bytes_sent": conn.bytes_sent,
            "bytes_received": conn.bytes_received,
            "message_count": len(conn.messages),
            "messages_dropped": conn.messages_dropped,
            "messages": [
                {
                    "type": msg.message_type,
                    "direction": msg.direction,
                    "size": msg.size_bytes,
                    "timestamp": msg.timestamp,
                    "preview": msg.get_content_preview(),
                    "content": msg.content
                    if isinstance(msg.content, str)
                    else (msg.get_binary_preview_hex(max_bytes=256) if isinstance(msg.content, bytes) else None),
                    "truncated": msg.truncated,
                }
                for msg in conn.messages
            ],
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing active connection count.

        Returns:
            Subtitle string showing active connection count, or empty string.
        """
        with self._connections_lock:
            active_count = sum(1 for c in self._active_connections.values() if c.state in ("connecting", "connected"))

        if active_count > 0:
            return f"{active_count} active"
        return ""

    @classmethod
    def get_current_stats(cls) -> dict[str, Any]:
        """Get current WebSocket statistics without a context.

        This is used for live updates via WebSocket.

        Returns:
            Dictionary containing current WebSocket statistics.
        """
        with cls._connections_lock:
            connections = list(cls._active_connections.values())

        active_connections = [c for c in connections if c.state in ("connecting", "connected")]
        closed_connections = [c for c in connections if c.state == "closed"]

        total_messages_sent = sum(c.total_sent for c in connections)
        total_messages_received = sum(c.total_received for c in connections)
        total_bytes_sent = sum(c.bytes_sent for c in connections)
        total_bytes_received = sum(c.bytes_received for c in connections)

        return {
            "active_connections": [cls._connection_to_dict(c) for c in active_connections],
            "closed_connections": [cls._connection_to_dict(c) for c in closed_connections],
            "total_active": len(active_connections),
            "total_closed": len(closed_connections),
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
        }
