"""Tests for the memory panel example script."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_memory_allocations(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real script should report real, non-zero memory deltas for both backends."""
    module = import_example("examples.memory_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Backend: tracemalloc" in output
    assert "Auto-selected backend:" in output
    assert "Top 5 Allocations:" in output

    delta_matches = re.findall(r"Memory delta: ([\d,]+) bytes", output)
    assert len(delta_matches) >= 2
    assert all(int(match.replace(",", "")) > 0 for match in delta_matches)

    peak_matches = re.findall(r"Peak memory: ([\d,]+) bytes", output)
    assert len(peak_matches) >= 1
    assert all(int(match.replace(",", "")) > 0 for match in peak_matches)

    assert "TRACEMALLOC Backend:" in output
    assert "AUTO Backend:" in output
