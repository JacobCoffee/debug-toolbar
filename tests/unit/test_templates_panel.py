"""Tests for the templates panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from debug_toolbar.core.panels.templates import TemplateRenderTracker, TemplatesPanel

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

    def test_patch_jinja2(self, tracker: TemplateRenderTracker) -> None:
        """Test patching Jinja2 templates."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        original_render = Template.render
        tracker.patch_jinja2()

        assert "jinja2" in tracker._patched
        assert Template.render != original_render

        tracker.unpatch_jinja2()

        assert "jinja2" not in tracker._patched
        assert Template.render == original_render

    def test_patch_mako(self, tracker: TemplateRenderTracker) -> None:
        """Test patching Mako templates."""
        try:
            from mako.template import Template
        except ImportError:
            pytest.skip("Mako not installed")

        original_render = Template.render
        tracker.patch_mako()

        assert "mako" in tracker._patched
        assert Template.render != original_render

        tracker.unpatch_mako()

        assert "mako" not in tracker._patched
        assert Template.render == original_render

    def test_patch_jinja2_idempotent(self, tracker: TemplateRenderTracker) -> None:
        """Test that patching Jinja2 multiple times is safe."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        tracker.patch_jinja2()
        first_render = Template.render
        tracker.patch_jinja2()
        second_render = Template.render

        assert first_render == second_render
        tracker.unpatch_jinja2()

    def test_jinja2_template_render_tracking(self, tracker: TemplateRenderTracker) -> None:
        """Test that Jinja2 template renders are tracked."""
        try:
            from jinja2 import Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        tracker.patch_jinja2()

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
            tracker.unpatch_jinja2()

    def test_mako_template_render_tracking(self, tracker: TemplateRenderTracker) -> None:
        """Test that Mako template renders are tracked."""
        try:
            from mako.template import Template
        except ImportError:
            pytest.skip("Mako not installed")

        tracker.patch_mako()

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
            tracker.unpatch_mako()


class TestTemplatesPanel:
    """Tests for TemplatesPanel."""

    def test_panel_attributes(self, templates_panel: TemplatesPanel) -> None:
        """Test panel class attributes are set correctly."""
        assert templates_panel.panel_id == "templates"
        assert templates_panel.title == "Templates"
        assert templates_panel.nav_title == "Templates"
        assert templates_panel.has_content is True

    @pytest.mark.asyncio
    async def test_process_request_patches_engines(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that process_request patches template engines."""
        try:
            from jinja2 import Template as Jinja2Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        original_jinja2_render = Jinja2Template.render

        try:
            await templates_panel.process_request(context)
            assert "jinja2" in templates_panel._tracker._patched
            assert Jinja2Template.render != original_jinja2_render
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

        await templates_panel.process_request(context)
        assert len(templates_panel._tracker.renders) == 0

    @pytest.mark.asyncio
    async def test_process_response_unpatches_engines(
        self,
        templates_panel: TemplatesPanel,
        context: RequestContext,
    ) -> None:
        """Test that process_response unpatches template engines."""
        try:
            from jinja2 import Template as Jinja2Template
        except ImportError:
            pytest.skip("Jinja2 not installed")

        original_render = Jinja2Template.render
        await templates_panel.process_request(context)
        await templates_panel.process_response(context)

        assert "jinja2" not in templates_panel._tracker._patched
        assert Jinja2Template.render == original_render

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
        context.store_panel_data("templates", "total_time", 0.45)
        context.store_panel_data("templates", "total_renders", 3)
        context.store_panel_data(
            "templates",
            "renders",
            [
                {"template_name": "t1.html", "engine": "jinja2", "render_time": 0.1, "context_keys": None},
                {"template_name": "t2.html", "engine": "mako", "render_time": 0.2, "context_keys": None},
                {"template_name": "t3.html", "engine": "jinja2", "render_time": 0.15, "context_keys": None},
            ],
        )
        context.store_panel_data("templates", "engines_used", ["jinja2", "mako"])

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

        await templates_panel.process_response(context)

        stats = await templates_panel.generate_stats(context)

        assert stats["total_renders"] == 1
        assert stats["total_time"] > 0
        assert "jinja2" in stats["engines_used"]
        assert len(stats["renders"]) == 1
        assert stats["renders"][0]["engine"] == "jinja2"
