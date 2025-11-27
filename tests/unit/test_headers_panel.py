"""Tests for the Headers panel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.core.panels.headers import HeadersPanel


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


@pytest.fixture
def headers_panel(mock_toolbar: MagicMock) -> HeadersPanel:
    """Create a HeadersPanel instance."""
    return HeadersPanel(mock_toolbar)


class TestHeadersPanel:
    """Tests for HeadersPanel."""

    def test_panel_attributes(self, headers_panel: HeadersPanel) -> None:
        """Test panel class attributes."""
        assert headers_panel.get_panel_id() == "HeadersPanel"
        assert headers_panel.title == "Headers"
        assert headers_panel.has_content is True
        assert headers_panel.nav_title == "Headers"

    @pytest.mark.asyncio
    async def test_generate_stats_empty(self, headers_panel: HeadersPanel, request_context: RequestContext) -> None:
        """Test generate_stats with no headers."""
        stats = await headers_panel.generate_stats(request_context)

        assert "request_headers" in stats
        assert "response_headers" in stats
        assert stats["request_headers"]["raw"] == {}
        assert stats["response_headers"]["raw"] == {}

    @pytest.mark.asyncio
    async def test_generate_stats_with_request_headers(
        self, headers_panel: HeadersPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats with request headers."""
        request_context.metadata["headers"] = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value",
        }

        stats = await headers_panel.generate_stats(request_context)
        request_headers = stats["request_headers"]

        assert request_headers["raw"]["Content-Type"] == "application/json"
        assert request_headers["auth_type"] == "Bearer"
        assert "token123" not in request_headers["auth_detail"]

    @pytest.mark.asyncio
    async def test_generate_stats_with_response_headers(
        self, headers_panel: HeadersPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats with response headers."""
        request_context.metadata["response_headers"] = {
            "Content-Type": "text/html",
            "Cache-Control": "max-age=3600, public",
            "X-Frame-Options": "DENY",
        }

        stats = await headers_panel.generate_stats(request_context)
        response_headers = stats["response_headers"]

        assert response_headers["raw"]["Content-Type"] == "text/html"
        assert response_headers["cache_control"] is not None
        assert "max-age" in response_headers["cache_control"]


class TestRequestHeaderAnalysis:
    """Tests for request header analysis."""

    def test_categorize_authentication_headers(self, headers_panel: HeadersPanel) -> None:
        """Test authentication headers are categorized correctly."""
        headers = {"Authorization": "Bearer token", "WWW-Authenticate": "Basic"}
        result = headers_panel._analyze_request_headers(headers)

        auth_category = result["categories"]["authentication"]
        assert len(auth_category) == 2
        assert any(h["name"] == "Authorization" for h in auth_category)

    def test_categorize_content_headers(self, headers_panel: HeadersPanel) -> None:
        """Test content headers are categorized correctly."""
        headers = {
            "Content-Type": "application/json",
            "Content-Length": "1234",
            "Accept": "application/json",
        }
        result = headers_panel._analyze_request_headers(headers)

        content_category = result["categories"]["content"]
        assert len(content_category) == 3

    def test_categorize_caching_headers(self, headers_panel: HeadersPanel) -> None:
        """Test caching headers are categorized correctly."""
        headers = {
            "Cache-Control": "no-cache",
            "If-None-Match": "etag123",
            "If-Modified-Since": "Mon, 01 Jan 2024 00:00:00 GMT",
        }
        result = headers_panel._analyze_request_headers(headers)

        caching_category = result["categories"]["caching"]
        assert len(caching_category) == 3

    def test_categorize_cors_headers(self, headers_panel: HeadersPanel) -> None:
        """Test CORS headers are categorized correctly."""
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        }
        result = headers_panel._analyze_request_headers(headers)

        cors_category = result["categories"]["cors"]
        assert len(cors_category) == 2

    def test_categorize_custom_headers(self, headers_panel: HeadersPanel) -> None:
        """Test custom headers are categorized correctly."""
        headers = {
            "X-Custom-Header": "value",
            "X-Request-ID": "req123",
        }
        result = headers_panel._analyze_request_headers(headers)

        custom_category = result["categories"]["custom"]
        assert len(custom_category) == 2


class TestAuthorizationParsing:
    """Tests for Authorization header parsing."""

    def test_parse_bearer_token(self, headers_panel: HeadersPanel) -> None:
        """Test parsing Bearer token."""
        auth_info = headers_panel._parse_authorization("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

        assert auth_info["type"] == "Bearer"
        assert auth_info["detail"].startswith("Bearer eyJh")
        assert auth_info["detail"].endswith("...VCJ9")

    def test_parse_basic_auth(self, headers_panel: HeadersPanel) -> None:
        """Test parsing Basic auth."""
        import base64

        credentials = base64.b64encode(b"username:password").decode("ascii")
        auth_info = headers_panel._parse_authorization(f"Basic {credentials}")

        assert auth_info["type"] == "Basic"
        assert "username: username" in auth_info["detail"]
        assert "[REDACTED]" in auth_info["detail"]
        assert "password:" in auth_info["detail"]

    def test_parse_no_authorization(self, headers_panel: HeadersPanel) -> None:
        """Test parsing when no Authorization header present."""
        auth_info = headers_panel._parse_authorization(None)

        assert auth_info["type"] is None
        assert auth_info["detail"] is None

    def test_parse_custom_auth_scheme(self, headers_panel: HeadersPanel) -> None:
        """Test parsing custom auth scheme."""
        auth_info = headers_panel._parse_authorization("Digest username=test")

        assert auth_info["type"] == "Digest"
        assert "Digest" in auth_info["detail"]
        assert "user" in auth_info["detail"]


class TestCookieParsing:
    """Tests for Cookie header parsing."""

    def test_parse_single_cookie(self, headers_panel: HeadersPanel) -> None:
        """Test parsing single cookie."""
        cookie_info = headers_panel._parse_cookies("sessionid=abc123")

        assert cookie_info["count"] == 1
        assert "sessionid" in cookie_info["names"]

    def test_parse_multiple_cookies(self, headers_panel: HeadersPanel) -> None:
        """Test parsing multiple cookies."""
        cookie_info = headers_panel._parse_cookies("sessionid=abc123; csrftoken=xyz789; user=john")

        assert cookie_info["count"] == 3
        assert "sessionid" in cookie_info["names"]
        assert "csrftoken" in cookie_info["names"]
        assert "user" in cookie_info["names"]

    def test_parse_no_cookies(self, headers_panel: HeadersPanel) -> None:
        """Test parsing when no cookies present."""
        cookie_info = headers_panel._parse_cookies(None)

        assert cookie_info["count"] == 0
        assert cookie_info["names"] == []


class TestResponseHeaderAnalysis:
    """Tests for response header analysis."""

    def test_categorize_security_headers(self, headers_panel: HeadersPanel) -> None:
        """Test security headers are categorized correctly."""
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'",
        }
        result = headers_panel._analyze_response_headers(headers)

        security_category = result["categories"]["security"]
        assert len(security_category) == 3

    def test_security_header_analysis_present(self, headers_panel: HeadersPanel) -> None:
        """Test security header analysis identifies present headers."""
        headers = {
            "strict-transport-security": "max-age=31536000",
            "x-content-type-options": "nosniff",
        }
        result = headers_panel._analyze_response_headers(headers)

        present = result["security_headers"]["present"]
        assert len(present) >= 2
        assert any(h["name"] == "strict-transport-security" for h in present)

    def test_security_header_analysis_missing(self, headers_panel: HeadersPanel) -> None:
        """Test security header analysis identifies missing headers."""
        headers = {}
        result = headers_panel._analyze_response_headers(headers)

        missing = result["security_headers"]["missing"]
        assert len(missing) > 0
        header_names = [h["name"] for h in missing]
        assert "strict-transport-security" in header_names


class TestCacheControlParsing:
    """Tests for Cache-Control header parsing."""

    def test_parse_cache_control_simple(self, headers_panel: HeadersPanel) -> None:
        """Test parsing simple Cache-Control directives."""
        cache_control = headers_panel._parse_cache_control("max-age=3600, public")

        assert cache_control is not None
        assert cache_control["max-age"] == "3600"
        assert cache_control["public"] is True

    def test_parse_cache_control_complex(self, headers_panel: HeadersPanel) -> None:
        """Test parsing complex Cache-Control directives."""
        cache_control = headers_panel._parse_cache_control("no-cache, no-store, must-revalidate, max-age=0")

        assert cache_control is not None
        assert cache_control["no-cache"] is True
        assert cache_control["no-store"] is True
        assert cache_control["must-revalidate"] is True
        assert cache_control["max-age"] == "0"

    def test_parse_cache_control_none(self, headers_panel: HeadersPanel) -> None:
        """Test parsing when no Cache-Control present."""
        cache_control = headers_panel._parse_cache_control(None)

        assert cache_control is None


class TestSecurityHeaderDescriptions:
    """Tests for security header descriptions."""

    def test_get_known_security_header_description(self, headers_panel: HeadersPanel) -> None:
        """Test getting description for known security header."""
        desc = headers_panel._get_security_header_description("strict-transport-security")

        assert desc != ""
        assert "HTTPS" in desc

    def test_get_unknown_security_header_description(self, headers_panel: HeadersPanel) -> None:
        """Test getting description for unknown security header."""
        desc = headers_panel._get_security_header_description("x-unknown-header")

        assert desc == "Security header"
