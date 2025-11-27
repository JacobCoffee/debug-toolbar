"""Example demonstrating the Profiling Panel usage."""

# ruff: noqa: T201, INP001

from __future__ import annotations

import asyncio
import time

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.profiling import ProfilingPanel
from debug_toolbar.core.toolbar import DebugToolbar


def fibonacci(n: int) -> int:
    """Calculate fibonacci number recursively (slow for demonstration)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def compute_intensive_task() -> dict[str, int]:
    """Simulate a compute-intensive task."""
    results = {}
    for i in range(10):
        results[f"fib_{i}"] = fibonacci(i + 15)
    return results


def io_simulation() -> None:
    """Simulate I/O operations."""
    time.sleep(0.01)
    data = [i**2 for i in range(1000)]
    _ = sum(data)


async def main() -> None:
    """Demonstrate Profiling Panel functionality."""
    print("=" * 70)
    print("Profiling Panel Examples")
    print("=" * 70)
    print()

    print("Example 1: Basic cProfile Profiling")
    print("-" * 70)
    config = DebugToolbarConfig(enabled=True)
    toolbar = DebugToolbar(config=config)
    toolbar.config.profiler_backend = "cprofile"
    toolbar.config.profiler_top_functions = 10
    toolbar.config.profiler_sort_by = "cumulative"

    panel = ProfilingPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    compute_intensive_task()
    io_simulation()

    await panel.process_response(context)

    stats = await panel.generate_stats(context)

    print(f"Backend: {stats['backend']}")
    print(f"Total Time: {stats['total_time']:.4f}s")
    print(f"Function Calls: {stats['function_calls']:,}")
    print(f"Primitive Calls: {stats['primitive_calls']:,}")
    print(f"Profiling Overhead: {stats['profiling_overhead']:.6f}s")
    print()
    print("Top 5 Functions by Cumulative Time:")
    for i, func in enumerate(stats["top_functions"][:5], 1):
        print(
            f"  {i}. {func['function']} "
            f"({func['calls']} calls, {func['cumulative_time']:.4f}s cumulative)"
        )
    print()

    print("Example 2: Profiling with Different Sort Order")
    print("-" * 70)
    toolbar2 = DebugToolbar(config=DebugToolbarConfig(enabled=True))
    toolbar2.config.profiler_backend = "cprofile"
    toolbar2.config.profiler_top_functions = 5
    toolbar2.config.profiler_sort_by = "time"

    panel2 = ProfilingPanel(toolbar2)
    context2 = await toolbar2.process_request()

    await panel2.process_request(context2)

    for _ in range(100):
        _ = [i**2 for i in range(100)]

    await panel2.process_response(context2)
    stats2 = await panel2.generate_stats(context2)

    print(f"Backend: {stats2['backend']}")
    print(f"Total Time: {stats2['total_time']:.4f}s")
    print("Sort By: time (total time spent in function)")
    print()
    print("Top 5 Functions by Total Time:")
    for i, func in enumerate(stats2["top_functions"][:5], 1):
        print(
            f"  {i}. {func['function']} "
            f"({func['calls']} calls, {func['total_time']:.4f}s total, "
            f"{func['per_call']:.6f}s per call)"
        )
    print()

    print("Example 3: Server-Timing Header Generation")
    print("-" * 70)
    panel.record_stats(context, stats)
    timing = panel.generate_server_timing(context)
    print("Server-Timing metrics:")
    for metric, duration in timing.items():
        print(f"  {metric}: {duration:.6f}s")
    print()

    print("Example 4: Call Tree Preview")
    print("-" * 70)
    if stats["call_tree"]:
        lines = stats["call_tree"].split("\n")
        preview_lines = [line for line in lines[:20] if line.strip()]
        print("First 20 lines of call tree:")
        for line in preview_lines:
            print(f"  {line}")
        print(f"\n  ... ({len(lines) - 20} more lines)")
    print()

    print("Example 5: Profiling Statistics Summary")
    print("-" * 70)
    print(f"Total execution time: {stats['total_time']:.4f}s")
    print(f"Profiler overhead: {stats['profiling_overhead']:.6f}s")
    overhead_percentage = (stats["profiling_overhead"] / stats["total_time"]) * 100
    print(f"Overhead percentage: {overhead_percentage:.2f}%")
    print(f"Total function calls: {stats['function_calls']:,}")
    print(f"Functions tracked: {len(stats['top_functions'])}")
    print()

    hottest_func = stats["top_functions"][0] if stats["top_functions"] else None
    if hottest_func:
        print("Hottest function (by cumulative time):")
        print(f"  Function: {hottest_func['function']}")
        print(f"  File: {hottest_func['filename']}:{hottest_func['lineno']}")
        print(f"  Calls: {hottest_func['calls']:,}")
        print(f"  Cumulative time: {hottest_func['cumulative_time']:.4f}s")
        print(f"  Time per call: {hottest_func['per_call']:.6f}s")
    print()

    print("Example 6: Navigation Subtitle")
    print("-" * 70)
    print(f"Panel navigation subtitle: {panel.get_nav_subtitle()}")
    print(f"Panel enabled: {panel.enabled}")
    print()

    print("=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
