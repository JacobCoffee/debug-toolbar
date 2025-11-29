"""Memory profiling panel for tracking memory allocations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from debug_toolbar.core.panel import Panel
from debug_toolbar.core.panels.memory.memray import MemrayBackend
from debug_toolbar.core.panels.memory.tracemalloc import TraceMallocBackend

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.panels.memory.base import MemoryBackend
    from debug_toolbar.core.toolbar import DebugToolbar

logger = logging.getLogger(__name__)

BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
BYTES_PER_GB = 1024 * 1024 * 1024


class MemoryPanel(Panel):
    """Panel for profiling memory allocations during request processing.

    Supports multiple profiling backends:
    - tracemalloc: Standard library profiler (default, always available)
    - memray: Bloomberg's profiler with C extension tracking (Linux/macOS only)

    The panel automatically selects the best available backend based on
    platform and installed dependencies, with an option to override via config.

    Features:
        - Before/after memory snapshots
        - Memory delta tracking
        - Peak memory monitoring
        - Top allocations by file and line
        - Multi-backend support with automatic selection

    Configure via toolbar config:
        memory_backend: "tracemalloc" | "memray" | "auto" (default: "auto")
    """

    panel_id: ClassVar[str] = "MemoryPanel"
    title: ClassVar[str] = "Memory"
    template: ClassVar[str] = "panels/memory.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Memory"

    __slots__ = ("_backend", "_backend_name", "_memory_delta")

    def __init__(self, toolbar: DebugToolbar) -> None:
        """Initialize the memory panel with appropriate backend.

        Args:
            toolbar: The parent DebugToolbar instance.
        """
        super().__init__(toolbar)
        self._backend_name = self._select_backend()
        self._backend = self._create_backend(self._backend_name)
        self._memory_delta: int = 0

    def _select_backend(self) -> Literal["tracemalloc", "memray"]:
        """Determine which memory backend to use.

        Returns:
            Name of the selected backend.
        """
        config_backend = self._get_config("memory_backend", "auto")

        if config_backend == "memray":
            if MemrayBackend.is_available():
                return "memray"
            logger.info("Memray requested but not available, falling back to tracemalloc")
            return "tracemalloc"

        if config_backend == "tracemalloc":
            return "tracemalloc"

        if MemrayBackend.is_available():
            return "memray"

        return "tracemalloc"

    def _create_backend(self, backend_name: str) -> MemoryBackend:
        """Create an instance of the specified backend.

        Args:
            backend_name: Name of the backend to create.

        Returns:
            Instance of the memory backend.
        """
        if backend_name == "memray":
            return MemrayBackend()
        return TraceMallocBackend()

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

    async def process_request(self, context: RequestContext) -> None:
        """Start memory profiling at request start.

        Args:
            context: The current request context.
        """
        try:
            self._backend.start()
        except Exception as e:
            logger.warning("Failed to start memory profiling: %s", e)

    async def process_response(self, context: RequestContext) -> None:
        """Stop memory profiling at response completion.

        Args:
            context: The current request context.
        """
        try:
            self._backend.stop()
        except Exception as e:
            logger.warning("Failed to stop memory profiling: %s", e)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate memory profiling statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary of memory statistics.
        """
        stats = self._backend.get_stats()
        self._memory_delta = stats.get("memory_delta", 0)
        return stats

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data for memory profiling overhead.

        Args:
            context: The current request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {
            "memory_profiling": stats.get("profiling_overhead", 0.0),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing memory delta.

        Returns:
            Formatted memory delta string (e.g., "+2.3 MB" or "-500 KB").
        """
        if self._memory_delta == 0:
            return "0 B"

        abs_delta = abs(self._memory_delta)
        sign = "+" if self._memory_delta > 0 else "-"

        if abs_delta >= BYTES_PER_GB:
            return f"{sign}{abs_delta / BYTES_PER_GB:.2f} GB"
        if abs_delta >= BYTES_PER_MB:
            return f"{sign}{abs_delta / BYTES_PER_MB:.2f} MB"
        if abs_delta >= BYTES_PER_KB:
            return f"{sign}{abs_delta / BYTES_PER_KB:.2f} KB"
        return f"{sign}{abs_delta} B"
