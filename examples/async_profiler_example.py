"""Example demonstrating the Async Profiler Panel usage."""

# ruff: noqa: T201, INP001, ASYNC251, C901, PLR0912

from __future__ import annotations

import asyncio
import time

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.panels.async_profiler import AsyncProfilerPanel
from debug_toolbar.core.toolbar import DebugToolbar


async def fast_task(task_id: int) -> int:
    """A fast async task that completes quickly.

    Args:
        task_id: Identifier for the task.

    Returns:
        The task_id multiplied by 2.
    """
    await asyncio.sleep(0.01)
    return task_id * 2


async def slow_task(task_id: int) -> int:
    """A slower async task that takes more time.

    Args:
        task_id: Identifier for the task.

    Returns:
        The task_id multiplied by 10.
    """
    await asyncio.sleep(0.1)
    return task_id * 10


async def blocking_task() -> None:
    """A task that contains blocking I/O (simulated)."""
    time.sleep(0.15)


async def nested_tasks() -> list[int]:
    """Create nested async tasks to demonstrate parent tracking.

    Returns:
        List of results from child tasks.
    """
    tasks = [asyncio.create_task(fast_task(i)) for i in range(3)]
    return await asyncio.gather(*tasks)


async def main() -> None:
    """Demonstrate Async Profiler Panel functionality."""
    print("=" * 70)
    print("Async Profiler Panel Examples")
    print("=" * 70)
    print()

    print("Example 1: Basic Async Task Tracking")
    print("-" * 70)
    config = DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_capture_task_stacks=True,
        async_max_stack_depth=5,
    )
    toolbar = DebugToolbar(config=config)
    panel = AsyncProfilerPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    tasks = [asyncio.create_task(fast_task(i), name=f"fast_task_{i}") for i in range(5)]
    await asyncio.gather(*tasks)

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    print(f"Backend: {stats['backend']}")
    print(f"Total tasks created: {stats['summary']['total_tasks']}")
    print(f"Completed tasks: {stats['summary']['completed_tasks']}")
    print(f"Profiling overhead: {stats['profiling_overhead']:.6f}s")
    print()
    print("Tasks tracked:")
    for task in stats["tasks"][:10]:
        if task["event_type"] == "created":
            print(f"  - {task['task_name']} ({task['coro_name']})")
    print()

    print("Example 2: Mixed Fast and Slow Tasks")
    print("-" * 70)
    toolbar2 = DebugToolbar(config=config)
    panel2 = AsyncProfilerPanel(toolbar2)
    context2 = await toolbar2.process_request()

    await panel2.process_request(context2)

    mixed_tasks = [
        asyncio.create_task(fast_task(1), name="fast_1"),
        asyncio.create_task(slow_task(2), name="slow_1"),
        asyncio.create_task(fast_task(3), name="fast_2"),
        asyncio.create_task(slow_task(4), name="slow_2"),
    ]
    await asyncio.gather(*mixed_tasks)

    await panel2.process_response(context2)
    stats2 = await panel2.generate_stats(context2)

    print(f"Total tasks: {stats2['summary']['total_tasks']}")
    print("Task durations:")
    for task in stats2["tasks"]:
        if task["event_type"] == "completed" and task.get("duration_ms"):
            print(f"  - {task['task_name']}: {task['duration_ms']:.2f}ms")
    print()

    print("Example 3: Timeline Visualization Data")
    print("-" * 70)
    timeline = stats2.get("timeline", {})
    print(f"Timeline duration: {timeline.get('total_duration_ms', 0):.2f}ms")
    print(f"Max concurrent tasks: {timeline.get('max_concurrent', 0)}")
    print(f"Timeline events: {len(timeline.get('events', []))}")
    print()

    print("Example 4: Blocking Call Detection")
    print("-" * 70)
    config_blocking = DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_enable_blocking_detection=True,
        async_blocking_threshold_ms=100.0,
    )
    toolbar3 = DebugToolbar(config=config_blocking)
    panel3 = AsyncProfilerPanel(toolbar3)
    context3 = await toolbar3.process_request()

    await panel3.process_request(context3)

    await asyncio.create_task(blocking_task(), name="blocking_task")

    await panel3.process_response(context3)
    stats3 = await panel3.generate_stats(context3)

    blocking_count = stats3["summary"]["blocking_calls_count"]
    print(f"Blocking calls detected: {blocking_count}")
    print(f"Has warnings: {stats3['summary']['has_warnings']}")
    if stats3.get("blocking_calls"):
        for call in stats3["blocking_calls"]:
            print(f"  - {call['function_name']}: {call['duration_ms']:.2f}ms")
            print(f"    Location: {call['file']}:{call['line']}")
    print()

    print("Example 5: Event Loop Lag Monitoring")
    print("-" * 70)
    config_lag = DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_enable_event_loop_monitoring=True,
        async_event_loop_lag_threshold_ms=5.0,
    )
    toolbar4 = DebugToolbar(config=config_lag)
    panel4 = AsyncProfilerPanel(toolbar4)
    context4 = await toolbar4.process_request()

    await panel4.process_request(context4)

    for _ in range(10):
        await asyncio.sleep(0.01)
        time.sleep(0.02)

    await panel4.process_response(context4)
    stats4 = await panel4.generate_stats(context4)

    print(f"Max event loop lag: {stats4['summary']['max_lag_ms']:.2f}ms")
    lag_samples = stats4.get("event_loop_lag", [])
    print(f"Lag samples above threshold: {len(lag_samples)}")
    if lag_samples:
        print("Sample lag readings:")
        for sample in lag_samples[:5]:
            print(f"  - Lag: {sample['lag_ms']:.2f}ms at t={sample['timestamp']:.3f}s")
    print()

    print("Example 6: Nested Task Parent Tracking")
    print("-" * 70)
    toolbar5 = DebugToolbar(config=config)
    panel5 = AsyncProfilerPanel(toolbar5)
    context5 = await toolbar5.process_request()

    await panel5.process_request(context5)

    result = await asyncio.create_task(nested_tasks(), name="parent_task")
    print(f"Nested task results: {result}")

    await panel5.process_response(context5)
    stats5 = await panel5.generate_stats(context5)

    print("Tasks with parent tracking:")
    for task in stats5["tasks"]:
        if task["event_type"] == "created":
            parent = task.get("parent_task_id", "None")
            print(f"  - {task['task_name']} (parent: {parent[:8] if parent else 'root'}...)")
    print()

    print("Example 7: Stack Trace Capture")
    print("-" * 70)
    config_stacks = DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_capture_task_stacks=True,
        async_max_stack_depth=3,
    )
    toolbar6 = DebugToolbar(config=config_stacks)
    panel6 = AsyncProfilerPanel(toolbar6)
    context6 = await toolbar6.process_request()

    await panel6.process_request(context6)

    await asyncio.create_task(fast_task(1), name="traced_task")

    await panel6.process_response(context6)
    stats6 = await panel6.generate_stats(context6)

    print("Stack frames captured for first task:")
    for task in stats6["tasks"]:
        if task["event_type"] == "created" and task.get("stack_frames"):
            for frame in task["stack_frames"][:3]:
                print(f"  {frame['file']}:{frame['line']} in {frame['function']}")
            break
    print()

    print("Example 8: Navigation Subtitle")
    print("-" * 70)
    print(f"Panel nav subtitle: {panel.get_nav_subtitle()}")
    print(f"Panel title: {panel.title}")
    print(f"Panel ID: {panel.panel_id}")
    print()

    print("Example 9: Server-Timing Header Generation")
    print("-" * 70)
    panel.record_stats(context, stats)
    timing = panel.generate_server_timing(context)
    print("Server-Timing metrics:")
    for metric, duration in timing.items():
        print(f"  {metric}: {duration:.6f}s")
    print()

    print("=" * 70)
    print("Examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
