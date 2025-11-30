"""Tests for WebSocket panel and data models."""

from __future__ import annotations

import time

import pytest

from debug_toolbar.core.panels.websocket import (
    WebSocketConnection,
    WebSocketMessage,
    WebSocketPanel,
)


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_create_text_message(self) -> None:
        """Should create message with text content."""
        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="Hello, World!",
            timestamp=time.time(),
            size_bytes=13,
        )

        assert msg.direction == "sent"
        assert msg.message_type == "text"
        assert msg.content == "Hello, World!"
        assert msg.size_bytes == 13
        assert msg.truncated is False

    def test_create_binary_message(self) -> None:
        """Should create message with binary content."""
        binary_data = b"\x00\x01\x02\x03"
        msg = WebSocketMessage(
            direction="received",
            message_type="binary",
            content=binary_data,
            timestamp=time.time(),
            size_bytes=4,
        )

        assert msg.direction == "received"
        assert msg.message_type == "binary"
        assert msg.content == binary_data
        assert msg.size_bytes == 4
        assert msg.truncated is False

    def test_get_content_preview_short_text(self) -> None:
        """Should return full preview for short text."""
        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="Short message",
            timestamp=time.time(),
            size_bytes=13,
        )

        preview = msg.get_content_preview()
        assert preview == "Short message"

    def test_get_content_preview_long_text(self) -> None:
        """Should truncate preview for long text."""
        long_text = "A" * 200
        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content=long_text,
            timestamp=time.time(),
            size_bytes=200,
        )

        preview = msg.get_content_preview(max_length=100)
        assert len(preview) == 103
        assert preview.endswith("...")
        assert preview.startswith("AAA")

    def test_get_content_preview_binary(self) -> None:
        """Should show hex representation for binary data."""
        binary_data = b"\x00\x01\x02\x03\x04"
        msg = WebSocketMessage(
            direction="received",
            message_type="binary",
            content=binary_data,
            timestamp=time.time(),
            size_bytes=5,
        )

        preview = msg.get_content_preview()
        assert "00 01 02 03 04" in preview

    def test_get_content_preview_none(self) -> None:
        """Should show placeholder when content is None."""
        msg = WebSocketMessage(
            direction="sent",
            message_type="ping",
            content=None,
            timestamp=time.time(),
            size_bytes=0,
        )

        preview = msg.get_content_preview()
        assert preview == "<no content>"

    def test_get_binary_preview_hex(self) -> None:
        """Should return hex string representation of binary data."""
        binary_data = b"\xde\xad\xbe\xef"
        msg = WebSocketMessage(
            direction="sent",
            message_type="binary",
            content=binary_data,
            timestamp=time.time(),
            size_bytes=4,
        )

        hex_preview = msg.get_binary_preview_hex()
        assert "de ad be ef" in hex_preview.lower()

    def test_get_binary_preview_hex_truncation(self) -> None:
        """Should truncate hex preview for large binary data."""
        binary_data = b"\x00" * 50
        msg = WebSocketMessage(
            direction="sent",
            message_type="binary",
            content=binary_data,
            timestamp=time.time(),
            size_bytes=50,
        )

        hex_preview = msg.get_binary_preview_hex(max_bytes=8)
        assert "..." in hex_preview
        assert "50 bytes total" in hex_preview

    def test_get_binary_preview_hex_not_binary(self) -> None:
        """Should return placeholder for non-binary content."""
        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="text content",
            timestamp=time.time(),
            size_bytes=12,
        )

        hex_preview = msg.get_binary_preview_hex()
        assert hex_preview == "<not binary>"


