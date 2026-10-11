"""Tests for the profiling panel example script."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_prints_expected_output(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The script's main() should report cProfile results with real function counts."""
    monkeypatch.chdir(tmp_path)
    module = import_example("examples.profiling_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Backend: cprofile" in output
    assert "Flame graph data generated successfully!" in output
    assert "Saved to: panel_profile.speedscope.json" in output

    saved_path = tmp_path / "panel_profile.speedscope.json"
    assert saved_path.exists()
    saved_data = json.loads(saved_path.read_text())
    assert saved_data["$schema"]
    assert len(saved_data["profiles"]) > 0


@pytest.mark.asyncio
async def test_profiling_panel_tracks_function_calls(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 1's setup to assert on real profiling stats."""
    module = import_example("examples.profiling_panel_example")

    config = module.DebugToolbarConfig(enabled=True)
    toolbar = module.DebugToolbar(config=config)
    toolbar.config.profiler_backend = "cprofile"
    toolbar.config.profiler_top_functions = 10
    toolbar.config.profiler_sort_by = "cumulative"

    panel = module.ProfilingPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    module.compute_intensive_task()
    module.io_simulation()

    await panel.process_response(context)

    stats = await panel.generate_stats(context)

    assert stats["backend"] == "cprofile"
    assert stats["total_time"] > 0
    assert stats["function_calls"] > 0
    assert stats["primitive_calls"] > 0
    assert len(stats["top_functions"]) > 0

    top_func = stats["top_functions"][0]
    assert top_func["calls"] > 0
    assert top_func["cumulative_time"] >= 0


@pytest.mark.asyncio
async def test_profiling_panel_flamegraph_data(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 7's flame graph generation and assert on the speedscope JSON."""
    module = import_example("examples.profiling_panel_example")

    toolbar3 = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))
    toolbar3.config.profiler_backend = "cprofile"
    toolbar3.config.enable_flamegraph = True

    panel3 = module.ProfilingPanel(toolbar3)
    context3 = await toolbar3.process_request()

    await panel3.process_request(context3)

    module.compute_intensive_task()

    await panel3.process_response(context3)
    stats3 = await panel3.generate_stats(context3)

    assert stats3["flamegraph_available"] is True
    flamegraph = stats3["flamegraph_data"]
    assert flamegraph["$schema"]
    assert len(flamegraph["shared"]["frames"]) > 0
    assert len(flamegraph["profiles"]) > 0

    profile_data = flamegraph["profiles"][0]
    assert profile_data["type"]
    assert profile_data["endValue"] >= 0
    assert len(profile_data["samples"]) > 0
