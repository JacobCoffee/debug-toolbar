"""Tests for MCP server module."""

from __future__ import annotations

import pytest

from debug_toolbar.mcp.server import MCPContext, is_available


class TestIsAvailable:
    """Tests for is_available function."""

    def test_returns_boolean(self) -> None:
        """Should return a boolean indicating MCP availability."""
        result = is_available()
        assert isinstance(result, bool)


class TestMCPContext:
    """Tests for MCPContext dataclass."""

    def test_creates_with_storage(self) -> None:
        """Should create context with storage."""
        from debug_toolbar.core.storage import ToolbarStorage

        storage = ToolbarStorage(max_size=10)
        ctx = MCPContext(storage=storage)

        assert ctx.storage is storage
        assert ctx.toolbar is None
        assert ctx.redact_sensitive is True

    def test_creates_with_toolbar(self) -> None:
        """Should create context with toolbar."""
        from debug_toolbar import DebugToolbar, DebugToolbarConfig

        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        ctx = MCPContext(storage=toolbar.storage, toolbar=toolbar)

        assert ctx.storage is toolbar.storage
        assert ctx.toolbar is toolbar

    def test_redact_sensitive_default_true(self) -> None:
        """Should default to redacting sensitive data."""
        from debug_toolbar.core.storage import ToolbarStorage

        storage = ToolbarStorage(max_size=10)
        ctx = MCPContext(storage=storage)

        assert ctx.redact_sensitive is True

    def test_redact_sensitive_can_be_disabled(self) -> None:
        """Should allow disabling sensitive data redaction."""
        from debug_toolbar.core.storage import ToolbarStorage

        storage = ToolbarStorage(max_size=10)
        ctx = MCPContext(storage=storage, redact_sensitive=False)

        assert ctx.redact_sensitive is False


@pytest.mark.skipif(not is_available(), reason="MCP package not installed")
class TestCreateMcpServer:
    """Tests for create_mcp_server function."""

    def test_creates_server_with_storage(self) -> None:
        """Should create MCP server with storage."""
        from debug_toolbar.core.storage import ToolbarStorage
        from debug_toolbar.mcp import create_mcp_server

        storage = ToolbarStorage(max_size=10)
        mcp = create_mcp_server(storage)

        assert mcp is not None
        assert mcp.name == "debug-toolbar"

    def test_creates_server_with_custom_name(self) -> None:
        """Should create MCP server with custom name."""
        from debug_toolbar.core.storage import ToolbarStorage
        from debug_toolbar.mcp import create_mcp_server

        storage = ToolbarStorage(max_size=10)
        mcp = create_mcp_server(storage, server_name="custom-toolbar")

        assert mcp.name == "custom-toolbar"

    def test_creates_server_with_toolbar(self) -> None:
        """Should create MCP server with full toolbar."""
        from debug_toolbar import DebugToolbar, DebugToolbarConfig
        from debug_toolbar.mcp import create_mcp_server

        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        mcp = create_mcp_server(toolbar.storage, toolbar)

        assert mcp is not None


class TestMcpNotAvailable:
    """Tests for when MCP is not available."""

    def test_import_error_message(self) -> None:
        """Should provide helpful import error message."""
        if is_available():
            pytest.skip("MCP is available")

        from debug_toolbar.core.storage import ToolbarStorage
        from debug_toolbar.mcp import create_mcp_server

        storage = ToolbarStorage(max_size=10)

        with pytest.raises(ImportError) as exc_info:
            create_mcp_server(storage)

        assert "mcp" in str(exc_info.value).lower()
        assert "pip install" in str(exc_info.value)
