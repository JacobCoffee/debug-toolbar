"""Tests for FastAPI debug toolbar configuration."""

from __future__ import annotations

from unittest.mock import MagicMock

from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig


class TestFastAPIDebugToolbarConfig:
    """Tests for FastAPIDebugToolbarConfig class."""

    def test_default_exclude_paths(self) -> None:
        """Should have FastAPI-specific default exclude paths."""
        config = FastAPIDebugToolbarConfig()
        assert "/_debug_toolbar" in config.exclude_paths
        assert "/docs" in config.exclude_paths
        assert "/redoc" in config.exclude_paths
        assert "/openapi.json" in config.exclude_paths
        assert "/favicon.ico" in config.exclude_paths

    def test_default_enabled(self) -> None:
        """Should be enabled by default."""
        config = FastAPIDebugToolbarConfig()
        assert config.enabled is True

    def test_track_dependency_injection_default(self) -> None:
        """Should track DI by default."""
        config = FastAPIDebugToolbarConfig()
        assert config.track_dependency_injection is True

    def test_disable_dependency_tracking(self) -> None:
        """Should allow disabling DI tracking."""
        config = FastAPIDebugToolbarConfig(track_dependency_injection=False)
        assert config.track_dependency_injection is False

    def test_adds_di_panel_when_tracking_enabled(self) -> None:
        """Should add DI panel when tracking is enabled."""
        config = FastAPIDebugToolbarConfig(track_dependency_injection=True)
        panel_names = [str(p) for p in config.panels]
        assert any("DependencyInjectionPanel" in name for name in panel_names)

    def test_no_di_panel_when_tracking_disabled(self) -> None:
        """Should not add DI panel when tracking is disabled."""
        config = FastAPIDebugToolbarConfig(track_dependency_injection=False)
        panel_names = [str(p) for p in config.panels]
        assert not any("DependencyInjectionPanel" in name for name in panel_names)

    def test_adds_starlette_routes_panel(self) -> None:
        """Should include Starlette routes panel."""
        config = FastAPIDebugToolbarConfig()
        panel_names = [str(p) for p in config.panels]
        assert any("RoutesPanel" in name for name in panel_names)

    def test_inherits_starlette_behavior(self) -> None:
        """Should inherit from StarletteDebugToolbarConfig."""
        config = FastAPIDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/_debug_toolbar/"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_docs(self) -> None:
        """Should hide toolbar for docs endpoint."""
        config = FastAPIDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/docs"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_redoc(self) -> None:
        """Should hide toolbar for redoc endpoint."""
        config = FastAPIDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/redoc"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False

    def test_should_show_toolbar_openapi(self) -> None:
        """Should hide toolbar for openapi.json endpoint."""
        config = FastAPIDebugToolbarConfig()
        mock_request = MagicMock()
        mock_request.url.path = "/openapi.json"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False

    def test_custom_callback(self) -> None:
        """Should support custom show_toolbar_callback."""
        callback = MagicMock(return_value=False)
        config = FastAPIDebugToolbarConfig(show_toolbar_callback=callback)
        mock_request = MagicMock()
        mock_request.url.path = "/api"
        mock_request.headers.get.return_value = ""
        assert config.should_show_toolbar(mock_request) is False
        callback.assert_called_once()
