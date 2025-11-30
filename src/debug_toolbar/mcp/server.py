"""MCP server for debug toolbar integration with AI assistants."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from debug_toolbar.core.storage import ToolbarStorage
    from debug_toolbar.core.toolbar import DebugToolbar

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None  # type: ignore[assignment, misc]


@dataclass
class MCPContext:
    """Context holding debug toolbar resources for MCP tools."""

    storage: ToolbarStorage
    toolbar: DebugToolbar | None = None
    redact_sensitive: bool = True


def create_mcp_server(
    storage: ToolbarStorage,
    toolbar: DebugToolbar | None = None,
    *,
    redact_sensitive: bool = True,
    server_name: str = "debug-toolbar",
) -> FastMCP:
    """Create an MCP server for debug toolbar data.

    Args:
        storage: The toolbar storage instance containing request data.
        toolbar: Optional DebugToolbar instance for additional features.
        redact_sensitive: Whether to redact sensitive data (default True).
        server_name: Name for the MCP server.

    Returns:
        Configured FastMCP server instance.

    Raises:
        ImportError: If mcp package is not installed.

    Example:
        ```python
        from debug_toolbar import DebugToolbar, DebugToolbarConfig
        from debug_toolbar.mcp import create_mcp_server

        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)

        mcp = create_mcp_server(toolbar.storage, toolbar)
        mcp.run()  # Run with stdio transport
        ```
    """
    if not MCP_AVAILABLE:
        msg = "MCP support requires the 'mcp' package. Install with: pip install debug-toolbar[mcp]"
        raise ImportError(msg)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[MCPContext]:
        """Manage MCP server lifecycle with debug toolbar context."""
        logger.info("Starting debug-toolbar MCP server")
        ctx = MCPContext(
            storage=storage,
            toolbar=toolbar,
            redact_sensitive=redact_sensitive,
        )
        try:
            yield ctx
        finally:
            logger.info("Shutting down debug-toolbar MCP server")

    mcp = FastMCP(
        server_name,
        lifespan=lifespan,
    )

    from debug_toolbar.mcp.resources import register_resources
    from debug_toolbar.mcp.tools import register_tools

    register_tools(mcp)
    register_resources(mcp)

    return mcp


def is_available() -> bool:
    """Check if MCP support is available.

    Returns:
        True if mcp package is installed.
    """
    return MCP_AVAILABLE
