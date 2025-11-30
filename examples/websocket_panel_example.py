# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "debug-toolbar[litestar]",
#   "jinja2>=3.1.0",
#   "uvicorn>=0.30.0",
# ]
# ///
"""WebSocket Panel Example for Debug Toolbar.

This example demonstrates the WebSocket Panel capabilities:
- Real-time connection tracking
- Bidirectional message logging (sent/received)
- Connection lifecycle monitoring (connect, disconnect)
- Message statistics and byte counts
- Close code/reason capture

Features demonstrated:
1. Echo WebSocket - Simple echo server that reflects messages back
2. Chat WebSocket - Multi-user chat room with broadcasting
3. Binary WebSocket - Binary data handling example

The WebSocket Panel is automatically added when WebSocket handlers are detected!

Run with: uv run examples/websocket_panel_example.py
Then open: http://127.0.0.1:8002

WebSocket endpoints:
- ws://127.0.0.1:8002/ws/echo - Echo server
- ws://127.0.0.1:8002/ws/chat - Chat room
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from litestar import Litestar, MediaType, get, websocket

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

if TYPE_CHECKING:
    from litestar.connection import WebSocket

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

chat_connections: set[WebSocket] = set()


@get("/", media_type=MediaType.HTML)
async def index() -> str:
    """Home page with WebSocket test interface."""
    logger.info("Home page accessed")
    return """<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Panel Demo</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .panel { border: 1px solid #ccc; padding: 15px; border-radius: 8px; }
        h2 { margin-top: 0; color: #333; }
        .messages { height: 200px; overflow-y: auto; border: 1px solid #eee; padding: 10px; margin: 10px 0; background: #f9f9f9; }
        .message { padding: 5px; margin: 2px 0; border-radius: 4px; }
        .sent { background: #e3f2fd; text-align: right; }
        .received { background: #f3e5f5; }
        .system { background: #fff3e0; font-style: italic; }
        input, button { padding: 8px 12px; margin: 5px 0; }
        input { width: 70%; }
        button { cursor: pointer; background: #4CAF50; color: white; border: none; border-radius: 4px; }
        button:hover { background: #45a049; }
        button.disconnect { background: #f44336; }
        button.disconnect:hover { background: #da190b; }
        .status { padding: 5px 10px; border-radius: 4px; display: inline-block; }
        .status.connected { background: #c8e6c9; color: #2e7d32; }
        .status.disconnected { background: #ffcdd2; color: #c62828; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>WebSocket Panel Demo</h1>
    <p>This demo shows the WebSocket Panel tracking connections and messages in real-time.</p>
    <p><strong>Check the Debug Toolbar</strong> on the right side to see the WebSocket Panel!</p>

    <div class="container">
        <div class="panel">
            <h2>Echo WebSocket</h2>
            <p>Messages are echoed back by the server.</p>
            <div>
                <span class="status disconnected" id="echo-status">Disconnected</span>
            </div>
            <div class="messages" id="echo-messages"></div>
            <input type="text" id="echo-input" placeholder="Type a message..." disabled>
            <button onclick="sendEcho()" disabled id="echo-send">Send</button>
            <button onclick="connectEcho()" id="echo-connect">Connect</button>
            <button onclick="disconnectEcho()" class="disconnect" disabled id="echo-disconnect">Disconnect</button>
        </div>

        <div class="panel">
            <h2>Chat Room</h2>
            <p>Messages are broadcast to all connected clients.</p>
            <div>
                <span class="status disconnected" id="chat-status">Disconnected</span>
                <span id="chat-users"></span>
            </div>
            <div class="messages" id="chat-messages"></div>
            <input type="text" id="chat-name" placeholder="Your name" style="width: 30%;">
            <input type="text" id="chat-input" placeholder="Type a message..." disabled style="width: 50%;">
            <button onclick="sendChat()" disabled id="chat-send">Send</button>
            <button onclick="connectChat()" id="chat-connect">Connect</button>
            <button onclick="disconnectChat()" class="disconnect" disabled id="chat-disconnect">Disconnect</button>
        </div>
    </div>

    <h2>How to Use</h2>
    <ol>
        <li>Click "Connect" on either panel to establish a WebSocket connection</li>
        <li>Send messages using the input field</li>
        <li>Watch the <strong>WebSocket Panel</strong> in the Debug Toolbar update in real-time</li>
        <li>The panel shows: active connections, message history, bytes transferred</li>
        <li>Click "Disconnect" to close the connection and see close codes captured</li>
    </ol>

    <h2>Debug Toolbar Features</h2>
    <ul>
        <li><strong>Active Connections</strong> - Shows currently open WebSocket connections</li>
        <li><strong>Recent Messages</strong> - Timeline of sent/received messages</li>
        <li><strong>Statistics</strong> - Total connections, messages, bytes transferred</li>
        <li><strong>Connection Details</strong> - Path, duration, close codes</li>
    </ul>

    <p><a href="/_debug_toolbar/">View Request History</a></p>

    <script>
        let echoWs = null;
        let chatWs = null;

        function addMessage(containerId, text, type) {
            const container = document.getElementById(containerId);
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = new Date().toLocaleTimeString() + ' - ' + text;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        function updateStatus(prefix, connected) {
            const status = document.getElementById(prefix + '-status');
            status.textContent = connected ? 'Connected' : 'Disconnected';
            status.className = 'status ' + (connected ? 'connected' : 'disconnected');
            document.getElementById(prefix + '-input').disabled = !connected;
            document.getElementById(prefix + '-send').disabled = !connected;
            document.getElementById(prefix + '-connect').disabled = connected;
            document.getElementById(prefix + '-disconnect').disabled = !connected;
        }

        // Echo WebSocket
        function connectEcho() {
            echoWs = new WebSocket('ws://' + window.location.host + '/ws/echo');
            echoWs.onopen = () => {
                updateStatus('echo', true);
                addMessage('echo-messages', 'Connected to echo server', 'system');
            };
            echoWs.onmessage = (event) => {
                addMessage('echo-messages', event.data, 'received');
            };
            echoWs.onclose = (event) => {
                updateStatus('echo', false);
                addMessage('echo-messages', 'Disconnected (code: ' + event.code + ')', 'system');
            };
            echoWs.onerror = () => {
                addMessage('echo-messages', 'Connection error', 'system');
            };
        }

        function disconnectEcho() {
            if (echoWs) {
                echoWs.close(1000, 'User requested disconnect');
            }
        }

        function sendEcho() {
            const input = document.getElementById('echo-input');
            if (echoWs && input.value) {
                echoWs.send(input.value);
                addMessage('echo-messages', input.value, 'sent');
                input.value = '';
            }
        }

        document.getElementById('echo-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendEcho();
        });

        // Chat WebSocket
        function connectChat() {
            const name = document.getElementById('chat-name').value || 'Anonymous';
            chatWs = new WebSocket('ws://' + window.location.host + '/ws/chat?name=' + encodeURIComponent(name));
            chatWs.onopen = () => {
                updateStatus('chat', true);
                addMessage('chat-messages', 'Connected to chat as ' + name, 'system');
            };
            chatWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'message') {
                    addMessage('chat-messages', data.user + ': ' + data.text, 'received');
                } else if (data.type === 'system') {
                    addMessage('chat-messages', data.text, 'system');
                }
            };
            chatWs.onclose = (event) => {
                updateStatus('chat', false);
                addMessage('chat-messages', 'Disconnected (code: ' + event.code + ')', 'system');
            };
            chatWs.onerror = () => {
                addMessage('chat-messages', 'Connection error', 'system');
            };
        }

        function disconnectChat() {
            if (chatWs) {
                chatWs.close(1000, 'User left chat');
            }
        }

        function sendChat() {
            const input = document.getElementById('chat-input');
            if (chatWs && input.value) {
                chatWs.send(input.value);
                addMessage('chat-messages', 'You: ' + input.value, 'sent');
                input.value = '';
            }
        }

        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendChat();
        });
    </script>
</body>
</html>"""


@websocket("/ws/echo")
async def echo_handler(socket: WebSocket) -> None:
    """Echo WebSocket handler - reflects messages back to client.

    Demonstrates:
    - Basic WebSocket lifecycle (accept, receive, send, close)
    - Text message handling
    - Connection tracking in the WebSocket Panel
    """
    await socket.accept()
    logger.info(f"Echo WebSocket connected: {socket.client}")

    try:
        while True:
            data = await socket.receive_text()
            logger.debug(f"Echo received: {data}")
            await socket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.debug(f"Echo WebSocket closed: {e}")


@websocket("/ws/chat")
async def chat_handler(socket: WebSocket) -> None:
    """Chat room WebSocket handler - broadcasts messages to all clients.

    Demonstrates:
    - Multiple concurrent WebSocket connections
    - Message broadcasting
    - JSON message handling
    - Query parameter extraction (name)
    """
    await socket.accept()
    name = socket.query_params.get("name", "Anonymous")
    chat_connections.add(socket)
    logger.info(f"Chat WebSocket connected: {name} ({socket.client})")

    join_msg = json.dumps({"type": "system", "text": f"{name} joined the chat"})
    for conn in chat_connections:
        try:
            await conn.send_text(join_msg)
        except Exception:
            pass

    try:
        while True:
            data = await socket.receive_text()
            logger.debug(f"Chat message from {name}: {data}")

            broadcast_msg = json.dumps({
                "type": "message",
                "user": name,
                "text": data,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })
            for conn in chat_connections:
                if conn != socket:
                    try:
                        await conn.send_text(broadcast_msg)
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Chat WebSocket closed for {name}: {e}")
    finally:
        chat_connections.discard(socket)
        leave_msg = json.dumps({"type": "system", "text": f"{name} left the chat"})
        for conn in chat_connections:
            try:
                await conn.send_text(leave_msg)
            except Exception:
                pass


@get("/api/connections", media_type=MediaType.JSON)
async def api_connections() -> dict:
    """API endpoint to check active chat connections."""
    return {
        "active_connections": len(chat_connections),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


toolbar_config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
)

app = Litestar(
    route_handlers=[index, echo_handler, chat_handler, api_connections],
    plugins=[DebugToolbarPlugin(toolbar_config)],
    debug=True,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
