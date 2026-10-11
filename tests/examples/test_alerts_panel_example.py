"""Tests for the alerts panel example script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_alerts_for_every_scenario(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real script should produce real, scenario-specific alerts."""
    module = import_example("examples.alerts_panel_example")

    await module.main()

    output = capsys.readouterr().out

    # Example 1: missing security headers.
    assert "Total Alerts: 3" in output
    assert "Content-Security-Policy" in output
    assert "X-Content-Type-Options" in output
    assert "Strict-Transport-Security" in output

    # Example 2: insecure cookie.
    assert "Cookie Security Alerts:" in output

    # Example 3: missing CSRF protection on a POST request.
    assert "CSRF Alerts:" in output

    # Example 4: debug mode enabled in production really triggers a configuration alert.
    assert "Configuration Alerts:" in output

    # Example 5: oversized response body.
    assert "Performance Alerts:" in output

    # Example 6: slow database queries.
    assert "Database Performance Alerts:" in output

    # Example 7: N+1 query pattern really triggers an alert naming the real suggestion.
    assert "N+1 Query Alerts:" in output
    assert "joinedload" in output

    # Example 8: combined scenario really spans multiple alert categories.
    assert "Summary by Category:" in output
    assert "Security:" in output
    assert "Database:" in output
    assert "All Alerts:" in output

    assert "Examples completed successfully!" in output
