"""Tests for the Settings panel."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from debug_toolbar.core.panels.settings import SettingsPanel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar with config."""
    toolbar = MagicMock()
    config = MagicMock()
    config.enabled = True
    config.intercept_redirects = False
    config.insert_before = "</body>"
    config.max_request_history = 50
    config.api_path = "/_debug_toolbar"
    config.static_path = "/_debug_toolbar/static"
    config.allowed_hosts = []
    config.exclude_panels = []
    config.get_all_panels.return_value = [
        "debug_toolbar.core.panels.timer.TimerPanel",
        "debug_toolbar.core.panels.request.RequestPanel",
    ]
    toolbar.config = config
    return toolbar


class TestSettingsPanel:
    """Tests for SettingsPanel."""

    def test_panel_class_attributes(self) -> None:
        """Test panel class attributes are set correctly."""
        assert SettingsPanel.panel_id == "SettingsPanel"
        assert SettingsPanel.title == "Settings"
        assert SettingsPanel.nav_title == "Settings"
        assert SettingsPanel.has_content is True
        assert SettingsPanel.template == "panels/settings.html"

    def test_initialization_defaults(self, mock_toolbar: MagicMock) -> None:
        """Test panel initializes with default parameters."""
        panel = SettingsPanel(mock_toolbar)
        assert panel._custom_settings is None
        assert panel._show_env is True
        assert SettingsPanel.DEFAULT_SENSITIVE_PATTERNS[0] in panel._sensitive_patterns

    def test_initialization_custom_settings(self, mock_toolbar: MagicMock) -> None:
        """Test panel initializes with custom settings."""
        custom_settings = {"app_name": "TestApp", "version": "1.0"}
        panel = SettingsPanel(mock_toolbar, custom_settings=custom_settings)
        assert panel._custom_settings == custom_settings

    def test_initialization_show_env_false(self, mock_toolbar: MagicMock) -> None:
        """Test panel initializes with show_env=False."""
        panel = SettingsPanel(mock_toolbar, show_env=False)
        assert panel._show_env is False

    def test_initialization_sensitive_keys(self, mock_toolbar: MagicMock) -> None:
        """Test panel initializes with additional sensitive keys."""
        panel = SettingsPanel(mock_toolbar, sensitive_keys=["CUSTOM_SECRET", "PRIVATE_DATA"])
        assert "CUSTOM_SECRET" in panel._sensitive_patterns
        assert "PRIVATE_DATA" in panel._sensitive_patterns

    def test_is_sensitive_key_default_patterns(self, mock_toolbar: MagicMock) -> None:
        """Test sensitive key detection with default patterns."""
        panel = SettingsPanel(mock_toolbar)

        assert panel._is_sensitive_key("DATABASE_PASSWORD") is True
        assert panel._is_sensitive_key("SECRET_KEY") is True
        assert panel._is_sensitive_key("API_TOKEN") is True
        assert panel._is_sensitive_key("AUTH_SECRET") is True
        assert panel._is_sensitive_key("PRIVATE_KEY") is True
        assert panel._is_sensitive_key("CREDENTIAL_ID") is True

        assert panel._is_sensitive_key("DATABASE_HOST") is False
        assert panel._is_sensitive_key("DEBUG") is False
        assert panel._is_sensitive_key("APP_NAME") is False

    def test_is_sensitive_key_case_insensitive(self, mock_toolbar: MagicMock) -> None:
        """Test sensitive key detection is case-insensitive."""
        panel = SettingsPanel(mock_toolbar)
        assert panel._is_sensitive_key("password") is True
        assert panel._is_sensitive_key("Password") is True
        assert panel._is_sensitive_key("PASSWORD") is True
        assert panel._is_sensitive_key("PaSsWoRd") is True

    def test_redact_sensitive_value(self, mock_toolbar: MagicMock) -> None:
        """Test sensitive value redaction."""
        panel = SettingsPanel(mock_toolbar)

        assert panel._redact_sensitive_value("PASSWORD", "secret123") == SettingsPanel.REDACTED_VALUE
        assert panel._redact_sensitive_value("API_KEY", "abc123") == SettingsPanel.REDACTED_VALUE
        assert panel._redact_sensitive_value("DEBUG", True) is True
        assert panel._redact_sensitive_value("PORT", 8000) == 8000

    def test_process_env_variables(self, mock_toolbar: MagicMock) -> None:
        """Test environment variable processing and redaction."""
        with patch.dict(
            "os.environ",
            {
                "DEBUG": "true",
                "DATABASE_HOST": "localhost",
                "DATABASE_PASSWORD": "secret123",
                "API_KEY": "abc123",
                "APP_NAME": "TestApp",
            },
            clear=True,
        ):
            panel = SettingsPanel(mock_toolbar)
            result = panel._process_env_variables()

            assert "variables" in result
            assert "redacted_count" in result

            variables = result["variables"]
            assert variables["DEBUG"] == "true"
            assert variables["DATABASE_HOST"] == "localhost"
            assert variables["DATABASE_PASSWORD"] == SettingsPanel.REDACTED_VALUE
            assert variables["API_KEY"] == SettingsPanel.REDACTED_VALUE
            assert variables["APP_NAME"] == "TestApp"

            assert result["redacted_count"] == 2

    def test_process_env_variables_sorted(self, mock_toolbar: MagicMock) -> None:
        """Test environment variables are returned sorted."""
        with patch.dict(
            "os.environ",
            {
                "Z_VAR": "last",
                "A_VAR": "first",
                "M_VAR": "middle",
            },
            clear=True,
        ):
            panel = SettingsPanel(mock_toolbar)
            result = panel._process_env_variables()
            variables = result["variables"]

            keys = list(variables.keys())
            assert keys == ["A_VAR", "M_VAR", "Z_VAR"]

    def test_get_toolbar_config_dict(self, mock_toolbar: MagicMock) -> None:
        """Test toolbar configuration dictionary generation."""
        panel = SettingsPanel(mock_toolbar)
        config_dict = panel._get_toolbar_config_dict()

        assert config_dict["enabled"] is True
        assert config_dict["intercept_redirects"] is False
        assert config_dict["insert_before"] == "</body>"
        assert config_dict["max_request_history"] == 50
        assert config_dict["api_path"] == "/_debug_toolbar"
        assert config_dict["static_path"] == "/_debug_toolbar/static"
        assert config_dict["allowed_hosts"] == []
        assert config_dict["exclude_panels"] == []
        assert "panels" in config_dict
        assert "TimerPanel" in config_dict["panels"]
        assert "RequestPanel" in config_dict["panels"]

    def test_get_python_settings(self, mock_toolbar: MagicMock) -> None:
        """Test Python settings generation."""
        panel = SettingsPanel(mock_toolbar)
        python_settings = panel._get_python_settings()

        assert "debug" in python_settings
        assert "optimize" in python_settings
        assert "path" in python_settings
        assert "path_truncated" in python_settings
        assert "path_total_count" in python_settings
        assert "executable" in python_settings
        assert "prefix" in python_settings

        assert python_settings["debug"] == sys.flags.debug
        assert python_settings["optimize"] == sys.flags.optimize
        assert python_settings["executable"] == sys.executable
        assert python_settings["prefix"] == sys.prefix
        assert python_settings["path_total_count"] == len(sys.path)

    def test_get_python_settings_path_truncation(self, mock_toolbar: MagicMock) -> None:
        """Test Python path is truncated when too long."""
        panel = SettingsPanel(mock_toolbar)
        python_settings = panel._get_python_settings()

        max_items = SettingsPanel.MAX_PATH_ITEMS
        if len(sys.path) > max_items:
            assert len(python_settings["path"]) == max_items
            assert python_settings["path_truncated"] is True
        else:
            assert len(python_settings["path"]) == len(sys.path)
            assert python_settings["path_truncated"] is False

    def test_process_custom_settings_none(self, mock_toolbar: MagicMock) -> None:
        """Test processing None custom settings."""
        panel = SettingsPanel(mock_toolbar)
        result = panel._process_custom_settings(None)
        assert result is None

    def test_process_custom_settings_simple(self, mock_toolbar: MagicMock) -> None:
        """Test processing simple custom settings."""
        panel = SettingsPanel(mock_toolbar)
        custom_settings = {
            "app_name": "TestApp",
            "version": "1.0",
            "debug": True,
        }
        result = panel._process_custom_settings(custom_settings)

        assert result is not None
        assert result["app_name"] == "TestApp"
        assert result["version"] == "1.0"
        assert result["debug"] is True

    def test_process_custom_settings_with_sensitive(self, mock_toolbar: MagicMock) -> None:
        """Test processing custom settings with sensitive values."""
        panel = SettingsPanel(mock_toolbar)
        custom_settings = {
            "app_name": "TestApp",
            "database_password": "secret123",
            "api_key": "abc123",
        }
        result = panel._process_custom_settings(custom_settings)

        assert result is not None
        assert result["app_name"] == "TestApp"
        assert result["database_password"] == SettingsPanel.REDACTED_VALUE
        assert result["api_key"] == SettingsPanel.REDACTED_VALUE

    def test_process_custom_settings_nested(self, mock_toolbar: MagicMock) -> None:
        """Test processing nested custom settings."""
        panel = SettingsPanel(mock_toolbar)
        custom_settings = {
            "app": {
                "name": "TestApp",
                "database": {
                    "host": "localhost",
                    "password": "secret123",
                },
            },
        }
        result = panel._process_custom_settings(custom_settings)

        assert result is not None
        assert result["app"]["name"] == "TestApp"
        assert result["app"]["database"]["host"] == "localhost"
        assert result["app"]["database"]["password"] == SettingsPanel.REDACTED_VALUE

    @pytest.mark.asyncio
    async def test_generate_stats_basic(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test basic stats generation."""
        panel = SettingsPanel(mock_toolbar)
        stats = await panel.generate_stats(request_context)

        assert "toolbar_config" in stats
        assert "python_settings" in stats
        assert "environment" in stats
        assert "custom_settings" in stats

        assert stats["toolbar_config"]["enabled"] is True
        assert stats["python_settings"]["debug"] == sys.flags.debug
        assert stats["environment"] is not None
        assert stats["custom_settings"] is None

    @pytest.mark.asyncio
    async def test_generate_stats_no_env(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test stats generation with environment disabled."""
        panel = SettingsPanel(mock_toolbar, show_env=False)
        stats = await panel.generate_stats(request_context)

        assert stats["environment"] is None

    @pytest.mark.asyncio
    async def test_generate_stats_with_custom_settings(
        self, mock_toolbar: MagicMock, request_context: RequestContext
    ) -> None:
        """Test stats generation with custom settings."""
        custom_settings = {
            "app_name": "TestApp",
            "version": "1.0",
            "api_key": "secret123",
        }
        panel = SettingsPanel(mock_toolbar, custom_settings=custom_settings)
        stats = await panel.generate_stats(request_context)

        assert stats["custom_settings"] is not None
        assert stats["custom_settings"]["app_name"] == "TestApp"
        assert stats["custom_settings"]["version"] == "1.0"
        assert stats["custom_settings"]["api_key"] == SettingsPanel.REDACTED_VALUE

    def test_get_nav_subtitle_basic(self, mock_toolbar: MagicMock) -> None:
        """Test navigation subtitle with basic configuration."""
        panel = SettingsPanel(mock_toolbar)
        subtitle = panel.get_nav_subtitle()
        assert subtitle == "3 sections"

    def test_get_nav_subtitle_no_env(self, mock_toolbar: MagicMock) -> None:
        """Test navigation subtitle without environment."""
        panel = SettingsPanel(mock_toolbar, show_env=False)
        subtitle = panel.get_nav_subtitle()
        assert subtitle == "2 sections"

    def test_get_nav_subtitle_with_custom(self, mock_toolbar: MagicMock) -> None:
        """Test navigation subtitle with custom settings."""
        panel = SettingsPanel(mock_toolbar, custom_settings={"test": "value"})
        subtitle = panel.get_nav_subtitle()
        assert subtitle == "4 sections"

    def test_get_nav_subtitle_no_env_with_custom(self, mock_toolbar: MagicMock) -> None:
        """Test navigation subtitle without env but with custom settings."""
        panel = SettingsPanel(mock_toolbar, show_env=False, custom_settings={"test": "value"})
        subtitle = panel.get_nav_subtitle()
        assert subtitle == "3 sections"

    def test_custom_sensitive_patterns(self, mock_toolbar: MagicMock) -> None:
        """Test custom sensitive patterns are included."""
        panel = SettingsPanel(mock_toolbar, sensitive_keys=["INTERNAL", "CONFIDENTIAL"])

        assert panel._is_sensitive_key("INTERNAL_DATA") is True
        assert panel._is_sensitive_key("CONFIDENTIAL_INFO") is True
        assert panel._is_sensitive_key("DATABASE_PASSWORD") is True

    def test_sensitive_patterns_overlap(self, mock_toolbar: MagicMock) -> None:
        """Test overlapping sensitive patterns don't cause issues."""
        panel = SettingsPanel(mock_toolbar, sensitive_keys=["PASSWORD"])

        assert panel._is_sensitive_key("PASSWORD") is True
        assert panel._is_sensitive_key("USER_PASSWORD") is True
        assert "PASSWORD" in panel._sensitive_patterns
