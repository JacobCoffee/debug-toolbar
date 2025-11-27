"""Tests for the config module."""

from __future__ import annotations

from debug_toolbar.core.config import DebugToolbarConfig


class TestDebugToolbarConfig:
    """Tests for DebugToolbarConfig class."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        config = DebugToolbarConfig()

        assert config.enabled is True
        assert config.intercept_redirects is False
        assert config.max_request_history == 50
        assert config.api_path == "/_debug_toolbar"
        assert len(config.panels) > 0

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = DebugToolbarConfig(
            enabled=False,
            max_request_history=100,
            api_path="/custom_debug",
        )

        assert config.enabled is False
        assert config.max_request_history == 100
        assert config.api_path == "/custom_debug"

    def test_get_all_panels_with_extras(self) -> None:
        """Should include extra panels."""
        config = DebugToolbarConfig(
            extra_panels=["custom.panel.CustomPanel"],
        )

        panels = config.get_all_panels()
        assert "custom.panel.CustomPanel" in panels

    def test_get_all_panels_with_exclusions(self) -> None:
        """Should exclude specified panels."""
        config = DebugToolbarConfig(
            exclude_panels=["TimerPanel"],
        )

        panels = config.get_all_panels()
        panel_names = [p.split(".")[-1] if isinstance(p, str) else p.__name__ for p in panels]
        assert "TimerPanel" not in panel_names

    def test_allowed_hosts(self) -> None:
        """Should accept allowed hosts."""
        config = DebugToolbarConfig(
            allowed_hosts=["localhost", "127.0.0.1"],
        )

        assert "localhost" in config.allowed_hosts
        assert "127.0.0.1" in config.allowed_hosts
