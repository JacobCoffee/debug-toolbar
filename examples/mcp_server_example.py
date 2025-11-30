# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "debug-toolbar[litestar,mcp]",
#   "uvicorn>=0.30.0",
# ]
# ///
"""Debug Toolbar with MCP Server for AI Assistant Integration.

This example demonstrates:
1. Running the debug toolbar with a Litestar web app
2. Running a standalone MCP server for AI assistant integration

Usage:
    # Run the web app (generates debug data)
    make example-mcp
    # or: uv run python examples/mcp_server_example.py

    # Run standalone MCP server (for Claude Code integration)
    make example-mcp-server
    # or: uv run python examples/mcp_server_example.py --mcp

Integration with Claude Code:
    Add to your .claude/settings.json:
    {{
        "mcpServers": {{
            "debug-toolbar": {{
                "command": "uv",
                "args": ["run", "python", "-m", "debug_toolbar.mcp"]
            }}
        }}
    }}
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar import Litestar

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

COMMON_CSS = """
:root {{
    --bg-primary: #ffffff;
    --bg-secondary: #f5f5f5;
    --bg-tertiary: #f9f9f9;
    --text-primary: #333333;
    --text-secondary: #666666;
    --accent: #0066cc;
    --border: #dddddd;
    --code-bg: #e8e8e8;
    --pre-bg: #2d2d2d;
    --pre-text: #f8f8f2;
    --success-bg: #d4edda;
    --success-border: #28a745;
    --warning-bg: #fff3cd;
    --warning-border: #ffc107;
    --error-bg: #f8d7da;
    --error-border: #dc3545;
    --danger: #dc3545;
}}
@media (prefers-color-scheme: dark) {{
    :root {{
        --bg-primary: #1a1a2e;
        --bg-secondary: #16213e;
        --bg-tertiary: #0f3460;
        --text-primary: #e8e8e8;
        --text-secondary: #a0a0a0;
        --accent: #4da6ff;
        --border: #404040;
        --code-bg: #2d2d2d;
        --pre-bg: #0d0d0d;
        --pre-text: #f8f8f2;
        --success-bg: #1e3a2f;
        --success-border: #28a745;
        --warning-bg: #3d3a1e;
        --warning-border: #ffc107;
        --error-bg: #3a1e1e;
        --error-border: #dc3545;
        --danger: #ff6b6b;
    }}
}}
body {{
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
}}
h1, h2 {{ color: var(--text-primary); }}
a {{ color: var(--accent); }}
.nav {{
    background: var(--bg-secondary);
    padding: 15px;
    border-radius: 8px;
    margin: 20px 0;
}}
.nav a {{
    margin-right: 15px;
    color: var(--accent);
    text-decoration: none;
}}
.nav a:hover {{ text-decoration: underline; }}
.section {{
    margin: 25px 0;
    padding: 15px;
    border-left: 4px solid var(--accent);
    background: var(--bg-tertiary);
    border-radius: 0 8px 8px 0;
}}
code {{
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 14px;
}}
pre {{
    background: var(--pre-bg);
    color: var(--pre-text);
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}}
th, td {{
    border: 1px solid var(--border);
    padding: 12px;
    text-align: left;
}}
th {{ background: var(--bg-secondary); }}
tr:hover {{ background: var(--bg-tertiary); }}
.tools-list {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 10px;
}}
.tool {{
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    padding: 10px;
    border-radius: 6px;
}}
.tool strong {{ color: var(--accent); }}
.timestamp {{ color: var(--text-secondary); font-size: 14px; }}
.warning {{
    background: var(--warning-bg);
    border: 1px solid var(--warning-border);
    padding: 15px;
    border-radius: 8px;
}}
.metric {{ font-size: 48px; font-weight: bold; color: var(--danger); }}
.result {{
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    padding: 15px;
    border-radius: 8px;
}}
.error {{
    background: var(--error-bg);
    border: 1px solid var(--error-border);
    padding: 15px;
    border-radius: 8px;
}}
"""

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Example - Debug Toolbar</title>
    <style>{css}</style>
</head>
<body>
    <h1>Debug Toolbar + MCP Server Example</h1>
    <p class="timestamp">Server time: {timestamp}</p>

    <div class="nav">
        <a href="/">Home</a>
        <a href="/slow">Slow Page (500ms)</a>
        <a href="/users">Users</a>
        <a href="/compute">CPU Intensive</a>
        <a href="/error-demo">Error Demo</a>
        <a href="/api/data">API Data (JSON)</a>
        <a href="/_debug_toolbar/">Request History</a>
    </div>

    <div class="section">
        <h2>About This Example</h2>
        <p>This example demonstrates the <strong>MCP (Model Context Protocol) Server</strong> integration
        for the debug toolbar. It allows AI assistants like Claude Code to analyze your application's
        debug data programmatically.</p>
    </div>

    <div class="section">
        <h2>MCP Tools Available</h2>
        <div class="tools-list">
            <div class="tool"><strong>get_request_history</strong><br>List all tracked HTTP requests</div>
            <div class="tool"><strong>get_request_details</strong><br>Get detailed info for a request</div>
            <div class="tool"><strong>analyze_performance_bottlenecks</strong><br>Find slow operations</div>
            <div class="tool"><strong>detect_n_plus_one_queries</strong><br>Find N+1 query patterns</div>
            <div class="tool"><strong>analyze_security_alerts</strong><br>Security issue detection</div>
            <div class="tool"><strong>compare_requests</strong><br>Compare two requests</div>
            <div class="tool"><strong>generate_optimization_report</strong><br>Full optimization report</div>
            <div class="tool"><strong>get_panel_data</strong><br>Get specific panel data</div>
        </div>
    </div>

    <div class="section">
        <h2>Claude Code Integration</h2>
        <p>Add to your <code>.claude/settings.json</code>:</p>
        <pre>{{
  "mcpServers": {{
    "debug-toolbar": {{
      "command": "uv",
      "args": ["run", "python", "-m", "debug_toolbar.mcp"]
    }}
  }}
}}</pre>
    </div>

    <div class="section">
        <h2>Try These Scenarios</h2>
        <ol>
            <li><strong>Click around</strong> - Visit different pages to generate request history</li>
            <li><strong>Check the toolbar</strong> - See timing, headers, logs for each request</li>
            <li><strong>View history</strong> - Go to <a href="/_debug_toolbar/">/_debug_toolbar/</a></li>
            <li><strong>Test MCP</strong> - Run <code>make example-mcp-server</code> in another terminal</li>
        </ol>
    </div>

    <p><em>The debug toolbar should appear on the right side of this page.</em></p>
</body>
</html>"""