class TestWebSocketConnection:
    """Tests for WebSocketConnection dataclass."""

    def test_create_connection(self) -> None:
        """Should create connection with required fields."""
        conn_id = WebSocketConnection.generate_id()
        conn = WebSocketConnection(
            connection_id=conn_id,
            path="/ws/chat",
            query_string="room=123",
            headers={"User-Agent": "TestClient"},
            connected_at=time.time(),
        )

        assert conn.connection_id == conn_id
        assert conn.path == "/ws/chat"
        assert conn.query_string == "room=123"
        assert conn.headers == {"User-Agent": "TestClient"}
        assert conn.disconnected_at is None
        assert conn.state == "connecting"
        assert conn.total_sent == 0
        assert conn.total_received == 0
        assert conn.messages_dropped == 0

    def test_generate_id(self) -> None:
        """Should generate unique UUID string."""
        id1 = WebSocketConnection.generate_id()
        id2 = WebSocketConnection.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) == 36

    def test_get_short_id(self) -> None:
        """Should return first 8 characters of connection ID."""
        conn = WebSocketConnection(
            connection_id="abcd1234-5678-90ef-ghij-klmnopqrstuv",
            path="/ws",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        short_id = conn.get_short_id()
        assert short_id == "abcd1234"

    def test_add_message_sent(self) -> None:
        """Should add message and increment sent counters."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="Hello",
            timestamp=time.time(),
            size_bytes=5,
        )

        conn.add_message(msg)

        assert len(conn.messages) == 1
        assert conn.total_sent == 1
        assert conn.total_received == 0
        assert conn.bytes_sent == 5
        assert conn.bytes_received == 0

    def test_add_message_received(self) -> None:
        """Should add message and increment received counters."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        msg = WebSocketMessage(
            direction="received",
            message_type="text",
            content="World",
            timestamp=time.time(),
            size_bytes=5,
        )

        conn.add_message(msg)

        assert len(conn.messages) == 1
        assert conn.total_sent == 0
        assert conn.total_received == 1
        assert conn.bytes_sent == 0
        assert conn.bytes_received == 5

    def test_message_buffer_limit(self) -> None:
        """Should respect max_messages and use FIFO eviction."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        for i in range(15):
            msg = WebSocketMessage(
                direction="sent",
                message_type="text",
                content=f"Message {i}",
                timestamp=time.time(),
                size_bytes=len(f"Message {i}"),
            )
            conn.add_message(msg, max_messages=10)

        assert len(conn.messages) == 10
        assert conn.messages[0].content == "Message 5"
        assert conn.messages[-1].content == "Message 14"

    def test_messages_dropped_counter(self) -> None:
        """Should track number of dropped messages."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        for i in range(15):
            msg = WebSocketMessage(
                direction="sent",
                message_type="text",
                content=f"Message {i}",
                timestamp=time.time(),
                size_bytes=10,
            )
            conn.add_message(msg, max_messages=10)

        assert conn.messages_dropped == 5
        assert conn.total_sent == 15

    def test_get_duration_active(self) -> None:
        """Should calculate duration for active connection."""
        start_time = time.time()
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=start_time,
        )

        time.sleep(0.1)

        duration = conn.get_duration()
        assert duration >= 0.1
        assert duration < 1.0

    def test_get_duration_closed(self) -> None:
        """Should use disconnected_at for closed connection."""
        start_time = time.time()
        end_time = start_time + 5.0

        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws",
            query_string="",
            headers={},
            connected_at=start_time,
            disconnected_at=end_time,
        )

        duration = conn.get_duration()
        assert duration == 5.0


