"""Tests for the templates panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from debug_toolbar.core.panels.templates import (
    TemplateRenderTracker,
    TemplatesPanel,
    _active_tracker,
    _patch_jinja2,
    _patch_mako,
)

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


@pytest.fixture
def tracker() -> TemplateRenderTracker:
    """Create a template render tracker."""
    return TemplateRenderTracker()


@pytest.fixture
def templates_panel(toolbar: DebugToolbar) -> TemplatesPanel:
    """Create a templates panel."""
    return TemplatesPanel(toolbar)


class TestTemplateRenderTracker:
    """Tests for TemplateRenderTracker."""

    def test_track_render(self, tracker: TemplateRenderTracker) -> None:
        """Test tracking a template render."""
        tracker.track_render(
            template_name="test.html",
            engine="jinja2",
            render_time=0.5,
            context_keys=["user", "posts"],
        )

        assert len(tracker.renders) == 1
        render = tracker.renders[0]
        assert render["template_name"] == "test.html"
        assert render["engine"] == "jinja2"
        assert render["render_time"] == 0.5
        assert render["context_keys"] == ["user", "posts"]

    def test_track_multiple_renders(self, tracker: TemplateRenderTracker) -> None:
        """Test tracking multiple template renders."""
        tracker.track_render("template1.html", "jinja2", 0.1)
        tracker.track_render("template2.html", "mako", 0.2)
        tracker.track_render("template3.html", "jinja2", 0.15)

        assert len(tracker.renders) == 3
        assert tracker.renders[0]["template_name"] == "template1.html"
        assert tracker.renders[1]["template_name"] == "template2.html"
        assert tracker.renders[2]["template_name"] == "template3.html"

    def test_clear_renders(self, tracker: TemplateRenderTracker) -> None:
        """Test clearing tracked renders."""
        tracker.track_render("test.html", "jinja2", 0.1)
        tracker.track_render("test2.html", "jinja2", 0.2)
        assert len(tracker.renders) == 2

        tracker.clear()
        assert len(tracker.renders) == 0


class TestTemplatePatchFunctions:
    """Tests for module-level patch functions."""

    def test_patch_jinja2_sets_flag(self) -> None:
        """Test that patching Jinja2 sets the global flag."""
        try:
            import jinja2  # noqa: F401
        except ImportError:
            pytest.skip("Jinja2 not installed")

        _patch_jinja2()
        from debug_toolbar.core.panels.templates import _jinja2_patched

        assert _jinja2_patched is True

    def test_patch_mako_sets_flag(self) -> None:
        """Test that patching Mako sets the global flag."""
        try:
            import mako  # noqa: F401
        except ImportError:
            pytest.skip("Mako not installed")

        _patch_mako()
        from debug_toolbar.core.panels.templates import _mako_patched

        assert _mako_patched is True

    def test_jinja2_template_render_tracking(self, tracker: TemplateRenderTracker) -> None:
        """Test that Jinja2 template renders are tracked via ContextVar."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        _patch_jinja2()
        _active_tracker.set(tracker)

        try:
            template = Template("Hello {{ name }}!")
            result = template.render(name="World")

            assert result == "Hello World!"
            assert len(tracker.renders) == 1

            render_info = tracker.renders[0]
            assert render_info["engine"] == "jinja2"
            assert render_info["render_time"] > 0
            assert "name" in (render_info.get("context_keys") or [])
        finally:
            _active_tracker.set(None)

    def test_mako_template_render_tracking(self, tracker: TemplateRenderTracker) -> None:
        """Test that Mako template renders are tracked via ContextVar."""
        try:
            from mako.template import Template
        except ImportError:
            pytest.skip("Mako not installed")

        _patch_mako()
        _active_tracker.set(tracker)

        try:
            template = Template("Hello ${name}!")
            result = template.render(name="World")

            assert "Hello World!" in result
            assert len(tracker.renders) == 1

            render_info = tracker.renders[0]
            assert render_info["engine"] == "mako"
            assert render_info["render_time"] > 0
            assert "name" in (render_info.get("context_keys") or [])
        finally:
            _active_tracker.set(None)

    def test_renders_not_tracked_without_active_tracker(self) -> None:
        """Test that renders are not tracked when no active tracker is set."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        _patch_jinja2()
        _active_tracker.set(None)

        template = Template("Hello {{ name }}!")
        result = template.render(name="World")

        assert result == "Hello World!"


class TestTemplatesPanel:
    """Tests for TemplatesPanel."""

    def test_panel_attributes(self, templates_panel: TemplatesPanel) -> None:
        """Test panel class attributes are set correctly."""
        assert templates_panel.panel_id == "TemplatesPanel"
        assert templates_panel.title == "Templates"
        assert templates_panel.nav_title == "Templates"
        assert templates_panel.has_content is True

    @pytest.mark.asyncio
    async def test_process_request_sets_active_tracker(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that process_request sets the active tracker."""
        try:
            await templates_panel.process_request(context)
            assert _active_tracker.get() is templates_panel._tracker
        finally:
            await templates_panel.process_response(context)

    @pytest.mark.asyncio
    async def test_process_request_clears_previous_renders(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that process_request clears previous render data."""
        templates_panel._tracker.track_render("old.html", "jinja2", 0.1)
        assert len(templates_panel._tracker.renders) == 1

        try:
            await templates_panel.process_request(context)
            assert len(templates_panel._tracker.renders) == 0
        finally:
            await templates_panel.process_response(context)

    @pytest.mark.asyncio
    async def test_process_response_clears_active_tracker(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that process_response clears the active tracker."""
        await templates_panel.process_request(context)
        assert _active_tracker.get() is not None

        await templates_panel.process_response(context)
        assert _active_tracker.get() is None

    @pytest.mark.asyncio
    async def test_generate_stats_empty(self, templates_panel: TemplatesPanel, context: RequestContext) -> None:
        """Test generate_stats with no renders."""
        stats = await templates_panel.generate_stats(context)

        assert stats["renders"] == []
        assert stats["total_renders"] == 0
        assert stats["total_time"] == 0
        assert stats["engines_used"] == []

    @pytest.mark.asyncio
    async def test_generate_stats_with_renders(self, templates_panel: TemplatesPanel, context: RequestContext) -> None:
        """Test generate_stats with tracked renders."""
        templates_panel._tracker.track_render("template1.html", "jinja2", 0.1, ["var1"])
        templates_panel._tracker.track_render("template2.html", "mako", 0.2, ["var2"])
        templates_panel._tracker.track_render("template3.html", "jinja2", 0.15, ["var3"])

        stats = await templates_panel.generate_stats(context)

        assert len(stats["renders"]) == 3
        assert stats["total_renders"] == 3
        assert stats["total_time"] == 0.45
        assert set(stats["engines_used"]) == {"jinja2", "mako"}

    @pytest.mark.asyncio
    async def test_generate_stats_records_timing(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that generate_stats records timing data to context."""
        templates_panel._tracker.track_render("test.html", "jinja2", 0.5)

        await templates_panel.generate_stats(context)

        assert context.get_timing("template_render_time") == 0.5

    @pytest.mark.asyncio
    async def test_generate_stats_no_timing_when_zero(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that no timing is recorded when total time is zero."""
        stats = await templates_panel.generate_stats(context)

        assert stats["total_time"] == 0
        assert context.get_timing("template_render_time") is None

    def test_generate_server_timing_empty(self, templates_panel: TemplatesPanel, context: RequestContext) -> None:
        """Test generate_server_timing with no stats."""
        timings = templates_panel.generate_server_timing(context)
        assert timings == {}

    def test_generate_server_timing_with_renders(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test generate_server_timing with renders."""
        context.store_panel_data("TemplatesPanel", "total_time", 0.45)
        context.store_panel_data("TemplatesPanel", "total_renders", 3)
        context.store_panel_data(
            "TemplatesPanel",
            "renders",
            [
                {"template_name": "t1.html", "engine": "jinja2", "render_time": 0.1, "context_keys": None},
                {"template_name": "t2.html", "engine": "mako", "render_time": 0.2, "context_keys": None},
                {"template_name": "t3.html", "engine": "jinja2", "render_time": 0.15, "context_keys": None},
            ],
        )
        context.store_panel_data("TemplatesPanel", "engines_used", ["jinja2", "mako"])

        timings = templates_panel.generate_server_timing(context)

        assert "templates" in timings
        assert timings["templates"] == 0.45
        assert "templates-jinja2" in timings
        assert timings["templates-jinja2"] == 0.25
        assert "templates-mako" in timings
        assert timings["templates-mako"] == 0.2

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, templates_panel: TemplatesPanel, context: RequestContext) -> None:
        """Test full panel lifecycle: request -> render -> response -> stats."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        await templates_panel.process_request(context)

        template = Template("Hello {{ name }}!")
        result = template.render(name="World")
        assert result == "Hello World!"

        stats = await templates_panel.generate_stats(context)

        await templates_panel.process_response(context)

        assert stats["total_renders"] == 1
        assert stats["total_time"] > 0
        assert "jinja2" in stats["engines_used"]
        assert len(stats["renders"]) == 1
        assert stats["renders"][0]["engine"] == "jinja2"

    @pytest.mark.asyncio
    async def test_parallel_trackers_isolated(self, toolbar: DebugToolbar, context: RequestContext) -> None:
        """Test that parallel panel instances have isolated tracking."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        panel1 = TemplatesPanel(toolbar)
        panel2 = TemplatesPanel(toolbar)

        await panel1.process_request(context)

        template = Template("Hello {{ name }}!")
        template.render(name="Panel1")

        stats1 = await panel1.generate_stats(context)
        await panel1.process_response(context)

        await panel2.process_request(context)

        template.render(name="Panel2")

        stats2 = await panel2.generate_stats(context)
        await panel2.process_response(context)

        assert stats1["total_renders"] == 1
        assert stats2["total_renders"] == 1