SLOW_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Slow Page - Debug Toolbar</title>
    <style>{css}</style>
</head>
<body>
    <h1>Slow Page</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/slow">Slow Page</a>
        <a href="/users">Users</a>
        <a href="/compute">CPU Intensive</a>
        <a href="/_debug_toolbar/">Request History</a>
    </div>

    <div class="warning">
        <p class="metric">{delay_ms}ms</p>
        <p>This page intentionally delayed for <strong>{delay_ms} milliseconds</strong>
        to demonstrate performance profiling.</p>
        <p>Check the <strong>Timer Panel</strong> in the debug toolbar to see the timing breakdown.</p>
    </div>

    <h2>What to Look For</h2>
    <ul>
        <li><strong>Timer Panel</strong> - Shows total request time exceeds 500ms</li>
        <li><strong>Alerts Panel</strong> - May show performance warnings</li>
        <li><strong>MCP Analysis</strong> - <code>analyze_performance_bottlenecks</code> will flag this</li>
    </ul>

    <p><a href="/">Back to Home</a></p>
</body>
</html>"""

USERS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Users - Debug Toolbar</title>
    <style>{css}</style>
</head>
<body>
    <h1>Users</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/slow">Slow Page</a>
        <a href="/users">Users</a>
        <a href="/compute">CPU Intensive</a>
        <a href="/_debug_toolbar/">Request History</a>
    </div>

    <table>
        <thead>
            <tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th></tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <p>This page demonstrates a typical data display. In a real app with a database,
    the <strong>SQLAlchemy Panel</strong> would show queries here.</p>

    <p><a href="/">Back to Home</a></p>
</body>
</html>"""

