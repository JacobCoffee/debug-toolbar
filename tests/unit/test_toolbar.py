"""Tests for the toolbar module."""

from __future__ import annotations

import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig
from debug_toolbar.core.context import get_request_context, set_request_context


class TestDebugToolbar:
    """Tests for DebugToolbar class."""

    def test_default_config(self) -> None:
        """Should use default config if none provided."""
        toolbar = DebugToolbar()
        assert toolbar.config.enabled is True

    def test_custom_config(self) -> None:
        """Should use provided config."""
        config = DebugToolbarConfig(enabled=False)
        toolbar = DebugToolbar(config)
        assert toolbar.config.enabled is False

    def test_disabled_toolbar_no_panels(self) -> None:
        """Disabled toolbar should not load panels."""
        config = DebugToolbarConfig(enabled=False)
        toolbar = DebugToolbar(config)
        assert len(toolbar.panels) == 0

    def test_get_panel(self) -> None:
        """Should retrieve panel by ID."""
        toolbar = DebugToolbar()
        panel = toolbar.get_panel("TimerPanel")
        assert panel is not None
        assert panel.get_panel_id() == "TimerPanel"

    def test_get_panel_nonexistent(self) -> None:
        """Should return None for nonexistent panel."""
        toolbar = DebugToolbar()
        assert toolbar.get_panel("NonexistentPanel") is None

    @pytest.mark.asyncio
    async def test_process_request(self) -> None:
        """Should create context and notify panels."""
        set_request_context(None)
        toolbar = DebugToolbar()

        context = await toolbar.process_request()

        assert context is not None
        assert context.get_timing("request_start") is not None

        set_request_context(None)

    @pytest.mark.asyncio
    async def test_process_response(self) -> None:
        """Should collect stats and store in history."""
        set_request_context(None)
        toolbar = DebugToolbar()

        context = await toolbar.process_request()
        await toolbar.process_response(context)

        assert len(toolbar.storage) == 1
        assert get_request_context() is None

    @pytest.mark.asyncio
    async def test_server_timing_header(self) -> None:
        """Should generate Server-Timing header."""
        set_request_context(None)
        toolbar = DebugToolbar()

        context = await toolbar.process_request()
        await toolbar.process_response(context)

        header = toolbar.get_server_timing_header(context)
        assert "total" in header
        assert "dur=" in header

        set_request_context(None)

    @pytest.mark.asyncio
    async def test_toolbar_data(self) -> None:
        """Should return toolbar data structure."""
        set_request_context(None)
        toolbar = DebugToolbar()

        context = await toolbar.process_request()
        await toolbar.process_response(context)

        data = toolbar.get_toolbar_data(context)
        assert "request_id" in data
        assert "panels" in data
        assert "timing" in data

        set_request_context(None)

    def test_extra_panels_string_import(self) -> None:
        """Should load extra panels from string import paths."""
        config = DebugToolbarConfig(
            extra_panels=["debug_toolbar.core.panels.headers.HeadersPanel"],
        )
        toolbar = DebugToolbar(config)

        panel_ids = [p.get_panel_id() for p in toolbar.panels]
        assert "HeadersPanel" in panel_ids

    def test_extra_panels_multiple_string_imports(self) -> None:
        """Should load multiple extra panels from string paths."""
        config = DebugToolbarConfig(
            extra_panels=[
                "debug_toolbar.core.panels.headers.HeadersPanel",
                "debug_toolbar.core.panels.settings.SettingsPanel",
                "debug_toolbar.core.panels.profiling.ProfilingPanel",
            ],
        )
        toolbar = DebugToolbar(config)

        panel_ids = [p.get_panel_id() for p in toolbar.panels]
        assert "HeadersPanel" in panel_ids
        assert "SettingsPanel" in panel_ids
        assert "ProfilingPanel" in panel_ids

    def test_extra_panels_invalid_import_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log warning for invalid panel import paths."""
        import logging

        with caplog.at_level(logging.WARNING):
            config = DebugToolbarConfig(
                extra_panels=["nonexistent.module.FakePanel"],
            )
            DebugToolbar(config)

        assert "Failed to import panel" in caplog.text
        assert "nonexistent.module.FakePanel" in caplog.text
