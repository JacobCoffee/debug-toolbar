"""Timer panel for request timing information."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class TimerPanel(Panel):
    """Panel displaying request timing information.

    Tracks:
    - Total request duration
    - Time spent in various phases
    - CPU time (user and system)
    """

    panel_id: ClassVar[str] = "TimerPanel"
    title: ClassVar[str] = "Time"
    template: ClassVar[str] = "panels/timer.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Time"

    __slots__ = ("_start_cpu_times", "_start_time")

    def __init__(self, toolbar: Any) -> None:
        super().__init__(toolbar)
        self._start_time: float = 0.0
        self._start_cpu_times: tuple[float, float] = (0.0, 0.0)

    async def process_request(self, context: RequestContext) -> None:
        """Record the start time."""
        self._start_time = time.perf_counter()
        cpu = time.process_time()
        self._start_cpu_times = (cpu, cpu)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate timing statistics."""
        end_time = time.perf_counter()
        end_cpu = time.process_time()

        total_time = end_time - self._start_time
        cpu_time = end_cpu - self._start_cpu_times[0]

        stats = {
            "total_time": total_time,
            "total_time_ms": total_time * 1000,
            "cpu_time": cpu_time,
            "cpu_time_ms": cpu_time * 1000,
        }

        context.record_timing("total_request_time", total_time)
        return stats

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing data."""
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {
            "total": stats.get("total_time", 0),
            "cpu": stats.get("cpu_time", 0),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing time."""
        return ""
