"""Tests for the Static files panel."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from litestar.static_files import create_static_files_router

from debug_toolbar.core.context import RequestContext
from debug_toolbar.litestar.panels.static_files import (
    StaticFilesPanel,
    collect_static_files_metadata,
)
from litestar import Litestar, get


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


@get("/hello")
async def _hello_handler() -> str:
    return "hello"


class TestCollectStaticFilesMetadata:
    """Tests for collect_static_files_metadata function."""

    def test_no_static_mounts(self, tmp_path: Path) -> None:
        """An app with no static file routers reports no mounts."""
        app = Litestar(route_handlers=[_hello_handler])
        context = RequestContext()

        collect_static_files_metadata(app, context)

        assert context.metadata["static_files"] == []

    def test_single_static_mount(self, tmp_path: Path) -> None:
        """A single static file router is reported with its URL path and folder."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()

        router = create_static_files_router(path="/static", directories=[static_dir])
        app = Litestar(route_handlers=[router])
        context = RequestContext()

        collect_static_files_metadata(app, context)

        mounts = context.metadata["static_files"]
        assert len(mounts) == 1
        assert mounts[0]["url_path"] == "/static"
        assert mounts[0]["directories"] == [str(static_dir)]

    def test_multiple_static_mounts(self, tmp_path: Path) -> None:
        """Multiple static file routers are all reported, sorted by URL path."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        static_dir = tmp_path / "static"
        static_dir.mkdir()

        assets_router = create_static_files_router(path="/assets", directories=[assets_dir])
        static_router = create_static_files_router(path="/static", directories=[static_dir])
        app = Litestar(route_handlers=[assets_router, static_router])
        context = RequestContext()

        collect_static_files_metadata(app, context)

        mounts = context.metadata["static_files"]
        assert [mount["url_path"] for mount in mounts] == ["/assets", "/static"]
        assert mounts[0]["directories"] == [str(assets_dir)]
        assert mounts[1]["directories"] == [str(static_dir)]

    def test_multiple_directories_for_one_mount(self, tmp_path: Path) -> None:
        """A mount backed by multiple directories reports all of them."""
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        dir_b = tmp_path / "b"
        dir_b.mkdir()

        router = create_static_files_router(path="/static", directories=[dir_a, dir_b])
        app = Litestar(route_handlers=[router])
        context = RequestContext()

        collect_static_files_metadata(app, context)

        mounts = context.metadata["static_files"]
        assert len(mounts) == 1
        assert mounts[0]["directories"] == [str(dir_a), str(dir_b)]


class TestStaticFilesPanel:
    """Tests for StaticFilesPanel class."""

    @pytest.mark.asyncio
    async def test_generate_stats_with_mounts(self, mock_toolbar: MagicMock) -> None:
        """Panel reports configured mounts."""
        context = RequestContext()
        context.metadata["static_files"] = [{"url_path": "/static", "directories": ["/tmp/static"]}]
        panel = StaticFilesPanel(mock_toolbar)

        stats = await panel.generate_stats(context)

        assert stats["mount_count"] == 1
        assert stats["mounts"][0]["url_path"] == "/static"

    @pytest.mark.asyncio
    async def test_generate_stats_without_mounts(self, mock_toolbar: MagicMock) -> None:
        """Panel reports a clear empty message when there are no mounts."""
        context = RequestContext()
        context.metadata["static_files"] = []
        panel = StaticFilesPanel(mock_toolbar)

        stats = await panel.generate_stats(context)

        assert stats["mounts"] == []
        assert stats["message"] == "No static files configured"

    def test_panel_metadata(self, mock_toolbar: MagicMock) -> None:
        """Panel exposes plain, non-technical labels."""
        panel = StaticFilesPanel(mock_toolbar)

        assert panel.title == "Static files"
        assert panel.nav_title == "Static files"
        assert panel.get_nav_subtitle() == ""
