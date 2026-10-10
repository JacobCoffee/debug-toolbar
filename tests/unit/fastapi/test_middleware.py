"""Tests for FastAPI debug toolbar middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from debug_toolbar.core import DebugToolbar
from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig
from debug_toolbar.fastapi.middleware import (
    DebugToolbarMiddleware,
    get_dependency_cache_stats,
    get_dependency_tracking,
    record_dependency_resolution,
    track_dependency,
)


class TestDependencyTracking:
    """Tests for dependency tracking functions."""

    def test_get_dependency_tracking_default(self) -> None:
        """Should return empty list by default."""
        tracking = get_dependency_tracking()
        assert isinstance(tracking, list)

    def test_get_dependency_cache_stats_default(self) -> None:
        """Should return zeroed stats by default."""
        stats = get_dependency_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0

    def test_record_dependency_resolution(self) -> None:
        """Should record dependency resolution."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([])
        _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        record_dependency_resolution(
            name="get_db",
            dependency_type="function",
            cached=False,
            duration_ms=1.5,
            module="myapp.deps",
        )

        tracking = get_dependency_tracking()
        stats = get_dependency_cache_stats()

        assert len(tracking) == 1
        assert tracking[0]["name"] == "get_db"
        assert tracking[0]["type"] == "function"
        assert tracking[0]["cached"] is False
        assert tracking[0]["duration_ms"] == 1.5
        assert tracking[0]["module"] == "myapp.deps"
        assert stats["total"] == 1
        assert stats["misses"] == 1

    def test_record_cached_dependency(self) -> None:
        """Should track cache hits."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([])
        _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        record_dependency_resolution(
            name="get_settings",
            dependency_type="function",
            cached=True,
            duration_ms=0.1,
        )

        stats = get_dependency_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["total"] == 1

    def test_track_dependency_function(self) -> None:
        """Should detect function dependencies."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([])
        _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        def my_dependency():
            return "value"

        track_dependency(my_dependency, cached=False, duration_ms=1.0)

        tracking = get_dependency_tracking()
        assert len(tracking) == 1
        assert tracking[0]["name"] == "my_dependency"
        assert tracking[0]["type"] == "function"

    def test_track_dependency_class(self) -> None:
        """Should detect class-based dependencies."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([])
        _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        class MyDependency:
            pass

        track_dependency(MyDependency, cached=False, duration_ms=1.0)

        tracking = get_dependency_tracking()
        assert len(tracking) == 1
        assert tracking[0]["name"] == "MyDependency"
        assert tracking[0]["type"] == "class"

    def test_track_dependency_generator(self) -> None:
        """Should detect generator dependencies."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([])
        _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        def get_db():
            yield "db"

        track_dependency(get_db, cached=False, duration_ms=1.0)

        tracking = get_dependency_tracking()
        assert len(tracking) == 1
        assert tracking[0]["type"] == "generator"


class TestDebugToolbarMiddleware:
    """Tests for FastAPI DebugToolbarMiddleware class."""

    def test_init_with_defaults(self) -> None:
        """Should initialize with default config."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)
        assert middleware.app is app
        assert isinstance(middleware.fastapi_config, FastAPIDebugToolbarConfig)
        assert middleware.fastapi_config.track_dependency_injection is True

    def test_init_with_custom_config(self) -> None:
        """Should accept custom config."""
        app = AsyncMock()
        config = FastAPIDebugToolbarConfig(track_dependency_injection=False)
        middleware = DebugToolbarMiddleware(app, config=config)
        assert middleware.fastapi_config.track_dependency_injection is False

    def test_init_with_shared_toolbar(self) -> None:
        """Should accept shared toolbar instance."""
        app = AsyncMock()
        config = FastAPIDebugToolbarConfig()
        toolbar = DebugToolbar(config)
        middleware = DebugToolbarMiddleware(app, config=config, toolbar=toolbar)
        assert middleware.toolbar is toolbar

    @pytest.mark.asyncio
    async def test_call_non_http(self) -> None:
        """Should pass through non-HTTP requests."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)
        scope = {"type": "websocket", "path": "/ws"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

    def test_populate_dependency_metadata(self) -> None:
        """Should populate dependency metadata into context."""
        from debug_toolbar.fastapi.middleware import _dependency_cache_stats, _dependency_tracking

        _dependency_tracking.set([{"name": "get_db", "type": "function", "cached": False, "duration_ms": 1.0}])
        _dependency_cache_stats.set({"hits": 0, "misses": 1, "total": 1})

        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)

        context = MagicMock()
        context.metadata = {}

        middleware._populate_dependency_metadata(context)

        assert "dependencies" in context.metadata
        assert len(context.metadata["dependencies"]["resolved"]) == 1
        assert context.metadata["dependencies"]["cache_stats"]["total"] == 1
