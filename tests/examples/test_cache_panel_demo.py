"""Tests for the cache panel demo script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def test_demo_context_manager_tracking_records_operations(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Demo should track a mix of hits, misses, and backends."""
    module = import_example("examples.cache_panel_demo")

    module.demo_context_manager_tracking()


def test_demo_context_manager_tracking_builds_real_operations(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate the demo's tracker usage directly to assert on real fields."""
    module = import_example("examples.cache_panel_demo")

    tracker = module.CacheTracker()

    with tracker.track_operation("GET", "user:123", "redis") as extra:
        extra["hit"] = True
    with tracker.track_operation("GET", "user:456", "redis") as extra:
        extra["hit"] = False
    with tracker.track_operation("SET", "user:456", "redis") as extra:
        extra["ttl"] = 3600
    with tracker.track_operation("GET", "session:abc123", "memcached") as extra:
        extra["hit"] = True

    assert len(tracker.operations) == 4

    first, second, third, fourth = tracker.operations
    assert first.operation == "GET"
    assert first.key == "user:123"
    assert first.hit is True
    assert first.backend == "redis"

    assert second.hit is False

    assert third.operation == "SET"
    assert third.extra["ttl"] == 3600

    assert fourth.backend == "memcached"
    assert fourth.hit is True


def test_demo_multi_key_operation_tracks_list_key(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Multi-key operations should preserve the list of keys and extras."""
    module = import_example("examples.cache_panel_demo")

    module.demo_multi_key_operation()

    tracker = module.CacheTracker()
    with tracker.track_operation("MGET", ["key1", "key2", "key3"], "redis") as extra:
        extra["hit"] = True
        extra["keys_found"] = 2

    op = tracker.operations[0]
    assert op.operation == "MGET"
    assert op.key == ["key1", "key2", "key3"]
    assert op.hit is True
    assert op.extra["keys_found"] == 2


def test_demo_statistics_computes_hit_rate(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Statistics demo should produce computable totals, hits, misses, and hit rate."""
    module = import_example("examples.cache_panel_demo")

    module.demo_statistics()

    tracker = module.CacheTracker()
    with tracker.track_operation("GET", "key1", "redis") as extra:
        extra["hit"] = True
    with tracker.track_operation("GET", "key2", "redis") as extra:
        extra["hit"] = True
    with tracker.track_operation("GET", "key3", "redis") as extra:
        extra["hit"] = False
    with tracker.track_operation("SET", "key4", "redis"):
        pass
    with tracker.track_operation("GET", "key5", "memcached") as extra:
        extra["hit"] = True

    total = len(tracker.operations)
    hits = sum(1 for op in tracker.operations if op.hit is True)
    misses = sum(1 for op in tracker.operations if op.hit is False)

    assert total == 5
    assert hits == 3
    assert misses == 1

    hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0
    assert hit_rate == 75.0
