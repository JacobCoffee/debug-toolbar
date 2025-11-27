"""Storage backend for toolbar request history using LRU cache."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class ToolbarStorage:
    """Thread-safe LRU storage for toolbar request history.

    This storage maintains a bounded history of request data, automatically
    evicting the oldest entries when the maximum size is reached.

    Attributes:
        max_size: Maximum number of requests to store.
    """

    __slots__ = ("_lock", "_store", "max_size")

    def __init__(self, max_size: int = 50) -> None:
        """Initialize the storage.

        Args:
            max_size: Maximum number of requests to store. Defaults to 50.
        """
        self._store: OrderedDict[UUID, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_size = max_size

    def store(self, request_id: UUID, data: dict[str, Any]) -> None:
        """Store request data.

        Args:
            request_id: Unique identifier for the request.
            data: Dictionary of data to store.
        """
        with self._lock:
            if request_id in self._store:
                self._store.move_to_end(request_id)
            self._store[request_id] = data

            while len(self._store) > self.max_size:
                self._store.popitem(last=False)

    def get(self, request_id: UUID) -> dict[str, Any] | None:
        """Retrieve request data.

        Args:
            request_id: Unique identifier for the request.

        Returns:
            The stored data, or None if not found.
        """
        with self._lock:
            return self._store.get(request_id)

    def get_all(self) -> list[tuple[UUID, dict[str, Any]]]:
        """Get all stored requests.

        Returns:
            List of (request_id, data) tuples, newest first.
        """
        with self._lock:
            return list(reversed(self._store.items()))

    def clear(self) -> None:
        """Clear all stored requests."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        """Get the number of stored requests."""
        with self._lock:
            return len(self._store)

    def store_from_context(self, context: RequestContext) -> None:
        """Store data from a request context.

        Args:
            context: The RequestContext to store.
        """
        data = {
            "panel_data": context.panel_data.copy(),
            "timing_data": context.timing_data.copy(),
            "metadata": context.metadata.copy(),
        }
        self.store(context.request_id, data)
