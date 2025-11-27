"""Base panel class for debug toolbar panels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


class Panel(ABC):
    """Abstract base class for debug toolbar panels.

    Panels are responsible for collecting and displaying specific types of
    debug information. Each panel should override the abstract methods to
    provide its functionality.

    Class Attributes:
        panel_id: Unique identifier for the panel. Defaults to class name.
        title: Display title shown in the toolbar.
        template: Template name for rendering the panel content.
        has_content: Whether this panel has detailed content.
        nav_title: Short title for the toolbar navigation.
        nav_subtitle: Subtitle shown in the toolbar navigation.
    """

    panel_id: ClassVar[str] = ""
    title: ClassVar[str] = ""
    template: ClassVar[str] = ""
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = ""
    nav_subtitle: ClassVar[str] = ""

    __slots__ = ("_enabled", "_toolbar")

    def __init__(self, toolbar: DebugToolbar) -> None:
        """Initialize the panel.

        Args:
            toolbar: The parent DebugToolbar instance.
        """
        self._toolbar = toolbar
        self._enabled = True

    @classmethod
    def get_panel_id(cls) -> str:
        """Get the panel's unique identifier.

        Returns:
            The panel_id class variable, or the class name if not set.
        """
        return cls.panel_id or cls.__name__

    @property
    def enabled(self) -> bool:
        """Check if the panel is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether the panel is enabled."""
        self._enabled = value

    @abstractmethod
    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate statistics for this panel.

        This method is called during request processing to collect data.

        Args:
            context: The current request context.

        Returns:
            Dictionary of statistics data.
        """
        ...

    async def process_request(self, context: RequestContext) -> None:
        """Process the request phase.

        Override this to perform actions at the start of request processing.

        Args:
            context: The current request context.
        """

    async def process_response(self, context: RequestContext) -> None:
        """Process the response phase.

        Override this to perform actions at the end of request processing.

        Args:
            context: The current request context.
        """

    def get_stats(self, context: RequestContext) -> dict[str, Any]:
        """Get stored stats from context.

        Args:
            context: The current request context.

        Returns:
            Dictionary of panel stats.
        """
        return context.get_panel_data(self.get_panel_id())

    def record_stats(self, context: RequestContext, stats: dict[str, Any]) -> None:
        """Record stats to the context.

        Args:
            context: The current request context.
            stats: Dictionary of stats to store.
        """
        panel_id = self.get_panel_id()
        for key, value in stats.items():
            context.store_panel_data(panel_id, key, value)

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data.

        Override this to contribute to the Server-Timing header.

        Args:
            context: The current request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        return {}

    def get_nav_title(self) -> str:
        """Get the navigation title.

        Returns:
            The nav_title class variable, or title if not set.
        """
        return self.nav_title or self.title

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle.

        Returns:
            The nav_subtitle class variable.
        """
        return self.nav_subtitle
