"""Tests for the async profiler panel example script."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_prints_expected_output(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The script's main() should report real task counts and durations."""
    module = import_example("examples.async_profiler_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Total tasks created: 5" in output
    assert "Completed tasks: 5" in output
    assert "Total tasks: 4" in output
    assert "Nested task results: [0, 2, 4]" in output


@pytest.mark.asyncio
async def test_async_profiler_tracks_task_completion(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 1's setup and assert on the real summary stats."""
    module = import_example("examples.async_profiler_example")

    config = module.DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_capture_task_stacks=True,
        async_max_stack_depth=5,
    )
    toolbar = module.DebugToolbar(config=config)
    panel = module.AsyncProfilerPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    tasks = [asyncio.create_task(module.fast_task(i), name=f"fast_task_{i}") for i in range(5)]
    await asyncio.gather(*tasks)

    await panel.process_response(context)
    stats = await panel.generate_stats(context)

    assert stats["backend"] == "taskfactory"
    assert stats["summary"]["total_tasks"] == 5
    assert stats["summary"]["completed_tasks"] == 5
    created = [task for task in stats["tasks"] if task["event_type"] == "created"]
    assert len(created) == 5
    assert all(task["coro_name"] == "fast_task" for task in created)


@pytest.mark.asyncio
async def test_async_profiler_detects_slow_tasks(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 2's mixed fast/slow tasks and assert durations separate them."""
    module = import_example("examples.async_profiler_example")

    config = module.DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_capture_task_stacks=True,
        async_max_stack_depth=5,
    )
    toolbar2 = module.DebugToolbar(config=config)
    panel2 = module.AsyncProfilerPanel(toolbar2)
    context2 = await toolbar2.process_request()

    await panel2.process_request(context2)

    mixed_tasks = [
        asyncio.create_task(module.fast_task(1), name="fast_1"),
        asyncio.create_task(module.slow_task(2), name="slow_1"),
        asyncio.create_task(module.fast_task(3), name="fast_2"),
        asyncio.create_task(module.slow_task(4), name="slow_2"),
    ]
    await asyncio.gather(*mixed_tasks)

    await panel2.process_response(context2)
    stats2 = await panel2.generate_stats(context2)

    assert stats2["summary"]["total_tasks"] == 4

    completed = [task for task in stats2["tasks"] if task["event_type"] == "completed" and task.get("duration_ms")]
    durations_by_coro: dict[str, list[float]] = {}
    for task in completed:
        durations_by_coro.setdefault(task["coro_name"], []).append(task["duration_ms"])

    assert all(duration < 50 for duration in durations_by_coro["fast_task"])
    assert all(duration >= 90 for duration in durations_by_coro["slow_task"])


@pytest.mark.asyncio
async def test_async_profiler_event_loop_lag_monitoring(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 5's event loop lag monitoring and assert real lag was recorded."""
    module = import_example("examples.async_profiler_example")

    config_lag = module.DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_enable_event_loop_monitoring=True,
        async_event_loop_lag_threshold_ms=5.0,
    )
    toolbar4 = module.DebugToolbar(config=config_lag)
    panel4 = module.AsyncProfilerPanel(toolbar4)
    context4 = await toolbar4.process_request()

    await panel4.process_request(context4)

    for _ in range(10):
        await asyncio.sleep(0.01)
        time.sleep(0.02)  # noqa: ASYNC251

    await panel4.process_response(context4)
    stats4 = await panel4.generate_stats(context4)

    assert stats4["summary"]["max_lag_ms"] > 0
    assert stats4["event_loop_lag"]


@pytest.mark.asyncio
async def test_async_profiler_nested_task_parent_tracking(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 6's nested task tracking and assert parent links are recorded."""
    module = import_example("examples.async_profiler_example")

    config = module.DebugToolbarConfig(
        enabled=True,
        async_profiler_backend="taskfactory",
        async_capture_task_stacks=True,
        async_max_stack_depth=5,
    )
    toolbar5 = module.DebugToolbar(config=config)
    panel5 = module.AsyncProfilerPanel(toolbar5)
    context5 = await toolbar5.process_request()

    await panel5.process_request(context5)

    result = await asyncio.create_task(module.nested_tasks(), name="parent_task")
    assert result == [0, 2, 4]

    await panel5.process_response(context5)
    stats5 = await panel5.generate_stats(context5)

    created_tasks = [task for task in stats5["tasks"] if task["event_type"] == "created"]
    parent_ids = [task["parent_task_id"] for task in created_tasks if task["parent_task_id"] is not None]
    counts: dict[str, int] = {}
    for parent_id in parent_ids:
        counts[parent_id] = counts.get(parent_id, 0) + 1

    assert 3 in counts.values()
