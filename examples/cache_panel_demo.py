"""Demo script showing how the Cache Panel tracks cache operations.

This example demonstrates how the Cache Panel automatically tracks Redis and
memcached operations when they occur during a request.

Note: This is a demonstration of the panel's capabilities. In practice, the
panel is automatically enabled when added to the debug toolbar configuration.
"""

from __future__ import annotations

from debug_toolbar.core.panels.cache import CachePanel, CacheTracker


def demo_manual_tracking() -> None:
    """Demonstrate manual cache tracking using the CacheTracker."""
    print("=== Manual Cache Tracking Demo ===\n")

    tracker = CacheTracker()

    print("1. Recording cache GET operations (hit and miss)...")
    tracker._record_operation(
        operation="GET",
        key="user:123",
        hit=True,
        duration=0.001,
        backend="redis",
    )

    tracker._record_operation(
        operation="GET",
        key="user:456",
        hit=False,
        duration=0.002,
        backend="redis",
    )

    print("2. Recording cache SET operation...")
    tracker._record_operation(
        operation="SET",
        key="user:456",
        hit=None,
        duration=0.003,
        backend="redis",
        extra={"ttl": 3600},
    )

    print("3. Recording memcached operation...")
    tracker._record_operation(
        operation="GET",
        key="session:abc123",
        hit=True,
        duration=0.0015,
        backend="memcached",
    )

    print(f"\nTotal operations tracked: {len(tracker.operations)}")
    print("\nOperations:")
    for i, op in enumerate(tracker.operations, 1):
        hit_status = "HIT" if op.hit else "MISS" if op.hit is False else "N/A"
        print(
            f"  {i}. {op.operation:8s} {op.key:20s} [{hit_status:4s}] "
            f"{op.duration*1000:.2f}ms ({op.backend})"
        )


def demo_context_manager() -> None:
    """Demonstrate using the track_operation context manager."""
    print("\n=== Context Manager Demo ===\n")

    tracker = CacheTracker()

    print("Using context manager to track a custom operation...")
    with tracker.track_operation("MGET", ["key1", "key2", "key3"], "redis") as extra:
        extra["hit"] = True
        extra["keys_found"] = 2

    op = tracker.operations[0]
    print(f"Operation: {op.operation}")
    print(f"Keys: {op.key}")
    print(f"Hit: {op.hit}")
    print(f"Extra: {op.extra}")


def demo_statistics() -> None:
    """Demonstrate statistics calculation."""
    print("\n=== Statistics Demo ===\n")

    tracker = CacheTracker()

    tracker._record_operation("GET", "key1", True, 0.001, "redis")
    tracker._record_operation("GET", "key2", True, 0.001, "redis")
    tracker._record_operation("GET", "key3", False, 0.002, "redis")
    tracker._record_operation("SET", "key4", None, 0.003, "redis")
    tracker._record_operation("GET", "key5", True, 0.0015, "memcached")

    total = len(tracker.operations)
    hits = sum(1 for op in tracker.operations if op.hit is True)
    misses = sum(1 for op in tracker.operations if op.hit is False)
    total_time = sum(op.duration for op in tracker.operations)

    hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0

    print(f"Total operations: {total}")
    print(f"Cache hits: {hits}")
    print(f"Cache misses: {misses}")
    print(f"Hit rate: {hit_rate:.1f}%")
    print(f"Total time: {total_time*1000:.3f}ms")
    print(f"Average time per operation: {(total_time/total)*1000:.3f}ms")


if __name__ == "__main__":
    demo_manual_tracking()
    demo_context_manager()
    demo_statistics()

    print("\n" + "=" * 50)
    print("\nIn a real application, the Cache Panel would:")
    print("  - Automatically patch Redis and memcached clients")
    print("  - Track all cache operations during each request")
    print("  - Display statistics in the debug toolbar UI")
    print("  - Add cache timing to Server-Timing headers")
    print("  - Show detailed operation logs with keys and durations")
    print("\nNo manual tracking code is needed in your application!")
