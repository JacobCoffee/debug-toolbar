"""Tests for the memory panel example script."""

from __future__ import annotations

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
    """The script's main() should report real memory tracking across backends."""
    module = import_example("examples.memory_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Backend: tracemalloc" in output
    assert "Auto-selected backend:" in output
    assert "Top 5 Allocations:" in output


@pytest.mark.asyncio
async def test_memory_panel_tracks_allocation(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 1's basic tracemalloc tracking and assert on real stats."""
    module = import_example("examples.memory_panel_example")

    config = module.DebugToolbarConfig(enabled=True)
    toolbar = module.DebugToolbar(config=config)
    toolbar.config.memory_backend = "tracemalloc"

    panel = module.MemoryPanel(toolbar)
    context = await toolbar.process_request()

    await panel.process_request(context)

    data = module.allocate_memory(5)
    nested = module.create_nested_structures()

    await panel.process_response(context)

    stats = await panel.generate_stats(context)

    assert stats["backend"] == "tracemalloc"
    assert stats["memory_before"] >= 0
    assert stats["memory_after"] >= 0
    assert stats["memory_delta"] > 0
    assert stats["peak_memory"] > 0
    assert len(stats["top_allocations"]) > 0

    top_alloc = stats["top_allocations"][0]
    assert top_alloc["size"] > 0
    assert top_alloc["count"] > 0

    del data
    del nested


@pytest.mark.asyncio
async def test_memory_panel_auto_backend_selection(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate example 2's auto backend selection and assert a real backend is chosen."""
    module = import_example("examples.memory_panel_example")

    toolbar2 = module.DebugToolbar(config=module.DebugToolbarConfig(enabled=True))
    toolbar2.config.memory_backend = "auto"

    panel2 = module.MemoryPanel(toolbar2)
    context2 = await toolbar2.process_request()

    await panel2.process_request(context2)

    temp_data = [i**3 for i in range(100000)]

    await panel2.process_response(context2)
    stats2 = await panel2.generate_stats(context2)

    assert stats2["backend"] in {"tracemalloc", "memray"}
    assert stats2["memory_delta"] >= 0
    assert stats2["peak_memory"] >= 0

    del temp_data
