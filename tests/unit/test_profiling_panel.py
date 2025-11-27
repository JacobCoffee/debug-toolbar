"""Tests for ProfilingPanel."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.core.panels.profiling import ProfilingPanel


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar with config."""
    toolbar = MagicMock()
    toolbar.config = MagicMock()
    toolbar.config.profiler_backend = "cprofile"
    toolbar.config.profiler_top_functions = 50
    toolbar.config.profiler_sort_by = "cumulative"
    return toolbar


@pytest.fixture
def profiling_panel(mock_toolbar: MagicMock) -> ProfilingPanel:
    """Create a ProfilingPanel instance."""
    panel = ProfilingPanel(mock_toolbar)
    yield panel
    if panel._profiler is not None and hasattr(panel._profiler, "disable"):
        try:
            panel._profiler.disable()
        except Exception:
            # Ignore exceptions during profiler cleanup to avoid interfering with test teardown
            pass


class TestProfilingPanelInit:
    """Tests for ProfilingPanel initialization."""

    def test_panel_id(self) -> None:
        """Test panel_id class variable."""
        assert ProfilingPanel.panel_id == "ProfilingPanel"

    def test_title(self) -> None:
        """Test title class variable."""
        assert ProfilingPanel.title == "Profiling"

    def test_nav_title(self) -> None:
        """Test nav_title class variable."""
        assert ProfilingPanel.nav_title == "Profile"

    def test_has_content(self) -> None:
        """Test has_content class variable."""
        assert ProfilingPanel.has_content is True

    def test_initialization_defaults(self, mock_toolbar: MagicMock) -> None:
        """Test initialization with default config."""
        panel = ProfilingPanel(mock_toolbar)
        assert panel._backend == "cprofile"
        assert panel._top_functions == 50
        assert panel._sort_by == "cumulative"
        assert panel._profiler is None
        assert panel._profiling_overhead == 0.0


class TestProfilingPanelBackendSelection:
    """Tests for backend selection logic."""

    def test_backend_defaults_to_cprofile(self, mock_toolbar: MagicMock) -> None:
        """Test backend defaults to cprofile."""
        mock_toolbar.config.profiler_backend = "cprofile"
        panel = ProfilingPanel(mock_toolbar)
        assert panel._backend == "cprofile"

    def test_backend_cprofile_when_pyinstrument_unavailable(self, mock_toolbar: MagicMock) -> None:
        """Test fallback to cprofile when pyinstrument not available."""
        mock_toolbar.config.profiler_backend = "pyinstrument"
        with patch.dict("sys.modules", {"pyinstrument": None}):
            panel = ProfilingPanel(mock_toolbar)
            assert panel._backend == "cprofile"

    @pytest.mark.skipif(True, reason="pyinstrument may not be installed in CI")
    def test_backend_pyinstrument_when_available(self, mock_toolbar: MagicMock) -> None:
        """Test pyinstrument backend when available."""
        mock_toolbar.config.profiler_backend = "pyinstrument"
        try:
            import pyinstrument  # noqa: F401

            panel = ProfilingPanel(mock_toolbar)
            assert panel._backend == "pyinstrument"
        except ImportError:
            pytest.skip("pyinstrument not installed")

    def test_get_config_with_missing_config(self) -> None:
        """Test _get_config when toolbar has no config."""
        toolbar = MagicMock()
        del toolbar.config
        panel = ProfilingPanel(toolbar)
        assert panel._backend == "cprofile"


