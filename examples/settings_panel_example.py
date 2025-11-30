# /// script
# requires-python = ">=3.10"
# dependencies = ["debug-toolbar"]
# ///
"""Example demonstrating the Settings Panel usage."""

# ruff: noqa: T201, INP001

from __future__ import annotations

import asyncio

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.settings import SettingsPanel
from debug_toolbar.core.toolbar import DebugToolbar


async def main() -> None:
    """Demonstrate Settings Panel functionality."""
    config = DebugToolbarConfig(
        enabled=True,
        intercept_redirects=False,
        max_request_history=100,
    )

    toolbar = DebugToolbar(config=config)

    print("Example 1: Basic Settings Panel")
    print("-" * 50)
    basic_panel = SettingsPanel(toolbar)
    context = await toolbar.process_request()
    stats = await basic_panel.generate_stats(context)

    print(f"Toolbar Config: {stats['toolbar_config']['enabled']}")
    print(f"Python Debug: {stats['python_settings']['debug']}")
    print(f"Environment Variables: {len(stats['environment']['variables'])} total")
    print(f"Redacted Variables: {stats['environment']['redacted_count']}")
    print()

    print("Example 2: Settings Panel with Custom Settings")
    print("-" * 50)
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

    custom_panel = SettingsPanel(toolbar, custom_settings=custom_settings)
    context2 = await toolbar.process_request()
    stats2 = await custom_panel.generate_stats(context2)

    print(f"App Name: {stats2['custom_settings']['app_name']}")
    print(f"Version: {stats2['custom_settings']['version']}")
    print(f"Database Host: {stats2['custom_settings']['database']['host']}")
    print(f"Database Password: {stats2['custom_settings']['database']['password']}")
    print(f"API Key: {stats2['custom_settings']['api_key']}")
    print(f"Debug Mode: {stats2['custom_settings']['debug_mode']}")
    print()

    print("Example 3: Settings Panel without Environment Variables")
    print("-" * 50)
    no_env_panel = SettingsPanel(toolbar, show_env=False)
    context3 = await toolbar.process_request()
    stats3 = await no_env_panel.generate_stats(context3)

    print(f"Environment Section: {stats3['environment']}")
    print(f"Navigation Subtitle: {no_env_panel.get_nav_subtitle()}")
    print()

    print("Example 4: Custom Sensitive Patterns")
    print("-" * 50)
    sensitive_panel = SettingsPanel(
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

    print(f"App Name: {stats4['custom_settings']['app_name']}")
    print(f"Internal ID: {stats4['custom_settings']['internal_id']}")
    print(f"Confidential Data: {stats4['custom_settings']['confidential_data']}")
    print(f"Public URL: {stats4['custom_settings']['public_url']}")


if __name__ == "__main__":
    asyncio.run(main())
