"""Tests for the settings panel example script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_settings_and_redactions(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real script should report real toolbar/custom settings and real redactions."""
    module = import_example("examples.settings_panel_example")

    await module.main()

    output = capsys.readouterr().out

    # Example 1: basic panel with real toolbar config and environment variable counts.
    assert "Toolbar Config: True" in output
    assert "Python Debug:" in output
    assert "Environment Variables:" in output
    assert "Redacted Variables:" in output

    # Example 2: custom settings with real password/api-key redaction.
    assert "App Name: My Litestar App" in output
    assert "Database Host: localhost" in output
    assert "Database Password: **********" in output
    assert "API Key: **********" in output
    assert "secret123" not in output
    assert "abc123xyz" not in output

    # Example 3: show_env=False really disables the environment section.
    assert "Environment Section: None" in output

    # Example 4: custom sensitive-key patterns really redact matching fields only.
    assert "App Name: My App" in output
    assert "Internal ID: **********" in output
    assert "Confidential Data: **********" in output
    assert "Public URL: https://example.com" in output
    assert "secret-internal-123" not in output
    assert "top-secret" not in output
