"""Alerts panel for proactive issue detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


@dataclass
class Alert:
    """Represents a single alert."""

    title: str
    message: str
    severity: str
    category: str
    suggestion: str


class AlertsPanel(Panel):
    """Panel displaying proactive alerts for potential issues.

    Detects and warns about:
    - Security issues (CSRF, insecure cookies, missing headers)
    - Performance problems (slow queries, large responses)
    - Database issues (N+1 queries)
    - Configuration problems (debug mode in production)
    """

    panel_id: ClassVar[str] = "AlertsPanel"
    title: ClassVar[str] = "Alerts"
    template: ClassVar[str] = "panels/alerts.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Alerts"

    SEVERITY_CRITICAL: ClassVar[str] = "critical"
    SEVERITY_WARNING: ClassVar[str] = "warning"
    SEVERITY_INFO: ClassVar[str] = "info"

    CATEGORY_SECURITY: ClassVar[str] = "security"
    CATEGORY_PERFORMANCE: ClassVar[str] = "performance"
    CATEGORY_DATABASE: ClassVar[str] = "database"
    CATEGORY_CONFIGURATION: ClassVar[str] = "configuration"

    RESPONSE_SIZE_WARNING_BYTES: ClassVar[int] = 1024 * 1024
    RESPONSE_SIZE_CRITICAL_BYTES: ClassVar[int] = 5 * 1024 * 1024

    QUERY_TIME_WARNING_MS: ClassVar[float] = 100.0
    QUERY_TIME_CRITICAL_MS: ClassVar[float] = 500.0

    N_PLUS_ONE_THRESHOLD: ClassVar[int] = 3
    N_PLUS_ONE_CRITICAL_THRESHOLD: ClassVar[int] = 10

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate alert statistics from context metadata."""
        alerts: list[Alert] = []

        alerts.extend(self._check_security_headers(context))
        alerts.extend(self._check_csrf_protection(context))
        alerts.extend(self._check_cookie_security(context))
        alerts.extend(self._check_debug_mode(context))
        alerts.extend(self._check_response_size(context))
        alerts.extend(self._check_slow_queries(context))
        alerts.extend(self._check_n_plus_one(context))

        by_severity: dict[str, int] = {
            self.SEVERITY_CRITICAL: 0,
            self.SEVERITY_WARNING: 0,
            self.SEVERITY_INFO: 0,
        }
        by_category: dict[str, int] = {
            self.CATEGORY_SECURITY: 0,
            self.CATEGORY_PERFORMANCE: 0,
            self.CATEGORY_DATABASE: 0,
            self.CATEGORY_CONFIGURATION: 0,
        }

        for alert in alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            by_category[alert.category] = by_category.get(alert.category, 0) + 1

        alert_dicts = [
            {
                "title": a.title,
                "message": a.message,
                "severity": a.severity,
                "category": a.category,
                "suggestion": a.suggestion,
            }
            for a in alerts
        ]

        return {
            "alerts": alert_dicts,
            "total_alerts": len(alerts),
            "by_severity": by_severity,
            "by_category": by_category,
        }

    def _check_security_headers(self, context: RequestContext) -> list[Alert]:
        """Check for missing security headers."""
        alerts = []
        headers_data = context.get_panel_data("HeadersPanel")
        if not headers_data:
            return alerts

        response_headers = headers_data.get("response_headers", {})
        security_headers = response_headers.get("security_headers", {})
        missing_headers = security_headers.get("missing", [])

        for missing in missing_headers:
            header_name = missing.get("name", "")
            description = missing.get("description", "Security header")

            alerts.append(
                Alert(
                    title=f"Missing Security Header: {header_name}",
                    message=f"{description}. This header is recommended for production applications.",
                    severity=self.SEVERITY_WARNING,
                    category=self.CATEGORY_SECURITY,
                    suggestion=(
                        f"Add the '{header_name}' header to your response middleware or application configuration."
                    ),
                )
            )

        return alerts

    def _check_csrf_protection(self, context: RequestContext) -> list[Alert]:
        """Check for missing CSRF protection on state-changing requests."""
        alerts = []
        metadata = context.metadata
        method = metadata.get("method", "GET").upper()
        headers = metadata.get("headers", {})

        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            csrf_headers = {
                "x-csrf-token",
                "x-csrftoken",
                "csrf-token",
            }
            normalized_headers = {k.lower() for k in headers}

            if not csrf_headers.intersection(normalized_headers):
                content_type = next((v for k, v in headers.items() if k.lower() == "content-type"), "")
                if "application/json" not in content_type.lower():
                    alerts.append(
                        Alert(
                            title="Potential Missing CSRF Protection",
                            message=f"State-changing request ({method}) detected without CSRF token header. "
                            "This may indicate missing CSRF protection.",
                            severity=self.SEVERITY_WARNING,
                            category=self.CATEGORY_SECURITY,
                            suggestion=(
                                "Implement CSRF protection middleware or ensure your application "
                                "validates CSRF tokens for state-changing requests."
                            ),
                        )
                    )

        return alerts

    def _check_cookie_security(self, context: RequestContext) -> list[Alert]:
        """Check for insecure cookie settings."""
        alerts = []
        metadata = context.metadata
        response_headers = metadata.get("response_headers", {})
        set_cookie_headers = [v for k, v in response_headers.items() if k.lower() == "set-cookie"]

        for cookie in set_cookie_headers:
            cookie_parts = cookie.split(";")

            if not any(part.strip().lower() == "secure" for part in cookie_parts):
                alerts.append(
                    Alert(
                        title="Insecure Cookie Detected",
                        message=(
                            "Cookie set without 'Secure' flag. This allows the cookie to be sent over "
                            "unencrypted HTTP connections."
                        ),
                        severity=self.SEVERITY_WARNING,
                        category=self.CATEGORY_SECURITY,
                        suggestion=(
                            "Add the 'Secure' flag to all cookies in production to ensure they are only "
                            "sent over HTTPS."
                        ),
                    )
                )

            has_httponly = any(part.strip().lower() == "httponly" for part in cookie_parts)
            if not has_httponly and "session" in cookie.lower():
                alerts.append(
                    Alert(
                        title="Cookie Missing HttpOnly Flag",
                        message=(
                            "Session cookie set without 'HttpOnly' flag. This makes it accessible to "
                            "JavaScript, increasing XSS risk."
                        ),
                        severity=self.SEVERITY_WARNING,
                        category=self.CATEGORY_SECURITY,
                        suggestion="Add the 'HttpOnly' flag to session cookies to prevent JavaScript access.",
                    )
                )

            if not any(part.strip().lower().startswith("samesite") for part in cookie_parts):
                alerts.append(
                    Alert(
                        title="Cookie Missing SameSite Attribute",
                        message="Cookie set without 'SameSite' attribute. This may allow CSRF attacks.",
                        severity=self.SEVERITY_INFO,
                        category=self.CATEGORY_SECURITY,
                        suggestion="Add 'SameSite=Lax' or 'SameSite=Strict' to cookies to prevent CSRF attacks.",
                    )
                )

        return alerts

    def _check_debug_mode(self, context: RequestContext) -> list[Alert]:
        """Check if debug mode appears to be enabled in production."""
        alerts = []
        settings_data = context.get_panel_data("SettingsPanel")

        is_debug = settings_data.get("debug", False) if settings_data else False
        env_value = settings_data.get("environment", "") if settings_data else ""
        environment = env_value.lower() if isinstance(env_value, str) else ""

        if is_debug and environment in {"production", "prod"}:
            alerts.append(
                Alert(
                    title="Debug Mode Enabled in Production",
                    message=(
                        "Debug mode is enabled in what appears to be a production environment. "
                        "This exposes sensitive information and reduces performance."
                    ),
                    severity=self.SEVERITY_CRITICAL,
                    category=self.CATEGORY_CONFIGURATION,
                    suggestion=(
                        "Set debug=False in production environments. Use environment variables or "
                        "configuration files to manage this setting."
                    ),
                )
            )

        return alerts

    def _check_response_size(self, context: RequestContext) -> list[Alert]:
        """Check for large response bodies."""
        alerts = []
        metadata = context.metadata
        response_headers = metadata.get("response_headers", {})
        content_length = next((v for k, v in response_headers.items() if k.lower() == "content-length"), "0")

        try:
            size_bytes = int(content_length)
        except (ValueError, TypeError):
            return alerts

        if size_bytes >= self.RESPONSE_SIZE_CRITICAL_BYTES:
            size_mb = size_bytes / (1024 * 1024)
            alerts.append(
                Alert(
                    title="Very Large Response Body",
                    message=(
                        f"Response body is {size_mb:.2f} MB, which may cause performance issues and slow page loads."
                    ),
                    severity=self.SEVERITY_CRITICAL,
                    category=self.CATEGORY_PERFORMANCE,
                    suggestion=(
                        "Consider implementing pagination, lazy loading, or response compression. "
                        "For APIs, limit the number of records returned per request."
                    ),
                )
            )
        elif size_bytes >= self.RESPONSE_SIZE_WARNING_BYTES:
            size_mb = size_bytes / (1024 * 1024)
            alerts.append(
                Alert(
                    title="Large Response Body",
                    message=f"Response body is {size_mb:.2f} MB. This may impact performance.",
                    severity=self.SEVERITY_WARNING,
                    category=self.CATEGORY_PERFORMANCE,
                    suggestion="Consider implementing pagination or response compression to reduce response size.",
                )
            )

        return alerts

    def _check_slow_queries(self, context: RequestContext) -> list[Alert]:
        """Check for slow database queries."""
        alerts = []
        sql_data = context.get_panel_data("SQLAlchemyPanel")
        if not sql_data:
            return alerts

        queries = sql_data.get("queries", [])
        critical_queries = [q for q in queries if q.get("duration_ms", 0) >= self.QUERY_TIME_CRITICAL_MS]
        warning_queries = [
            q for q in queries if self.QUERY_TIME_WARNING_MS <= q.get("duration_ms", 0) < self.QUERY_TIME_CRITICAL_MS
        ]

        if critical_queries:
            slowest = max(critical_queries, key=lambda q: q.get("duration_ms", 0))
            duration = slowest.get("duration_ms", 0)
            alerts.append(
                Alert(
                    title=f"Critical Slow Query Detected ({len(critical_queries)} total)",
                    message=(
                        f"Found {len(critical_queries)} database queries exceeding "
                        f"{self.QUERY_TIME_CRITICAL_MS}ms. Slowest query took {duration:.2f}ms."
                    ),
                    severity=self.SEVERITY_CRITICAL,
                    category=self.CATEGORY_DATABASE,
                    suggestion=(
                        "Review the SQL panel for slow queries. Add database indexes, optimize query logic, "
                        "or use query result caching to improve performance."
                    ),
                )
            )
        elif warning_queries:
            slowest = max(warning_queries, key=lambda q: q.get("duration_ms", 0))
            duration = slowest.get("duration_ms", 0)
            alerts.append(
                Alert(
                    title=f"Slow Query Warning ({len(warning_queries)} total)",
                    message=f"Found {len(warning_queries)} database queries exceeding {self.QUERY_TIME_WARNING_MS}ms. "
                    f"Slowest query took {duration:.2f}ms.",
                    severity=self.SEVERITY_WARNING,
                    category=self.CATEGORY_DATABASE,
                    suggestion="Review the SQL panel for queries that could benefit from optimization or indexing.",
                )
            )

        return alerts

    def _check_n_plus_one(self, context: RequestContext) -> list[Alert]:
        """Check for N+1 query patterns."""
        alerts = []
        sql_data = context.get_panel_data("SQLAlchemyPanel")
        if not sql_data:
            return alerts

        n_plus_one_groups = sql_data.get("n_plus_one_groups", [])

        for group in n_plus_one_groups:
            count = group.get("count", 0)
            if count >= self.N_PLUS_ONE_THRESHOLD:
                origin = group.get("origin_display", "unknown location")
                severity = (
                    self.SEVERITY_CRITICAL if count >= self.N_PLUS_ONE_CRITICAL_THRESHOLD else self.SEVERITY_WARNING
                )

                alerts.append(
                    Alert(
                        title=f"N+1 Query Pattern Detected ({count} queries)",
                        message=(
                            f"Detected {count} similar queries from {origin}. This is likely an N+1 query problem."
                        ),
                        severity=severity,
                        category=self.CATEGORY_DATABASE,
                        suggestion=group.get(
                            "suggestion",
                            (
                                "Use SQLAlchemy's eager loading (joinedload/selectinload) to fetch "
                                "related data in fewer queries."
                            ),
                        ),
                    )
                )

        return alerts

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing alert count and severity."""
        return ""
