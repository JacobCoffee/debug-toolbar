"""CLI entry point for debug toolbar MCP server.

Run with:
    python -m debug_toolbar.mcp

Or with uv:
    uv run python -m debug_toolbar.mcp
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    """Run the debug toolbar MCP server."""
    parser = argparse.ArgumentParser(
        description="Debug Toolbar MCP Server - AI assistant integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default, for Claude Code)
  python -m debug_toolbar.mcp

  # Run with HTTP transport on custom port
  python -m debug_toolbar.mcp --transport http --port 8765

  # Disable sensitive data redaction (development only)
  python -m debug_toolbar.mcp --no-redact
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mechanism (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for HTTP transport (default: 8765)",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="Disable sensitive data redaction (development only)",
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=100,
        help="Maximum request history to store (default: 100)",
    )

    args = parser.parse_args()

    try:
        from debug_toolbar.mcp.server import is_available
    except ImportError:
        print("Error: debug_toolbar package not found", file=sys.stderr)  # noqa: T201
        return 1

    if not is_available():
        print(  # noqa: T201
            "Error: MCP support requires the 'mcp' package.\n"
            "Install with: pip install debug-toolbar[mcp]",
            file=sys.stderr,
        )
        return 1

    from debug_toolbar import DebugToolbar, DebugToolbarConfig
    from debug_toolbar.mcp import create_mcp_server

    config = DebugToolbarConfig(
        enabled=True,
        max_request_history=args.max_history,
    )
    toolbar = DebugToolbar(config)

    mcp = create_mcp_server(
        storage=toolbar.storage,
        toolbar=toolbar,
        redact_sensitive=not args.no_redact,
        server_name="debug-toolbar",
    )

    print(f"Starting debug-toolbar MCP server ({args.transport} transport)...", file=sys.stderr)  # noqa: T201

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="sse", host=args.host, port=args.port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
