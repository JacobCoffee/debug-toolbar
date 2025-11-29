"""Basic Litestar application with debug toolbar.

This example demonstrates using debug-toolbar
with a simple Litestar application, including the new Phase 10 panels:
- Headers Panel: HTTP header inspection
- Settings Panel: Application configuration viewer
- Profiling Panel: Request profiling (optional)
- Templates Panel: Template rendering tracking (with Jinja2)
- Alerts Panel: Proactive issue detection (security, performance, database)

UI Features:
- Toolbar position: Click the arrow buttons to move the toolbar (left/right/top/bottom)
- Request history: Visit /_debug_toolbar/ to see all recorded requests
- Panel details: Click panel buttons to expand and view detailed data

Run with: litestar --app examples.litestar_basic.app:app run --reload
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from jinja2 import Template

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from litestar import Litestar, MediaType, get

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

INDEX_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head><title>Litestar Debug Toolbar Example</title></head>
<body>
    <h1>Litestar Debug Toolbar Example</h1>
    <p>Welcome to the Litestar debug toolbar demo!</p>
    <p>Current time: {{ current_time }}</p>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/users">Users</a></li>
        <li><a href="/alerts-demo">Alerts Demo</a></li>
        <li><a href="/api/status">API Status (JSON)</a></li>
    </ul>
    <h2>New Phase 10 Panels</h2>
    <ul>
        <li><strong>Headers Panel</strong> - Inspect request/response headers, security analysis</li>
        <li><strong>Settings Panel</strong> - View toolbar and app configuration</li>
        <li><strong>Templates Panel</strong> - Track Jinja2 template render times</li>
        <li><strong>Profiling Panel</strong> - Profile request execution (optional)</li>
        <li><strong>Alerts Panel</strong> - Proactive detection of security, performance, and configuration issues</li>
    </ul>
    <p>The debug toolbar should appear on the right side of this page (default position).</p>
    <p>Use the arrow buttons in the toolbar to move it to left/right/top/bottom.</p>
    <p><a href="/_debug_toolbar/">View Request History</a></p>
</body>
</html>""")


@get("/", media_type=MediaType.HTML)
async def index() -> str:
    """Home page - demonstrates Templates Panel tracking Jinja2 renders."""
    logger.info("Home page accessed")
    return INDEX_TEMPLATE.render(current_time=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))


ABOUT_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head><title>About</title></head>
<body>
    <h1>About</h1>
    <p>This is a simple Litestar application demonstrating the debug toolbar.</p>
    <h2>Core Panels</h2>
    <ul>
        <li>Timer Panel - Request timing</li>
        <li>Request Panel - Request details</li>
        <li>Response Panel - Response info</li>
        <li>Logging Panel - Captured logs</li>
        <li>Versions Panel - Environment info</li>
        <li>Routes Panel - Litestar routes</li>
    </ul>
    <h2>Phase 10 Panels (New!)</h2>
    <ul>
        <li><strong>Headers Panel</strong> - Detailed HTTP header inspection with security analysis</li>
        <li><strong>Settings Panel</strong> - Application configuration viewer with sensitive data redaction</li>
        <li><strong>Templates Panel</strong> - Track Jinja2/Mako template rendering times</li>
        <li><strong>Profiling Panel</strong> - cProfile/pyinstrument request profiling</li>
        <li><strong>Alerts Panel</strong> - Proactive detection of security, performance, and configuration issues</li>
        <li><strong>Cache Panel</strong> - Redis/memcached operation tracking (when configured)</li>
    </ul>
    <a href="/">Back to Home</a>
</body>
</html>""")


@get("/about", media_type=MediaType.HTML)
async def about() -> str:
    """About page - demonstrates Templates Panel with another template."""
    logger.info("About page accessed")
    logger.debug("Debug message from about page")
    return ABOUT_TEMPLATE.render()


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


@get("/alerts-demo", media_type=MediaType.HTML)
async def alerts_demo() -> str:
    """Alerts demonstration page - deliberately triggers some alerts."""
    logger.info("Alerts demo page accessed")
    logger.warning("This page demonstrates the Alerts Panel by triggering warnings")

    return """<!DOCTYPE html>
<html>
<head><title>Alerts Demo</title></head>
<body>
    <h1>Alerts Panel Demo</h1>
    <p>This page is designed to trigger alerts in the debug toolbar.</p>
    <p>Check the <strong>Alerts Panel</strong> in the debug toolbar to see warnings about:</p>
    <ul>
        <li>Missing security headers (Content-Security-Policy, X-Content-Type-Options, etc.)</li>
        <li>Debug mode enabled (since this app runs with debug=True)</li>
        <li>Potential CSRF protection issues</li>
    </ul>
    <p>The Alerts Panel proactively detects:</p>
    <ul>
        <li><strong>Security issues:</strong> Missing headers, insecure cookies, CSRF vulnerabilities</li>
        <li><strong>Performance problems:</strong> Large responses, slow queries</li>
        <li><strong>Database issues:</strong> N+1 queries, slow queries</li>
        <li><strong>Configuration problems:</strong> Debug mode in production, missing settings</li>
    </ul>
    <p><em>Note: This demo runs with debug=True and minimal security headers, so you should see several alerts!</em></p>
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
    extra_panels=[
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.core.panels.settings.SettingsPanel",
        "debug_toolbar.core.panels.templates.TemplatesPanel",
        "debug_toolbar.core.panels.alerts.AlertsPanel",
    ],
)

app = Litestar(
    route_handlers=[index, about, users, alerts_demo, api_status],
    plugins=[DebugToolbarPlugin(toolbar_config)],
    debug=True,
)
