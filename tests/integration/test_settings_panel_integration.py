"""Integration tests for Settings Panel with Debug Toolbar."""

from __future__ import annotations

import pytest

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.settings import SettingsPanel
from debug_toolbar.core.toolbar import DebugToolbar


class TestSettingsPanelIntegration:
    """Integration tests for Settings Panel."""

    @pytest.mark.asyncio
    async def test_settings_panel_in_toolbar(self) -> None:
        """Test Settings Panel integrates with Debug Toolbar."""
        config = DebugToolbarConfig(
            enabled=True,
            extra_panels=[SettingsPanel],
        )
        toolbar = DebugToolbar(config=config)

        settings_panel = None
        for panel in toolbar.enabled_panels:
            if isinstance(panel, SettingsPanel):
                settings_panel = panel
                break

        assert settings_panel is not None
        assert settings_panel.enabled is True
        assert settings_panel.get_panel_id() == "settings"

    @pytest.mark.asyncio
    async def test_settings_panel_generates_stats_in_toolbar(self) -> None:
        """Test Settings Panel generates stats in toolbar context."""
        config = DebugToolbarConfig(
            enabled=True,
            extra_panels=[SettingsPanel],
        )
        toolbar = DebugToolbar(config=config)

        context = await toolbar.process_request()

        settings_panel = None
        for panel in toolbar.enabled_panels:
            if isinstance(panel, SettingsPanel):
                settings_panel = panel
                break

        assert settings_panel is not None

        stats = await settings_panel.generate_stats(context)

        assert "toolbar_config" in stats
        assert "python_settings" in stats
        assert "environment" in stats
        assert "custom_settings" in stats

        assert stats["toolbar_config"]["enabled"] is True
        assert isinstance(stats["python_settings"]["debug"], int)

    @pytest.mark.asyncio
    async def test_settings_panel_with_custom_config(self) -> None:
        """Test Settings Panel with custom configuration."""
        custom_settings = {
            "app_name": "Test App",
            "version": "1.0.0",
            "api_key": "secret123",
        }

        panel = SettingsPanel(
            DebugToolbar(config=DebugToolbarConfig()),
            custom_settings=custom_settings,
            show_env=False,
        )

        config = DebugToolbarConfig(
            enabled=True,
            extra_panels=[type(panel)],
        )
        toolbar = DebugToolbar(config=config)

        context = await toolbar.process_request()
        stats = await panel.generate_stats(context)

        assert stats["environment"] is None
        assert stats["custom_settings"]["app_name"] == "Test App"
        assert stats["custom_settings"]["api_key"] == SettingsPanel.REDACTED_VALUE

    @pytest.mark.asyncio
    async def test_settings_panel_nav_data(self) -> None:
        """Test Settings Panel navigation data."""
        config = DebugToolbarConfig(
            enabled=True,
            extra_panels=[SettingsPanel],
        )
        toolbar = DebugToolbar(config=config)

        context = await toolbar.process_request()
        await toolbar.process_response(context)

        toolbar_data = toolbar.get_toolbar_data(context)

        settings_panel_data = None
        for panel_data in toolbar_data["panels"]:
            if panel_data["panel_id"] == "settings":
                settings_panel_data = panel_data
                break

        assert settings_panel_data is not None
        assert settings_panel_data["title"] == "Settings"
        assert settings_panel_data["nav_title"] == "Settings"
        assert settings_panel_data["has_content"] is True
        assert "sections" in settings_panel_data["nav_subtitle"]
