"""Tests for Litestar-specific configuration."""

from __future__ import annotations

from unittest.mock import MagicMock

from debug_toolbar.litestar.config import LitestarDebugToolbarConfig


class TestLitestarDebugToolbarConfig:
    """Tests for LitestarDebugToolbarConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = LitestarDebugToolbarConfig()
        assert config.enabled is True
        assert "/_debug_toolbar" in config.exclude_paths
        assert "/static" in config.exclude_paths
        assert config.show_on_errors is True
        assert config.show_toolbar_callback is None

    def test_adds_routes_panel(self) -> None:
        """Test that RoutesPanel is added automatically."""
        config = LitestarDebugToolbarConfig()
        panel_strings = [p if isinstance(p, str) else p.__name__ for p in config.panels]
        assert "debug_toolbar.litestar.panels.routes.RoutesPanel" in panel_strings

    def test_does_not_duplicate_routes_panel(self) -> None:
        """Test that RoutesPanel is not added if already present."""
        config = LitestarDebugToolbarConfig(panels=["debug_toolbar.litestar.panels.routes.RoutesPanel"])
        panel_strings = [p for p in config.panels if isinstance(p, str)]
        routes_count = sum(1 for p in panel_strings if "RoutesPanel" in p)
        assert routes_count == 1

    def test_should_show_toolbar_when_disabled(self) -> None:
        """Test should_show_toolbar returns False when disabled."""
        config = LitestarDebugToolbarConfig(enabled=False)
        mock_request = MagicMock()
        mock_request.url.path = "/"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_excludes_path(self) -> None:
        """Test should_show_toolbar excludes configured paths."""
        config = LitestarDebugToolbarConfig(exclude_paths=["/api", "/health"])
        mock_request = MagicMock()
        mock_request.url.path = "/api/users"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_excludes_pattern(self) -> None:
        """Test should_show_toolbar excludes pattern matches."""
        config = LitestarDebugToolbarConfig(exclude_patterns=[r"^/api/v\d+/"])
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/users"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_pattern_no_match(self) -> None:
        """Test should_show_toolbar allows non-matching patterns."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            exclude_patterns=[r"^/api/v\d+/"],
        )
        mock_request = MagicMock()
        mock_request.url.path = "/users"
        mock_request.headers = {}
        assert config.should_show_toolbar(mock_request) is True

    def test_should_show_toolbar_allowed_hosts(self) -> None:
        """Test should_show_toolbar respects allowed_hosts."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            allowed_hosts=["localhost", "127.0.0.1"],
        )
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers = {"host": "evil.com"}
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_allowed_hosts_with_port(self) -> None:
        """Test should_show_toolbar strips port from host."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            allowed_hosts=["localhost"],
        )
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers = {"host": "localhost:8000"}
        assert config.should_show_toolbar(mock_request) is True

    def test_should_show_toolbar_allowed_hosts_empty(self) -> None:
        """Test should_show_toolbar allows all hosts when empty."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            allowed_hosts=[],
        )
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers = {}
        assert config.should_show_toolbar(mock_request) is True

    def test_should_show_toolbar_callback_true(self) -> None:
        """Test should_show_toolbar uses callback returning True."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            show_toolbar_callback=lambda req: True,
        )
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers = {}
        assert config.should_show_toolbar(mock_request) is True

    def test_should_show_toolbar_callback_false(self) -> None:
        """Test should_show_toolbar uses callback returning False."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=[],
            show_toolbar_callback=lambda req: False,
        )
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers = {}
        assert config.should_show_toolbar(mock_request) is False

    def test_custom_exclude_paths(self) -> None:
        """Test custom exclude_paths."""
        config = LitestarDebugToolbarConfig(
            exclude_paths=["/custom", "/another"],
        )
        assert "/custom" in config.exclude_paths
        assert "/another" in config.exclude_paths

    def test_custom_exclude_patterns(self) -> None:
        """Test custom exclude_patterns."""
        config = LitestarDebugToolbarConfig(
            exclude_patterns=[r"^/test/\d+"],
        )
        assert r"^/test/\d+" in config.exclude_patterns
