"""Abstract base class for async profiling backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio


class AsyncProfilerBackend(ABC):
    """Abstract base class for async profiling backends.

    Backends are responsible for tracking async task creation and execution
    during request processing. Each backend should implement methods to start
    and stop tracking, and retrieve profiling statistics.
    """

    @abstractmethod
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Begin async profiling.

        Called at the start of request processing to initialize tracking.

        Args:
            loop: The asyncio event loop to monitor.
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """End async profiling.

        Called at the end of request processing to stop tracking.
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Retrieve async profiling statistics.

        Returns:
            Dictionary containing profiling data with keys:
                - tasks: List of TaskEvent records
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
