"""Tests for Starlette routes panel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.starlette.panels.routes import RoutesPanel


class TestRoutesPanel:
    """Tests for RoutesPanel class."""

    @pytest.fixture
    def mock_toolbar(self) -> MagicMock:
        """Create a mock toolbar."""
        return MagicMock(spec=["config"])

    @pytest.fixture
    def context(self) -> RequestContext:
        """Create a request context."""
        return RequestContext()

    def test_panel_class_attributes(self, mock_toolbar: MagicMock) -> None:
        """Test panel class attributes are set correctly."""
        panel = RoutesPanel(mock_toolbar)
        assert panel.get_panel_id() == "StarletteRoutesPanel"
        assert panel.title == "Routes"
        assert panel.has_content is True
        assert panel.nav_title == "Routes"

    @pytest.mark.asyncio
    async def test_generate_stats_empty(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with no routes."""
        panel = RoutesPanel(mock_toolbar)
        context.metadata["routes"] = []
        context.metadata["matched_route"] = ""

        stats = await panel.generate_stats(context)

        assert stats["routes"] == []
        assert stats["route_count"] == 0
        assert stats["current_route"] == ""

    @pytest.mark.asyncio
    async def test_generate_stats_with_routes(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with routes."""
        panel = RoutesPanel(mock_toolbar)
        context.metadata["routes"] = [
            {"path": "/", "methods": ["GET"], "name": "home", "handler": "homepage"},
            {"path": "/users", "methods": ["GET", "POST"], "name": "users", "handler": "users"},
        ]
        context.metadata["matched_route"] = "/"

        stats = await panel.generate_stats(context)

        assert len(stats["routes"]) == 2
        assert stats["route_count"] == 2
        assert stats["current_route"] == "/"

    @pytest.mark.asyncio
    async def test_generate_stats_no_metadata(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with missing metadata."""
        panel = RoutesPanel(mock_toolbar)

        stats = await panel.generate_stats(context)

        assert stats["routes"] == []
        assert stats["route_count"] == 0
        assert stats["current_route"] == ""

    def test_get_nav_subtitle(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_subtitle returns empty string."""
        panel = RoutesPanel(mock_toolbar)
        assert panel.get_nav_subtitle() == ""
