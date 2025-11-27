"""Basic Litestar application with debug toolbar.

This example demonstrates using debug-toolbar
with a simple Litestar application.

Run with: litestar --app examples.litestar_basic.app:app run --reload
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from litestar import Litestar, MediaType, get

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@get("/", media_type=MediaType.HTML)
async def index() -> str:
    """Home page."""
    logger.info("Home page accessed")
    return """<!DOCTYPE html>
<html>
<head><title>Litestar Debug Toolbar Example</title></head>
<body>
    <h1>Litestar Debug Toolbar Example</h1>
    <p>Welcome to the Litestar debug toolbar demo!</p>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/users">Users</a></li>
        <li><a href="/api/status">API Status (JSON)</a></li>
    </ul>
    <p>The debug toolbar should appear at the bottom of this page.</p>
</body>
</html>"""


@get("/about", media_type=MediaType.HTML)
async def about() -> str:
    """About page."""
    logger.info("About page accessed")
    logger.debug("Debug message from about page")
    return """<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About</h1>
    <p>This is a simple Litestar application demonstrating the debug toolbar.</p>
    <p>Features:</p>
    <ul>
        <li>Timer Panel - Request timing</li>
        <li>Request Panel - Request details</li>
        <li>Response Panel - Response info</li>
        <li>Logging Panel - Captured logs</li>
        <li>Versions Panel - Environment info</li>
        <li>Routes Panel - Litestar routes</li>
    </ul>
    <a href="/">Back to Home</a>
</body>
</html>"""


@get("/users", media_type=MediaType.HTML)
async def users() -> str:
    """Users page with some simulated data."""
    logger.info("Users page accessed")
    user_list = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]

    rows = "".join(f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['email']}</td></tr>" for u in user_list)

    return f"""<!DOCTYPE html>
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


@get("/api/status", media_type=MediaType.JSON)
async def api_status() -> dict:
    """API status endpoint."""
    logger.info("API status requested")
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": "1.0.0",
    }


toolbar_config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
)

app = Litestar(
    route_handlers=[index, about, users, api_status],
    plugins=[DebugToolbarPlugin(toolbar_config)],
    debug=True,
)
