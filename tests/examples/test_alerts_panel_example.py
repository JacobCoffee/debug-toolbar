"""Tests for the alerts panel example script."""

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
    """The script's main() should report real alerts for each scenario."""
    module = import_example("examples.alerts_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Total Alerts: 3" in output
    assert "Content-Security-Policy" in output


@pytest.mark.asyncio
async def test_alerts_panel_missing_security_headers(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 1's missing headers scenario and assert real alerts generated."""
    module = import_example("examples.alerts_panel_example")

    config = module.DebugToolbarConfig(enabled=True)
    toolbar = module.DebugToolbar(config=config)
    panel = module.AlertsPanel(toolbar)
    context = await toolbar.process_request()

    context.metadata["headers"] = {
        "content-type": "text/html",
        "user-agent": "Mozilla/5.0",
    }
    context.metadata["response_headers"] = {
        "content-type": "text/html; charset=utf-8",
        "content-length": "1024",
    }

    headers_panel_data = {
        "response_headers": {
            "security_headers": {
                "missing": [
                    {
                        "name": "Content-Security-Policy",
                        "description": "Prevents XSS and other code injection attacks",
                    },
                    {
                        "name": "X-Content-Type-Options",
                        "description": "Prevents MIME-sniffing attacks",
                    },
                    {
                        "name": "Strict-Transport-Security",
                        "description": "Forces HTTPS connections",
                    },
                ]
            }
        }
    }
    context.panel_data["HeadersPanel"] = headers_panel_data

    stats = await panel.generate_stats(context)

    assert stats["total_alerts"] == 3
    titles = {alert["title"] for alert in stats["alerts"]}
    assert any("Content-Security-Policy" in title for title in titles)
    assert all(alert["category"] == "security" for alert in stats["alerts"])


@pytest.mark.asyncio
async def test_alerts_panel_debug_mode_in_production(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 4's debug-in-production scenario and assert a configuration alert fires."""
    module = import_example("examples.alerts_panel_example")

    toolbar4 = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))
    panel4 = module.AlertsPanel(toolbar4)
    context4 = await toolbar4.process_request()

    context4.metadata["headers"] = {}
    context4.metadata["response_headers"] = {}
    context4.panel_data["SettingsPanel"] = {
        "debug": True,
        "environment": "production",
    }

    stats4 = await panel4.generate_stats(context4)

    configuration_alerts = [alert for alert in stats4["alerts"] if alert["category"] == "configuration"]
    assert len(configuration_alerts) >= 1


@pytest.mark.asyncio
async def test_alerts_panel_n_plus_one_detection(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 7's N+1 query scenario and assert a database alert fires."""
    module = import_example("examples.alerts_panel_example")

    toolbar7 = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))
    panel7 = module.AlertsPanel(toolbar7)
    context7 = await toolbar7.process_request()

    context7.metadata["headers"] = {}
    context7.metadata["response_headers"] = {}
    context7.panel_data["SQLAlchemyPanel"] = {
        "queries": [],
        "n_plus_one_groups": [
            {
                "count": 15,
                "origin_display": "app.py:42 in get_users()",
                "suggestion": "Use joinedload(User.posts) to fetch related posts in a single query.",
            }
        ],
    }

    stats7 = await panel7.generate_stats(context7)

    n_plus_one_alerts = [alert for alert in stats7["alerts"] if "n+1" in alert["title"].lower()]
    assert len(n_plus_one_alerts) == 1
    assert "joinedload" in n_plus_one_alerts[0]["suggestion"]


@pytest.mark.asyncio
async def test_alerts_panel_multiple_categories_summary(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 8's combined scenario and assert alerts are split across categories."""
    module = import_example("examples.alerts_panel_example")

    toolbar8 = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))
    panel8 = module.AlertsPanel(toolbar8)
    context8 = await toolbar8.process_request()

    context8.metadata["method"] = "POST"
    context8.metadata["headers"] = {"content-type": "text/html"}
    context8.metadata["response_headers"] = {
        "content-length": str(2 * 1024 * 1024),
        "set-cookie": "token=xyz; Path=/",
    }

    context8.panel_data["HeadersPanel"] = {
        "response_headers": {
            "security_headers": {
                "missing": [
                    {
                        "name": "X-Frame-Options",
                        "description": "Prevents clickjacking attacks",
                    }
                ]
            }
        }
    }

    context8.panel_data["SQLAlchemyPanel"] = {
        "queries": [
            {"duration_ms": 250.0, "sql": "SELECT * FROM large_table"},
        ],
        "n_plus_one_groups": [
            {
                "count": 5,
                "origin_display": "views.py:123 in list_items()",
                "suggestion": "Use selectinload() to optimize the query.",
            }
        ],
    }

    stats8 = await panel8.generate_stats(context8)

    assert stats8["total_alerts"] == len(stats8["alerts"])
    assert sum(stats8["by_category"].values()) == stats8["total_alerts"]
    assert stats8["by_category"].get("security", 0) >= 1
    assert stats8["by_category"].get("database", 0) >= 1
