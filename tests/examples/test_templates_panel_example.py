"""Tests for the templates panel example script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from debug_toolbar.core.context import RequestContext, set_request_context

if TYPE_CHECKING:
    from types import ModuleType


@pytest.mark.asyncio
async def test_main_prints_expected_summary(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The script's main() should report three renders across the jinja2 engine."""
    module = import_example("examples.templates_panel_example")

    await module.main()

    output = capsys.readouterr().out
    assert "Total renders: 3" in output
    assert "Engines used: jinja2" in output
    assert "Template 1 result: Hello World!" in output


@pytest.mark.asyncio
async def test_templates_panel_generates_real_stats(
    import_example: Callable[[str], ModuleType],
) -> None:
    """Replicate the example's panel setup directly to assert on the real stats dict."""
    module = import_example("examples.templates_panel_example")

    config = module.DebugToolbarConfig(
        enabled=True,
        panels=[
            "debug_toolbar.core.panels.timer.TimerPanel",
            "debug_toolbar.core.panels.templates.TemplatesPanel",
        ],
    )
    toolbar = module.DebugToolbar(config)
    templates_panel = toolbar.get_panel("TemplatesPanel")
    assert templates_panel is not None

    context = RequestContext()
    set_request_context(context)

    await templates_panel.process_request(context)

    from jinja2 import Environment, Template

    template1 = Template("Hello {{ name }}!")
    result1 = template1.render(name="World")
    assert result1 == "Hello World!"

    env = Environment()
    template2 = Template("<div>{{ title }}</div>")
    result2 = template2.render(title="My List")
    assert result2 == "<div>My List</div>"

    template3 = env.from_string("{{ greeting }}, {{ name }}!")
    result3 = template3.render(greeting="Hi", name="Jinja")
    assert result3 == "Hi, Jinja!"

    await templates_panel.process_response(context)

    stats = await templates_panel.generate_stats(context)

    assert stats["total_renders"] == 3
    assert stats["total_time"] >= 0
    assert stats["engines_used"] == ["jinja2"]
    assert stats["renders"][0]["template_name"]
    assert stats["renders"][1]["template_name"]
    assert stats["renders"][2]["template_name"]
