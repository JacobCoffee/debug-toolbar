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
    {
        "mcpServers": {
            "debug-toolbar": {
                "command": "uv",
                "args": ["run", "python", "-m", "debug_toolbar.mcp"]
            }
        }
    }
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar import Litestar


def create_app() -> Litestar:
    """Create Litestar application with debug toolbar."""
    from litestar import Litestar, get, post

    from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

    config = LitestarDebugToolbarConfig(
        enabled=True,
        panels=[
            "debug_toolbar.core.panels.timer.TimerPanel",
            "debug_toolbar.core.panels.request.RequestPanel",
            "debug_toolbar.core.panels.response.ResponsePanel",
            "debug_toolbar.core.panels.headers.HeadersPanel",
            "debug_toolbar.core.panels.logging.LoggingPanel",
        ],
    )

    plugin = DebugToolbarPlugin(config=config)

    @get("/")
    async def index() -> dict:
        """Home endpoint."""
        return {
            "message": "Debug Toolbar + MCP Example",
            "endpoints": ["/", "/slow", "/error", "/api/data"],
            "mcp_info": "Run with --mcp flag to start MCP server",
        }

    @get("/slow")
    async def slow_endpoint() -> dict:
        """Simulates a slow endpoint for profiling."""
        await asyncio.sleep(0.5)
        return {"message": "This was slow", "delay_ms": 500}

    @get("/error")
    async def error_endpoint() -> dict:
        """Returns an error response (simulated via dict for simplicity)."""
        return {"error": "Something went wrong", "status": "error"}

    @get("/api/data")
    async def api_data() -> dict:
        """API endpoint returning sample data."""
        return {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
            "total": 2,
        }

    @post("/api/create")
    async def api_create(data: dict) -> dict:
        """API endpoint for creating data."""
        return {"created": True, "data": data}

    return Litestar(
        route_handlers=[index, slow_endpoint, error_endpoint, api_data, api_create],
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
