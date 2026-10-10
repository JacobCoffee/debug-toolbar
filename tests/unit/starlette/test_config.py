"""Tests for Starlette debug toolbar configuration."""

from __future__ import annotations

from unittest.mock import MagicMock

from debug_toolbar.starlette.config import StarletteDebugToolbarConfig


class TestStarletteDebugToolbarConfig:
    """Tests for StarletteDebugToolbarConfig class."""

    def test_default_exclude_paths(self) -> None:
        """Should have sensible default exclude paths."""
        config = StarletteDebugToolbarConfig()
        assert "/_debug_toolbar" in config.exclude_paths
        assert "/static" in config.exclude_paths
        assert "/favicon.ico" in config.exclude_paths

    def test_default_enabled(self) -> None:
        """Should be enabled by default."""
        config = StarletteDebugToolbarConfig()
        assert config.enabled is True

    def test_custom_exclude_paths(self) -> None:
        """Should accept custom exclude paths."""
        config = StarletteDebugToolbarConfig(exclude_paths=["/api", "/health"])
        assert "/api" in config.exclude_paths
        assert "/health" in config.exclude_paths

    def test_show_on_errors_default(self) -> None:
        """Should show on errors by default."""
        config = StarletteDebugToolbarConfig()
        assert config.show_on_errors is True

    def test_exclude_patterns_default(self) -> None:
        """Should have empty exclude patterns by default."""
        config = StarletteDebugToolbarConfig()
        assert len(config.exclude_patterns) == 0

    def test_adds_routes_panel(self) -> None:
        """Should add Starlette routes panel to default panels."""
        config = StarletteDebugToolbarConfig()
        panel_names = [str(p) for p in config.panels]
        assert any("RoutesPanel" in name for name in panel_names)

    def test_should_show_toolbar_disabled(self) -> None:
        """Should return False when disabled."""
        config = StarletteDebugToolbarConfig(enabled=False)
        mock_request = MagicMock()
        mock_request.url.path = "/"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_excluded_path(self) -> None:
        """Should return False for excluded paths."""
        config = StarletteDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/_debug_toolbar/"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_excluded_pattern(self) -> None:
        """Should return False for paths matching exclude patterns."""
        config = StarletteDebugToolbarConfig(exclude_patterns=[r"^/api/v\d+/.*"])
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/users"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_allowed_host(self) -> None:
        """Should respect allowed_hosts setting."""
        config = StarletteDebugToolbarConfig(allowed_hosts=["localhost", "127.0.0.1"])
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers.get.return_value = "localhost:8000"
        assert config.should_show_toolbar(mock_request) is True

    def test_should_show_toolbar_disallowed_host(self) -> None:
        """Should return False for disallowed hosts."""
        config = StarletteDebugToolbarConfig(allowed_hosts=["localhost"])
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers.get.return_value = "production.example.com:443"
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_callback(self) -> None:
        """Should use custom callback when provided."""
        callback = MagicMock(return_value=False)
        config = StarletteDebugToolbarConfig(show_toolbar_callback=callback)
        mock_request = MagicMock()
        mock_request.url.path = "/"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False
        callback.assert_called_once_with(mock_request)

    def test_should_show_toolbar_normal_path(self) -> None:
        """Should return True for normal paths."""
        config = StarletteDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/users"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is True
