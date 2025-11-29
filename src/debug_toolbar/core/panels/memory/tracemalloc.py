"""TraceMalloc backend for memory profiling using Python stdlib."""

from __future__ import annotations

import time
import tracemalloc
from typing import Any

from debug_toolbar.core.panels.memory.base import MemoryBackend


class TraceMallocBackend(MemoryBackend):
    """Memory profiling backend using Python's built-in tracemalloc module.

    This backend uses the standard library tracemalloc module to track
    Python memory allocations. It provides low overhead profiling and
    works on all platforms.

    Features:
        - Snapshot-based tracking (before/after comparison)
        - Top allocations by file and line number
        - Allocation diff (what grew during request)
        - Peak memory tracking
        - Cross-platform support (stdlib, no dependencies)

    Limitations:
        - Only tracks Python allocations (no native C extensions)
        - Cannot track memory allocated by C libraries
    """

    def __init__(self) -> None:
        """Initialize the TraceMalloc backend."""
        self._snapshot_before: tracemalloc.Snapshot | None = None
        self._snapshot_after: tracemalloc.Snapshot | None = None
        self._profiling_overhead: float = 0.0
        self._was_running: bool = False
        self._peak_memory: int = 0

    def start(self) -> None:
        """Begin memory tracking with tracemalloc."""
        start_time = time.perf_counter()

        self._was_running = tracemalloc.is_tracing()
        if not self._was_running:
            tracemalloc.start()

        self._snapshot_before = tracemalloc.take_snapshot()

        self._profiling_overhead += time.perf_counter() - start_time

    def stop(self) -> None:
        """End memory tracking and capture final snapshot."""
        start_time = time.perf_counter()

        self._snapshot_after = tracemalloc.take_snapshot()

        self._peak_memory = tracemalloc.get_traced_memory()[1]

        if not self._was_running:
            tracemalloc.stop()

        self._profiling_overhead += time.perf_counter() - start_time

    def get_stats(self) -> dict[str, Any]:
        """Retrieve memory statistics from tracemalloc snapshots.

        Returns:
            Dictionary with memory profiling data including before/after
            memory usage, delta, peak, and top allocations.
        """
        if self._snapshot_before is None or self._snapshot_after is None:
            return self._empty_stats()

        stats_before = self._snapshot_before.statistics("lineno")
        stats_after = self._snapshot_after.statistics("lineno")

        memory_before = sum(stat.size for stat in stats_before)
        memory_after = sum(stat.size for stat in stats_after)
        memory_delta = memory_after - memory_before

        top_allocations = self._extract_top_allocations(stats_after, limit=20)

        return {
            "memory_before": memory_before,
            "memory_after": memory_after,
            "memory_delta": memory_delta,
            "peak_memory": self._peak_memory,
            "top_allocations": top_allocations,
            "backend": "tracemalloc",
            "profiling_overhead": self._profiling_overhead,
        }

    def _extract_top_allocations(self, stats: list[tracemalloc.Statistic], limit: int = 20) -> list[dict[str, Any]]:
        """Extract top memory allocations from statistics.

        Args:
            stats: List of tracemalloc statistics.
            limit: Maximum number of allocations to return.

        Returns:
            List of dictionaries containing allocation details.
        """
        allocations = []
        for stat in stats[:limit]:
            if stat.traceback and len(stat.traceback) > 0:
                formatted = stat.traceback.format()
                file_info = formatted[0] if formatted else "unknown"
                line_no = stat.traceback[0].lineno
            else:
                file_info = "unknown"
                line_no = 0

            allocations.append(
                {
                    "file": file_info,
                    "line": line_no,
                    "size": stat.size,
                    "count": stat.count,
                }
            )
        return allocations

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure when no data is available."""
        return {
            "memory_before": 0,
            "memory_after": 0,
            "memory_delta": 0,
            "peak_memory": 0,
            "top_allocations": [],
            "backend": "tracemalloc",
            "profiling_overhead": self._profiling_overhead,
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check if tracemalloc is available.

        Returns:
            Always True, as tracemalloc is part of the standard library.
        """
        return True
