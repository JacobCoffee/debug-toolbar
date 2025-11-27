"""Request panel for displaying request information."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class RequestPanel(Panel):
    """Panel displaying request details.

    Shows:
    - HTTP method and path
    - Query parameters
    - Headers
    - Cookies
    - Request body (if available)
    """

    panel_id: ClassVar[str] = "RequestPanel"
    title: ClassVar[str] = "Request"
    template: ClassVar[str] = "panels/request.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Request"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate request statistics from context metadata."""
        metadata = context.metadata

        return {
            "method": metadata.get("method", ""),
            "path": metadata.get("path", ""),
            "query_string": metadata.get("query_string", ""),
            "query_params": metadata.get("query_params", {}),
            "headers": metadata.get("headers", {}),
            "cookies": metadata.get("cookies", {}),
            "content_type": metadata.get("content_type", ""),
            "content_length": metadata.get("content_length", 0),
            "client_host": metadata.get("client_host", ""),
            "client_port": metadata.get("client_port", 0),
            "scheme": metadata.get("scheme", "http"),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""
