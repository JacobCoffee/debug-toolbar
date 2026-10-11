"""Tests for the profiling panel example script."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_profiling_results(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Running the real script should report real cProfile counts and a valid flame graph."""
    monkeypatch.chdir(tmp_path)
    module = import_example("examples.profiling_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Backend: cprofile" in output

    calls_match = re.search(r"Function Calls: ([\d,]+)", output)
    assert calls_match is not None
    assert int(calls_match.group(1).replace(",", "")) > 0

    primitive_match = re.search(r"Primitive Calls: ([\d,]+)", output)
    assert primitive_match is not None
    assert int(primitive_match.group(1).replace(",", "")) > 0

    assert "Top 5 Functions by Cumulative Time:" in output
    assert "fibonacci" in output

    assert "Flame graph data generated successfully!" in output
    assert "Saved to: panel_profile.speedscope.json" in output

    saved_path = tmp_path / "panel_profile.speedscope.json"
    assert saved_path.exists()
    saved_data = json.loads(saved_path.read_text())
    assert saved_data["$schema"]
    assert len(saved_data["profiles"]) > 0
    assert len(saved_data["shared"]["frames"]) > 0
