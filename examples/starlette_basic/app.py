"""Basic Starlette application with debug toolbar.

This example demonstrates using debug-toolbar with a simple Starlette application.

Run with:
    uvicorn examples.starlette_basic.app:app --reload

Then visit:
    http://localhost:8000/
    http://localhost:8000/about
    http://localhost:8000/users
    http://localhost:8000/api/status
    http://localhost:8000/_debug_toolbar/  (request history)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from debug_toolbar.core.toolbar import DebugToolbar
from debug_toolbar.starlette import (
    DebugToolbarMiddleware,
    StarletteDebugToolbarConfig,
    create_debug_toolbar_routes,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def homepage(request):
    """Home page."""
    logger.info("Home page accessed")
    html = f"""<!DOCTYPE html>
<html>
<head><title>Starlette Debug Toolbar Example</title></head>
<body>
    <h1>Starlette Debug Toolbar Example</h1>
    <p>Welcome to the Starlette debug toolbar demo!</p>
    <p>Current time: {datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/users">Users</a></li>
        <li><a href="/api/status">API Status (JSON)</a></li>
    </ul>
    <p>The debug toolbar should appear on the right side of this page.</p>
    <p><a href="/_debug_toolbar/">View Request History</a></p>
</body>
</html>"""
    return HTMLResponse(html)


async def about(request):
    """About page."""
    logger.info("About page accessed")
    html = """<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About</h1>
    <p>This is a simple Starlette application demonstrating the debug toolbar.</p>
    <h2>Core Panels</h2>
    <ul>
        <li>Timer Panel - Request timing</li>
        <li>Request Panel - Request details</li>
        <li>Response Panel - Response info</li>
        <li>Logging Panel - Captured logs</li>
        <li>Versions Panel - Environment info</li>
        <li>Routes Panel - Starlette routes</li>
    </ul>
    <a href="/">Back to Home</a>
</body>
</html>"""
    return HTMLResponse(html)


async def users(request):
    """Users page."""
    logger.info("Users page accessed")
    user_list = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]

    rows = "".join(
        f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['email']}</td></tr>" for u in user_list
    )

    html = f"""<!DOCTYPE html>
<html>
<head><title>Users</title></head>
<body>
    <h1>Users</h1>
    <table border="1">
        <thead><tr><th>ID</th><th>Name</th><th>Email</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <a href="/">Back to Home</a>
</body>
</html>"""
    return HTMLResponse(html)


async def api_status(request):
    """API status endpoint."""
    logger.info("API status requested")
    return JSONResponse(
        {
            "status": "ok",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "version": "1.0.0",
        }
    )


toolbar_config = StarletteDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
)

toolbar = DebugToolbar(toolbar_config)
debug_routes = create_debug_toolbar_routes(toolbar.storage)

routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Route("/users", endpoint=users),
    Route("/api/status", endpoint=api_status),
    *debug_routes,
]

app = Starlette(
    debug=True,
    routes=routes,
    middleware=[
        Middleware(DebugToolbarMiddleware, config=toolbar_config, toolbar=toolbar),
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
