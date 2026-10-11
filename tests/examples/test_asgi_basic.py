"""Tests for the raw-ASGI ``examples/asgi_basic`` example.

This example hand-rolls its own debug-toolbar middleware directly against the
``DebugToolbar`` core API. It injects the toolbar markup into HTML responses,
serves ``/_debug_toolbar/static/*`` assets, and exposes JSON endpoints at
``/_debug_toolbar/api/requests`` and ``/_debug_toolbar/api/requests/<id>``.
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


async def test_home_page_injects_toolbar_markup(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "ASGI Debug Toolbar Example" in response.text
    assert 'id="debug-toolbar"' in response.text
    assert '<link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">' in response.text
    assert '<script src="/_debug_toolbar/static/toolbar.js"></script>' in response.text


async def test_about_page_injects_toolbar_markup(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/about")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "About" in response.text
    assert 'id="debug-toolbar"' in response.text


async def test_api_data_returns_json_without_toolbar_markup(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/api/data")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["message"] == "Hello from the API"
    assert 'id="debug-toolbar"' not in response.text


async def test_unknown_path_returns_404(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/no-such-page")

    assert response.status_code == 404


async def test_server_timing_header_present_after_request(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/")

    assert "server-timing" in response.headers


async def test_static_css_asset(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/_debug_toolbar/static/toolbar.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert response.text


async def test_static_js_asset(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get("/_debug_toolbar/static/toolbar.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text


async def test_debug_toolbar_api_requests_lists_recorded_request(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        await client.get("/")
        response = await client.get("/_debug_toolbar/api/requests")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    requests_list = response.json()
    assert len(requests_list) >= 1
    assert "request_id" in requests_list[0]
    assert requests_list[0]["path"] == "/"


async def test_debug_toolbar_api_request_detail_contains_panel_data(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        await client.get("/")
        requests_response = await client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = await client.get(f"/_debug_toolbar/api/requests/{request_id}")

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


async def test_debug_toolbar_api_request_detail_unknown_id_returns_404(asgi_basic: ModuleType) -> None:
    async with _client(asgi_basic) as client:
        response = await client.get(f"/_debug_toolbar/api/requests/{uuid4()}")

    assert response.status_code == 404