class TestProfilingPanelCProfileProcessing:
    """Tests for cProfile profiling workflow."""

    @pytest.mark.asyncio
    async def test_process_request_starts_cprofile(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test process_request starts cProfile profiler."""
        assert profiling_panel._profiler is None
        await profiling_panel.process_request(request_context)
        assert profiling_panel._profiler is not None
        assert profiling_panel._profiling_overhead > 0.0

    @pytest.mark.asyncio
    async def test_process_response_stops_cprofile(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test process_response stops cProfile profiler."""
        await profiling_panel.process_request(request_context)
        initial_overhead = profiling_panel._profiling_overhead

        def dummy_function() -> int:
            total = 0
            for i in range(1000):
                total += i
            return total

        dummy_function()

        await profiling_panel.process_response(request_context)
        assert profiling_panel._profiling_overhead >= initial_overhead

    @pytest.mark.asyncio
    async def test_generate_stats_returns_cprofile_data(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats returns proper cProfile statistics."""
        await profiling_panel.process_request(request_context)

        def test_function(n: int) -> int:
            result = 0
            for i in range(n):
                result += i * i
            return result

        test_function(1000)

        await profiling_panel.process_response(request_context)
        stats = await profiling_panel.generate_stats(request_context)

        assert stats["backend"] == "cprofile"
        assert isinstance(stats["total_time"], float)
        assert isinstance(stats["function_calls"], int)
        assert isinstance(stats["primitive_calls"], int)
        assert isinstance(stats["top_functions"], list)
        assert isinstance(stats["call_tree"], str)
        assert stats["function_calls"] > 0
        assert stats["profiling_overhead"] > 0.0

    @pytest.mark.asyncio
    async def test_top_functions_structure(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test top_functions list has correct structure."""
        await profiling_panel.process_request(request_context)

        def profiled_function() -> None:
            sum(range(100))

        profiled_function()

        await profiling_panel.process_response(request_context)
        stats = await profiling_panel.generate_stats(request_context)

        if stats["top_functions"]:
            func = stats["top_functions"][0]
            assert "function" in func
            assert "filename" in func
            assert "lineno" in func
            assert "calls" in func
            assert "primitive_calls" in func
            assert "total_time" in func
            assert "cumulative_time" in func
            assert "per_call" in func
            assert isinstance(func["function"], str)
            assert isinstance(func["filename"], str)
            assert isinstance(func["lineno"], int)


class TestProfilingPanelEmptyStats:
    """Tests for empty stats handling."""

    @pytest.mark.asyncio
    async def test_generate_stats_without_profiler(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats returns empty stats when no profiler active."""
        stats = await profiling_panel.generate_stats(request_context)

        assert stats["backend"] == "cprofile"
        assert stats["total_time"] == 0.0
        assert stats["function_calls"] == 0
        assert stats["primitive_calls"] == 0
        assert stats["top_functions"] == []
        assert stats["call_tree"] is None
        assert stats["profiling_overhead"] == 0.0

    @pytest.mark.asyncio
    async def test_process_response_with_no_profiler(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test process_response handles missing profiler gracefully."""
        await profiling_panel.process_response(request_context)


class TestProfilingPanelServerTiming:
    """Tests for Server-Timing header generation."""

    @pytest.mark.asyncio
    async def test_generate_server_timing(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing returns profiling metrics."""
        await profiling_panel.process_request(request_context)
        sum(range(100))
        await profiling_panel.process_response(request_context)

        stats = await profiling_panel.generate_stats(request_context)
        request_context.store_panel_data("ProfilingPanel", "profiling_overhead", stats["profiling_overhead"])
        request_context.store_panel_data("ProfilingPanel", "total_time", stats["total_time"])

        timing = profiling_panel.generate_server_timing(request_context)

        assert "profiling" in timing
        assert "profiled_time" in timing
        assert isinstance(timing["profiling"], float)
        assert isinstance(timing["profiled_time"], float)

    def test_generate_server_timing_no_stats(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing with no stats returns empty dict."""
        timing = profiling_panel.generate_server_timing(request_context)
        assert timing == {}


class TestProfilingPanelNavSubtitle:
    """Tests for navigation subtitle."""

    def test_get_nav_subtitle(self, profiling_panel: ProfilingPanel) -> None:
        """Test get_nav_subtitle returns backend name."""
        subtitle = profiling_panel.get_nav_subtitle()
        assert subtitle == "cprofile"


class TestProfilingPanelConfigOptions:
    """Tests for configuration options."""

    def test_custom_top_functions_limit(self, mock_toolbar: MagicMock) -> None:
        """Test custom top_functions limit from config."""
        mock_toolbar.config.profiler_top_functions = 25
        panel = ProfilingPanel(mock_toolbar)
        assert panel._top_functions == 25

    def test_custom_sort_by(self, mock_toolbar: MagicMock) -> None:
        """Test custom sort_by from config."""
        mock_toolbar.config.profiler_sort_by = "time"
        panel = ProfilingPanel(mock_toolbar)
        assert panel._sort_by == "time"


class TestProfilingPanelCProfileTree:
    """Tests for cProfile call tree generation."""

    @pytest.mark.asyncio
    async def test_call_tree_generation(self, profiling_panel: ProfilingPanel, request_context: RequestContext) -> None:
        """Test call tree is generated as string."""
        await profiling_panel.process_request(request_context)

        def nested_call() -> int:
            return sum(range(50))

        def outer_call() -> int:
            return nested_call() + nested_call()

        outer_call()

        await profiling_panel.process_response(request_context)
        stats = await profiling_panel.generate_stats(request_context)

        assert isinstance(stats["call_tree"], str)
        assert len(stats["call_tree"]) > 0


class TestProfilingPanelPyinstrument:
    """Tests for pyinstrument backend (when available)."""

    @pytest.mark.asyncio
    async def test_pyinstrument_backend_with_mock(
        self, mock_toolbar: MagicMock, request_context: RequestContext
    ) -> None:
        """Test pyinstrument backend using mocks."""
        mock_toolbar.config.profiler_backend = "pyinstrument"

        mock_profiler = Mock()
        mock_session = Mock()
        mock_frame = Mock()
        mock_frame.time.return_value = 0.123
        mock_frame.function = "test_function"
        mock_frame.file_path_short = "test.py"
        mock_frame.line_no = 42
        mock_frame.children = []
        mock_session.root_frame.return_value = mock_frame
        mock_profiler.last_session = mock_session
        mock_profiler.output_text.return_value = "Mock call tree"

        with patch.dict("sys.modules", {"pyinstrument": Mock()}):
            panel = ProfilingPanel(mock_toolbar)
            if panel._backend == "pyinstrument":
                panel._profiler = mock_profiler
                stats = await panel.generate_stats(request_context)

                assert stats["backend"] == "pyinstrument"
                assert stats["total_time"] == 0.123
                assert stats["call_tree"] == "Mock call tree"

    @pytest.mark.asyncio
    async def test_pyinstrument_count_calls_recursive(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test _count_pyinstrument_calls recursive counting."""
        mock_frame = Mock()
        mock_child1 = Mock()
        mock_child2 = Mock()
        mock_child1.children = []
        mock_child2.children = []
        mock_frame.children = [mock_child1, mock_child2]

        count = profiling_panel._count_pyinstrument_calls(mock_frame)
        assert count == 3

    def test_empty_stats_structure(self, profiling_panel: ProfilingPanel) -> None:
        """Test _empty_stats returns correct structure."""
        stats = profiling_panel._empty_stats()
        assert stats["backend"] == "cprofile"
        assert stats["total_time"] == 0.0
        assert stats["function_calls"] == 0
        assert stats["primitive_calls"] == 0
        assert stats["top_functions"] == []
        assert stats["call_tree"] is None
        assert "profiling_overhead" in stats


class TestProfilingPanelEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_generate_stats_called_twice(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats can be called multiple times."""
        await profiling_panel.process_request(request_context)
        sum(range(100))
        await profiling_panel.process_response(request_context)

        stats1 = await profiling_panel.generate_stats(request_context)
        stats2 = await profiling_panel.generate_stats(request_context)

        assert stats1["backend"] == stats2["backend"]

    def test_profiler_disabled_state(self, profiling_panel: ProfilingPanel) -> None:
        """Test panel can be disabled."""
        profiling_panel.enabled = False
        assert profiling_panel.enabled is False

    @pytest.mark.asyncio
    async def test_zero_division_protection_in_per_call(
        self, profiling_panel: ProfilingPanel, request_context: RequestContext
    ) -> None:
        """Test per_call calculation handles zero calls."""
        await profiling_panel.process_request(request_context)
        await profiling_panel.process_response(request_context)
        stats = await profiling_panel.generate_stats(request_context)

        for func in stats["top_functions"]:
            if func["calls"] == 0:
                assert func["per_call"] == 0.0
