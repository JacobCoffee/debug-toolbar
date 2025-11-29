"""Tests for MemoryPanel."""

from __future__ import annotations

import platform
from unittest.mock import MagicMock, patch

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.core.panels.memory import MemoryPanel
from debug_toolbar.core.panels.memory.base import MemoryBackend
from debug_toolbar.core.panels.memory.memray import MemrayBackend
from debug_toolbar.core.panels.memory.tracemalloc import TraceMallocBackend


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar with config."""
    toolbar = MagicMock()
    toolbar.config = MagicMock()
    toolbar.config.memory_backend = "auto"
    return toolbar


@pytest.fixture
def memory_panel(mock_toolbar: MagicMock) -> MemoryPanel:
    """Create a MemoryPanel instance."""
    return MemoryPanel(mock_toolbar)


class TestMemoryPanelInit:
    """Tests for MemoryPanel initialization."""

    def test_panel_id(self) -> None:
        """Test panel_id class variable."""
        assert MemoryPanel.panel_id == "MemoryPanel"

    def test_title(self) -> None:
        """Test title class variable."""
        assert MemoryPanel.title == "Memory"

    def test_nav_title(self) -> None:
        """Test nav_title class variable."""
        assert MemoryPanel.nav_title == "Memory"

    def test_has_content(self) -> None:
        """Test has_content class variable."""
        assert MemoryPanel.has_content is True

    def test_initialization_defaults(self, mock_toolbar: MagicMock) -> None:
        """Test initialization with default config."""
        panel = MemoryPanel(mock_toolbar)
        assert panel._backend is not None
        assert panel._backend_name in ("tracemalloc", "memray")
        assert panel._memory_delta == 0


class TestMemoryBackendSelection:
    """Tests for backend selection logic."""

    def test_backend_defaults_to_tracemalloc(self, mock_toolbar: MagicMock) -> None:
        """Test backend defaults to tracemalloc when memray unavailable."""
        mock_toolbar.config.memory_backend = "tracemalloc"
        panel = MemoryPanel(mock_toolbar)
        assert panel._backend_name == "tracemalloc"
        assert isinstance(panel._backend, TraceMallocBackend)

    def test_backend_auto_selects_best_available(self, mock_toolbar: MagicMock) -> None:
        """Test auto backend selection picks best available."""
        mock_toolbar.config.memory_backend = "auto"
        panel = MemoryPanel(mock_toolbar)
        if MemrayBackend.is_available():
            assert panel._backend_name == "memray"
        else:
            assert panel._backend_name == "tracemalloc"

    def test_backend_memray_when_requested_and_available(self, mock_toolbar: MagicMock) -> None:
        """Test memray backend when explicitly requested and available."""
        mock_toolbar.config.memory_backend = "memray"
        panel = MemoryPanel(mock_toolbar)
        if MemrayBackend.is_available():
            assert panel._backend_name == "memray"
            assert isinstance(panel._backend, MemrayBackend)
        else:
            assert panel._backend_name == "tracemalloc"

    def test_backend_fallback_when_memray_unavailable(self, mock_toolbar: MagicMock) -> None:
        """Test fallback to tracemalloc when memray requested but unavailable."""
        mock_toolbar.config.memory_backend = "memray"
        with patch.object(MemrayBackend, "is_available", return_value=False):
            panel = MemoryPanel(mock_toolbar)
            assert panel._backend_name == "tracemalloc"

    def test_get_config_with_missing_config(self) -> None:
        """Test _get_config when toolbar has no config."""
        toolbar = MagicMock()
        del toolbar.config
        panel = MemoryPanel(toolbar)
        assert panel._backend_name == "tracemalloc"


class TestTraceMallocBackend:
    """Tests for TraceMallocBackend."""

    def test_is_available(self) -> None:
        """Test TraceMallocBackend is always available."""
        assert TraceMallocBackend.is_available() is True

    def test_start_and_stop(self) -> None:
        """Test starting and stopping tracemalloc backend."""
        backend = TraceMallocBackend()
        backend.start()
        assert backend._snapshot_before is not None
        backend.stop()
        assert backend._snapshot_after is not None

    def test_get_stats_structure(self) -> None:
        """Test get_stats returns correct structure."""
        backend = TraceMallocBackend()
        backend.start()

        data = [1] * 1000000
        del data

        backend.stop()
        stats = backend.get_stats()

        assert "memory_before" in stats
        assert "memory_after" in stats
        assert "memory_delta" in stats
        assert "peak_memory" in stats
        assert "top_allocations" in stats
        assert "backend" in stats
        assert "profiling_overhead" in stats
        assert stats["backend"] == "tracemalloc"
        assert isinstance(stats["profiling_overhead"], float)

    def test_get_stats_without_snapshots(self) -> None:
        """Test get_stats returns empty stats when not started."""
        backend = TraceMallocBackend()
        stats = backend.get_stats()

        assert stats["memory_before"] == 0
        assert stats["memory_after"] == 0
        assert stats["memory_delta"] == 0
        assert stats["peak_memory"] == 0
        assert stats["top_allocations"] == []
        assert stats["backend"] == "tracemalloc"

    def test_top_allocations_structure(self) -> None:
        """Test top_allocations list has correct structure."""
        backend = TraceMallocBackend()
        backend.start()

        test_data = list(range(10000))
        del test_data

        backend.stop()
        stats = backend.get_stats()

        if stats["top_allocations"]:
            allocation = stats["top_allocations"][0]
            assert "file" in allocation
            assert "line" in allocation
            assert "size" in allocation
            assert "count" in allocation
            assert isinstance(allocation["file"], str)
            assert isinstance(allocation["line"], int)
            assert isinstance(allocation["size"], int)
            assert isinstance(allocation["count"], int)


class TestMemrayBackend:
    """Tests for MemrayBackend."""

    def test_is_available_on_supported_platforms(self) -> None:
        """Test MemrayBackend availability check."""
        if platform.system() in ("Linux", "Darwin"):
            try:
                import memray  # noqa: F401

                assert MemrayBackend.is_available() is True
            except ImportError:
                assert MemrayBackend.is_available() is False
        else:
            assert MemrayBackend.is_available() is False

    @pytest.mark.skipif(not MemrayBackend.is_available(), reason="memray not available")
    def test_start_and_stop(self) -> None:
        """Test starting and stopping memray backend."""
        backend = MemrayBackend()
        backend.start()
        assert backend._tracker is not None
        backend.stop()

    @pytest.mark.skipif(not MemrayBackend.is_available(), reason="memray not available")
    def test_get_stats_structure(self) -> None:
        """Test get_stats returns correct structure."""
        backend = MemrayBackend()
        backend.start()

        data = [1] * 1000000
        del data

        backend.stop()
        stats = backend.get_stats()

        assert "memory_before" in stats
        assert "memory_after" in stats
        assert "memory_delta" in stats
        assert "peak_memory" in stats
        assert "top_allocations" in stats
        assert "backend" in stats
        assert "profiling_overhead" in stats
        assert stats["backend"] == "memray"

    def test_get_stats_without_tracker(self) -> None:
        """Test get_stats returns empty stats when not started."""
        backend = MemrayBackend()
        stats = backend.get_stats()

        assert stats["memory_before"] == 0
        assert stats["memory_after"] == 0
        assert stats["memory_delta"] == 0
        assert stats["peak_memory"] == 0
        assert stats["top_allocations"] == []
        assert stats["backend"] == "memray"


class TestMemoryPanelProcessing:
    """Tests for memory panel request/response processing."""

    @pytest.mark.asyncio
    async def test_process_request_starts_tracking(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test process_request starts memory tracking."""
        await memory_panel.process_request(request_context)

    @pytest.mark.asyncio
    async def test_process_response_stops_tracking(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test process_response stops memory tracking."""
        await memory_panel.process_request(request_context)
        await memory_panel.process_response(request_context)

    @pytest.mark.asyncio
    async def test_generate_stats_returns_memory_data(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats returns proper memory statistics."""
        await memory_panel.process_request(request_context)

        test_data = [i * 2 for i in range(100000)]
        del test_data

        await memory_panel.process_response(request_context)
        stats = await memory_panel.generate_stats(request_context)

        assert stats["backend"] in ("tracemalloc", "memray")
        assert isinstance(stats["memory_before"], int)
        assert isinstance(stats["memory_after"], int)
        assert isinstance(stats["memory_delta"], int)
        assert isinstance(stats["peak_memory"], int)
        assert isinstance(stats["top_allocations"], list)
        assert isinstance(stats["profiling_overhead"], float)

    @pytest.mark.asyncio
    async def test_memory_delta_tracking(self, memory_panel: MemoryPanel, request_context: RequestContext) -> None:
        """Test memory delta is tracked correctly."""
        await memory_panel.process_request(request_context)

        data = [1] * 500000
        del data

        await memory_panel.process_response(request_context)
        stats = await memory_panel.generate_stats(request_context)

        assert memory_panel._memory_delta == stats["memory_delta"]


class TestMemoryPanelServerTiming:
    """Tests for Server-Timing header generation."""

    @pytest.mark.asyncio
    async def test_generate_server_timing(self, memory_panel: MemoryPanel, request_context: RequestContext) -> None:
        """Test generate_server_timing returns profiling metrics."""
        await memory_panel.process_request(request_context)
        await memory_panel.process_response(request_context)

        stats = await memory_panel.generate_stats(request_context)
        request_context.store_panel_data("MemoryPanel", "profiling_overhead", stats["profiling_overhead"])

        timing = memory_panel.generate_server_timing(request_context)

        assert "memory_profiling" in timing
        assert isinstance(timing["memory_profiling"], float)

    def test_generate_server_timing_no_stats(self, memory_panel: MemoryPanel, request_context: RequestContext) -> None:
        """Test generate_server_timing with no stats returns empty dict."""
        timing = memory_panel.generate_server_timing(request_context)
        assert timing == {}


class TestMemoryPanelNavSubtitle:
    """Tests for navigation subtitle formatting."""

    def test_nav_subtitle_zero_bytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with zero delta."""
        memory_panel._memory_delta = 0
        assert memory_panel.get_nav_subtitle() == "0 B"

    def test_nav_subtitle_positive_bytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with positive byte delta."""
        memory_panel._memory_delta = 512
        assert memory_panel.get_nav_subtitle() == "+512 B"

    def test_nav_subtitle_negative_bytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with negative byte delta."""
        memory_panel._memory_delta = -256
        assert memory_panel.get_nav_subtitle() == "-256 B"

    def test_nav_subtitle_kilobytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with KB delta."""
        memory_panel._memory_delta = 5120
        subtitle = memory_panel.get_nav_subtitle()
        assert "KB" in subtitle
        assert subtitle.startswith("+")

    def test_nav_subtitle_megabytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with MB delta."""
        memory_panel._memory_delta = 2 * 1024 * 1024
        subtitle = memory_panel.get_nav_subtitle()
        assert "MB" in subtitle
        assert "2.00" in subtitle

    def test_nav_subtitle_gigabytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with GB delta."""
        memory_panel._memory_delta = 3 * 1024 * 1024 * 1024
        subtitle = memory_panel.get_nav_subtitle()
        assert "GB" in subtitle
        assert "3.00" in subtitle

    def test_nav_subtitle_negative_megabytes(self, memory_panel: MemoryPanel) -> None:
        """Test nav subtitle with negative MB delta."""
        memory_panel._memory_delta = -1024 * 1024
        subtitle = memory_panel.get_nav_subtitle()
        assert "MB" in subtitle
        assert subtitle.startswith("-")


class TestMemoryPanelConfigOptions:
    """Tests for configuration options."""

    def test_custom_backend_tracemalloc(self, mock_toolbar: MagicMock) -> None:
        """Test custom backend selection via config."""
        mock_toolbar.config.memory_backend = "tracemalloc"
        panel = MemoryPanel(mock_toolbar)
        assert panel._backend_name == "tracemalloc"

    @pytest.mark.skipif(not MemrayBackend.is_available(), reason="memray not available")
    def test_custom_backend_memray(self, mock_toolbar: MagicMock) -> None:
        """Test custom memray backend selection via config."""
        mock_toolbar.config.memory_backend = "memray"
        panel = MemoryPanel(mock_toolbar)
        assert panel._backend_name == "memray"


class TestMemoryPanelErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_process_request_handles_errors(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test process_request handles backend errors gracefully."""
        with patch.object(memory_panel._backend, "start", side_effect=Exception("Test error")):
            await memory_panel.process_request(request_context)

    @pytest.mark.asyncio
    async def test_process_response_handles_errors(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test process_response handles backend errors gracefully."""
        with patch.object(memory_panel._backend, "stop", side_effect=Exception("Test error")):
            await memory_panel.process_response(request_context)

    @pytest.mark.asyncio
    async def test_generate_stats_called_twice(
        self, memory_panel: MemoryPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats can be called multiple times."""
        await memory_panel.process_request(request_context)
        await memory_panel.process_response(request_context)

        stats1 = await memory_panel.generate_stats(request_context)
        stats2 = await memory_panel.generate_stats(request_context)

        assert stats1["backend"] == stats2["backend"]

    def test_panel_disabled_state(self, memory_panel: MemoryPanel) -> None:
        """Test panel can be disabled."""
        memory_panel.enabled = False
        assert memory_panel.enabled is False


class TestMemoryBackendABC:
    """Tests for MemoryBackend abstract base class."""

    def test_cannot_instantiate_abstract_backend(self) -> None:
        """Test MemoryBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MemoryBackend()  # type: ignore[abstract]

    def test_backend_interface_methods(self) -> None:
        """Test MemoryBackend defines required abstract methods."""
        assert hasattr(MemoryBackend, "start")
        assert hasattr(MemoryBackend, "stop")
        assert hasattr(MemoryBackend, "get_stats")
        assert hasattr(MemoryBackend, "is_available")
