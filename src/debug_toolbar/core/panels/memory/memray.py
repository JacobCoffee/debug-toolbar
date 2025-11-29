"""Memray backend for memory profiling with native C tracking."""

from __future__ import annotations

import contextlib
import logging
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from debug_toolbar.core.panels.memory.base import MemoryBackend

if TYPE_CHECKING:
    try:
        from memray import Tracker  # type: ignore[import-untyped]
    except ImportError:
        Tracker = None

logger = logging.getLogger(__name__)

TOP_ALLOCATIONS_LIMIT = 20


class MemrayBackend(MemoryBackend):
    """Memory profiling backend using Bloomberg's memray library.

    This backend uses memray for comprehensive memory tracking including
    native C extensions and detailed call stacks.

    Features:
        - Native extension tracking (C/C++ allocations)
        - Full call stack with C frames
        - Detailed allocation tracking
        - Support for flame graphs (via file output)

    Limitations:
        - Linux/macOS only (no Windows support)
        - Requires memray to be installed
        - Requires psutil to be installed for RSS memory measurement
        - File-based tracking (creates temp files)
        - Higher overhead than tracemalloc

    Note:
        Memray and psutil are optional dependencies. If not available, the panel
        will gracefully fall back to tracemalloc.
    """

    def __init__(self) -> None:
        """Initialize the Memray backend."""
        self._tracker: Tracker | None = None
        self._output_file: Path | None = None
        self._profiling_overhead: float = 0.0
        self._memory_before: int = 0
        self._memory_after: int = 0
        self._peak_memory: int = 0
        self._top_allocations: list[dict[str, Any]] = []

    def start(self) -> None:
        """Begin memory tracking with memray."""
        if not self.is_available():
            raise RuntimeError("Memray backend is not available on this platform")

        start_time = time.perf_counter()

        try:
            import memray  # type: ignore[import-untyped]

            fd, temp_path = tempfile.mkstemp(suffix=".bin", prefix="memray_")
            os.close(fd)
            self._output_file = Path(temp_path)

            self._tracker = memray.Tracker(str(self._output_file))
            self._tracker.__enter__()

            import psutil  # type: ignore[import-untyped]

            process = psutil.Process()
            self._memory_before = process.memory_info().rss

        except ImportError as e:
            logger.warning("Failed to initialize memray backend: %s", e)
            if self._tracker is not None:
                with contextlib.suppress(Exception):
                    self._tracker.__exit__(None, None, None)
            self._cleanup_temp_file()
            self._tracker = None
            self._output_file = None

        self._profiling_overhead += time.perf_counter() - start_time

    def stop(self) -> None:
        """End memory tracking and capture final state."""
        start_time = time.perf_counter()

        if self._tracker is not None:
            try:
                self._tracker.__exit__(None, None, None)

                import psutil  # type: ignore[import-untyped]

                process = psutil.Process()
                self._memory_after = process.memory_info().rss

                if self._output_file and self._output_file.exists():
                    import memray  # type: ignore[import-untyped]

                    reader = memray.FileReader(str(self._output_file))
                    self._peak_memory = reader.metadata.peak_memory

                self._top_allocations = self._extract_allocations()

            except Exception as e:
                logger.warning("Failed to stop memray tracker: %s", e)
            finally:
                self._cleanup_temp_file()

        self._profiling_overhead += time.perf_counter() - start_time

    def get_stats(self) -> dict[str, Any]:
        """Retrieve memory statistics from memray tracking.

        Returns:
            Dictionary with memory profiling data including before/after
            memory usage, delta, peak, and allocation details.
        """
        if self._tracker is None:
            return self._empty_stats()

        memory_delta = self._memory_after - self._memory_before

        return {
            "memory_before": self._memory_before,
            "memory_after": self._memory_after,
            "memory_delta": memory_delta,
            "peak_memory": self._peak_memory,
            "top_allocations": self._top_allocations,
            "backend": "memray",
            "profiling_overhead": self._profiling_overhead,
        }

    def _extract_allocations(self) -> list[dict[str, Any]]:
        """Extract top allocations from memray output file.

        Returns:
            List of top memory allocations with file, line, size, and count.
        """
        if not self._output_file or not self._output_file.exists():
            return []

        try:
            import memray  # type: ignore[import-untyped]

            allocations = []
            reader = memray.FileReader(str(self._output_file))

            allocation_records = []
            for record in reader.get_allocation_records():
                allocation_records.append(record)
                if len(allocation_records) >= TOP_ALLOCATIONS_LIMIT:
                    break

            for record in allocation_records:
                stack_trace = record.stack_trace()
                if stack_trace:
                    frame = stack_trace[0]
                    allocations.append(
                        {
                            "file": frame[0],
                            "line": frame[1],
                            "size": record.size,
                            "count": record.n_allocations,
                        }
                    )

            return allocations

        except Exception as e:
            logger.warning("Failed to extract memray allocations: %s", e)
            return []

    def _cleanup_temp_file(self) -> None:
        """Clean up temporary memray output file."""
        if self._output_file and self._output_file.exists():
            try:
                self._output_file.unlink()
            except OSError as e:
                logger.warning("Failed to clean up memray temp file: %s", e)

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure when no data is available."""
        return {
            "memory_before": 0,
            "memory_after": 0,
            "memory_delta": 0,
            "peak_memory": 0,
            "top_allocations": [],
            "backend": "memray",
            "profiling_overhead": self._profiling_overhead,
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check if memray is available on this platform.

        Returns:
            True if memray is installed and platform is Linux/macOS.
        """
        if platform.system() not in ("Linux", "Darwin"):
            return False

        try:
            import memray  # noqa: F401  # type: ignore[import-untyped]
            import psutil  # noqa: F401  # type: ignore[import-untyped]

            return True
        except ImportError:
            return False

    def __del__(self) -> None:
        """Ensure cleanup on deletion."""
        self._cleanup_temp_file()
