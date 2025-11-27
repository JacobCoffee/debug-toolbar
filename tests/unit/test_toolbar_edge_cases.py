"""Edge case tests for toolbar and related modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig
from debug_toolbar.core.context import set_request_context

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class TestDebugToolbarImportErrors:
    """Tests for panel import error handling."""

    def test_invalid_panel_import_path(self) -> None:
        """Test handling of invalid panel import paths."""
        config = DebugToolbarConfig(
            panels=["nonexistent.module.Panel"],
        )
        toolbar = DebugToolbar(config)
        # Should not raise, but panel won't be loaded
        assert len(toolbar.panels) == 0

    def test_invalid_panel_class_name(self) -> None:
        """Test handling of valid module but invalid class."""
        config = DebugToolbarConfig(
            panels=["debug_toolbar.core.panel.NonexistentPanel"],
        )
        toolbar = DebugToolbar(config)
        assert len(toolbar.panels) == 0

    def test_malformed_import_path(self) -> None:
        """Test handling of malformed import path."""
        config = DebugToolbarConfig(
            panels=["no_dot_in_path"],
        )
        toolbar = DebugToolbar(config)
        assert len(toolbar.panels) == 0


class TestToolbarContextHandling:
    """Tests for toolbar context edge cases."""

    @pytest.mark.asyncio
    async def test_process_response_with_none_context(self) -> None:
        """Test process_response when context is None."""
        set_request_context(None)
        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        # Should not raise
        await toolbar.process_response(None)

    @pytest.mark.asyncio
    async def test_process_response_with_no_start_time(self) -> None:
        """Test process_response when no start time recorded."""
        from debug_toolbar import RequestContext

        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        # Create context without going through process_request
        context = RequestContext()
        # Should handle missing start time gracefully
        await toolbar.process_response(context)

    def test_get_server_timing_header_no_context(self) -> None:
        """Test get_server_timing_header with no context."""
        set_request_context(None)
        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        result = toolbar.get_server_timing_header(None)
        assert result == ""

    def test_get_toolbar_data_no_context(self) -> None:
        """Test get_toolbar_data with no context."""
        set_request_context(None)
        config = DebugToolbarConfig()
        toolbar = DebugToolbar(config)
        result = toolbar.get_toolbar_data(None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_server_timing_with_panel_timing(self, context: RequestContext) -> None:
        """Test server timing includes panel timing."""
        config = DebugToolbarConfig(panels=["debug_toolbar.core.panels.timer.TimerPanel"])
        toolbar = DebugToolbar(config)
        ctx = await toolbar.process_request()
        await toolbar.process_response(ctx)
        timing = toolbar.get_server_timing_header(ctx)
        assert "total" in timing


class TestToolbarPanelAccess:
    """Tests for panel access."""

    def test_enabled_panels_filters_disabled(self) -> None:
        """Test enabled_panels property filters disabled panels."""
        config = DebugToolbarConfig(panels=["debug_toolbar.core.panels.timer.TimerPanel"])
        toolbar = DebugToolbar(config)
        assert len(toolbar.enabled_panels) == 1
        # Disable the panel
        toolbar.panels[0].enabled = False
        assert len(toolbar.enabled_panels) == 0
