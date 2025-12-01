"""Tests for FastAPI dependency injection panel."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.fastapi.panels.dependencies import (
    DependencyInjectionPanel,
    _get_dependency_info,
    collect_dependency_metadata,
    record_dependency_resolution,
)


class TestDependencyInjectionPanel:
    """Tests for DependencyInjectionPanel class."""

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
        panel = DependencyInjectionPanel(mock_toolbar)
        assert panel.get_panel_id() == "DependencyInjectionPanel"
        assert panel.title == "Dependencies"
        assert panel.has_content is True
        assert panel.nav_title == "Dependencies"

    @pytest.mark.asyncio
    async def test_generate_stats_empty(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with no dependencies."""
        panel = DependencyInjectionPanel(mock_toolbar)
        context.metadata["dependencies"] = {
            "resolved": [],
            "tree": {},
            "cache_stats": {"hits": 0, "misses": 0, "total": 0},
        }

        stats = await panel.generate_stats(context)

        assert stats["total_count"] == 0
        assert stats["cached_count"] == 0
        assert stats["fresh_count"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["total_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_generate_stats_with_dependencies(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with dependencies."""
        panel = DependencyInjectionPanel(mock_toolbar)
        context.metadata["dependencies"] = {
            "resolved": [
                {"name": "get_db", "type": "function", "cached": False, "duration_ms": 2.0},
                {"name": "get_settings", "type": "function", "cached": True, "duration_ms": 0.1},
                {"name": "get_user", "type": "function", "cached": False, "duration_ms": 1.5},
            ],
            "tree": {},
            "cache_stats": {"hits": 1, "misses": 2, "total": 3},
        }

        stats = await panel.generate_stats(context)

        assert stats["total_count"] == 3
        assert stats["cached_count"] == 1
        assert stats["fresh_count"] == 2
        assert stats["cache_hit_rate"] == pytest.approx(33.33, rel=0.1)
        assert stats["total_time_ms"] == 3.6

    @pytest.mark.asyncio
    async def test_generate_stats_no_metadata(self, mock_toolbar: MagicMock, context: RequestContext) -> None:
        """Test generate_stats with missing metadata."""
        panel = DependencyInjectionPanel(mock_toolbar)

        stats = await panel.generate_stats(context)

        assert stats["total_count"] == 0
        assert stats["cache_hit_rate"] == 0

    def test_get_nav_subtitle(self, mock_toolbar: MagicMock) -> None:
        """Test get_nav_subtitle returns empty string."""
        panel = DependencyInjectionPanel(mock_toolbar)
        assert panel.get_nav_subtitle() == ""


class TestCollectDependencyMetadata:
    """Tests for collect_dependency_metadata helper."""

    def test_initializes_metadata(self) -> None:
        """Should initialize dependency metadata structure."""
        context = RequestContext()
        collect_dependency_metadata(context)

        assert "dependencies" in context.metadata
        assert context.metadata["dependencies"]["resolved"] == []
        assert context.metadata["dependencies"]["tree"] == {}
        assert context.metadata["dependencies"]["cache_stats"]["hits"] == 0


class TestRecordDependencyResolution:
    """Tests for record_dependency_resolution helper."""

    def test_records_dependency(self) -> None:
        """Should record dependency resolution."""
        context = RequestContext()
        record_dependency_resolution(
            context=context,
            dependency_name="get_db",
            dependency_type="generator",
            cached=False,
            duration_ms=2.5,
            module="myapp.deps",
        )

        deps = context.metadata["dependencies"]["resolved"]
        assert len(deps) == 1
        assert deps[0]["name"] == "get_db"
        assert deps[0]["type"] == "generator"
        assert deps[0]["cached"] is False
        assert deps[0]["duration_ms"] == 2.5
        assert deps[0]["module"] == "myapp.deps"

    def test_updates_cache_stats(self) -> None:
        """Should update cache statistics."""
        context = RequestContext()
        record_dependency_resolution(
            context=context,
            dependency_name="get_settings",
            dependency_type="function",
            cached=True,
            duration_ms=0.1,
        )

        stats = context.metadata["dependencies"]["cache_stats"]
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["total"] == 1

    def test_records_multiple(self) -> None:
        """Should record multiple dependencies."""
        context = RequestContext()

        record_dependency_resolution(
            context=context,
            dependency_name="dep1",
            dependency_type="function",
            cached=False,
            duration_ms=1.0,
        )
        record_dependency_resolution(
            context=context,
            dependency_name="dep2",
            dependency_type="class",
            cached=True,
            duration_ms=0.5,
        )

        deps = context.metadata["dependencies"]["resolved"]
        stats = context.metadata["dependencies"]["cache_stats"]

        assert len(deps) == 2
        assert stats["total"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestGetDependencyInfo:
    """Tests for _get_dependency_info helper."""

    def test_function_info(self) -> None:
        """Should extract function info."""

        def my_func():
            pass

        info = _get_dependency_info(my_func)
        assert info["name"] == "my_func"
        assert info["type"] == "function"
        assert "test_dependencies_panel" in info["module"]

    def test_class_info(self) -> None:
        """Should extract class info."""

        class MyClass:
            pass

        info = _get_dependency_info(MyClass)
        assert info["name"] == "MyClass"
        assert info["type"] == "class"

    def test_async_function_info(self) -> None:
        """Should detect async functions."""

        async def my_async_func():
            pass

        info = _get_dependency_info(my_async_func)
        assert info["name"] == "my_async_func"
        assert info["type"] == "async_function"

    def test_generator_info(self) -> None:
        """Should detect generators."""

        def my_generator():
            yield "value"

        info = _get_dependency_info(my_generator)
        assert info["name"] == "my_generator"
        assert info["type"] == "generator"

    def test_async_generator_info(self) -> None:
        """Should detect async generators."""

        async def my_async_gen():
            yield "value"

        info = _get_dependency_info(my_async_gen)
        assert info["name"] == "my_async_gen"
        assert info["type"] == "generator"
