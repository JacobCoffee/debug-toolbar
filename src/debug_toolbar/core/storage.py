"""Storage backend for toolbar request history using LRU cache."""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from pathlib import Path
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


class FileToolbarStorage(ToolbarStorage):
    """File-backed storage for sharing data between processes.

    Extends ToolbarStorage to persist data to a JSON file, enabling
    the web app and MCP server to share request history.

    Attributes:
        file_path: Path to the JSON storage file.
    """

    __slots__ = ("file_path",)

    def __init__(self, file_path: str | Path, max_size: int = 50) -> None:
        """Initialize file-backed storage.

        Args:
            file_path: Path to the JSON file for persistence.
            max_size: Maximum number of requests to store. Defaults to 50.
        """
        super().__init__(max_size)
        self.file_path = Path(file_path)
        self._load()

    def _load(self) -> None:
        """Load data from file if it exists."""
        if self.file_path.exists():
            try:
                with self._lock:
                    data = json.loads(self.file_path.read_text())
                    self._store.clear()
                    for item in data:
                        request_id = UUID(item["request_id"])
                        self._store[request_id] = item["data"]
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

    def _save(self) -> None:
        """Save data to file."""
        with self._lock:
            data = [{"request_id": str(rid), "data": d} for rid, d in self._store.items()]
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(data, default=str))

    def store(self, request_id: UUID, data: dict[str, Any]) -> None:
        """Store request data and persist to file."""
        super().store(request_id, data)
        self._save()

    def clear(self) -> None:
        """Clear all stored requests and the file."""
        super().clear()
        if self.file_path.exists():
            self.file_path.unlink()

    def reload(self) -> None:
        """Reload data from file (useful for MCP server to get fresh data)."""
        self._load()

    def get(self, request_id: UUID) -> dict[str, Any] | None:
        """Retrieve request data, reloading from file first."""
        self._load()
        return super().get(request_id)

    def get_all(self) -> list[tuple[UUID, dict[str, Any]]]:
        """Get all stored requests, reloading from file first."""
        self._load()
        return super().get_all()