COMPUTE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>CPU Intensive - Debug Toolbar</title>
    <style>{css}</style>
</head>
<body>
    <h1>CPU Intensive Computation</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/slow">Slow Page</a>
        <a href="/users">Users</a>
        <a href="/compute">CPU Intensive</a>
        <a href="/_debug_toolbar/">Request History</a>
    </div>

    <div class="result">
        <p><strong>Fibonacci({n}) = {result}</strong></p>
        <p>Computed in approximately <strong>{time_ms:.2f}ms</strong></p>
    </div>

    <h2>What to Look For</h2>
    <ul>
        <li><strong>Profiling Panel</strong> - Shows CPU time spent in computation</li>
        <li><strong>Async Profiler Panel</strong> - Shows this was synchronous (blocking) work</li>
        <li><strong>Flame Graph</strong> - Download from <code>/_debug_toolbar/api/flamegraph/{{request_id}}</code></li>
    </ul>

    <p><a href="/">Back to Home</a></p>
</body>
</html>"""

ERROR_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Error Demo - Debug Toolbar</title>
    <style>{css}</style>
</head>
<body>
    <h1>Error Demo</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/slow">Slow Page</a>
        <a href="/users">Users</a>
        <a href="/compute">CPU Intensive</a>
        <a href="/_debug_toolbar/">Request History</a>
    </div>

    <div class="error">
        <h2>Simulated Error Response</h2>
        <p>This page returns successfully but represents an error scenario.</p>
        <p>In a real application, check the <strong>Logging Panel</strong> for error logs.</p>
    </div>

    <p><a href="/">Back to Home</a></p>
</body>
</html>"""


