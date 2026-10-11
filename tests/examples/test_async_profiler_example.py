"""Tests for the async profiler panel example script."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_task_tracking(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real script should report real task counts, durations, and lag samples."""
    module = import_example("examples.async_profiler_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Backend: taskfactory" in output

    total_match = re.search(r"Total tasks created: (\d+)", output)
    assert total_match is not None
    assert int(total_match.group(1)) == 5

    completed_match = re.search(r"Completed tasks: (\d+)", output)
    assert completed_match is not None
    assert int(completed_match.group(1)) == 5

    assert "Tasks tracked:" in output
    for i in range(5):
        assert f"fast_task_{i} (fast_task)" in output

    assert "Total tasks: 4" in output
    duration_lines = re.findall(r" - (fast_\d+|slow_\d+): ([\d.]+)ms", output)
    assert len(duration_lines) >= 2
    durations_by_name = dict(duration_lines)
    assert float(durations_by_name["fast_1"]) < float(durations_by_name["slow_1"])

    timeline_match = re.search(r"Timeline duration: ([\d.]+)ms", output)
    assert timeline_match is not None
    assert float(timeline_match.group(1)) > 0

    max_concurrent_match = re.search(r"Max concurrent tasks: (\d+)", output)
    assert max_concurrent_match is not None
    assert int(max_concurrent_match.group(1)) >= 1

    blocking_match = re.search(r"Blocking calls detected: (\d+)", output)
    assert blocking_match is not None
    assert int(blocking_match.group(1)) == 1
    assert "Has warnings: True" in output
    assert "blocking_task:" in output
    blocking_duration_match = re.search(r" - blocking_task: ([\d.]+)ms", output)
    assert blocking_duration_match is not None
    assert float(blocking_duration_match.group(1)) >= 100

    lag_match = re.search(r"Max event loop lag: ([\d.]+)ms", output)
    assert lag_match is not None
    assert float(lag_match.group(1)) > 0
    assert "Lag samples above threshold:" in output

    assert "Nested task results: [0, 2, 4]" in output

    parent_lines = [line for line in output.splitlines() if "(parent:" in line]
    assert len(parent_lines) == 4

    assert "Panel nav subtitle:" in output
    assert "Panel title: Async" in output
    assert "Examples completed successfully!" in output
