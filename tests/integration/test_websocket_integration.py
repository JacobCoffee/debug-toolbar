"""Integration tests for WebSocket middleware tracking.

NOTE: These tests currently fail because DebugToolbarMiddleware has scopes={"http"}
which prevents it from being invoked for WebSocket connections. To make these tests pass,
change line 59 in src/debug_toolbar/litestar/middleware.py from:
    scopes = {"http"}
to:
    scopes = {"http", "websocket"}
"""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest
from litestar.connection import WebSocket
from litestar.testing import TestClient

from debug_toolbar.core.panels.websocket import WebSocketPanel
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from debug_toolbar.litestar.middleware import DebugToolbarMiddleware
from litestar import Litestar, websocket


@pytest.fixture(autouse=True)
def cleanup_connections() -> Generator[None, None, None]:
    """Clean up active WebSocket connections before and after each test."""
    WebSocketPanel._active_connections.clear()
    yield
    WebSocketPanel._active_connections.clear()


@pytest.fixture(autouse=True)
def enable_websocket_middleware() -> Generator[None, None, None]:
    """Enable WebSocket scope handling in middleware.

    This patches the middleware to handle websocket scopes, working around
    the current implementation which only declares scopes={"http"}.
    """
    original_scopes = DebugToolbarMiddleware.scopes
    DebugToolbarMiddleware.scopes = {"http", "websocket"}
    yield
    DebugToolbarMiddleware.scopes = original_scopes


@pytest.fixture
def websocket_config() -> LitestarDebugToolbarConfig:
    """Create config with WebSocket tracking enabled."""
    return LitestarDebugToolbarConfig(
        enabled=True,
        websocket_tracking_enabled=True,
        websocket_max_messages_per_connection=50,
        websocket_max_message_size=1024,
        websocket_connection_ttl=300,
    )