class TestWebSocketPanel:
    """Tests for WebSocketPanel class."""

    @pytest.fixture(autouse=True)
    def cleanup_connections(self) -> None:
        """Clear connections before/after each test."""
        WebSocketPanel._active_connections.clear()
        yield
        WebSocketPanel._active_connections.clear()

    def test_panel_metadata(self, toolbar) -> None:
        """Should have correct panel metadata."""
        panel = WebSocketPanel(toolbar)

        assert panel.panel_id == "WebSocketPanel"
        assert panel.title == "WebSocket"
        assert panel.template == "panels/websocket.html"
        assert panel.has_content is True
        assert panel.nav_title == "WebSocket"

    def test_track_connection(self) -> None:
        """Should add connection to active connections."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/test",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connected",
        )

        WebSocketPanel.track_connection(conn)

        assert conn.connection_id in WebSocketPanel._active_connections
        assert WebSocketPanel._active_connections[conn.connection_id] == conn

    def test_untrack_connection(self) -> None:
        """Should set disconnected_at when untracking."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/test",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connected",
        )

        WebSocketPanel.track_connection(conn)
        before_untrack = time.time()

        WebSocketPanel.untrack_connection(conn.connection_id)

        tracked_conn = WebSocketPanel._active_connections[conn.connection_id]
        assert tracked_conn.disconnected_at is not None
        assert tracked_conn.disconnected_at >= before_untrack

    def test_untrack_connection_not_found(self) -> None:
        """Should handle untracking non-existent connection gracefully."""
        WebSocketPanel.untrack_connection("nonexistent-id")

    def test_get_connection(self) -> None:
        """Should retrieve connection by ID."""
        conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/test",
            query_string="",
            headers={},
            connected_at=time.time(),
        )

        WebSocketPanel.track_connection(conn)

        retrieved = WebSocketPanel.get_connection(conn.connection_id)
        assert retrieved == conn

    def test_get_connection_not_found(self) -> None:
        """Should return None for unknown connection ID."""
        result = WebSocketPanel.get_connection("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_stats_empty(self, toolbar, request_context) -> None:
        """Should return empty stats when no connections."""
        panel = WebSocketPanel(toolbar)

        stats = await panel.generate_stats(request_context)

        assert stats["active_connections"] == []
        assert stats["closed_connections"] == []
        assert stats["total_active"] == 0
        assert stats["total_closed"] == 0
        assert stats["total_messages_sent"] == 0
        assert stats["total_messages_received"] == 0
        assert stats["total_bytes_sent"] == 0
        assert stats["total_bytes_received"] == 0

    @pytest.mark.asyncio
    async def test_generate_stats_with_connections(self, toolbar, request_context) -> None:
        """Should return stats with active and closed connections."""
        active_conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/active",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connected",
        )

        closed_conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/closed",
            query_string="",
            headers={},
            connected_at=time.time() - 100,
            disconnected_at=time.time() - 50,
            state="closed",
        )

        msg_sent = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="test",
            timestamp=time.time(),
            size_bytes=4,
        )
        msg_received = WebSocketMessage(
            direction="received",
            message_type="text",
            content="response",
            timestamp=time.time(),
            size_bytes=8,
        )

        active_conn.add_message(msg_sent)
        closed_conn.add_message(msg_received)

        WebSocketPanel.track_connection(active_conn)
        WebSocketPanel.track_connection(closed_conn)

        panel = WebSocketPanel(toolbar)
        stats = await panel.generate_stats(request_context)

        assert stats["total_active"] == 1
        assert stats["total_closed"] == 1
        assert stats["total_messages_sent"] == 1
        assert stats["total_messages_received"] == 1
        assert stats["total_bytes_sent"] == 4
        assert stats["total_bytes_received"] == 8
        assert len(stats["active_connections"]) == 1
        assert len(stats["closed_connections"]) == 1

    def test_nav_subtitle_no_active(self, toolbar) -> None:
        """Should return empty string when no active connections."""
        panel = WebSocketPanel(toolbar)

        subtitle = panel.get_nav_subtitle()
        assert subtitle == ""

    def test_nav_subtitle_with_active(self, toolbar) -> None:
        """Should return count when there are active connections."""
        conn1 = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/1",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connected",
        )
        conn2 = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/2",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connecting",
        )
        conn3 = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/3",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="closed",
        )

        WebSocketPanel.track_connection(conn1)
        WebSocketPanel.track_connection(conn2)
        WebSocketPanel.track_connection(conn3)

        panel = WebSocketPanel(toolbar)
        subtitle = panel.get_nav_subtitle()
        assert subtitle == "2 active"

    def test_connection_to_dict(self, toolbar) -> None:
        """Should convert connection to template dictionary."""
        conn = WebSocketConnection(
            connection_id="test-connection-id-12345",
            path="/ws/chat",
            query_string="room=lobby",
            headers={"User-Agent": "TestClient"},
            connected_at=1000.0,
            disconnected_at=1010.0,
            close_code=1000,
            close_reason="Normal closure",
            state="closed",
        )

        msg = WebSocketMessage(
            direction="sent",
            message_type="text",
            content="Hello",
            timestamp=1005.0,
            size_bytes=5,
            truncated=False,
        )
        conn.add_message(msg)

        panel = WebSocketPanel(toolbar)
        result = panel._connection_to_dict(conn)

        assert result["connection_id"] == "test-connection-id-12345"
        assert result["short_id"] == "test-con"
        assert result["path"] == "/ws/chat"
        assert result["query_string"] == "room=lobby"
        assert result["headers"] == {"User-Agent": "TestClient"}
        assert result["connected_at"] == 1000.0
        assert result["disconnected_at"] == 1010.0
        assert result["close_code"] == 1000
        assert result["close_reason"] == "Normal closure"
        assert result["state"] == "closed"
        assert result["duration"] == 10.0
        assert result["total_sent"] == 1
        assert result["total_received"] == 0
        assert result["bytes_sent"] == 5
        assert result["bytes_received"] == 0
        assert result["message_count"] == 1
        assert result["messages_dropped"] == 0
        assert len(result["messages"]) == 1

        msg_dict = result["messages"][0]
        assert msg_dict["type"] == "text"
        assert msg_dict["direction"] == "sent"
        assert msg_dict["size"] == 5
        assert msg_dict["timestamp"] == 1005.0
        assert msg_dict["preview"] == "Hello"
        assert msg_dict["truncated"] is False

    def test_cleanup_old_connections(self) -> None:
        """Should remove expired disconnected connections."""
        old_conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/old",
            query_string="",
            headers={},
            connected_at=time.time() - 7200,
            disconnected_at=time.time() - 7200,
            state="closed",
        )

        recent_conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/recent",
            query_string="",
            headers={},
            connected_at=time.time() - 100,
            disconnected_at=time.time() - 50,
            state="closed",
        )

        active_conn = WebSocketConnection(
            connection_id=WebSocketConnection.generate_id(),
            path="/ws/active",
            query_string="",
            headers={},
            connected_at=time.time(),
            state="connected",
        )

        WebSocketPanel._active_connections[old_conn.connection_id] = old_conn
        WebSocketPanel._active_connections[recent_conn.connection_id] = recent_conn
        WebSocketPanel._active_connections[active_conn.connection_id] = active_conn

        WebSocketPanel._cleanup_old_connections(ttl=3600)

        assert old_conn.connection_id not in WebSocketPanel._active_connections
        assert recent_conn.connection_id in WebSocketPanel._active_connections
        assert active_conn.connection_id in WebSocketPanel._active_connections
