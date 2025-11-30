"""Async profiling panel for tracking async task execution."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from debug_toolbar.core.panel import Panel
from debug_toolbar.core.panels.async_profiler.taskfactory import TaskFactoryBackend

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.panels.async_profiler.base import AsyncProfilerBackend
    from debug_toolbar.core.panels.async_profiler.detector import BlockingCallDetector, EventLoopLagMonitor
    from debug_toolbar.core.toolbar import DebugToolbar

logger = logging.getLogger(__name__)


class AsyncProfilerPanel(Panel):
    """Panel for profiling async task execution and event loop behavior.

    Tracks:
    - Async task creation and completion via task factory hooks
    - Blocking calls that stall the event loop
    - Event loop lag monitoring
    - Timeline visualization of concurrent execution

    Configure via toolbar config:
        async_profiler_backend: "taskfactory" | "yappi" | "auto" (default: "auto")
        async_blocking_threshold_ms: float (default: 100.0)
        async_enable_blocking_detection: bool (default: True)
        async_enable_event_loop_monitoring: bool (default: True)
        async_capture_task_stacks: bool (default: True)
        async_max_stack_depth: int (default: 10)
    """

    panel_id: ClassVar[str] = "AsyncProfilerPanel"
    title: ClassVar[str] = "Async"
    template: ClassVar[str] = "panels/async_profiler.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Async"

    __slots__ = (
        "_backend",
        "_backend_name",
        "_blocking_count",
        "_blocking_detector",
        "_lag_monitor",
        "_profiling_overhead",
        "_task_count",
    )

    def __init__(self, toolbar: DebugToolbar) -> None:
        """Initialize the async profiler panel.

        Args:
            toolbar: The parent DebugToolbar instance.
        """
        super().__init__(toolbar)
        self._backend_name = self._select_backend()
        self._backend = self._create_backend(self._backend_name)
        self._blocking_detector: BlockingCallDetector | None = None
        self._lag_monitor: EventLoopLagMonitor | None = None
        self._profiling_overhead: float = 0.0
        self._task_count: int = 0
        self._blocking_count: int = 0

    def _get_config(self, key: str, default: Any) -> Any:
        """Get configuration value from toolbar config.

        Args:
            key: Configuration key to retrieve.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        config = getattr(self._toolbar, "config", None)
        if config is None:
            return default
        return getattr(config, key, default)

    def _select_backend(self) -> Literal["taskfactory", "yappi"]:
        """Determine which async profiling backend to use.

        Returns:
            Name of the selected backend.
        """
        config_backend = self._get_config("async_profiler_backend", "auto")

        if config_backend == "yappi":
            try:
                from debug_toolbar.core.panels.async_profiler.yappi_backend import (  # type: ignore[import-not-found]
                    YappiBackend,
                )

                if YappiBackend.is_available():
                    return "yappi"
            except ImportError:
                pass  # Yappi is not installed; fall back to taskfactory backend.
            logger.info("Yappi requested but not available, falling back to taskfactory")
            return "taskfactory"

        if config_backend == "taskfactory":
            return "taskfactory"

        try:
            from debug_toolbar.core.panels.async_profiler.yappi_backend import (  # type: ignore[import-not-found]
                YappiBackend,
            )

            if YappiBackend.is_available():
                return "yappi"
        except ImportError:
            pass  # Yappi backend is not available; fall back to taskfactory backend.

        return "taskfactory"

    def _create_backend(self, backend_name: str) -> AsyncProfilerBackend:
        """Create an instance of the specified backend.

        Args:
            backend_name: Name of the backend to create.

        Returns:
            Instance of the async profiler backend.
        """
        capture_stacks = self._get_config("async_capture_task_stacks", True)  # noqa: FBT003
        max_stack_depth = self._get_config("async_max_stack_depth", 10)

        if backend_name == "yappi":
            try:
                from debug_toolbar.core.panels.async_profiler.yappi_backend import (  # type: ignore[import-not-found]
                    YappiBackend,
                )

                return YappiBackend(
                    capture_stacks=capture_stacks,
                    max_stack_depth=max_stack_depth,
                )
            except ImportError:
                pass  # Yappi not available; will use TaskFactoryBackend instead.

        return TaskFactoryBackend(
            capture_stacks=capture_stacks,
            max_stack_depth=max_stack_depth,
        )

    def _create_detectors(self) -> None:
        """Create detection utilities if enabled."""
        if self._get_config("async_enable_blocking_detection", True):  # noqa: FBT003
            from debug_toolbar.core.panels.async_profiler.detector import BlockingCallDetector

            threshold = self._get_config("async_blocking_threshold_ms", 100.0)
            self._blocking_detector = BlockingCallDetector(threshold_ms=threshold)

        if self._get_config("async_enable_event_loop_monitoring", True):  # noqa: FBT003
            from debug_toolbar.core.panels.async_profiler.detector import EventLoopLagMonitor

            threshold = self._get_config("async_event_loop_lag_threshold_ms", 10.0)
            self._lag_monitor = EventLoopLagMonitor(lag_threshold_ms=threshold)

    async def process_request(self, context: RequestContext) -> None:
        """Start async profiling at request start.

        Args:
            context: The current request context.
        """
        start = time.perf_counter()

        try:
            loop = asyncio.get_running_loop()
            self._backend.start(loop)

            self._create_detectors()

            if self._blocking_detector:
                self._blocking_detector.install(loop)

            if self._lag_monitor:
                self._lag_monitor.start(loop)

        except Exception as e:
            logger.warning("Failed to start async profiling: %s", e)

        self._profiling_overhead = time.perf_counter() - start

    async def process_response(self, context: RequestContext) -> None:
        """Stop async profiling at response completion.

        Args:
            context: The current request context.
        """
        start = time.perf_counter()

        try:
            self._backend.stop()

            if self._blocking_detector:
                self._blocking_detector.uninstall()

            if self._lag_monitor:
                self._lag_monitor.stop()

        except Exception as e:
            logger.warning("Failed to stop async profiling: %s", e)

        self._profiling_overhead += time.perf_counter() - start

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate async profiling statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary of async profiling statistics.
        """
        backend_stats = self._backend.get_stats()

        tasks = backend_stats.get("tasks", [])
        self._task_count = len([t for t in tasks if t.get("event_type") == "created"])

        blocking_calls: list[dict[str, Any]] = []
        if self._blocking_detector:
            blocking_stats = self._blocking_detector.get_stats()
            blocking_calls = blocking_stats.get("blocking_calls", [])
        self._blocking_count = len(blocking_calls)

        lag_samples: list[dict[str, Any]] = []
        max_lag_ms: float = 0.0
        if self._lag_monitor:
            lag_stats = self._lag_monitor.get_stats()
            lag_samples = lag_stats.get("samples", [])
            max_lag_ms = lag_stats.get("max_lag_ms", 0.0)

        from debug_toolbar.core.panels.async_profiler.timeline import generate_timeline

        timeline = generate_timeline(tasks, blocking_calls)

        return {
            "backend": self._backend_name,
            "tasks": tasks,
            "blocking_calls": blocking_calls,
            "event_loop_lag": lag_samples,
            "timeline": timeline,
            "summary": {
                "total_tasks": self._task_count,
                "completed_tasks": len([t for t in tasks if t.get("event_type") == "completed"]),
                "cancelled_tasks": len([t for t in tasks if t.get("event_type") == "cancelled"]),
                "error_tasks": len([t for t in tasks if t.get("event_type") == "error"]),
                "blocking_calls_count": self._blocking_count,
                "max_lag_ms": max_lag_ms,
                "has_warnings": self._blocking_count > 0,
            },
            "profiling_overhead": self._profiling_overhead + backend_stats.get("profiling_overhead", 0.0),
        }

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data for async profiling overhead.

        Args:
            context: The current request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {
            "async_profiling": stats.get("profiling_overhead", 0.0),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing task count or warnings.

        Returns:
            Formatted subtitle string.
        """
        if self._blocking_count > 0:
            return f"{self._blocking_count} blocking"
        return f"{self._task_count} tasks"
