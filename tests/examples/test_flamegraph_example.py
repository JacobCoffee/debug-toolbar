"""Tests for the flame graph example script."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    import pytest


def test_main_writes_valid_speedscope_json(
    import_example: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The script's main() should profile real work and write a valid speedscope file."""
    monkeypatch.chdir(tmp_path)
    module = import_example("examples.flamegraph_example")

    module.main()

    output = capsys.readouterr().out
    assert "Profiled 10 fibonacci calculations" in output
    assert "Speedscope JSON generated successfully!" in output

    saved_path = tmp_path / "profile.speedscope.json"
    assert saved_path.exists()

    data = json.loads(saved_path.read_text())
    assert data["$schema"]
    assert len(data["shared"]["frames"]) > 0
    assert len(data["profiles"]) > 0

    profile = data["profiles"][0]
    assert profile["type"]
    assert profile["unit"]
    assert profile["endValue"] >= 0
    assert len(profile["samples"]) > 0
    assert len(profile["samples"]) == len(profile["weights"])


def test_flamegraph_generator_produces_fibonacci_frames(
    import_example: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Replicate the example's profiling setup directly and inspect the frame names."""
    monkeypatch.chdir(tmp_path)
    module = import_example("examples.flamegraph_example")

    import cProfile

    from debug_toolbar.core.panels.flamegraph import FlameGraphGenerator

    profiler = cProfile.Profile()
    profiler.enable()
    module.compute_intensive_task()
    module.data_processing()
    profiler.disable()

    generator = FlameGraphGenerator(profiler)
    speedscope_json = generator.generate()

    frame_names = [frame["name"] for frame in speedscope_json["shared"]["frames"]]
    assert any("fibonacci" in name for name in frame_names)
    assert any("data_processing" in name for name in frame_names)
