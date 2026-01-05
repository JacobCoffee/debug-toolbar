"""Debug toolbar middleware for Litestar."""

from __future__ import annotations

import gzip
import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import uuid4

from debug_toolbar.core import DebugToolbar, RequestContext, set_request_context
from debug_toolbar.core.panels.websocket import WebSocketConnection, WebSocketMessage, WebSocketPanel
from debug_toolbar.litestar.config import LitestarDebugToolbarConfig
from debug_toolbar.litestar.panels.events import collect_events_metadata
from litestar.middleware import AbstractMiddleware

if TYPE_CHECKING:
    from litestar.types import (
        ASGIApp,
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Message,
        Receive,
        Scope,
        Send,
    )

    from litestar import Request

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


class DebugToolbarMiddleware(AbstractMiddleware):
    """Litestar middleware for the debug toolbar.

    This middleware:
    - Initializes the request context for each request
    - Collects request/response metadata
    - Injects the toolbar HTML into responses
    - Adds Server-Timing headers
    """

    scopes = {"http", "websocket"}
    exclude = ["_debug_toolbar"]

    def __init__(
        self,
        app: ASGIApp,
        config: LitestarDebugToolbarConfig | None = None,
        toolbar: DebugToolbar | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The next ASGI application.
            config: Toolbar configuration. Uses defaults if not provided.
            toolbar: Optional shared toolbar instance. Creates new if not provided.
        """
        super().__init__(app)
        self.config = config or LitestarDebugToolbarConfig()
        self.toolbar = toolbar or DebugToolbar(self.config)

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

        from litestar import Request

        request = Request(scope)

        if not self.config.should_show_toolbar(request):
            await self.app(scope, receive, send)
            return

        context = await self.toolbar.process_request()
        scope["_debug_toolbar_context"] = context  # type: ignore[typeddict-unknown-key]
        self._populate_request_metadata(request, context)
        self._populate_events_metadata(request, context)

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
        start_msg = cast("HTTPResponseStartEvent", message)
        state.status_code = start_msg["status"]
        state.original_headers = list(start_msg.get("headers", []))
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
        modified_msg: HTTPResponseStartEvent = {
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
        body_msg = cast("HTTPResponseBodyEvent", message)
        body = body_msg.get("body", b"")

        if not state.is_html:
            await send(message)
            return

        state.body_chunks.append(body)

        if not body_msg.get("more_body", False):
            await self._send_html_response(send, context, state)

    async def _send_html_response(self, send: Send, context: RequestContext, state: ResponseState) -> None:
        """Process and send buffered HTML response with toolbar injection."""
        full_body = b"".join(state.body_chunks)
        content_encoding = state.headers.get("content-encoding", "")

        try:
            await self.toolbar.process_response(context)
            modified_body, new_encoding = self._inject_toolbar(full_body, context, content_encoding)
            server_timing = self.toolbar.get_server_timing_header(context)
        except Exception:
            logger.debug("Toolbar processing failed, sending original response", exc_info=True)
            modified_body = full_body
            new_encoding = content_encoding
            server_timing = None

        # Build headers, excluding content-length (recalculated) and content-encoding (may have changed)
        excluded_headers = {"content-length", "content-encoding"}
        new_headers: list[tuple[bytes, bytes]] = [
            (k.encode(), v.encode()) for k, v in state.headers.items() if k.lower() not in excluded_headers
        ]
        new_headers.append((b"content-length", str(len(modified_body)).encode()))
        # Only add content-encoding if we still have one (not stripped due to decompression)
        if new_encoding:
            new_headers.append((b"content-encoding", new_encoding.encode()))
        if server_timing:
            new_headers.append((b"server-timing", server_timing.encode()))

        start_event: HTTPResponseStartEvent = {
            "type": "http.response.start",
            "status": state.status_code,
            "headers": new_headers,
        }
        await send(start_event)
        body_event: HTTPResponseBodyEvent = {
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
            start_event: HTTPResponseStartEvent = {
                "type": "http.response.start",
                "status": state.status_code,
                "headers": state.original_headers,
            }
            await send(start_event)
            body_event: HTTPResponseBodyEvent = {
                "type": "http.response.body",
                "body": b"".join(state.body_chunks),
                "more_body": False,
            }
            await send(body_event)
        except Exception:
            logger.debug("Failed to send buffered response during exception handling", exc_info=True)

    async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle WebSocket connection tracking.

        Args:
            scope: ASGI scope for the WebSocket connection.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
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
        """Create a WebSocketMessage from message data.

        Args:
            direction: Whether the message was sent or received.
            message_data: The message content (text or bytes).

        Returns:
            A WebSocketMessage instance with proper type and truncation handling.
        """
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
        """Create a send wrapper for WebSocket messages.

        Args:
            send: The original ASGI send callable.
            connection: The WebSocket connection being tracked.

        Returns:
            A wrapped send callable that tracks WebSocket messages.
        """

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
        """Create a receive wrapper for WebSocket messages.

        Args:
            receive: The original ASGI receive callable.
            connection: The WebSocket connection being tracked.

        Returns:
            A wrapped receive callable that tracks WebSocket messages.
        """

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
        """Populate request metadata in the context.

        Args:
            request: The Litestar request.
            context: The request context to populate.
        """
        context.metadata["method"] = request.method
        context.metadata["path"] = request.url.path
        context.metadata["query_string"] = request.url.query
        context.metadata["query_params"] = dict(request.query_params)
        context.metadata["headers"] = dict(request.headers)
        context.metadata["cookies"] = dict(request.cookies)
        context.metadata["content_type"] = request.content_type[0] if request.content_type else ""
        context.metadata["scheme"] = request.url.scheme

        if request.client:
            context.metadata["client_host"] = request.client.host
            context.metadata["client_port"] = request.client.port

        self._populate_routes_metadata(request, context)

    def _populate_events_metadata(self, request: Request, context: RequestContext) -> None:
        """Populate events/lifecycle metadata from the Litestar app.

        Args:
            request: The Litestar request.
            context: The request context to populate.
        """
        try:
            collect_events_metadata(request.app, context)
        except Exception:
            context.metadata["events"] = {
                "lifecycle_hooks": {},
                "request_hooks": {},
                "exception_handlers": [],
                "executed_hooks": [],
            }

    def _populate_routes_metadata(self, request: Request, context: RequestContext) -> None:
        """Populate route information from the Litestar app.

        Args:
            request: The Litestar request.
            context: The request context to populate.
        """
        try:
            app = request.app
            routes_info = []

            for route in app.routes:
                route_data = {
                    "path": route.path,
                    "methods": sorted(getattr(route, "methods", [])),
                    "name": getattr(route, "name", None),
                }
                handler = getattr(route, "route_handler", None)
                if handler:
                    route_data["handler"] = getattr(handler, "fn", handler).__name__
                    route_data["tags"] = list(getattr(handler, "tags", []))
                routes_info.append(route_data)

            context.metadata["routes"] = routes_info

            scope = request.scope
            route_handler = scope.get("route_handler")
            if route_handler:
                context.metadata["matched_route"] = getattr(route_handler, "path", request.url.path)
        except Exception:
            context.metadata["routes"] = []
            context.metadata["matched_route"] = ""

    def _inject_toolbar(self, body: bytes, context: RequestContext, content_encoding: str = "") -> tuple[bytes, str]:
        """Inject the toolbar HTML into the response body.

        Args:
            body: The original response body (may be compressed).
            context: The request context with collected data.
            content_encoding: The content-encoding header value (e.g., "gzip", "br", "zstd").

        Returns:
            Tuple of (modified body, content_encoding to use).
            If compression was handled, returns uncompressed body with empty encoding.
        """
        decompressed = False
        encodings = [e.strip() for e in content_encoding.lower().split(",")] if content_encoding else []

        if "gzip" in encodings:
            try:
                body = gzip.decompress(body)
                decompressed = True
            except gzip.BadGzipFile:
                logger.debug("Invalid gzip data, attempting to decode as-is")

        elif "br" in encodings:
            try:
                import brotli  # type: ignore[import-untyped]

                body = brotli.decompress(body)
                decompressed = True
            except ImportError:
                logger.debug("Brotli not installed, skipping toolbar injection for br-encoded response")
                return body, content_encoding
            except Exception:
                logger.debug("Invalid brotli data, attempting to decode as-is")

        elif "zstd" in encodings:
            try:
                import zstandard  # type: ignore[import-untyped]

                dctx = zstandard.ZstdDecompressor()
                body = dctx.decompress(body)
                decompressed = True
            except ImportError:
                logger.debug("zstandard not installed, skipping toolbar injection for zstd-encoded response")
                return body, content_encoding
            except Exception:
                logger.debug("Invalid zstd data, attempting to decode as-is")

        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError:
            if decompressed:
                return body, ""
            return body, content_encoding

        toolbar_data = self.toolbar.get_toolbar_data(context)
        toolbar_html = self._render_toolbar(toolbar_data)

        insert_before = self.config.insert_before
        if insert_before in html:
            html = html.replace(insert_before, toolbar_html + insert_before)
        else:
            pattern = re.compile(re.escape(insert_before), re.IGNORECASE)
            html = pattern.sub(toolbar_html + insert_before, html, count=1)

        # Return body as uncompressed UTF-8 with empty content-encoding.
        # This applies to all successful toolbar injections, regardless of whether
        # the input was originally compressed (we decompress before processing).
        return html.encode("utf-8"), ""

    def _render_toolbar(self, data: dict[str, Any]) -> str:
        """Render the toolbar HTML.

        Args:
            data: Toolbar data from get_toolbar_data().

        Returns:
            HTML string for the toolbar.
        """
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
                <button class="toolbar-collapse-btn" title="Collapse toolbar"
                        aria-label="Collapse toolbar" aria-expanded="true">
                    <span class="collapse-icon">&laquo;</span>
                </button>
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
            <!-- Reserved for future toolbar content and use by toolbar.js -->
            <div class="toolbar-content"></div>
        </div>
        <script src="/_debug_toolbar/static/toolbar.js"></script>
        """
