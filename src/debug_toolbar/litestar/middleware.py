"""Debug toolbar middleware for Litestar."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from debug_toolbar.core import DebugToolbar, RequestContext, set_request_context
from debug_toolbar.litestar.config import LitestarDebugToolbarConfig
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


class DebugToolbarMiddleware(AbstractMiddleware):
    """Litestar middleware for the debug toolbar.

    This middleware:
    - Initializes the request context for each request
    - Collects request/response metadata
    - Injects the toolbar HTML into responses
    - Adds Server-Timing headers
    """

    scopes = {"http"}
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
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from litestar import Request

        request = Request(scope)

        if not self.config.should_show_toolbar(request):
            await self.app(scope, receive, send)
            return

        context = await self.toolbar.process_request()
        self._populate_request_metadata(request, context)

        response_started = False
        response_body_chunks: list[bytes] = []
        response_headers: dict[str, str] = {}
        status_code = 200
        is_html_response = False
        headers_sent = False
        original_headers: list[tuple[bytes, bytes]] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started, status_code, response_headers, is_html_response, headers_sent, original_headers

            if message["type"] == "http.response.start":
                response_started = True
                start_msg = cast("HTTPResponseStartEvent", message)
                status_code = start_msg["status"]
                original_headers = list(start_msg.get("headers", []))
                headers = dict(original_headers)
                response_headers = {
                    k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
                    for k, v in headers.items()
                }

                context.metadata["status_code"] = status_code
                context.metadata["response_headers"] = response_headers
                context.metadata["response_content_type"] = response_headers.get("content-type", "")

                is_html_response = "text/html" in response_headers.get("content-type", "")
                if not is_html_response:
                    await self.toolbar.process_response(context)
                    server_timing = self.toolbar.get_server_timing_header(context)
                    new_headers = list(original_headers)
                    if server_timing:
                        new_headers.append((b"server-timing", server_timing.encode()))
                    modified_msg: HTTPResponseStartEvent = {
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": new_headers,
                    }
                    await send(modified_msg)
                    headers_sent = True
                return

            if message["type"] == "http.response.body":
                body_msg = cast("HTTPResponseBodyEvent", message)
                body = body_msg.get("body", b"")

                if not is_html_response:
                    await send(message)
                    return

                response_body_chunks.append(body)

                if not body_msg.get("more_body", False):
                    await self.toolbar.process_response(context)

                    full_body = b"".join(response_body_chunks)
                    modified_body = self._inject_toolbar(full_body, context)

                    server_timing = self.toolbar.get_server_timing_header(context)

                    new_headers: list[tuple[bytes, bytes]] = [
                        (k.encode(), v.encode()) for k, v in response_headers.items() if k.lower() != "content-length"
                    ]
                    new_headers.append((b"content-length", str(len(modified_body)).encode()))
                    if server_timing:
                        new_headers.append((b"server-timing", server_timing.encode()))

                    start_event: HTTPResponseStartEvent = {
                        "type": "http.response.start",
                        "status": status_code,
                        "headers": new_headers,
                    }
                    await send(start_event)
                    body_event: HTTPResponseBodyEvent = {
                        "type": "http.response.body",
                        "body": modified_body,
                        "more_body": False,
                    }
                    await send(body_event)
                    headers_sent = True
                return

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            set_request_context(None)

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

    def _inject_toolbar(self, body: bytes, context: RequestContext) -> bytes:
        """Inject the toolbar HTML into the response body.

        Args:
            body: The original response body.
            context: The request context with collected data.

        Returns:
            The modified response body with toolbar injected.
        """
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
            pattern = re.compile(re.escape(insert_before), re.IGNORECASE)
            html = pattern.sub(toolbar_html + insert_before, html, count=1)

        return html.encode("utf-8")

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
