"""Logging panel for capturing log records during requests."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


class ToolbarLoggingHandler(logging.Handler):
    """Logging handler that captures records for the debug toolbar."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Capture a log record."""
        self.records.append(
            {
                "level": record.levelname,
                "level_no": record.levelno,
                "message": self.format(record),
                "name": record.name,
                "pathname": record.pathname,
                "lineno": record.lineno,
                "funcname": record.funcName,
                "created": record.created,
                "exc_info": record.exc_info is not None,
            }
        )

    def clear(self) -> None:
        """Clear captured records."""
        self.records = []


class LoggingPanel(Panel):
    """Panel displaying log records captured during the request.

    Shows:
    - Log level
    - Logger name
    - Message
    - Source location
    - Exception info (if present)
    """

    panel_id: ClassVar[str] = "LoggingPanel"
    title: ClassVar[str] = "Logging"
    template: ClassVar[str] = "panels/logging.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Logs"

    __slots__ = ("_handler",)

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._handler = ToolbarLoggingHandler()
        self._handler.setFormatter(logging.Formatter("%(message)s"))

    async def process_request(self, context: RequestContext) -> None:
        """Start capturing logs."""
        self._handler.clear()
        logging.root.addHandler(self._handler)

    async def process_response(self, context: RequestContext) -> None:
        """Stop capturing logs."""
        logging.root.removeHandler(self._handler)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate logging statistics."""
        records = list(self._handler.records)

        level_counts: dict[str, int] = {}
        for record in records:
            level = record["level"]
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "records": records,
            "count": len(records),
            "level_counts": level_counts,
            "has_errors": level_counts.get("ERROR", 0) > 0 or level_counts.get("CRITICAL", 0) > 0,
            "has_warnings": level_counts.get("WARNING", 0) > 0,
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing log count."""
        return ""
