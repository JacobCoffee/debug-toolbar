"""Abstract base class for memory profiling backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryBackend(ABC):
    """Abstract base class for memory profiling backends.

    Backends are responsible for tracking memory allocations during
    request processing. Each backend should implement methods to start
    and stop tracking, and retrieve memory statistics.
    """

    @abstractmethod
    def start(self) -> None:
        """Begin memory tracking.

        Called at the start of request processing to initialize tracking.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """End memory tracking.

        Called at the end of request processing to stop tracking.
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Retrieve memory statistics.

        Returns:
            Dictionary containing memory profiling data with keys:
                - memory_before: Memory usage at request start (bytes)
                - memory_after: Memory usage at request end (bytes)
                - memory_delta: Change in memory during request (bytes)
                - peak_memory: Peak memory usage during request (bytes)
                - top_allocations: List of top memory allocations
                - backend: Name of the backend used
                - profiling_overhead: Time spent profiling (seconds)
        """
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend is available.

        Returns:
            True if the backend can be used, False otherwise.
        """
        ...
