"""Example demonstrating the Memory Panel usage."""

# ruff: noqa: T201, INP001

from __future__ import annotations

import asyncio

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.memory import MemoryPanel
from debug_toolbar.core.toolbar import DebugToolbar


def allocate_memory(size_mb: int = 10) -> list[bytes]:
    """Allocate memory by creating a large list.

    Args:
        size_mb: Size of memory to allocate in megabytes.

    Returns:
        List of byte arrays totaling approximately size_mb megabytes.
    """
    chunk_size = 1024 * 1024
    return [b"x" * chunk_size for _ in range(size_mb)]


def create_nested_structures() -> dict:
    """Create nested data structures to consume memory.

    Returns:
        Dictionary with nested lists and dictionaries.
    """
    result = {}
    for i in range(100):
        result[f"key_{i}"] = {
            "data": [j**2 for j in range(1000)],
            "nested": {
                "items": list(range(500)),
                "values": [f"value_{k}" for k in range(100)],
            },
        }
    return result


async def main() -> None:
    """Demonstrate Memory Panel functionality."""
    print("=" * 70)
    print("Memory Panel Examples")
    print("=" * 70)
    print()

    print("Example 1: Basic Memory Tracking (tracemalloc backend)")
    print("-" * 70)
    config = DebugToolbarConfig(enabled=True)
    toolbar = DebugToolbar(config=config)
    toolbar.config.memory_backend = "tracemalloc"

    panel = MemoryPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    data = allocate_memory(5)
    nested = create_nested_structures()

    await panel.process_response(context)

    stats = await panel.generate_stats(context)

    print(f"Backend: {stats['backend']}")
    print(f"Memory before: {stats['memory_before']:,} bytes")
    print(f"Memory after: {stats['memory_after']:,} bytes")
    print(f"Memory delta: {stats['memory_delta']:,} bytes")
    print(f"Peak memory: {stats['peak_memory']:,} bytes")
    print(f"Profiling overhead: {stats['profiling_overhead']:.6f}s")
    print()
    print("Top 5 Allocations:")
    for i, alloc in enumerate(stats["top_allocations"][:5], 1):
        print(f"  {i}. {alloc['file']}")
        print(f"     Line: {alloc['line']}, Size: {alloc['size']:,} bytes, Count: {alloc['count']}")
    print()

    del data
    del nested

    print("Example 2: Auto Backend Selection")
    print("-" * 70)
    toolbar2 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    toolbar2.config.memory_backend = "auto"

    panel2 = MemoryPanel(toolbar2)
    context2 = await toolbar2.process_request()

    await panel2.process_request(context2)

    temp_data = [i**3 for i in range(100000)]

    await panel2.process_response(context2)
    stats2 = await panel2.generate_stats(context2)

    print(f"Auto-selected backend: {stats2['backend']}")
    print(f"Memory delta: {stats2['memory_delta']:,} bytes")
    print(f"Peak memory: {stats2['peak_memory']:,} bytes")
    print()

    del temp_data

    print("Example 3: Server-Timing Header Generation")
    print("-" * 70)
    panel.record_stats(context, stats)
    timing = panel.generate_server_timing(context)
    print("Server-Timing metrics:")
    for metric, duration in timing.items():
        print(f"  {metric}: {duration:.6f}s")
    print()

    print("Example 4: Navigation Subtitle Formatting")
    print("-" * 70)
    toolbar3 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    toolbar3.config.memory_backend = "tracemalloc"
    panel3 = MemoryPanel(toolbar3)
    context3 = await toolbar3.process_request()

    await panel3.process_request(context3)

    large_data = allocate_memory(20)

    await panel3.process_response(context3)
    stats3 = await panel3.generate_stats(context3)

    print(f"Panel navigation subtitle: {panel3.get_nav_subtitle()}")
    print(f"Raw memory delta: {stats3['memory_delta']:,} bytes")
    print(f"Panel enabled: {panel3.enabled}")
    print()

    del large_data

    print("Example 5: Comparing Memory Backends")
    print("-" * 70)
    backends = ["tracemalloc", "auto"]

    for backend_name in backends:
        toolbar_test = DebugToolbar(config=DebugToolbarConfig(enabled=True))
        toolbar_test.config.memory_backend = backend_name
        panel_test = MemoryPanel(toolbar_test)
        context_test = await toolbar_test.process_request()

        await panel_test.process_request(context_test)

        test_data = [b"test" * 1000 for _ in range(10000)]

        await panel_test.process_response(context_test)
        stats_test = await panel_test.generate_stats(context_test)

        print(f"{backend_name.upper()} Backend:")
        print(f"  Selected: {stats_test['backend']}")
        print(f"  Memory delta: {stats_test['memory_delta']:,} bytes")
        print(f"  Overhead: {stats_test['profiling_overhead']:.6f}s")
        print(f"  Top allocations: {len(stats_test['top_allocations'])}")
        print()

        del test_data

    print("Example 6: Memory Statistics Summary")
    print("-" * 70)
    print(f"Total memory tracked: {stats['memory_after'] - stats['memory_before']:,} bytes")
    overhead_percentage = (stats["profiling_overhead"] / 0.1) * 100 if stats.get("profiling_overhead") else 0
    print(f"Profiling overhead: {stats['profiling_overhead']:.6f}s ({overhead_percentage:.2f}% of 0.1s)")
    print(f"Peak memory usage: {stats['peak_memory']:,} bytes")
    print(f"Allocations tracked: {len(stats['top_allocations'])}")
    print()

    if stats["top_allocations"]:
        top_alloc = stats["top_allocations"][0]
        print("Largest allocation:")
        print(f"  Location: {top_alloc['file']}")
        print(f"  Line: {top_alloc['line']}")
        print(f"  Size: {top_alloc['size']:,} bytes")
        print(f"  Count: {top_alloc['count']}")
    print()

    print("=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
