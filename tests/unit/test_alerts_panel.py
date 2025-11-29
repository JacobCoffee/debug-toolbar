"""Tests for the Alerts panel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.core.panels.alerts import Alert, AlertsPanel


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


@pytest.fixture
def alerts_panel(mock_toolbar: MagicMock) -> AlertsPanel:
    """Create an AlertsPanel instance."""
    return AlertsPanel(mock_toolbar)


class TestAlertsPanel:
    """Tests for AlertsPanel."""

    def test_panel_attributes(self, alerts_panel: AlertsPanel) -> None:
        """Test panel class attributes."""
        assert alerts_panel.get_panel_id() == "AlertsPanel"
        assert alerts_panel.title == "Alerts"
        assert alerts_panel.has_content is True
        assert alerts_panel.nav_title == "Alerts"

    @pytest.mark.asyncio
    async def test_generate_stats_no_issues(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test generate_stats with no issues detected."""
        request_context.metadata["method"] = "GET"
        request_context.metadata["headers"] = {}
        request_context.metadata["response_headers"] = {}

        stats = await alerts_panel.generate_stats(request_context)

        assert "alerts" in stats
        assert "total_alerts" in stats
        assert "by_severity" in stats
        assert "by_category" in stats
        assert stats["total_alerts"] == 0

    @pytest.mark.asyncio
    async def test_generate_stats_structure(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test generate_stats returns proper structure."""
        stats = await alerts_panel.generate_stats(request_context)

        assert stats["by_severity"]["critical"] == 0
        assert stats["by_severity"]["warning"] == 0
        assert stats["by_severity"]["info"] == 0

        assert stats["by_category"]["security"] == 0
        assert stats["by_category"]["performance"] == 0
        assert stats["by_category"]["database"] == 0
        assert stats["by_category"]["configuration"] == 0


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self) -> None:
        """Test creating an Alert instance."""
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity="warning",
            category="security",
            suggestion="Test suggestion",
        )

        assert alert.title == "Test Alert"
        assert alert.message == "Test message"
        assert alert.severity == "warning"
        assert alert.category == "security"
        assert alert.suggestion == "Test suggestion"


class TestSecurityHeaderAlerts:
    """Tests for security header alert detection."""

    @pytest.mark.asyncio
    async def test_missing_security_headers(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test alert for missing security headers."""
        request_context.store_panel_data(
            "HeadersPanel",
            "response_headers",
            {
                "raw": {},
                "security_headers": {
                    "present": [],
                    "missing": [
                        {"name": "strict-transport-security", "description": "Enforces HTTPS connections"},
                        {"name": "x-content-type-options", "description": "Prevents MIME type sniffing"},
                    ],
                },
            },
        )

        alerts = alerts_panel._check_security_headers(request_context)

        assert len(alerts) == 2
        assert all(a.severity == "warning" for a in alerts)
        assert all(a.category == "security" for a in alerts)
        assert any("strict-transport-security" in a.title for a in alerts)

    @pytest.mark.asyncio
    async def test_no_missing_security_headers(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test no alerts when all security headers present."""
        request_context.store_panel_data(
            "HeadersPanel",
            "response_headers",
            {
                "raw": {},
                "security_headers": {
                    "present": [
                        {"name": "strict-transport-security", "value": "max-age=31536000"},
                    ],
                    "missing": [],
                },
            },
        )

        alerts = alerts_panel._check_security_headers(request_context)

        assert len(alerts) == 0


class TestCSRFProtectionAlerts:
    """Tests for CSRF protection alert detection."""

    @pytest.mark.asyncio
    async def test_csrf_missing_on_post(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test alert for missing CSRF token on POST request."""
        request_context.metadata["method"] = "POST"
        request_context.metadata["headers"] = {"content-type": "application/x-www-form-urlencoded"}

        alerts = alerts_panel._check_csrf_protection(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].category == "security"
        assert "CSRF" in alerts[0].title

    @pytest.mark.asyncio
    async def test_csrf_present_on_post(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alert when CSRF token present on POST."""
        request_context.metadata["method"] = "POST"
        request_context.metadata["headers"] = {
            "x-csrf-token": "token123",
            "content-type": "application/x-www-form-urlencoded",
        }

        alerts = alerts_panel._check_csrf_protection(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_csrf_not_required_for_get(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no CSRF alert for GET requests."""
        request_context.metadata["method"] = "GET"
        request_context.metadata["headers"] = {}

        alerts = alerts_panel._check_csrf_protection(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_csrf_not_required_for_json_api(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test no CSRF alert for JSON API requests."""
        request_context.metadata["method"] = "POST"
        request_context.metadata["headers"] = {"content-type": "application/json"}

        alerts = alerts_panel._check_csrf_protection(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_csrf_on_put_delete(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test CSRF alert for PUT and DELETE requests."""
        for method in ["PUT", "PATCH", "DELETE"]:
            request_context.metadata["method"] = method
            request_context.metadata["headers"] = {"content-type": "text/html"}

            alerts = alerts_panel._check_csrf_protection(request_context)

            assert len(alerts) == 1


class TestCookieSecurityAlerts:
    """Tests for cookie security alert detection."""

    @pytest.mark.asyncio
    async def test_insecure_cookie_no_secure_flag(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test alert for cookie without Secure flag."""
        request_context.metadata["response_headers"] = {
            "set-cookie": "sessionid=abc123; HttpOnly; SameSite=Lax",
        }

        alerts = alerts_panel._check_cookie_security(request_context)

        assert len(alerts) >= 1
        assert any("Insecure Cookie" in a.title for a in alerts)
        assert any(a.category == "security" for a in alerts)

    @pytest.mark.asyncio
    async def test_session_cookie_no_httponly(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test alert for session cookie without HttpOnly flag."""
        request_context.metadata["response_headers"] = {
            "set-cookie": "sessionid=abc123; Secure; SameSite=Lax",
        }

        alerts = alerts_panel._check_cookie_security(request_context)

        assert len(alerts) >= 1
        assert any("HttpOnly" in a.title for a in alerts)

    @pytest.mark.asyncio
    async def test_cookie_no_samesite(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test alert for cookie without SameSite attribute."""
        request_context.metadata["response_headers"] = {
            "set-cookie": "sessionid=abc123; Secure; HttpOnly",
        }

        alerts = alerts_panel._check_cookie_security(request_context)

        assert len(alerts) >= 1
        assert any("SameSite" in a.title for a in alerts)

    @pytest.mark.asyncio
    async def test_secure_cookie_no_alerts(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alerts for properly configured cookie."""
        request_context.metadata["response_headers"] = {
            "set-cookie": "sessionid=abc123; Secure; HttpOnly; SameSite=Lax",
        }

        alerts = alerts_panel._check_cookie_security(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_cookie_attributes_without_spaces(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test cookie security check handles attributes without spaces after semicolons."""
        request_context.metadata["response_headers"] = {
            "set-cookie": "sessionid=abc;Secure;HttpOnly;SameSite=Lax",
        }

        alerts = alerts_panel._check_cookie_security(request_context)

        assert len(alerts) == 0


class TestDebugModeAlerts:
    """Tests for debug mode alert detection."""

    @pytest.mark.asyncio
    async def test_debug_mode_in_production(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test critical alert when debug mode enabled in production."""
        request_context.store_panel_data("SettingsPanel", "debug", True)
        request_context.store_panel_data("SettingsPanel", "environment", "production")

        alerts = alerts_panel._check_debug_mode(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].category == "configuration"
        assert "Debug Mode" in alerts[0].title

    @pytest.mark.asyncio
    async def test_debug_mode_in_development(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alert when debug mode enabled in development."""
        request_context.store_panel_data("SettingsPanel", "debug", True)
        request_context.store_panel_data("SettingsPanel", "environment", "development")

        alerts = alerts_panel._check_debug_mode(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_debug_mode_disabled(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alert when debug mode disabled."""
        request_context.store_panel_data("SettingsPanel", "debug", False)
        request_context.store_panel_data("SettingsPanel", "environment", "production")

        alerts = alerts_panel._check_debug_mode(request_context)

        assert len(alerts) == 0


class TestResponseSizeAlerts:
    """Tests for response size alert detection."""

    @pytest.mark.asyncio
    async def test_large_response_warning(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test warning for large response (1-5 MB)."""
        request_context.metadata["response_headers"] = {
            "content-length": str(2 * 1024 * 1024),
        }

        alerts = alerts_panel._check_response_size(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].category == "performance"
        assert "Large Response" in alerts[0].title

    @pytest.mark.asyncio
    async def test_very_large_response_critical(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test critical alert for very large response (>5 MB)."""
        request_context.metadata["response_headers"] = {
            "content-length": str(6 * 1024 * 1024),
        }

        alerts = alerts_panel._check_response_size(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].category == "performance"
        assert "Very Large Response" in alerts[0].title

    @pytest.mark.asyncio
    async def test_small_response_no_alert(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alert for small response."""
        request_context.metadata["response_headers"] = {
            "content-length": str(500 * 1024),
        }

        alerts = alerts_panel._check_response_size(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_invalid_content_length(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no error with invalid content-length."""
        request_context.metadata["response_headers"] = {
            "content-length": "invalid",
        }

        alerts = alerts_panel._check_response_size(request_context)

        assert len(alerts) == 0


class TestSlowQueryAlerts:
    """Tests for slow query alert detection."""

    @pytest.mark.asyncio
    async def test_critical_slow_query(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test critical alert for very slow queries (>500ms)."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "queries",
            [
                {"sql": "SELECT * FROM users", "duration_ms": 600},
                {"sql": "SELECT * FROM posts", "duration_ms": 550},
            ],
        )

        alerts = alerts_panel._check_slow_queries(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].category == "database"
        assert "Critical Slow Query" in alerts[0].title
        assert "600.00ms" in alerts[0].message

    @pytest.mark.asyncio
    async def test_warning_slow_query(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test warning for slow queries (100-500ms)."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "queries",
            [
                {"sql": "SELECT * FROM users", "duration_ms": 150},
                {"sql": "SELECT * FROM posts", "duration_ms": 120},
            ],
        )

        alerts = alerts_panel._check_slow_queries(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].category == "database"
        assert "Slow Query Warning" in alerts[0].title

    @pytest.mark.asyncio
    async def test_fast_queries_no_alert(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test no alert for fast queries."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "queries",
            [
                {"sql": "SELECT * FROM users", "duration_ms": 50},
                {"sql": "SELECT * FROM posts", "duration_ms": 30},
            ],
        )

        alerts = alerts_panel._check_slow_queries(request_context)

        assert len(alerts) == 0


class TestNPlusOneAlerts:
    """Tests for N+1 query alert detection."""

    @pytest.mark.asyncio
    async def test_n_plus_one_detection_warning(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test warning for N+1 pattern (3-9 queries)."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "n_plus_one_groups",
            [
                {
                    "count": 5,
                    "origin_display": "views.py:42 in get_users",
                    "suggestion": "Use eager loading",
                },
            ],
        )

        alerts = alerts_panel._check_n_plus_one(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].category == "database"
        assert "N+1 Query Pattern" in alerts[0].title
        assert "5 queries" in alerts[0].title

    @pytest.mark.asyncio
    async def test_n_plus_one_detection_critical(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test critical alert for severe N+1 pattern (>=10 queries)."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "n_plus_one_groups",
            [
                {
                    "count": 15,
                    "origin_display": "views.py:42 in get_users",
                    "suggestion": "Use eager loading",
                },
            ],
        )

        alerts = alerts_panel._check_n_plus_one(request_context)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_no_n_plus_one_below_threshold(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test no alert for queries below N+1 threshold."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "n_plus_one_groups",
            [
                {
                    "count": 2,
                    "origin_display": "views.py:42 in get_users",
                    "suggestion": "Use eager loading",
                },
            ],
        )

        alerts = alerts_panel._check_n_plus_one(request_context)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_multiple_n_plus_one_patterns(
        self, alerts_panel: AlertsPanel, request_context: RequestContext
    ) -> None:
        """Test detection of multiple N+1 patterns."""
        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "n_plus_one_groups",
            [
                {
                    "count": 5,
                    "origin_display": "views.py:42 in get_users",
                    "suggestion": "Use eager loading",
                },
                {
                    "count": 8,
                    "origin_display": "views.py:50 in get_posts",
                    "suggestion": "Use eager loading",
                },
            ],
        )

        alerts = alerts_panel._check_n_plus_one(request_context)

        assert len(alerts) == 2


class TestIntegrationAlerts:
    """Integration tests for multiple alert types."""

    @pytest.mark.asyncio
    async def test_multiple_alert_types(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test multiple different alert types together."""
        request_context.metadata["method"] = "POST"
        request_context.metadata["headers"] = {"content-type": "text/html"}
        request_context.metadata["response_headers"] = {
            "content-length": str(6 * 1024 * 1024),
            "set-cookie": "session=abc; HttpOnly",
        }

        request_context.store_panel_data(
            "HeadersPanel",
            "response_headers",
            {
                "raw": {},
                "security_headers": {
                    "present": [],
                    "missing": [
                        {"name": "strict-transport-security", "description": "Enforces HTTPS"},
                    ],
                },
            },
        )

        request_context.store_panel_data(
            "SQLAlchemyPanel",
            "queries",
            [{"sql": "SELECT * FROM users", "duration_ms": 600}],
        )

        stats = await alerts_panel.generate_stats(request_context)

        assert stats["total_alerts"] >= 4
        assert stats["by_severity"]["critical"] >= 1
        assert stats["by_severity"]["warning"] >= 1

    @pytest.mark.asyncio
    async def test_alert_categorization(self, alerts_panel: AlertsPanel, request_context: RequestContext) -> None:
        """Test alerts are properly categorized."""
        request_context.metadata["response_headers"] = {
            "content-length": str(6 * 1024 * 1024),
            "set-cookie": "session=abc",
        }

        request_context.store_panel_data(
            "HeadersPanel",
            "response_headers",
            {
                "raw": {},
                "security_headers": {
                    "present": [],
                    "missing": [
                        {"name": "x-frame-options", "description": "Prevents clickjacking"},
                    ],
                },
            },
        )

        stats = await alerts_panel.generate_stats(request_context)

        assert stats["by_category"]["security"] >= 2
        assert stats["by_category"]["performance"] >= 1
