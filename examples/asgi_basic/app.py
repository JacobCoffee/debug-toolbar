"""Basic ASGI application with debug-toolbar.

This example demonstrates using the core debug-toolbar
with a plain ASGI application, without any framework.

Run with: uvicorn examples.asgi_basic.app:app --reload
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from debug_toolbar import DebugToolbar, DebugToolbarConfig, set_request_context

if TYPE_CHECKING:
    from collections.abc import Callable


config = DebugToolbarConfig(
    enabled=True,
    max_request_history=50,
)
toolbar = DebugToolbar(config)


async def debug_toolbar_middleware(inner_app: Callable, scope: dict, receive: Callable, send: Callable) -> None:
    """Simple ASGI middleware that integrates the debug toolbar."""
    if scope["type"] != "http":
        await inner_app(scope, receive, send)
        return

    path = scope.get("path", "/")
    if path.startswith("/_debug_toolbar"):
        await handle_debug_toolbar_request(scope, receive, send)
        return

    context = await toolbar.process_request()

    context.metadata["method"] = scope.get("method", "GET")
    context.metadata["path"] = path
    context.metadata["query_string"] = scope.get("query_string", b"").decode()

    response_started = False
    status_code = 200
    response_headers: list[tuple[bytes, bytes]] = []

    async def send_wrapper(message: dict) -> None:
        nonlocal response_started, status_code, response_headers

        if message["type"] == "http.response.start":
            response_started = True
            status_code = message.get("status", 200)
            response_headers = list(message.get("headers", []))

            context.metadata["status_code"] = status_code
            await toolbar.process_response(context)

            server_timing = toolbar.get_server_timing_header(context)
            if server_timing:
                response_headers.append((b"server-timing", server_timing.encode()))

            message = {**message, "headers": response_headers}

        await send(message)

    try:
        await inner_app(scope, receive, send_wrapper)
    finally:
        set_request_context(None)


async def handle_debug_toolbar_request(
    scope: dict,
    receive: Callable,  # noqa: ARG001
    send: Callable,
) -> None:
    """Handle debug toolbar API requests."""
    path = scope.get("path", "")

    if path == "/_debug_toolbar/requests":
        requests_list = []
        for rid in toolbar.storage.get_request_ids():
            ctx = toolbar.storage.get_context(rid)
            if ctx:
                requests_list.append({
                    "request_id": rid,
                    "method": ctx.metadata.get("method", ""),
                    "path": ctx.metadata.get("path", ""),
                })
        body = json.dumps(requests_list).encode()
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": body})
        return

    if path.startswith("/_debug_toolbar/request/"):
        request_id = path.split("/")[-1]
        ctx = toolbar.storage.get_context(request_id)
        if ctx:
            stats = toolbar.storage.get_stats(request_id)
            body = json.dumps({"request_id": request_id, "stats": stats}).encode()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({"type": "http.response.body", "body": body})
            return

    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b"Not Found"})


async def application(scope: dict, receive: Callable, send: Callable) -> None:  # noqa: ARG001
    """Simple ASGI application."""
    if scope["type"] != "http":
        return

    path = scope.get("path", "/")

    if path == "/":
        body = b"""<!DOCTYPE html>
<html>
<head><title>ASGI Debug Toolbar Example</title></head>
<body>
    <h1>ASGI Debug Toolbar Example</h1>
    <p>This is a basic ASGI app with the debug-toolbar.</p>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/api/data">API Data</a></li>
        <li><a href="/_debug_toolbar/requests">Debug Toolbar Requests</a></li>
    </ul>
</body>
</html>"""
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/html")],
        })
        await send({"type": "http.response.body", "body": body})

    elif path == "/about":
        body = b"""<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About</h1>
    <p>This example shows the framework-agnostic core of debug-toolbar.</p>
    <a href="/">Back to Home</a>
</body>
</html>"""
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/html")],
        })
        await send({"type": "http.response.body", "body": body})

    elif path == "/api/data":
        data = {"message": "Hello from the API", "items": [1, 2, 3]}
        body = json.dumps(data).encode()
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": body})

    else:
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"Not Found"})


async def app(scope: dict, receive: Callable, send: Callable) -> None:
    """ASGI app with debug toolbar middleware."""
    await debug_toolbar_middleware(application, scope, receive, send)
