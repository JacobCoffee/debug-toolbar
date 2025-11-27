"""Tests for the Cache panel."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from debug_toolbar.core.panels.cache import (
    CacheOperationRecord,
    CachePanel,
    CacheTracker,
    _get_tracker,
    _set_tracker,
)

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


@pytest.fixture
def cache_tracker() -> CacheTracker:
    """Create a fresh cache tracker."""
    return CacheTracker()


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


@pytest.fixture
def cache_panel(mock_toolbar: MagicMock) -> CachePanel:
    """Create a Cache panel instance."""
    return CachePanel(mock_toolbar)


class TestCacheOperationRecord:
    """Tests for CacheOperationRecord dataclass."""

    def test_create_record(self) -> None:
        """Test creating a cache operation record."""
        record = CacheOperationRecord(
            operation="GET",
            key="test_key",
            hit=True,
            duration=0.001,
            timestamp=1234567890.0,
            backend="redis",
        )

        assert record.operation == "GET"
        assert record.key == "test_key"
        assert record.hit is True
        assert record.duration == 0.001
        assert record.timestamp == 1234567890.0
        assert record.backend == "redis"
        assert record.extra == {}

    def test_create_record_with_extra(self) -> None:
        """Test creating a record with extra data."""
        extra_data = {"ttl": 3600, "size": 1024}
        record = CacheOperationRecord(
            operation="SET",
            key="cache_key",
            hit=None,
            duration=0.002,
            timestamp=1234567890.0,
            backend="memcached",
            extra=extra_data,
        )

        assert record.extra == extra_data

    def test_create_record_with_multiple_keys(self) -> None:
        """Test creating a record with multiple keys (MGET)."""
        keys = ["key1", "key2", "key3"]
        record = CacheOperationRecord(
            operation="MGET",
            key=keys,
            hit=True,
            duration=0.003,
            timestamp=1234567890.0,
            backend="redis",
        )

        assert record.key == keys


class TestCacheTracker:
    """Tests for CacheTracker."""

    def test_initial_state(self, cache_tracker: CacheTracker) -> None:
        """Test initial state."""
        assert cache_tracker.operations == []
        assert not cache_tracker._tracking_enabled

    def test_clear_operations(self, cache_tracker: CacheTracker) -> None:
        """Test clearing operations."""
        cache_tracker._record_operation(
            operation="GET",
            key="test",
            hit=True,
            duration=0.001,
            backend="redis",
        )
        assert len(cache_tracker.operations) == 1

        cache_tracker.clear()
        assert len(cache_tracker.operations) == 0

    def test_record_operation(self, cache_tracker: CacheTracker) -> None:
        """Test recording a cache operation."""
        cache_tracker._record_operation(
            operation="GET",
            key="user:123",
            hit=True,
            duration=0.002,
            backend="redis",
        )

        assert len(cache_tracker.operations) == 1
        op = cache_tracker.operations[0]
        assert op.operation == "GET"
        assert op.key == "user:123"
        assert op.hit is True
        assert op.duration == 0.002
        assert op.backend == "redis"

    def test_record_multiple_operations(self, cache_tracker: CacheTracker) -> None:
        """Test recording multiple operations."""
        cache_tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.001, backend="redis")
        cache_tracker._record_operation(operation="SET", key="key2", hit=None, duration=0.002, backend="redis")
        cache_tracker._record_operation(operation="DELETE", key="key3", hit=None, duration=0.003, backend="memcached")

        assert len(cache_tracker.operations) == 3

    def test_track_operation_context_manager(self, cache_tracker: CacheTracker) -> None:
        """Test track_operation context manager."""
        with cache_tracker.track_operation("GET", "test_key", "redis") as extra:
            extra["hit"] = True

        assert len(cache_tracker.operations) == 1
        op = cache_tracker.operations[0]
        assert op.operation == "GET"
        assert op.key == "test_key"
        assert op.hit is True
        assert op.backend == "redis"

    def test_start_tracking(self, cache_tracker: CacheTracker) -> None:
        """Test starting tracking."""
        cache_tracker.start_tracking()
        assert cache_tracker._tracking_enabled

    def test_stop_tracking(self, cache_tracker: CacheTracker) -> None:
        """Test stopping tracking."""
        cache_tracker.start_tracking()
        cache_tracker.stop_tracking()
        assert not cache_tracker._tracking_enabled

    def test_start_tracking_idempotent(self, cache_tracker: CacheTracker) -> None:
        """Test starting tracking multiple times is safe."""
        cache_tracker.start_tracking()
        cache_tracker.start_tracking()
        assert cache_tracker._tracking_enabled

    def test_stop_tracking_idempotent(self, cache_tracker: CacheTracker) -> None:
        """Test stopping tracking when not tracking is safe."""
        cache_tracker.stop_tracking()
        cache_tracker.stop_tracking()
        assert not cache_tracker._tracking_enabled

    def test_patch_redis_when_not_installed(self, cache_tracker: CacheTracker) -> None:
        """Test patching Redis when it's not installed."""
        import sys

        with patch.dict(sys.modules, {"redis": None}):
            cache_tracker._patch_redis()
            assert len(cache_tracker._original_redis_methods) == 0

    def test_patch_memcache_when_not_installed(self, cache_tracker: CacheTracker) -> None:
        """Test patching memcache when it's not installed."""
        import sys

        with patch.dict(sys.modules, {"pymemcache": None, "pymemcache.client.base": None}):
            cache_tracker._patch_memcache()
            assert len(cache_tracker._original_memcache_methods) == 0


