"""Tests for the storage module."""

from __future__ import annotations

from uuid import uuid4

from debug_toolbar.core.context import RequestContext
from debug_toolbar.core.storage import ToolbarStorage


class TestToolbarStorage:
    """Tests for ToolbarStorage class."""

    def test_store_and_retrieve(self) -> None:
        """Should store and retrieve data."""
        storage = ToolbarStorage()
        request_id = uuid4()
        data = {"key": "value"}

        storage.store(request_id, data)
        retrieved = storage.get(request_id)

        assert retrieved == data

    def test_get_nonexistent(self) -> None:
        """Should return None for nonexistent request."""
        storage = ToolbarStorage()
        assert storage.get(uuid4()) is None

    def test_lru_eviction(self) -> None:
        """Should evict oldest entries when max size exceeded."""
        storage = ToolbarStorage(max_size=3)

        ids = [uuid4() for _ in range(5)]
        for i, rid in enumerate(ids):
            storage.store(rid, {"index": i})

        assert len(storage) == 3
        assert storage.get(ids[0]) is None
        assert storage.get(ids[1]) is None
        assert storage.get(ids[2]) is not None
        assert storage.get(ids[3]) is not None
        assert storage.get(ids[4]) is not None

    def test_get_all(self) -> None:
        """Should return all entries newest first."""
        storage = ToolbarStorage()

        ids = [uuid4() for _ in range(3)]
        for i, rid in enumerate(ids):
            storage.store(rid, {"index": i})

        all_items = storage.get_all()
        assert len(all_items) == 3
        assert all_items[0][0] == ids[2]
        assert all_items[2][0] == ids[0]

    def test_clear(self) -> None:
        """Should clear all entries."""
        storage = ToolbarStorage()
        storage.store(uuid4(), {"key": "value"})
        storage.store(uuid4(), {"key": "value2"})

        storage.clear()
        assert len(storage) == 0

    def test_store_from_context(self) -> None:
        """Should store data from a RequestContext."""
        storage = ToolbarStorage()
        ctx = RequestContext()
        ctx.store_panel_data("TestPanel", "key", "value")
        ctx.record_timing("test", 0.5)
        ctx.metadata["path"] = "/test"

        storage.store_from_context(ctx)

        data = storage.get(ctx.request_id)
        assert data is not None
        assert data["panel_data"]["TestPanel"]["key"] == "value"
        assert data["timing_data"]["test"] == 0.5
        assert data["metadata"]["path"] == "/test"
