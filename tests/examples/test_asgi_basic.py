"""Tests for the raw-ASGI ``examples/asgi_basic`` example.

This example hand-rolls its own debug-toolbar middleware directly against the
``DebugToolbar`` core API, predating the framework integrations' HTML
injection and static-asset routes. On this branch (ahead of PR #61) it does
not inject the toolbar markup into HTML responses and does not serve
``/_debug_toolbar/static/*`` assets at all -- only the two hand-rolled JSON
endpoints (``/_debug_toolbar/requests`` and ``/_debug_toolbar/request/<id>``)
exist. These tests assert the behavior that is actually present today.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


@pytest.fixture
def asgi_basic(import_example: Callable[[str], ModuleType]) -> ModuleType:
    return import_example("examples.asgi_basic.app")


def _client(asgi_basic: ModuleType) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=asgi_basic.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_home_page_returns_html(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "ASGI Debug Toolbar Example" in response.text


async def test_home_page_does_not_inject_toolbar_markup(asgi_basic: ModuleType) -> None:
    """The hand-rolled middleware never rewrites the response body (PR #61)."""
    async with _client(asgi_basic) as client:
        response = await client.get("/")

    assert 'id="debug-toolbar"' not in response.text


async def test_about_page_returns_html(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/about")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "About" in response.text


async def test_api_data_returns_json_without_toolbar_markup(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/api/data")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["items"] == [1, 2, 3]
    assert 'id="debug-toolbar"' not in response.text


async def test_unknown_path_returns_404(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/nope")

    assert response.status_code == 404


async def test_server_timing_header_present_after_request(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/")

    assert "server-timing" in response.headers


async def test_debug_toolbar_requests_lists_recorded_request(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        await client.get("/")
        response = await client.get("/_debug_toolbar/requests")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    requests_list = response.json()
    assert len(requests_list) == 1
    assert requests_list[0]["method"] == "GET"
    assert requests_list[0]["path"] == "/"


async def test_debug_toolbar_request_detail_contains_panel_data(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        await client.get("/")
        requests_response = await client.get("/_debug_toolbar/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = await client.get(f"/_debug_toolbar/request/{request_id}")

    assert detail_response.status_code == 200
    assert detail_response.headers["content-type"].startswith("application/json")
    detail = detail_response.json()

    assert detail["request_id"] == request_id
    panel_data = detail["panel_data"]
    assert set(panel_data) >= {"TimerPanel", "RequestPanel", "ResponsePanel", "LoggingPanel", "VersionsPanel"}

    timer_stats = panel_data["TimerPanel"]
    assert timer_stats["total_time_ms"] >= 0

    request_stats = panel_data["RequestPanel"]
    assert request_stats["method"] == "GET"
    assert request_stats["path"] == "/"


async def test_debug_toolbar_request_detail_unknown_id_returns_404(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get(f"/_debug_toolbar/request/{uuid4()}")

    assert response.status_code == 404


async def test_static_assets_are_not_served_yet(asgi_basic: ModuleType) -> None:
    """No ``/_debug_toolbar/static/*`` route exists in this example (PR #61)."""
    async with _client(asgi_basic) as client:
        css_response = await client.get("/_debug_toolbar/static/toolbar.css")
        js_response = await client.get("/_debug_toolbar/static/toolbar.js")

    assert css_response.status_code == 404
    assert js_response.status_code == 404
