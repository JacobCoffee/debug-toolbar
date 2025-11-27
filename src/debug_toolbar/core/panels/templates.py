"""Templates panel for tracking template rendering times and metadata."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

_patch_lock = threading.Lock()

if TYPE_CHECKING:
    from collections.abc import Callable

    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

    try:
        from jinja2 import Template as Jinja2Template
    except ImportError:
        Jinja2Template = Any  # type: ignore[misc]

    try:
        from mako.template import Template as MakoTemplate
    except ImportError:
        MakoTemplate = Any  # type: ignore[misc]


class TemplateRenderTracker:
    """Thread-safe tracker for template renders during a request."""

    __slots__ = ("_original_jinja2_render", "_original_mako_render", "_patched", "renders")

    def __init__(self) -> None:
        self.renders: list[dict[str, Any]] = []
        self._original_jinja2_render: Callable[..., Any] | None = None
        self._original_mako_render: Callable[..., Any] | None = None
        self._patched: set[str] = set()

    def track_render(
        self,
        template_name: str,
        engine: str,
        render_time: float,
        context_keys: list[str] | None = None,
    ) -> None:
        """Record a template render.

        Args:
            template_name: Name or path of the template.
            engine: Template engine used ('jinja2' or 'mako').
            render_time: Time taken to render in seconds.
            context_keys: List of context variable names, if available.
        """
        self.renders.append(
            {
                "template_name": template_name,
                "engine": engine,
                "render_time": render_time,
                "context_keys": context_keys,
            }
        )

    def patch_jinja2(self) -> None:
        """Patch Jinja2 template rendering to track renders."""
        if "jinja2" in self._patched:
            return

        try:
            from jinja2 import Template as Jinja2Template
        except ImportError:
            return

        with _patch_lock:
            if hasattr(Jinja2Template, "_debug_toolbar_patched"):
                self._patched.add("jinja2")
                return

            if self._original_jinja2_render is None:
                self._original_jinja2_render = Jinja2Template.render

            def tracked_render(template_self: Jinja2Template, *args: Any, **kwargs: Any) -> str:
                start_time = time.perf_counter()

                context_keys = None
                if args and isinstance(args[0], dict):
                    context_keys = list(args[0].keys())
                elif kwargs:
                    context_keys = list(kwargs.keys())

                result = self._original_jinja2_render(template_self, *args, **kwargs)  # type: ignore[misc]

                render_time = time.perf_counter() - start_time

                template_name = getattr(template_self, "name", None) or getattr(template_self, "filename", "<string>")

                self.track_render(
                    template_name=template_name,
                    engine="jinja2",
                    render_time=render_time,
                    context_keys=context_keys,
                )

                return result

            Jinja2Template.render = tracked_render  # type: ignore[method-assign]
            Jinja2Template._debug_toolbar_patched = True  # type: ignore[attr-defined]  # noqa: SLF001
            self._patched.add("jinja2")

    def patch_mako(self) -> None:
        """Patch Mako template rendering to track renders."""
        if "mako" in self._patched:
            return

        try:
            from mako.template import Template as MakoTemplate  # type: ignore[import-untyped]
        except ImportError:
            return

        with _patch_lock:
            if hasattr(MakoTemplate, "_debug_toolbar_patched"):
                self._patched.add("mako")
                return

            if self._original_mako_render is None:
                self._original_mako_render = MakoTemplate.render

            def tracked_render(template_self: MakoTemplate, *args: Any, **kwargs: Any) -> str:
                start_time = time.perf_counter()

                context_keys = None
                if args and isinstance(args[0], dict):
                    context_keys = list(args[0].keys())
                elif kwargs:
                    context_keys = list(kwargs.keys())

                result = self._original_mako_render(template_self, *args, **kwargs)  # type: ignore[misc]

                render_time = time.perf_counter() - start_time

                template_name = getattr(template_self, "filename", None) or getattr(template_self, "uri", "<string>")

                self.track_render(
                    template_name=template_name,
                    engine="mako",
                    render_time=render_time,
                    context_keys=context_keys,
                )

                return result

            MakoTemplate.render = tracked_render  # type: ignore[method-assign]
            MakoTemplate._debug_toolbar_patched = True  # type: ignore[attr-defined]  # noqa: SLF001
            self._patched.add("mako")

    def unpatch_jinja2(self) -> None:
        """Restore original Jinja2 render method."""
        if "jinja2" not in self._patched:
            return

        try:
            from jinja2 import Template as Jinja2Template
        except ImportError:
            return

        with _patch_lock:
            if self._original_jinja2_render is not None and hasattr(Jinja2Template, "_debug_toolbar_patched"):
                Jinja2Template.render = self._original_jinja2_render  # type: ignore[method-assign]
                delattr(Jinja2Template, "_debug_toolbar_patched")
            self._patched.discard("jinja2")

    def unpatch_mako(self) -> None:
        """Restore original Mako render method."""
        if "mako" not in self._patched:
            return

        try:
            from mako.template import Template as MakoTemplate  # type: ignore[import-untyped]
        except ImportError:
            return

        with _patch_lock:
            if self._original_mako_render is not None and hasattr(MakoTemplate, "_debug_toolbar_patched"):
                MakoTemplate.render = self._original_mako_render  # type: ignore[method-assign]
                delattr(MakoTemplate, "_debug_toolbar_patched")
            self._patched.discard("mako")

    def clear(self) -> None:
        """Clear all tracked renders."""
        self.renders = []


class TemplatesPanel(Panel):
    """Panel for tracking template rendering performance.

    Monitors template renders across multiple engines (Jinja2, Mako) and collects:
    - Template names
    - Render times
    - Template engines used
    - Context variable names (when available)

    The panel patches template engine render methods during the request to
    capture timing data transparently.
    """

    panel_id: ClassVar[str] = "templates"
    title: ClassVar[str] = "Templates"
    template: ClassVar[str] = "panels/templates.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Templates"

    __slots__ = ("_tracker",)

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._tracker = TemplateRenderTracker()

    async def process_request(self, context: RequestContext) -> None:
        """Install template rendering hooks.

        Patches Jinja2 and Mako template engines to track renders.
        """
        self._tracker.clear()
        self._tracker.patch_jinja2()
        self._tracker.patch_mako()

    async def process_response(self, context: RequestContext) -> None:
        """Remove template rendering hooks.

        Restores original template rendering methods.
        """
        self._tracker.unpatch_jinja2()
        self._tracker.unpatch_mako()

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate template rendering statistics.

        Returns:
            Dictionary containing:
                - renders: List of render events with timing data
                - total_renders: Total number of templates rendered
                - total_time: Cumulative render time in seconds
                - engines_used: List of template engines used
        """
        renders = list(self._tracker.renders)
        total_time = sum(r["render_time"] for r in renders)
        engines_used = sorted({r["engine"] for r in renders})

        stats = {
            "renders": renders,
            "total_renders": len(renders),
            "total_time": total_time,
            "engines_used": engines_used,
        }

        if total_time > 0:
            context.record_timing("template_render_time", total_time)

        return stats

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data for template rendering.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats or not stats.get("total_time"):
            return {}

        timings = {"templates": stats["total_time"]}

        for engine in stats.get("engines_used", []):
            engine_renders = [r for r in stats["renders"] if r["engine"] == engine]
            engine_time = sum(r["render_time"] for r in engine_renders)
            timings[f"templates-{engine}"] = engine_time

        return timings

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle showing render count and time."""
        return ""
