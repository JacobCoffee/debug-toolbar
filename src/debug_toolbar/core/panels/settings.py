"""Settings panel for displaying application configuration."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from collections.abc import Sequence

    from debug_toolbar.core.context import RequestContext


class SettingsPanel(Panel):
    """Panel displaying application configuration and environment settings.

    Shows:
    - Debug toolbar configuration
    - Environment variables (with sensitive values redacted)
    - Python runtime settings
    - Custom application settings

    Args:
        toolbar: The parent DebugToolbar instance.
        custom_settings: Optional custom settings to display.
        show_env: Whether to show environment variables.
        sensitive_keys: Additional keys to redact beyond default patterns.
    """

    panel_id: ClassVar[str] = "SettingsPanel"
    title: ClassVar[str] = "Settings"
    template: ClassVar[str] = "panels/settings.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Settings"

    REDACTED_VALUE: ClassVar[str] = "**********"
    MAX_PATH_ITEMS: ClassVar[int] = 10

    DEFAULT_SENSITIVE_PATTERNS: ClassVar[tuple[str, ...]] = (
        "PASSWORD",
        "SECRET",
        "KEY",
        "TOKEN",
        "API_KEY",
        "AUTH",
        "CREDENTIAL",
        "PRIVATE",
    )

    __slots__ = ("_custom_settings", "_sensitive_patterns", "_show_env")

    def __init__(
        self,
        toolbar: Any,
        *,
        custom_settings: dict[str, Any] | None = None,
        show_env: bool = True,
        sensitive_keys: Sequence[str] | None = None,
    ) -> None:
        """Initialize the settings panel.

        Args:
            toolbar: The parent DebugToolbar instance.
            custom_settings: Optional custom settings to display.
            show_env: Whether to show environment variables.
            sensitive_keys: Additional keys to redact beyond default patterns.
        """
        super().__init__(toolbar)
        self._custom_settings = custom_settings
        self._show_env = show_env

        patterns = list(self.DEFAULT_SENSITIVE_PATTERNS)
        if sensitive_keys:
            patterns.extend(sensitive_keys)
        self._sensitive_patterns = tuple(patterns)

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key should be redacted based on sensitive patterns.

        Args:
            key: The key to check.

        Returns:
            True if the key matches any sensitive pattern.
        """
        key_upper = key.upper()
        return any(pattern in key_upper for pattern in self._sensitive_patterns)

    def _redact_sensitive_value(self, key: str, value: Any) -> Any:
        """Redact sensitive values based on key patterns.

        Args:
            key: The setting key.
            value: The setting value.

        Returns:
            The original value or redacted placeholder.
        """
        if self._is_sensitive_key(key):
            return self.REDACTED_VALUE
        return value

    def _process_env_variables(self) -> dict[str, Any]:
        """Process environment variables and redact sensitive ones.

        Returns:
            Dictionary containing processed environment variables and metadata.
        """
        variables = {}
        redacted_count = 0

        for key, value in os.environ.items():
            if self._is_sensitive_key(key):
                variables[key] = self.REDACTED_VALUE
                redacted_count += 1
            else:
                variables[key] = value

        return {
            "variables": dict(sorted(variables.items())),
            "redacted_count": redacted_count,
        }

    def _get_toolbar_config_dict(self) -> dict[str, Any]:
        """Get toolbar configuration as a dictionary.

        Returns:
            Dictionary containing toolbar configuration.
        """
        config = self._toolbar.config

        panel_ids = []
        for panel_spec in config.get_all_panels():
            if isinstance(panel_spec, str):
                panel_ids.append(panel_spec.split(".")[-1])
            else:
                panel_ids.append(panel_spec.__name__)

        return {
            "enabled": config.enabled,
            "panels": panel_ids,
            "intercept_redirects": config.intercept_redirects,
            "insert_before": config.insert_before,
            "max_request_history": config.max_request_history,
            "api_path": config.api_path,
            "static_path": config.static_path,
            "allowed_hosts": list(config.allowed_hosts) if config.allowed_hosts else [],
            "exclude_panels": list(config.exclude_panels) if config.exclude_panels else [],
        }

    def _get_python_settings(self) -> dict[str, Any]:
        """Get Python runtime settings.

        Returns:
            Dictionary containing Python configuration.
        """
        sys_path = sys.path[: self.MAX_PATH_ITEMS] if len(sys.path) > self.MAX_PATH_ITEMS else sys.path

        return {
            "debug": sys.flags.debug,
            "optimize": sys.flags.optimize,
            "path": sys_path,
            "path_truncated": len(sys.path) > self.MAX_PATH_ITEMS,
            "path_total_count": len(sys.path),
            "executable": sys.executable,
            "prefix": sys.prefix,
        }

    def _process_custom_settings(self, settings: dict[str, Any] | None) -> dict[str, Any] | None:
        """Process custom settings and redact sensitive values.

        Args:
            settings: Custom settings dictionary.

        Returns:
            Processed settings with sensitive values redacted, or None.
        """
        if settings is None:
            return None

        processed = {}
        for key, value in settings.items():
            if isinstance(value, dict):
                processed[key] = self._process_custom_settings(value)
            else:
                processed[key] = self._redact_sensitive_value(key, value)

        return processed

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate settings statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary containing all settings data.
        """
        stats: dict[str, Any] = {
            "toolbar_config": self._get_toolbar_config_dict(),
            "python_settings": self._get_python_settings(),
        }

        if self._show_env:
            stats["environment"] = self._process_env_variables()
        else:
            stats["environment"] = None

        if self._custom_settings:
            stats["custom_settings"] = self._process_custom_settings(self._custom_settings)
        else:
            stats["custom_settings"] = None

        return stats

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle.

        Returns:
            The number of configuration sections.
        """
        sections = 2
        if self._show_env:
            sections += 1
        if self._custom_settings:
            sections += 1
        return f"{sections} sections"
