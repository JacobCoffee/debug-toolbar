"""MCP (Model Context Protocol) server for debug toolbar.

This module provides AI assistant integration for the debug toolbar,
allowing tools like Claude Code and Cursor to access debug data.

Example:
    ```python
    from debug_toolbar import DebugToolbar, DebugToolbarConfig
    from debug_toolbar.mcp import create_mcp_server, is_available

    if is_available():
        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)

        mcp = create_mcp_server(toolbar.storage, toolbar)
        mcp.run()  # Run with stdio transport
    ```

To run as a standalone server:
    ```bash
    python -m debug_toolbar.mcp --storage-path /path/to/storage.json
    ```
"""

from __future__ import annotations

from debug_toolbar.mcp.server import create_mcp_server, is_available

__all__ = [
    "create_mcp_server",
    "is_available",
]
