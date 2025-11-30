# /// script
# requires-python = ">=3.10"
# dependencies = ["debug-toolbar", "jinja2>=3.1.0"]
# ///
"""Example demonstrating the Templates Panel with Jinja2 templates.

This example shows how the Templates Panel tracks template rendering
performance across Jinja2 templates.

Run with: uv run examples/templates_panel_example.py
"""

from __future__ import annotations

import asyncio

from jinja2 import Environment, Template

from debug_toolbar import DebugToolbar, DebugToolbarConfig
from debug_toolbar.core.context import RequestContext, set_request_context


async def main() -> None:
    config = DebugToolbarConfig(
        enabled=True,
        panels=[
            "debug_toolbar.core.panels.timer.TimerPanel",
            "debug_toolbar.core.panels.templates.TemplatesPanel",
        ],
    )

    toolbar = DebugToolbar(config)
    templates_panel = toolbar.get_panel("templates")

    if not templates_panel:
        print("Templates panel not found!")
        return

    context = RequestContext()
    set_request_context(context)

    print("Starting template rendering example...\n")

    await templates_panel.process_request(context)

    env = Environment()

    template1 = Template("Hello {{ name }}!")
    result1 = template1.render(name="World")
    print(f"Template 1 result: {result1}")

    template2 = Template(
        """
        <div>
            <h1>{{ title }}</h1>
            <ul>
            {% for item in items %}
                <li>{{ item }}</li>
            {% endfor %}
            </ul>
        </div>
        """
    )
    result2 = template2.render(title="My List", items=["Item 1", "Item 2", "Item 3"])
    print(f"Template 2 result: {result2[:50]}...")

    template3 = env.from_string(
        """
        <table>
        {% for user in users %}
            <tr>
                <td>{{ user.name }}</td>
                <td>{{ user.email }}</td>
            </tr>
        {% endfor %}
        </table>
        """
    )
    result3 = template3.render(
        users=[
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
    )
    print(f"Template 3 result: {result3[:50]}...")

    await templates_panel.process_response(context)

    stats = await templates_panel.generate_stats(context)

    print("\n" + "=" * 50)
    print("Template Rendering Statistics")
    print("=" * 50)
    print(f"Total renders: {stats['total_renders']}")
    print(f"Total time: {stats['total_time']:.6f} seconds")
    print(f"Engines used: {', '.join(stats['engines_used'])}")
    print("\nIndividual renders:")
    for idx, render in enumerate(stats["renders"], 1):
        print(f"  {idx}. Template: {render['template_name']}")
        print(f"     Engine: {render['engine']}")
        print(f"     Time: {render['render_time']:.6f}s")
        if render.get("context_keys"):
            print(f"     Context keys: {', '.join(render['context_keys'])}")
        print()

    timings = templates_panel.generate_server_timing(context)
    if timings:
        print("Server-Timing Metrics:")
        for metric, duration in timings.items():
            print(f"  {metric}: {duration:.6f}s")


if __name__ == "__main__":
    asyncio.run(main())
