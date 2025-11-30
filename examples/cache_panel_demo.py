# /// script
# requires-python = ">=3.10"
# dependencies = ["debug-toolbar"]
# ///
"""Demo script showing how the Cache Panel tracks cache operations.

This example demonstrates how the Cache Panel automatically tracks Redis and
memcached operations when they occur during a request.

Note: This is a demonstration of the panel's capabilities. In practice, the
panel is automatically enabled when added to the debug toolbar configuration.
"""

from __future__ import annotations

from debug_toolbar.core.panels.cache import CacheTracker


def demo_context_manager_tracking() -> None:
    """Demonstrate cache tracking using the public context manager API."""
    print("=== Context Manager Cache Tracking Demo ===\n")

    tracker = CacheTracker()

    print("1. Recording cache GET operations (hit and miss)...")
    with tracker.track_operation("GET", "user:123", "redis") as extra:
        extra["hit"] = True

    with tracker.track_operation("GET", "user:456", "redis") as extra:
        extra["hit"] = False

    print("2. Recording cache SET operation...")
    with tracker.track_operation("SET", "user:456", "redis") as extra:
        extra["ttl"] = 3600

    print("3. Recording memcached operation...")
    with tracker.track_operation("GET", "session:abc123", "memcached") as extra:
        extra["hit"] = True

    print(f"\nTotal operations tracked: {len(tracker.operations)}")
    print("\nOperations:")
    for i, op in enumerate(tracker.operations, 1):
        hit_status = "HIT" if op.hit else "MISS" if op.hit is False else "N/A"
        print(
            f"  {i}. {op.operation:8s} {op.key:20s} [{hit_status:4s}] "
            f"{op.duration*1000:.2f}ms ({op.backend})"
        )


def demo_multi_key_operation() -> None:
    """Demonstrate tracking multi-key operations."""
    print("\n=== Multi-Key Operation Demo ===\n")

    tracker = CacheTracker()

    print("Using context manager to track a multi-key operation...")
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
    total_time = sum(op.duration for op in tracker.operations)

    hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0

    print(f"Total operations: {total}")
    print(f"Cache hits: {hits}")
    print(f"Cache misses: {misses}")
    print(f"Hit rate: {hit_rate:.1f}%")
    print(f"Total time: {total_time*1000:.3f}ms")
    print(f"Average time per operation: {(total_time/total)*1000:.3f}ms")


if __name__ == "__main__":
    demo_context_manager_tracking()
    demo_multi_key_operation()
    demo_statistics()

    print("\n" + "=" * 50)
    print("\nIn a real application, the Cache Panel would:")
    print("  - Automatically patch Redis and memcached clients")
    print("  - Track all cache operations during each request")
    print("  - Display statistics in the debug toolbar UI")
    print("  - Add cache timing to Server-Timing headers")
    print("  - Show detailed operation logs with keys and durations")
    print("\nNo manual tracking code is needed in your application!")
