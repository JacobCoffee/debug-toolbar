"""Example demonstrating the Alerts Panel usage."""

# ruff: noqa: T201, INP001, PLR0912, C901

from __future__ import annotations

import asyncio

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.alerts import AlertsPanel
from debug_toolbar.core.toolbar import DebugToolbar


async def main() -> None:
    """Demonstrate Alerts Panel functionality."""
    print("=" * 70)
    print("Alerts Panel Examples")
    print("=" * 70)
    print()

    print("Example 1: Missing Security Headers")
    print("-" * 70)
    config = DebugToolbarConfig(enabled=True)
    toolbar = DebugToolbar(config=config)
    panel = AlertsPanel(toolbar)
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

    print(f"Total Alerts: {stats['total_alerts']}")
    print(f"By Severity: {stats['by_severity']}")
    print(f"By Category: {stats['by_category']}")
    print()
    print("Alerts:")
    for i, alert in enumerate(stats["alerts"], 1):
        print(f"\n  {i}. {alert['title']}")
        print(f"     Severity: {alert['severity']}")
        print(f"     Category: {alert['category']}")
        print(f"     Message: {alert['message']}")
        print(f"     Suggestion: {alert['suggestion']}")
    print()

    print("Example 2: Insecure Cookies")
    print("-" * 70)
    toolbar2 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel2 = AlertsPanel(toolbar2)
    context2 = await toolbar2.process_request()

    context2.metadata["headers"] = {"content-type": "text/html"}
    context2.metadata["response_headers"] = {
        "content-type": "text/html",
        "set-cookie": "sessionid=abc123; Path=/",
    }

    stats2 = await panel2.generate_stats(context2)

    print(f"Total Alerts: {stats2['total_alerts']}")
    print("Cookie Security Alerts:")
    for i, alert in enumerate(stats2["alerts"], 1):
        if "cookie" in alert["title"].lower():
            print(f"\n  {i}. {alert['title']}")
            print(f"     Severity: {alert['severity']}")
            print(f"     Message: {alert['message']}")
    print()

    print("Example 3: Missing CSRF Protection")
    print("-" * 70)
    toolbar3 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel3 = AlertsPanel(toolbar3)
    context3 = await toolbar3.process_request()

    context3.metadata["method"] = "POST"
    context3.metadata["headers"] = {
        "content-type": "application/x-www-form-urlencoded",
    }
    context3.metadata["response_headers"] = {
        "content-type": "text/html",
    }

    stats3 = await panel3.generate_stats(context3)

    print(f"Total Alerts: {stats3['total_alerts']}")
    print("CSRF Alerts:")
    for alert in stats3["alerts"]:
        if "csrf" in alert["title"].lower():
            print(f"\n  Title: {alert['title']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message']}")
            print(f"  Suggestion: {alert['suggestion']}")
    print()

    print("Example 4: Debug Mode in Production")
    print("-" * 70)
    toolbar4 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel4 = AlertsPanel(toolbar4)
    context4 = await toolbar4.process_request()

    context4.metadata["headers"] = {}
    context4.metadata["response_headers"] = {}
    settings_panel_data = {
        "debug": True,
        "environment": "production",
    }
    context4.panel_data["SettingsPanel"] = settings_panel_data

    stats4 = await panel4.generate_stats(context4)

    print(f"Total Alerts: {stats4['total_alerts']}")
    print("Configuration Alerts:")
    for alert in stats4["alerts"]:
        if alert["category"] == "configuration":
            print(f"\n  Title: {alert['title']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message']}")
    print()

    print("Example 5: Large Response Body")
    print("-" * 70)
    toolbar5 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel5 = AlertsPanel(toolbar5)
    context5 = await toolbar5.process_request()

    context5.metadata["headers"] = {}
    context5.metadata["response_headers"] = {
        "content-length": str(6 * 1024 * 1024),
    }

    stats5 = await panel5.generate_stats(context5)

    print(f"Total Alerts: {stats5['total_alerts']}")
    print("Performance Alerts:")
    for alert in stats5["alerts"]:
        if "response" in alert["title"].lower():
            print(f"\n  Title: {alert['title']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message']}")
    print()

    print("Example 6: Slow Database Queries")
    print("-" * 70)
    toolbar6 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel6 = AlertsPanel(toolbar6)
    context6 = await toolbar6.process_request()

    context6.metadata["headers"] = {}
    context6.metadata["response_headers"] = {}
    sql_panel_data = {
        "queries": [
            {"duration_ms": 150.5, "sql": "SELECT * FROM users WHERE id = 1"},
            {"duration_ms": 520.8, "sql": "SELECT * FROM posts JOIN comments"},
            {"duration_ms": 50.0, "sql": "SELECT COUNT(*) FROM logs"},
        ]
    }
    context6.panel_data["SQLAlchemyPanel"] = sql_panel_data

    stats6 = await panel6.generate_stats(context6)

    print(f"Total Alerts: {stats6['total_alerts']}")
    print("Database Performance Alerts:")
    for alert in stats6["alerts"]:
        if "query" in alert["title"].lower():
            print(f"\n  Title: {alert['title']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message']}")
            print(f"  Suggestion: {alert['suggestion']}")
    print()

    print("Example 7: N+1 Query Detection")
    print("-" * 70)
    toolbar7 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel7 = AlertsPanel(toolbar7)
    context7 = await toolbar7.process_request()

    context7.metadata["headers"] = {}
    context7.metadata["response_headers"] = {}
    sql_panel_data_n_plus_one = {
        "queries": [],
        "n_plus_one_groups": [
            {
                "count": 15,
                "origin_display": "app.py:42 in get_users()",
                "suggestion": "Use joinedload(User.posts) to fetch related posts in a single query.",
            }
        ],
    }
    context7.panel_data["SQLAlchemyPanel"] = sql_panel_data_n_plus_one

    stats7 = await panel7.generate_stats(context7)

    print(f"Total Alerts: {stats7['total_alerts']}")
    print("N+1 Query Alerts:")
    for alert in stats7["alerts"]:
        if "n+1" in alert["title"].lower():
            print(f"\n  Title: {alert['title']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message']}")
            print(f"  Suggestion: {alert['suggestion']}")
    print()

    print("Example 8: Multiple Alert Categories")
    print("-" * 70)
    toolbar8 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    panel8 = AlertsPanel(toolbar8)
    context8 = await toolbar8.process_request()

    context8.metadata["method"] = "POST"
    context8.metadata["headers"] = {"content-type": "text/html"}
    context8.metadata["response_headers"] = {
        "content-length": str(2 * 1024 * 1024),
        "set-cookie": "token=xyz; Path=/",
    }

    headers_panel_mixed = {
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
    context8.panel_data["HeadersPanel"] = headers_panel_mixed

    sql_panel_mixed = {
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
    context8.panel_data["SQLAlchemyPanel"] = sql_panel_mixed

    stats8 = await panel8.generate_stats(context8)

    print(f"Total Alerts: {stats8['total_alerts']}")
    print(f"Alerts by Severity: {stats8['by_severity']}")
    print(f"Alerts by Category: {stats8['by_category']}")
    print()
    print("Summary by Category:")
    for category, count in stats8["by_category"].items():
        if count > 0:
            print(f"  {category.capitalize()}: {count} alert(s)")
    print()

    print("All Alerts:")
    for i, alert in enumerate(stats8["alerts"], 1):
        print(f"\n  {i}. [{alert['severity'].upper()}] {alert['title']}")
        print(f"     Category: {alert['category']}")
        print(f"     {alert['message'][:80]}...")
    print()

    print("=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