class TestGlobalTrackerManagement:
    """Tests for global tracker management."""

    def test_get_tracker_initial_state(self) -> None:
        """Test getting tracker when none is set."""
        _set_tracker(None)
        tracker = _get_tracker()
        assert tracker is None

    def test_set_and_get_tracker(self) -> None:
        """Test setting and getting tracker."""
        tracker = CacheTracker()
        _set_tracker(tracker)
        retrieved = _get_tracker()
        assert retrieved is tracker

        _set_tracker(None)


class TestCachePanel:
    """Tests for CachePanel."""

    def test_panel_attributes(self, cache_panel: CachePanel) -> None:
        """Test panel class attributes."""
        assert cache_panel.panel_id == "CachePanel"
        assert cache_panel.title == "Cache"
        assert cache_panel.template == "panels/cache.html"
        assert cache_panel.has_content is True
        assert cache_panel.nav_title == "Cache"

    def test_panel_initialization(self, mock_toolbar: MagicMock) -> None:
        """Test panel initialization."""
        panel = CachePanel(mock_toolbar)
        assert panel._tracker is not None
        assert isinstance(panel._tracker, CacheTracker)

    @pytest.mark.asyncio
    async def test_process_request(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test process_request starts tracking."""
        await cache_panel.process_request(request_context)

        assert cache_panel._tracker._tracking_enabled
        assert _get_tracker() is cache_panel._tracker

        _set_tracker(None)

    @pytest.mark.asyncio
    async def test_process_response(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test process_response stops tracking."""
        await cache_panel.process_request(request_context)
        await cache_panel.process_response(request_context)

        assert not cache_panel._tracker._tracking_enabled
        assert _get_tracker() is None

    @pytest.mark.asyncio
    async def test_generate_stats_no_operations(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test generate_stats with no operations."""
        stats = await cache_panel.generate_stats(request_context)

        assert stats["total_operations"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_time"] == 0.0
        assert stats["avg_time"] == 0.0
        assert stats["backends"] == []
        assert stats["operations"] == []

    @pytest.mark.asyncio
    async def test_generate_stats_with_operations(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats with recorded operations."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="GET", key="key2", hit=False, duration=0.002, backend="redis")
        cache_panel._tracker._record_operation(
            operation="SET", key="key3", hit=None, duration=0.003, backend="memcached"
        )

        stats = await cache_panel.generate_stats(request_context)

        assert stats["total_operations"] == 3
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0
        assert stats["total_time"] == 0.006
        assert stats["avg_time"] == 0.002
        assert set(stats["backends"]) == {"redis", "memcached"}
        assert len(stats["operations"]) == 3

    @pytest.mark.asyncio
    async def test_generate_stats_all_hits(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test generate_stats with all hits."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="GET", key="key2", hit=True, duration=0.001, backend="redis")

        stats = await cache_panel.generate_stats(request_context)

        assert stats["hits"] == 2
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_generate_stats_all_misses(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test generate_stats with all misses."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=False, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="GET", key="key2", hit=False, duration=0.001, backend="redis")

        stats = await cache_panel.generate_stats(request_context)

        assert stats["hits"] == 0
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_generate_stats_operation_breakdown(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats includes operation breakdown."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="GET", key="key2", hit=False, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="SET", key="key3", hit=None, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(
            operation="DELETE", key="key4", hit=None, duration=0.001, backend="redis"
        )

        stats = await cache_panel.generate_stats(request_context)

        assert stats["by_operation"]["GET"] == 2
        assert stats["by_operation"]["SET"] == 1
        assert stats["by_operation"]["DELETE"] == 1

    @pytest.mark.asyncio
    async def test_generate_stats_backend_breakdown(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats includes backend breakdown."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(operation="GET", key="key2", hit=True, duration=0.001, backend="redis")
        cache_panel._tracker._record_operation(
            operation="GET", key="key3", hit=True, duration=0.001, backend="memcached"
        )

        stats = await cache_panel.generate_stats(request_context)

        assert stats["by_backend"]["redis"] == 2
        assert stats["by_backend"]["memcached"] == 1

    @pytest.mark.asyncio
    async def test_generate_stats_timing_recorded(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats records timing to context."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.005, backend="redis")

        await cache_panel.generate_stats(request_context)

        cache_time = request_context.get_timing("cache_time")
        assert cache_time == 0.005

    @pytest.mark.asyncio
    async def test_generate_stats_no_timing_when_zero(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats doesn't record timing when zero."""
        await cache_panel.generate_stats(request_context)

        cache_time = request_context.get_timing("cache_time")
        assert cache_time is None

    def test_generate_server_timing_no_stats(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test generate_server_timing with no stats."""
        timing = cache_panel.generate_server_timing(request_context)
        assert timing == {}

    @pytest.mark.asyncio
    async def test_generate_server_timing_with_stats(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing with stats."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.005, backend="redis")
        cache_panel._tracker._record_operation(
            operation="GET", key="key2", hit=True, duration=0.003, backend="memcached"
        )

        stats = await cache_panel.generate_stats(request_context)
        cache_panel.record_stats(request_context, stats)

        timing = cache_panel.generate_server_timing(request_context)

        assert "cache" in timing
        assert timing["cache"] == 0.008
        assert "cache-redis" in timing
        assert timing["cache-redis"] == 0.005
        assert "cache-memcached" in timing
        assert timing["cache-memcached"] == 0.003

    @pytest.mark.asyncio
    async def test_generate_server_timing_single_backend(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing with single backend."""
        cache_panel._tracker._record_operation(operation="GET", key="key1", hit=True, duration=0.010, backend="redis")

        stats = await cache_panel.generate_stats(request_context)
        cache_panel.record_stats(request_context, stats)

        timing = cache_panel.generate_server_timing(request_context)

        assert timing["cache"] == 0.010
        assert timing["cache-redis"] == 0.010
        assert "cache-memcached" not in timing

    def test_get_nav_subtitle(self, cache_panel: CachePanel) -> None:
        """Test get_nav_subtitle."""
        assert cache_panel.get_nav_subtitle() == ""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test full panel lifecycle."""
        await cache_panel.process_request(request_context)

        cache_panel._tracker._record_operation(
            operation="GET", key="user:123", hit=True, duration=0.001, backend="redis"
        )
        cache_panel._tracker._record_operation(
            operation="SET", key="user:123", hit=None, duration=0.002, backend="redis"
        )

        stats = await cache_panel.generate_stats(request_context)
        cache_panel.record_stats(request_context, stats)

        await cache_panel.process_response(request_context)

        assert not cache_panel._tracker._tracking_enabled
        assert stats["total_operations"] == 2
        assert stats["hits"] == 1
        assert stats["hit_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_operation_list_format(self, cache_panel: CachePanel, request_context: RequestContext) -> None:
        """Test operation list has correct format."""
        cache_panel._tracker._record_operation(
            operation="GET",
            key="test_key",
            hit=True,
            duration=0.001,
            backend="redis",
            extra={"ttl": 3600},
        )

        stats = await cache_panel.generate_stats(request_context)

        op = stats["operations"][0]
        assert op["operation"] == "GET"
        assert op["key"] == "test_key"
        assert op["hit"] is True
        assert op["duration"] == 0.001
        assert op["duration_ms"] == 1.0
        assert "timestamp" in op
        assert op["backend"] == "redis"
        assert op["extra"] == {"ttl": 3600}

    @pytest.mark.asyncio
    async def test_operation_list_multikey_format(
        self, cache_panel: CachePanel, request_context: RequestContext
    ) -> None:
        """Test operation list handles multiple keys."""
        cache_panel._tracker._record_operation(
            operation="MGET",
            key=["key1", "key2", "key3"],
            hit=True,
            duration=0.001,
            backend="redis",
        )

        stats = await cache_panel.generate_stats(request_context)

        op = stats["operations"][0]
        assert op["key"] == "key1,key2,key3"
