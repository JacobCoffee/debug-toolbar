"""Tests for the templates panel example script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_reports_real_jinja2_render_statistics(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real script should report three real Jinja2 template renders."""
    module = import_example("examples.templates_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Template 1 result: Hello World!" in output
    assert "Template 2 result:" in output
    assert "Template 3 result:" in output
    assert "Total renders: 3" in output
    assert "Engines used: jinja2" in output
    assert output.count("Template:") == 3
    assert output.count("Engine: jinja2") == 3
    assert "Context keys: name" in output
