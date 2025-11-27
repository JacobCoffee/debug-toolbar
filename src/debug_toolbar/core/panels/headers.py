"""Headers panel for displaying HTTP header analysis."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class HeadersPanel(Panel):
    """Panel displaying detailed HTTP header analysis.

    Analyzes both request and response headers, providing:
    - Categorization by type (authentication, content, caching, CORS, security, custom)
    - Authorization header parsing and analysis
    - Cookie inspection and counting
    - Cache-Control directive parsing
    - Security header detection and validation
    - CORS header analysis
    """

    panel_id: ClassVar[str] = "HeadersPanel"
    title: ClassVar[str] = "Headers"
    template: ClassVar[str] = "panels/headers.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Headers"

    AUTHENTICATION_HEADERS = frozenset(
        {
            "authorization",
            "www-authenticate",
            "proxy-authenticate",
            "proxy-authorization",
        }
    )

    CONTENT_HEADERS = frozenset(
        {
            "content-type",
            "content-length",
            "content-encoding",
            "content-language",
            "content-location",
            "content-md5",
            "content-range",
            "content-disposition",
            "accept",
            "accept-charset",
            "accept-encoding",
            "accept-language",
        }
    )

    CACHING_HEADERS = frozenset(
        {
            "cache-control",
            "pragma",
            "expires",
            "etag",
            "last-modified",
            "if-match",
            "if-none-match",
            "if-modified-since",
            "if-unmodified-since",
            "vary",
            "age",
        }
    )

    CORS_HEADERS = frozenset(
        {
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
            "access-control-allow-credentials",
            "access-control-expose-headers",
            "access-control-max-age",
            "access-control-request-method",
            "access-control-request-headers",
            "origin",
        }
    )

    SECURITY_HEADERS = frozenset(
        {
            "strict-transport-security",
            "content-security-policy",
            "content-security-policy-report-only",
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "referrer-policy",
            "permissions-policy",
            "cross-origin-embedder-policy",
            "cross-origin-opener-policy",
            "cross-origin-resource-policy",
        }
    )

    RECOMMENDED_SECURITY_HEADERS = frozenset(
        {
            "strict-transport-security",
            "x-content-type-options",
            "x-frame-options",
            "content-security-policy",
        }
    )

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate header statistics from context metadata."""
        metadata = context.metadata

        request_headers = metadata.get("headers", {})
        response_headers = metadata.get("response_headers", {})

        return {
            "request_headers": self._analyze_request_headers(request_headers),
            "response_headers": self._analyze_response_headers(response_headers),
        }

    def _analyze_request_headers(self, headers: dict[str, str]) -> dict[str, Any]:
        """Analyze request headers and categorize them.

        Args:
            headers: Dictionary of request headers.

        Returns:
            Dictionary containing categorized headers and analysis.
        """
        categories = {
            "authentication": [],
            "content": [],
            "caching": [],
            "cors": [],
            "custom": [],
        }

        normalized_headers = {k.lower(): v for k, v in headers.items()}

        for header_name, header_value in headers.items():
            normalized_name = header_name.lower()
            header_info = {"name": header_name, "value": header_value}

            if normalized_name in self.AUTHENTICATION_HEADERS:
                categories["authentication"].append(header_info)
            elif normalized_name in self.CONTENT_HEADERS:
                categories["content"].append(header_info)
            elif normalized_name in self.CACHING_HEADERS:
                categories["caching"].append(header_info)
            elif normalized_name in self.CORS_HEADERS:
                categories["cors"].append(header_info)
            elif normalized_name not in {"cookie", "host", "user-agent", "referer"}:
                categories["custom"].append(header_info)

        auth_info = self._parse_authorization(normalized_headers.get("authorization"))
        cookie_info = self._parse_cookies(normalized_headers.get("cookie"))

        return {
            "raw": headers,
            "categories": categories,
            "cookie_count": cookie_info["count"],
            "cookie_names": cookie_info["names"],
            "auth_type": auth_info["type"],
            "auth_detail": auth_info["detail"],
        }

    def _analyze_response_headers(self, headers: dict[str, str]) -> dict[str, Any]:
        """Analyze response headers and categorize them.

        Args:
            headers: Dictionary of response headers.

        Returns:
            Dictionary containing categorized headers and analysis.
        """
        categories = {
            "content": [],
            "caching": [],
            "cors": [],
            "security": [],
            "custom": [],
        }

        normalized_headers = {k.lower(): v for k, v in headers.items()}

        for header_name, header_value in headers.items():
            normalized_name = header_name.lower()
            header_info = {"name": header_name, "value": header_value}

            if normalized_name in self.SECURITY_HEADERS:
                categories["security"].append(header_info)
            elif normalized_name in self.CONTENT_HEADERS:
                categories["content"].append(header_info)
            elif normalized_name in self.CACHING_HEADERS:
                categories["caching"].append(header_info)
            elif normalized_name in self.CORS_HEADERS:
                categories["cors"].append(header_info)
            elif normalized_name not in {"date", "server", "set-cookie"}:
                categories["custom"].append(header_info)

        security_analysis = self._analyze_security_headers(normalized_headers)
        cache_control = self._parse_cache_control(normalized_headers.get("cache-control"))

        return {
            "raw": headers,
            "categories": categories,
            "security_headers": security_analysis,
            "cache_control": cache_control,
        }

    def _parse_authorization(self, auth_header: str | None) -> dict[str, Any]:
        """Parse and analyze Authorization header.

        Args:
            auth_header: The Authorization header value.

        Returns:
            Dictionary with auth type and redacted details.
        """
        if not auth_header:
            return {"type": None, "detail": None}

        parts = auth_header.split(maxsplit=1)
        if not parts:
            return {"type": None, "detail": None}

        auth_type = parts[0]
        auth_value = parts[1] if len(parts) > 1 else ""

        detail = self._redact_auth_value(auth_type, auth_value)

        return {"type": auth_type, "detail": detail}

    def _redact_auth_value(self, auth_type: str, auth_value: str) -> str:
        """Redact sensitive parts of authorization value.

        Args:
            auth_type: The authorization type (e.g., 'Bearer', 'Basic').
            auth_value: The authorization value.

        Returns:
            Redacted authorization value with analysis.
        """
        min_length_for_partial_reveal = 8
        auth_type_lower = auth_type.lower()

        if auth_type_lower == "basic":
            try:
                decoded = base64.b64decode(auth_value).decode("utf-8")
                if ":" in decoded:
                    username, _ = decoded.split(":", 1)
                    return f"Basic (username: {username}, password: [REDACTED])"
            except (ValueError, UnicodeDecodeError):
                return "Basic [REDACTED]"

        if auth_type_lower == "bearer":
            if len(auth_value) > min_length_for_partial_reveal:
                return f"Bearer {auth_value[:4]}...{auth_value[-4:]}"
            return "Bearer [REDACTED]"

        if len(auth_value) > min_length_for_partial_reveal:
            return f"{auth_type} {auth_value[:4]}...{auth_value[-4:]}"

        return f"{auth_type} [REDACTED]"

    def _parse_cookies(self, cookie_header: str | None) -> dict[str, Any]:
        """Parse and count cookies from Cookie header.

        Args:
            cookie_header: The Cookie header value.

        Returns:
            Dictionary with cookie count and names.
        """
        if not cookie_header:
            return {"count": 0, "names": []}

        cookie_parts = [c.strip() for c in cookie_header.split(";")]
        cookie_names = []

        for part in cookie_parts:
            if "=" in part:
                name, _ = part.split("=", 1)
                cookie_names.append(name.strip())

        return {"count": len(cookie_names), "names": cookie_names}

    def _parse_cache_control(self, cache_control: str | None) -> dict[str, Any] | None:
        """Parse Cache-Control header directives.

        Args:
            cache_control: The Cache-Control header value.

        Returns:
            Dictionary of parsed directives, or None if not present.
        """
        if not cache_control:
            return None

        directives = {}
        for raw_directive in cache_control.split(","):
            directive = raw_directive.strip()
            if "=" in directive:
                key, value = directive.split("=", 1)
                directives[key.strip()] = value.strip()
            else:
                directives[directive] = True

        return directives

    def _analyze_security_headers(self, headers: dict[str, str]) -> dict[str, Any]:
        """Analyze security headers and identify missing ones.

        Args:
            headers: Dictionary of normalized (lowercase) headers.

        Returns:
            Dictionary with present and missing security headers.
        """
        present = []
        missing = []

        for header_name in self.SECURITY_HEADERS:
            if header_name in headers:
                present.append(
                    {
                        "name": header_name,
                        "value": headers[header_name],
                        "recommended": header_name in self.RECOMMENDED_SECURITY_HEADERS,
                    }
                )

        for header_name in self.RECOMMENDED_SECURITY_HEADERS:
            if header_name not in headers:
                missing.append(
                    {
                        "name": header_name,
                        "description": self._get_security_header_description(header_name),
                    }
                )

        return {
            "present": present,
            "missing": missing,
        }

    def _get_security_header_description(self, header_name: str) -> str:
        """Get a description for a security header.

        Args:
            header_name: The security header name.

        Returns:
            Description of what the header does.
        """
        descriptions = {
            "strict-transport-security": "Enforces HTTPS connections",
            "x-content-type-options": "Prevents MIME type sniffing",
            "x-frame-options": "Prevents clickjacking attacks",
            "content-security-policy": "Controls resources the browser can load",
            "x-xss-protection": "Enables XSS filtering (legacy)",
            "referrer-policy": "Controls referrer information",
            "permissions-policy": "Controls browser features and APIs",
        }
        return descriptions.get(header_name, "Security header")

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""
