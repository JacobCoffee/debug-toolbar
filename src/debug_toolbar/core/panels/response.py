"""Response panel for displaying response information."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class ResponsePanel(Panel):
    """Panel displaying response details.

    Shows:
    - Status code
    - Response headers
    - Content type
    - Content length
    """

    panel_id: ClassVar[str] = "ResponsePanel"
    title: ClassVar[str] = "Response"
    template: ClassVar[str] = "panels/response.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Response"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate response statistics from context metadata."""
        metadata = context.metadata

        return {
            "status_code": metadata.get("status_code", 0),
            "reason_phrase": metadata.get("reason_phrase", ""),
            "headers": metadata.get("response_headers", {}),
            "content_type": metadata.get("response_content_type", ""),
            "content_length": metadata.get("response_content_length", 0),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""
