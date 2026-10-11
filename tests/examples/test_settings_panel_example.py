"""Tests for the settings panel example script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_prints_expected_output(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The script's main() should report real toolbar, custom, and redacted settings."""
    module = import_example("examples.settings_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Toolbar Config: True" in output
    assert "App Name: My Litestar App" in output
    assert "Database Host: localhost" in output
    assert "Database Password: " in output
    assert "secret123" not in output


@pytest.mark.asyncio
async def test_settings_panel_basic_stats(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 1's basic panel setup and assert on real stats fields."""
    module = import_example("examples.settings_panel_example")

    config = module.DebugToolbarConfig(
        enabled=True,
        intercept_redirects=False,
        max_request_history=100,
    )
    toolbar = module.DebugToolbar(config=config)

    basic_panel = module.SettingsPanel(toolbar)
    context = await toolbar.process_request()
    stats = await basic_panel.generate_stats(context)

    assert stats["toolbar_config"]["enabled"] is True
    assert "debug" in stats["python_settings"]
    assert "variables" in stats["environment"]
    assert isinstance(stats["environment"]["redacted_count"], int)


@pytest.mark.asyncio
async def test_settings_panel_redacts_sensitive_custom_settings(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 2's custom settings and assert the password/api key are redacted."""
    module = import_example("examples.settings_panel_example")

    toolbar = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))

    custom_settings = {
        "app_name": "My Litestar App",
        "version": "1.0.0",
        "database": {
            "host": "localhost",
            "port": 5432,
            "password": "secret123",
        },
        "api_key": "abc123xyz",
        "debug_mode": True,
    }

    custom_panel = module.SettingsPanel(toolbar, custom_settings=custom_settings)
    context2 = await toolbar.process_request()
    stats2 = await custom_panel.generate_stats(context2)

    assert stats2["custom_settings"]["app_name"] == "My Litestar App"
    assert stats2["custom_settings"]["database"]["host"] == "localhost"
    assert stats2["custom_settings"]["database"]["password"] == module.SettingsPanel.REDACTED_VALUE
    assert stats2["custom_settings"]["api_key"] == module.SettingsPanel.REDACTED_VALUE


@pytest.mark.asyncio
async def test_settings_panel_without_environment_section(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 3's show_env=False behavior."""
    module = import_example("examples.settings_panel_example")

    toolbar = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))

    no_env_panel = module.SettingsPanel(toolbar, show_env=False)
    context3 = await toolbar.process_request()
    stats3 = await no_env_panel.generate_stats(context3)

    assert stats3["environment"] is None


@pytest.mark.asyncio
async def test_settings_panel_custom_sensitive_patterns(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 4's custom sensitive key patterns."""
    module = import_example("examples.settings_panel_example")

    toolbar = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))

    sensitive_panel = module.SettingsPanel(
        toolbar,
        custom_settings={
            "app_name": "My App",
            "internal_id": "secret-internal-123",
            "confidential_data": "top-secret",
            "public_url": "https://example.com",
        },
        sensitive_keys=["INTERNAL", "CONFIDENTIAL"],
    )
    context4 = await toolbar.process_request()
    stats4 = await sensitive_panel.generate_stats(context4)

    assert stats4["custom_settings"]["app_name"] == "My App"
    assert stats4["custom_settings"]["internal_id"] == module.SettingsPanel.REDACTED_VALUE
    assert stats4["custom_settings"]["confidential_data"] == module.SettingsPanel.REDACTED_VALUE
    assert stats4["custom_settings"]["public_url"] == "https://example.com"
