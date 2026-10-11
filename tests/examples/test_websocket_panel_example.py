"""Tests for the WebSocket Panel example application."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from litestar.testing import TestClient

from debug_toolbar.core.panels.websocket import WebSocketPanel

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType


@pytest.fixture(autouse=True)
def _clear_websocket_connections() -> Iterator[None]:
    """Isolate the module-level WebSocketPanel connection registry between tests."""
    WebSocketPanel._active_connections.clear()
    yield
    WebSocketPanel._active_connections.clear()


@pytest.fixture
def app_module(import_example: Callable[[str], ModuleType]) -> ModuleType:
    return import_example("examples.websocket_panel_example")


def test_index_page_shows_toolbar(app_module: ModuleType) -> None:
    with TestClient(app_module.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="debug-toolbar"' in response.text


def test_echo_websocket_echoes_message(app_module: ModuleType) -> None:
    with TestClient(app_module.app) as client, client.websocket_connect("/ws/echo") as ws:
        ws.send_text("hello")
        response = ws.receive_text()
        assert response == "Echo: hello"
        ws.close()


def test_chat_websocket_broadcasts_and_tracks_connections(app_module: ModuleType) -> None:
    with TestClient(app_module.app) as client:
        with client.websocket_connect("/ws/chat?name=Alice") as ws_alice:
            alice_join = json.loads(ws_alice.receive_text())
            assert alice_join == {"type": "system", "text": "Alice joined the chat"}

            with client.websocket_connect("/ws/chat?name=Bob") as ws_bob:
                alice_sees_bob_join = json.loads(ws_alice.receive_text())
                bob_join = json.loads(ws_bob.receive_text())
                assert alice_sees_bob_join == {"type": "system", "text": "Bob joined the chat"}
                assert bob_join == {"type": "system", "text": "Bob joined the chat"}

                connections = client.get("/api/connections").json()
                assert connections["active_connections"] == 2

                ws_alice.send_text("Hello Bob")
                broadcast = json.loads(ws_bob.receive_text())
                assert broadcast["type"] == "message"
                assert broadcast["user"] == "Alice"
                assert broadcast["text"] == "Hello Bob"

            bob_left = json.loads(ws_alice.receive_text())
            assert bob_left == {"type": "system", "text": "Bob left the chat"}

        connections_after = client.get("/api/connections").json()
        assert connections_after["active_connections"] == 0


def test_websocket_panel_records_closed_connection_stats(app_module: ModuleType) -> None:
    with TestClient(app_module.app) as client:
        with client.websocket_connect("/ws/echo") as ws:
            ws.send_text("ping")
            assert ws.receive_text() == "Echo: ping"
            ws.close()

        html_response = client.get("/")
        assert html_response.status_code == 200

        requests = client.get("/_debug_toolbar/api/requests").json()
        root_request = next(req for req in requests if req["metadata"].get("path") == "/")

        detail = client.get(f"/_debug_toolbar/api/requests/{root_request['request_id']}").json()
        ws_stats = detail["panel_data"]["WebSocketPanel"]

        assert ws_stats["total_closed"] >= 1
        closed_paths = [conn["path"] for conn in ws_stats["closed_connections"]]
        assert "/ws/echo" in closed_paths
