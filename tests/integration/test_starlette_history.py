"""Integration tests for the Starlette request history pages."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from debug_toolbar.core.toolbar import DebugToolbar
from debug_toolbar.starlette import DebugToolbarMiddleware, StarletteDebugToolbarConfig, create_debug_toolbar_routes
from starlette.middleware import Middleware


async def echo(request):
    return JSONResponse({"ok": True})


def _client() -> tuple[TestClient, DebugToolbar]:
    config = StarletteDebugToolbarConfig(enabled=True, exclude_paths=["/_debug_toolbar"])
    toolbar = DebugToolbar(config)
    app = Starlette(
        routes=[*create_debug_toolbar_routes(toolbar.storage), Route("/{name:path}", endpoint=echo)],
        middleware=[Middleware(DebugToolbarMiddleware, config=config, toolbar=toolbar)],
    )
    return TestClient(app), toolbar


def test_detail_page_shows_panels_and_escapes_path() -> None:
    client, toolbar = _client()
    with client:
        client.get("/%3Cscript%3Ealert(1)%3C/script%3E")
        request_id, _ = toolbar.storage.get_all()[0]

        detail = client.get(f"/_debug_toolbar/{request_id}").text
        history = client.get("/_debug_toolbar/").text

    assert "<h3>RequestPanel</h3>" in detail
    assert "<script>alert(1)" not in detail
    assert "<script>alert(1)" not in history
    assert "&lt;script&gt;alert(1)" in detail
