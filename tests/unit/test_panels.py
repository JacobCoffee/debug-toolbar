"""Tests for built-in panels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class ConcretePanel(Panel):
    """Concrete panel implementation for testing."""

    panel_id: ClassVar[str] = "TestPanel"
    title: ClassVar[str] = "Test Panel"
    template: ClassVar[str] = "test.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Test"
    nav_subtitle: ClassVar[str] = "Subtitle"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        return {"test_key": "test_value"}


class MinimalPanel(Panel):
    """Panel with minimal class attributes."""

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        return {}


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


class TestPanel:
    """Tests for Panel base class."""

    def test_get_panel_id_with_class_var(self, mock_toolbar: MagicMock) -> None:
        """Test get_panel_id returns panel_id class var."""
        panel = ConcretePanel(mock_toolbar)
        assert panel.get_panel_id() == "TestPanel"

    def test_get_panel_id_fallback_to_classname(self, mock_toolbar: MagicMock) -> None:
        """Test get_panel_id falls back to class name."""
        panel = MinimalPanel(mock_toolbar)
        assert panel.get_panel_id() == "MinimalPanel"

    def test_enabled_default(self, mock_toolbar: MagicMock) -> None:
        """Test panel is enabled by default."""
        panel = ConcretePanel(mock_toolbar)
        assert panel.enabled is True

    def test_enabled_setter(self, mock_toolbar: MagicMock) -> None:
        """Test enabled setter."""
        panel = ConcretePanel(mock_toolbar)
        panel.enabled = False
        assert panel.enabled is False

    def test_get_nav_title_with_class_var(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_title returns nav_title class var."""
        panel = ConcretePanel(mock_toolbar)
        assert panel.get_nav_title() == "Test"

    def test_get_nav_title_fallback_to_title(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_title falls back to title."""
        panel = MinimalPanel(mock_toolbar)
        assert panel.get_nav_title() == ""  # MinimalPanel has no title

    def test_get_nav_subtitle(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_subtitle."""
        panel = ConcretePanel(mock_toolbar)
        assert panel.get_nav_subtitle() == "Subtitle"

    def test_get_nav_subtitle_empty(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_subtitle with no subtitle."""
        panel = MinimalPanel(mock_toolbar)
        assert panel.get_nav_subtitle() == ""

    def test_generate_server_timing_default(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test generate_server_timing returns empty dict by default."""
        panel = ConcretePanel(mock_toolbar)
        result = panel.generate_server_timing(request_context)
        assert result == {}

    @pytest.mark.asyncio
    async def test_process_request_default(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test process_request default implementation."""
        panel = ConcretePanel(mock_toolbar)
        # Should not raise
        await panel.process_request(request_context)

    @pytest.mark.asyncio
    async def test_process_response_default(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test process_response default implementation."""
        panel = ConcretePanel(mock_toolbar)
        # Should not raise
        await panel.process_response(request_context)

    def test_get_stats(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test get_stats retrieves from context."""
        panel = ConcretePanel(mock_toolbar)
        request_context.store_panel_data("TestPanel", "key", "value")
        stats = panel.get_stats(request_context)
        assert stats == {"key": "value"}

    def test_record_stats(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test record_stats stores to context."""
        panel = ConcretePanel(mock_toolbar)
        panel.record_stats(request_context, {"a": 1, "b": 2})
        assert request_context.get_panel_data("TestPanel") == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_generate_stats(self, mock_toolbar: MagicMock, request_context: RequestContext) -> None:
        """Test generate_stats implementation."""
        panel = ConcretePanel(mock_toolbar)
        stats = await panel.generate_stats(request_context)
        assert stats == {"test_key": "test_value"}