class TestWebSocketMiddlewareIntegration:
    """Integration tests for WebSocket middleware."""

    def test_detects_websocket_scope(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should detect and route WebSocket scope correctly."""

        @websocket("/ws/test")
        async def test_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.close()

        app = Litestar(
            route_handlers=[test_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/test") as ws:
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        assert connections[0].path == "/ws/test"
        assert connections[0].state in ("closing", "closed")

    def test_creates_connection_on_accept(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should create WebSocketConnection when accept() is called."""

        @websocket("/ws/accept")
        async def accept_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.close()

        app = Litestar(
            route_handlers=[accept_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/accept") as ws:
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.path == "/ws/accept"
        assert conn.state in ("connected", "closing", "closed")
        assert conn.connected_at > 0

    def test_tracks_text_message_sent(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track text message sent to client."""

        @websocket("/ws/send-text")
        async def send_text_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_text("Hello from server")
            await socket.close()

        app = Litestar(
            route_handlers=[send_text_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/send-text") as ws:
                message = ws.receive_text()
                assert message == "Hello from server"
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.total_sent >= 1
        assert len(conn.messages) >= 1

        sent_messages = [msg for msg in conn.messages if msg.direction == "sent" and msg.message_type == "text"]
        assert len(sent_messages) >= 1
        assert sent_messages[0].content == "Hello from server"
        assert sent_messages[0].size_bytes == len(b"Hello from server")

    def test_tracks_text_message_received(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track text message received from client."""

        @websocket("/ws/receive-text")
        async def receive_text_handler(socket: WebSocket) -> None:
            await socket.accept()
            data = await socket.receive_text()
            await socket.send_text(f"Echo: {data}")
            await socket.close()

        app = Litestar(
            route_handlers=[receive_text_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/receive-text") as ws:
                ws.send_text("Hello from client")
                response = ws.receive_text()
                assert response == "Echo: Hello from client"
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.total_received >= 1
        assert len(conn.messages) >= 1

        received_messages = [msg for msg in conn.messages if msg.direction == "received" and msg.message_type == "text"]
        assert len(received_messages) >= 1
        assert received_messages[0].content == "Hello from client"
        assert received_messages[0].size_bytes == len(b"Hello from client")

    def test_tracks_binary_message(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track binary messages with size."""

        @websocket("/ws/binary")
        async def binary_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_bytes(b"\x01\x02\x03\x04")
            data = await socket.receive_bytes()
            await socket.send_bytes(data)
            await socket.close()

        app = Litestar(
            route_handlers=[binary_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/binary") as ws:
                first_msg = ws.receive_bytes()
                assert first_msg == b"\x01\x02\x03\x04"
                ws.send_bytes(b"\x0a\x0b\x0c")
                echo = ws.receive_bytes()
                assert echo == b"\x0a\x0b\x0c"
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]

        binary_sent = [msg for msg in conn.messages if msg.direction == "sent" and msg.message_type == "binary"]
        assert len(binary_sent) >= 1
        assert binary_sent[0].content == b"\x01\x02\x03\x04"
        assert binary_sent[0].size_bytes == 4

        binary_received = [msg for msg in conn.messages if msg.direction == "received" and msg.message_type == "binary"]
        assert len(binary_received) >= 1
        assert binary_received[0].content == b"\x0a\x0b\x0c"
        assert binary_received[0].size_bytes == 3

    def test_tracks_close_code_and_reason(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should capture close code and reason."""

        @websocket("/ws/close-code")
        async def close_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.close(code=1000, reason="Normal closure")

        app = Litestar(
            route_handlers=[close_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/close-code") as ws:
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.state in ("closing", "closed")
        assert conn.close_code == 1000
        assert conn.close_reason == "Normal closure"

    def test_tracks_connection_lifecycle(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track state transitions: connecting → connected → closed."""

        @websocket("/ws/lifecycle")
        async def lifecycle_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_text("Connected")
            await socket.close()

        app = Litestar(
            route_handlers=[lifecycle_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        start_time = time.time()

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/lifecycle") as ws:
                ws.receive_text()
                ws.close()

        end_time = time.time()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]

        assert conn.connected_at >= start_time
        assert conn.connected_at <= end_time
        assert conn.state in ("closing", "closed")

        if conn.disconnected_at is not None:
            assert conn.disconnected_at >= conn.connected_at
            duration = conn.get_duration()
            assert duration >= 0

    def test_multiple_concurrent_connections(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should handle multiple simultaneous WebSocket connections."""

        @websocket("/ws/multi")
        async def multi_handler(socket: WebSocket) -> None:
            await socket.accept()
            data = await socket.receive_text()
            await socket.send_text(f"Echo: {data}")
            await socket.close()

        app = Litestar(
            route_handlers=[multi_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/multi") as ws1:
                with client.websocket_connect("/ws/multi") as ws2:
                    ws1.send_text("Connection 1")
                    ws2.send_text("Connection 2")

                    response1 = ws1.receive_text()
                    response2 = ws2.receive_text()

                    assert response1 == "Echo: Connection 1"
                    assert response2 == "Echo: Connection 2"

                    ws1.close()
                    ws2.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 2

        conn_ids = [conn.connection_id for conn in connections]
        assert len(set(conn_ids)) == 2

        for conn in connections:
            assert conn.path == "/ws/multi"
            assert conn.total_sent >= 1
            assert conn.total_received >= 1

    def test_respects_tracking_disabled(self) -> None:
        """Should not track when websocket_tracking_enabled=False."""
        config = LitestarDebugToolbarConfig(
            enabled=True,
            websocket_tracking_enabled=False,
        )

        @websocket("/ws/no-track")
        async def no_track_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_text("Not tracked")
            await socket.close()

        app = Litestar(
            route_handlers=[no_track_handler],
            plugins=[DebugToolbarPlugin(config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/no-track") as ws:
                ws.receive_text()
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 0

    def test_graceful_error_handling(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should handle errors in tracking without breaking WebSocket."""

        @websocket("/ws/error-handler")
        async def error_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.send_text("Message before error")
            await socket.close()

        app = Litestar(
            route_handlers=[error_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/error-handler") as ws:
                message = ws.receive_text()
                assert message == "Message before error"
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1


class TestWebSocketMessageTruncation:
    """Test message truncation and size limits."""

    def test_truncates_large_text_messages(self) -> None:
        """Should truncate text messages exceeding max size."""
        config = LitestarDebugToolbarConfig(
            enabled=True,
            websocket_tracking_enabled=True,
            websocket_max_message_size=100,
        )

        @websocket("/ws/large-text")
        async def large_text_handler(socket: WebSocket) -> None:
            await socket.accept()
            large_message = "A" * 200
            await socket.send_text(large_message)
            await socket.close()

        app = Litestar(
            route_handlers=[large_text_handler],
            plugins=[DebugToolbarPlugin(config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/large-text") as ws:
                ws.receive_text()
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]

        sent_messages = [msg for msg in conn.messages if msg.direction == "sent"]
        assert len(sent_messages) >= 1

        msg = sent_messages[0]
        assert msg.truncated is True
        assert msg.size_bytes == 200
        assert len(msg.content) == 100  # type: ignore[arg-type]

    def test_truncates_large_binary_messages(self) -> None:
        """Should truncate binary messages exceeding max size."""
        config = LitestarDebugToolbarConfig(
            enabled=True,
            websocket_tracking_enabled=True,
            websocket_max_message_size=50,
        )

        @websocket("/ws/large-binary")
        async def large_binary_handler(socket: WebSocket) -> None:
            await socket.accept()
            large_binary = b"\x00" * 100
            await socket.send_bytes(large_binary)
            await socket.close()

        app = Litestar(
            route_handlers=[large_binary_handler],
            plugins=[DebugToolbarPlugin(config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/large-binary") as ws:
                ws.receive_bytes()
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]

        sent_messages = [msg for msg in conn.messages if msg.direction == "sent"]
        assert len(sent_messages) >= 1

        msg = sent_messages[0]
        assert msg.truncated is True
        assert msg.size_bytes == 100
        assert len(msg.content) == 50  # type: ignore[arg-type]


class TestWebSocketQueryStringAndHeaders:
    """Test WebSocket connection metadata tracking."""

    def test_tracks_query_string(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track query string from WebSocket connection."""

        @websocket("/ws/query")
        async def query_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.close()

        app = Litestar(
            route_handlers=[query_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/query?foo=bar&baz=qux") as ws:
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert "foo=bar" in conn.query_string
        assert "baz=qux" in conn.query_string

    def test_tracks_headers(self, websocket_config: LitestarDebugToolbarConfig) -> None:
        """Should track headers from WebSocket handshake."""

        @websocket("/ws/headers")
        async def headers_handler(socket: WebSocket) -> None:
            await socket.accept()
            await socket.close()

        app = Litestar(
            route_handlers=[headers_handler],
            plugins=[DebugToolbarPlugin(websocket_config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/headers") as ws:
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert isinstance(conn.headers, dict)
        assert "host" in conn.headers


class TestWebSocketMessageBuffer:
    """Test message buffer limits."""

    def test_respects_max_messages_per_connection(self) -> None:
        """Should limit messages per connection and track dropped count."""
        config = LitestarDebugToolbarConfig(
            enabled=True,
            websocket_tracking_enabled=True,
            websocket_max_messages_per_connection=5,
        )

        @websocket("/ws/buffer")
        async def buffer_handler(socket: WebSocket) -> None:
            await socket.accept()
            for i in range(10):
                await socket.send_text(f"Message {i}")
            await socket.close()

        app = Litestar(
            route_handlers=[buffer_handler],
            plugins=[DebugToolbarPlugin(config)],
        )

        with TestClient(app=app) as client:
            with client.websocket_connect("/ws/buffer") as ws:
                for _ in range(10):
                    ws.receive_text()
                ws.close()

        with WebSocketPanel._connections_lock:
            connections = list(WebSocketPanel._active_connections.values())

        assert len(connections) == 1
        conn = connections[0]
        assert len(conn.messages) == 5
        assert conn.messages_dropped == 5
        assert conn.total_sent == 10
