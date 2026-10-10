"""Starlette routes panel for the debug toolbar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class RoutesPanel(Panel):
    """Panel displaying Starlette application routes.

    Shows:
    - All registered routes (Route, Mount, WebSocketRoute)
    - HTTP methods for each route
    - Handler names and paths
    - Current matched route
    """

    panel_id: ClassVar[str] = "StarletteRoutesPanel"
    title: ClassVar[str] = "Routes"
    template: ClassVar[str] = ""
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Routes"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate route statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary containing route information.
        """
        routes_info = context.metadata.get("routes", [])

        return {
            "routes": routes_info,
            "route_count": len(routes_info),
            "current_route": context.metadata.get("matched_route", ""),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing route count."""
        return ""