def create_app() -> Litestar:
    """Create Litestar application with debug toolbar."""
    import time

    from litestar import Litestar, MediaType, get, post

    from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

    config = LitestarDebugToolbarConfig(
        enabled=True,
        panels=[
            "debug_toolbar.core.panels.timer.TimerPanel",
            "debug_toolbar.core.panels.request.RequestPanel",
            "debug_toolbar.core.panels.response.ResponsePanel",
            "debug_toolbar.core.panels.headers.HeadersPanel",
            "debug_toolbar.core.panels.logging.LoggingPanel",
            "debug_toolbar.core.panels.profiling.ProfilingPanel",
            "debug_toolbar.core.panels.alerts.AlertsPanel",
        ],
    )

    plugin = DebugToolbarPlugin(config=config)

    @get("/", media_type=MediaType.HTML)
    async def index() -> str:
        """Home page with MCP documentation."""
        logger.info("Home page accessed")
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return INDEX_HTML.format(css=COMMON_CSS, timestamp=timestamp)

    @get("/slow", media_type=MediaType.HTML)
    async def slow_endpoint() -> str:
        """Simulates a slow endpoint for profiling."""
        logger.info("Slow endpoint accessed - waiting 500ms")
        await asyncio.sleep(0.5)
        logger.warning("Slow endpoint completed after delay")
        return SLOW_HTML.format(css=COMMON_CSS, delay_ms=500)

    @get("/users", media_type=MediaType.HTML)
    async def users_page() -> str:
        """Users listing page."""
        logger.info("Users page accessed")
        users = [
            {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "Admin"},
            {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "User"},
            {"id": 3, "name": "Charlie Brown", "email": "charlie@example.com", "role": "User"},
            {"id": 4, "name": "Diana Prince", "email": "diana@example.com", "role": "Moderator"},
        ]
        rows = "\n".join(
            f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['email']}</td><td>{u['role']}</td></tr>"
            for u in users
        )
        return USERS_HTML.format(css=COMMON_CSS, rows=rows)

    @get("/compute", media_type=MediaType.HTML)
    async def compute_endpoint() -> str:
        """CPU-intensive computation for profiling."""
        logger.info("Compute endpoint accessed - running fibonacci")

        def fib(n: int) -> int:
            if n <= 1:
                return n
            return fib(n - 1) + fib(n - 2)

        n = 30
        start = time.perf_counter()
        result = fib(n)
        elapsed = (time.perf_counter() - start) * 1000

        logger.info(f"Fibonacci({n}) = {result} computed in {elapsed:.2f}ms")
        return COMPUTE_HTML.format(css=COMMON_CSS, n=n, result=result, time_ms=elapsed)

    @get("/error-demo", media_type=MediaType.HTML)
    async def error_demo() -> str:
        """Error demonstration page."""
        logger.error("Error demo page accessed - simulating error scenario")
        logger.warning("This is a warning message")
        return ERROR_HTML.format(css=COMMON_CSS)

    @get("/api/data")
    async def api_data() -> dict:
        """API endpoint returning sample data."""
        logger.info("API data endpoint accessed")
        return {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
            "total": 2,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    @post("/api/create")
    async def api_create(data: dict) -> dict:
        """API endpoint for creating data."""
        logger.info(f"API create endpoint accessed with data: {data}")
        return {"created": True, "data": data}

    return Litestar(
        route_handlers=[index, slow_endpoint, users_page, compute_endpoint, error_demo, api_data, api_create],
        plugins=[plugin],
        debug=True,
    )


def run_mcp_server(transport: str = "stdio") -> None:
    """Run standalone MCP server for AI assistant integration."""
    from debug_toolbar import DebugToolbar, DebugToolbarConfig
    from debug_toolbar.mcp import create_mcp_server, is_available

    if not is_available():
        print("Error: MCP support requires the 'mcp' package.", file=sys.stderr)  # noqa: T201
        print("Install with: pip install debug-toolbar[mcp]", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    config = DebugToolbarConfig(enabled=True, max_request_history=100)
    toolbar = DebugToolbar(config)

    mcp = create_mcp_server(
        storage=toolbar.storage,
        toolbar=toolbar,
        redact_sensitive=True,
        server_name="debug-toolbar-example",
    )

    print(f"Starting MCP server ({transport} transport)...", file=sys.stderr)  # noqa: T201
    print("", file=sys.stderr)  # noqa: T201
    print("Available tools:", file=sys.stderr)  # noqa: T201
    print("  - get_request_history: List tracked requests", file=sys.stderr)  # noqa: T201
    print("  - analyze_performance_bottlenecks: Find slow operations", file=sys.stderr)  # noqa: T201
    print("  - detect_n_plus_one_queries: Find N+1 patterns", file=sys.stderr)  # noqa: T201
    print("  - analyze_security_alerts: Security analysis", file=sys.stderr)  # noqa: T201
    print("  - compare_requests: Compare two requests", file=sys.stderr)  # noqa: T201
    print("  - generate_optimization_report: Full optimization report", file=sys.stderr)  # noqa: T201
    print("", file=sys.stderr)  # noqa: T201

    print(f"Listening on {transport}...", file=sys.stderr)  # noqa: T201
    mcp.run(transport=transport)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Debug Toolbar + MCP Server Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run web app (port 8004)
  make example-mcp

  # Run MCP server (stdio for Claude Code)
  make example-mcp-server

  # Or using the module directly:
  python -m debug_toolbar.mcp

Integration with Claude Code:
  Add to your .claude/settings.json:
  {
    "mcpServers": {
      "debug-toolbar": {
        "command": "uv",
        "args": ["run", "python", "-m", "debug_toolbar.mcp"]
      }
    }
  }
        """,
    )

    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run MCP server instead of web app",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8004,
        help="Port for web app (default: 8004)",
    )

    args = parser.parse_args()

    if args.mcp:
        run_mcp_server(args.transport)
    else:
        import uvicorn

        print(f"Starting web app on http://127.0.0.1:{args.web_port}", file=sys.stderr)  # noqa: T201
        print("", file=sys.stderr)  # noqa: T201
        print("Debug toolbar available at /_debug_toolbar", file=sys.stderr)  # noqa: T201
        print("", file=sys.stderr)  # noqa: T201

        app = create_app()
        uvicorn.run(app, host="127.0.0.1", port=args.web_port)


if __name__ == "__main__":
    main()
