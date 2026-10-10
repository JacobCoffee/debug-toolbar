"""Debug toolbar middleware for Starlette.

This module provides a pure ASGI middleware for Starlette applications.
It uses pure ASGI pattern instead of BaseHTTPMiddleware to avoid:
- Contextvars propagation issues
- Streaming response problems
- Performance overhead
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from debug_toolbar.core import DebugToolbar, RequestContext, set_request_context
from debug_toolbar.core.panels.websocket import WebSocketConnection, WebSocketMessage, WebSocketPanel
from debug_toolbar.starlette.config import StarletteDebugToolbarConfig

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


@dataclass
class ResponseState:
    """Tracks response state during middleware processing."""

    started: bool = False
    body_chunks: list[bytes] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    status_code: int = 200
    is_html: bool = False
    headers_sent: bool = False
    original_headers: list[tuple[bytes, bytes]] = field(default_factory=list)


class DebugToolbarMiddleware:
    """Pure ASGI middleware for the debug toolbar.

    This middleware:
    - Initializes the request context for each request
    - Collects request/response metadata
    - Injects the toolbar HTML into responses
    - Adds Server-Timing headers

    Uses pure ASGI pattern for better compatibility with contextvars
    and streaming responses.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: StarletteDebugToolbarConfig | None = None,
        toolbar: DebugToolbar | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The next ASGI application.
            config: Toolbar configuration. Uses defaults if not provided.
            toolbar: Optional shared toolbar instance. Creates new if not provided.
        """
        self.app = app
        self.config = config or StarletteDebugToolbarConfig()
        self.toolbar = toolbar or DebugToolbar(self.config)
        self._insert_pattern = re.compile(re.escape(self.config.insert_before), re.IGNORECASE)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an ASGI request."""
        path = scope.get("path", "/")

        if scope["type"] == "websocket":
            if any(path.startswith(excluded) for excluded in self.config.exclude_paths):
                await self.app(scope, receive, send)
                return
            await self._handle_websocket(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request

        request = Request(scope)

        if not self.config.should_show_toolbar(request):
            await self.app(scope, receive, send)
            return

        context = await self.toolbar.process_request()
        scope["_debug_toolbar_context"] = context  # type: ignore[typeddict-unknown-key]
        self._populate_request_metadata(request, context)
        self._populate_routes_metadata(request, context)

        state = ResponseState()
        send_wrapper = self._create_send_wrapper(send, context, state)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            await self._handle_exception(send, state)
            raise
        finally:
            set_request_context(None)

    def _create_send_wrapper(self, send: Send, context: RequestContext, state: ResponseState) -> Send:
        """Create a send wrapper that intercepts and modifies responses."""

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                await self._handle_response_start(send, message, context, state)
            elif message["type"] == "http.response.body":
                await self._handle_response_body(send, message, context, state)
            else:
                await send(message)

        return send_wrapper

    async def _handle_response_start(
        self,
        send: Send,
        message: Message,
        context: RequestContext,
        state: ResponseState,
    ) -> None:
        """Handle http.response.start message."""
        state.started = True
        state.status_code = message["status"]
        state.original_headers = list(message.get("headers", []))
        headers = dict(state.original_headers)
        state.headers = {
            k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
            for k, v in headers.items()
        }

        context.metadata["status_code"] = state.status_code
        context.metadata["response_headers"] = state.headers
        context.metadata["response_content_type"] = state.headers.get("content-type", "")

        state.is_html = "text/html" in state.headers.get("content-type", "")
        if not state.is_html:
            await self._send_non_html_start(send, context, state)

    async def _send_non_html_start(self, send: Send, context: RequestContext, state: ResponseState) -> None:
        """Send response start for non-HTML responses."""
        await self.toolbar.process_response(context)
        server_timing = self.toolbar.get_server_timing_header(context)
        new_headers = list(state.original_headers)
        if server_timing:
            new_headers.append((b"server-timing", server_timing.encode()))
        modified_msg: dict[str, Any] = {
            "type": "http.response.start",
            "status": state.status_code,
            "headers": new_headers,
        }
        await send(modified_msg)
        state.headers_sent = True

    async def _handle_response_body(
        self,
        send: Send,
        message: Message,
        context: RequestContext,
        state: ResponseState,
    ) -> None:
        """Handle http.response.body message."""
        body = message.get("body", b"")

        if not state.is_html:
            await send(message)
            return

        state.body_chunks.append(body)

        if not message.get("more_body", False):
            await self._send_html_response(send, context, state)

    async def _send_html_response(self, send: Send, context: RequestContext, state: ResponseState) -> None:
        """Process and send buffered HTML response with toolbar injection."""
        full_body = b"".join(state.body_chunks)

        try:
            await self.toolbar.process_response(context)
            modified_body = self._inject_toolbar(full_body, context)
            server_timing = self.toolbar.get_server_timing_header(context)
        except Exception:
            logger.debug("Toolbar processing failed, sending original response", exc_info=True)
            modified_body = full_body
            server_timing = None

        new_headers: list[tuple[bytes, bytes]] = [
            (k.encode() if isinstance(k, str) else k, v.encode() if isinstance(v, str) else v)
            for k, v in state.headers.items()
            if k.lower() != "content-length"
        ]
        new_headers.append((b"content-length", str(len(modified_body)).encode()))
        if server_timing:
            new_headers.append((b"server-timing", server_timing.encode()))

        start_event: dict[str, Any] = {
            "type": "http.response.start",
            "status": state.status_code,
            "headers": new_headers,
        }
        await send(start_event)
        body_event: dict[str, Any] = {
            "type": "http.response.body",
            "body": modified_body,
            "more_body": False,
        }
        await send(body_event)
        state.headers_sent = True

    async def _handle_exception(self, send: Send, state: ResponseState) -> None:
        """Handle exception during response processing."""
        if not (state.started and state.is_html and not state.headers_sent):
            return

        try:
            start_event: dict[str, Any] = {
                "type": "http.response.start",
                "status": state.status_code,
                "headers": state.original_headers,
            }
            await send(start_event)
            body_event: dict[str, Any] = {
                "type": "http.response.body",
                "body": b"".join(state.body_chunks),
                "more_body": False,
            }
            await send(body_event)
        except Exception:
            logger.debug("Failed to send buffered response during exception handling", exc_info=True)

    async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle WebSocket connection tracking."""
        if not self.config.websocket_tracking_enabled:
            await self.app(scope, receive, send)
            return

        connection = WebSocketConnection(
            connection_id=str(uuid4()),
            path=scope.get("path", "/"),
            query_string=scope.get("query_string", b"").decode("utf-8", errors="replace"),
            headers={
                k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                for k, v in scope.get("headers", [])
            },
            connected_at=time.time(),
            state="connecting",
        )

        WebSocketPanel.track_connection(
            connection,
            ttl=self.config.websocket_connection_ttl,
            max_connections=self.config.websocket_max_connections,
        )
        logger.debug("WebSocket tracked: %s at %s", connection.connection_id[:8], connection.path)

        send_wrapper = self._create_websocket_send_wrapper(send, connection)
        receive_wrapper = self._create_websocket_receive_wrapper(receive, connection)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            if connection.state not in ("closing", "closed"):
                connection.state = "closed"
                connection.disconnected_at = time.time()

    def _create_websocket_message(
        self,
        direction: Literal["sent", "received"],
        message_data: str | bytes,
    ) -> WebSocketMessage:
        """Create a WebSocketMessage from message data."""
        if isinstance(message_data, str):
            message_type: Literal["text", "binary"] = "text"
            content: str | bytes = message_data
            size_bytes = len(message_data.encode("utf-8"))
        else:
            message_type = "binary"
            content = message_data
            size_bytes = len(message_data)

        truncated = size_bytes > self.config.websocket_max_message_size
        if truncated:
            content = content[: self.config.websocket_max_message_size]

        return WebSocketMessage(
            direction=direction,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            size_bytes=size_bytes,
            truncated=truncated,
        )

    def _create_websocket_send_wrapper(self, send: Send, connection: WebSocketConnection) -> Send:
        """Create a send wrapper for WebSocket messages."""

        async def send_wrapper(message: Message) -> None:
            try:
                msg_type = message.get("type", "")

                if msg_type == "websocket.accept":
                    connection.state = "connected"
                    WebSocketPanel.broadcast_state_change(connection.connection_id, "connected")

                elif msg_type == "websocket.send":
                    message_data = message.get("text") or message.get("bytes")
                    if message_data is not None:
                        ws_message = self._create_websocket_message("sent", message_data)
                        connection.add_message(
                            ws_message, max_messages=self.config.websocket_max_messages_per_connection
                        )
                        WebSocketPanel.broadcast_message(connection.connection_id, ws_message)

                elif msg_type == "websocket.close":
                    connection.state = "closing"
                    connection.close_code = message.get("code")
                    connection.close_reason = message.get("reason", "")
                    WebSocketPanel.broadcast_state_change(connection.connection_id, "closing", connection.close_code)

            except Exception:
                logger.debug("Error tracking WebSocket send message", exc_info=True)

            await send(message)

        return send_wrapper

    def _create_websocket_receive_wrapper(self, receive: Receive, connection: WebSocketConnection) -> Receive:
        """Create a receive wrapper for WebSocket messages."""

        async def receive_wrapper() -> Any:
            message = await receive()

            try:
                msg_type = message.get("type", "")

                if msg_type == "websocket.receive":
                    message_data = message.get("text") or message.get("bytes")
                    if message_data is not None:
                        ws_message = self._create_websocket_message("received", message_data)
                        connection.add_message(
                            ws_message, max_messages=self.config.websocket_max_messages_per_connection
                        )
                        WebSocketPanel.broadcast_message(connection.connection_id, ws_message)

                elif msg_type == "websocket.disconnect":
                    connection.state = "closed"
                    connection.close_code = message.get("code")
                    connection.disconnected_at = time.time()
                    WebSocketPanel.broadcast_state_change(connection.connection_id, "closed", connection.close_code)

            except Exception:
                logger.debug("Error tracking WebSocket receive message", exc_info=True)

            return message

        return receive_wrapper

    def _populate_request_metadata(self, request: Request, context: RequestContext) -> None:
        """Populate request metadata in the context."""
        context.metadata["method"] = request.method
        context.metadata["path"] = request.url.path
        context.metadata["query_string"] = str(request.url.query)
        context.metadata["query_params"] = dict(request.query_params)
        context.metadata["headers"] = dict(request.headers)
        context.metadata["cookies"] = dict(request.cookies)
        context.metadata["scheme"] = request.url.scheme

        if request.client:
            context.metadata["client_host"] = request.client.host
            context.metadata["client_port"] = request.client.port

    def _populate_routes_metadata(self, request: Request, context: RequestContext) -> None:
        """Populate route information from the Starlette app."""
        try:
            app = request.app
            routes_info = []

            for route in getattr(app, "routes", []):
                route_data: dict[str, Any] = {"path": getattr(route, "path", "/")}

                if hasattr(route, "methods"):
                    route_data["methods"] = sorted(route.methods) if route.methods else []

                if hasattr(route, "name") and route.name:
                    route_data["name"] = route.name

                if hasattr(route, "endpoint"):
                    endpoint = route.endpoint
                    route_data["handler"] = getattr(endpoint, "__name__", str(endpoint))

                routes_info.append(route_data)

            context.metadata["routes"] = routes_info

            scope = request.scope
            route = scope.get("route")
            if route:
                context.metadata["matched_route"] = getattr(route, "path", request.url.path)
            else:
                context.metadata["matched_route"] = ""

        except Exception:
            context.metadata["routes"] = []
            context.metadata["matched_route"] = ""

    def _inject_toolbar(self, body: bytes, context: RequestContext) -> bytes:
        """Inject the toolbar HTML into the response body."""
        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError:
            return body

        toolbar_data = self.toolbar.get_toolbar_data(context)
        toolbar_html = self._render_toolbar(toolbar_data)

        insert_before = self.config.insert_before
        if insert_before in html:
            html = html.replace(insert_before, toolbar_html + insert_before)
        else:
            html = self._insert_pattern.sub(toolbar_html + insert_before, html, count=1)

        return html.encode("utf-8")

    def _render_toolbar(self, data: dict[str, Any]) -> str:
        """Render the toolbar HTML."""
        panels_html = []
        for panel in data.get("panels", []):
            subtitle = panel.get("nav_subtitle", "")
            subtitle_html = f'<span class="panel-subtitle">{subtitle}</span>' if subtitle else ""
            panels_html.append(f"""
                <button class="toolbar-panel-btn" data-panel-id="{panel["panel_id"]}">
                    <span class="panel-title">{panel["nav_title"]}</span>
                    {subtitle_html}
                </button>
            """)

        timing = data.get("timing", {})
        total_time = timing.get("total_time", 0) * 1000
        request_id = data.get("request_id", "N/A")

        return f"""
        <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
        <div id="debug-toolbar" data-request-id="{request_id}">
            <div class="toolbar-bar">
                <span class="toolbar-brand" title="Click to toggle">Debug Toolbar</span>
                <span class="toolbar-time">{total_time:.2f}ms</span>
                <div class="toolbar-panels">
                    {"".join(panels_html)}
                </div>
                <span class="toolbar-request-id">
                    <a href="/_debug_toolbar/{request_id}" class="toolbar-history-link"
                       title="View request details">{request_id[:8]}</a>
                </span>
                <a href="/_debug_toolbar/" class="toolbar-history-link" title="View request history">History</a>
            </div>
            <div class="toolbar-details"></div>
        </div>
        <script src="/_debug_toolbar/static/toolbar.js"></script>
        """
