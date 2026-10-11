"""Tests for the ``examples/litestar_basic`` example."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from litestar.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

HTML_ROUTES = ["/", "/about", "/users", "/alerts-demo"]


@pytest.fixture
def litestar_basic(import_example: Callable[[str], ModuleType]) -> ModuleType:
    return import_example("examples.litestar_basic.app")


@pytest.mark.parametrize("path", HTML_ROUTES)
def test_html_route_returns_toolbar_injected_page(litestar_basic: ModuleType, path: str) -> None:
    with TestClient(litestar_basic.app) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="debug-toolbar"' in response.text
    assert "/_debug_toolbar/static/toolbar.css" in response.text
    assert "/_debug_toolbar/static/toolbar.js" in response.text


def test_api_status_returns_json_without_toolbar_markup(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        response = client.get("/api/status")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "ok"
    assert 'id="debug-toolbar"' not in response.text


def test_static_css_asset(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        response = client.get("/_debug_toolbar/static/toolbar.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert response.text


def test_static_js_asset(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        response = client.get("/_debug_toolbar/static/toolbar.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert response.text


def test_history_api_lists_requests_after_html_requests(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        client.get("/")
        client.get("/about")
        response = client.get("/_debug_toolbar/api/requests")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_request_detail_unknown_id_returns_404(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        response = client.get(f"/_debug_toolbar/api/requests/{uuid4()}")

    assert response.status_code == 404


def test_request_detail_contains_multiple_panels(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        client.get("/")
        requests_response = client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = client.get(f"/_debug_toolbar/api/requests/{request_id}")

    assert detail_response.status_code == 200
    assert detail_response.headers["content-type"].startswith("application/json")
    detail = detail_response.json()

    panel_data = detail["panel_data"]
    expected_panels = {
        "TimerPanel",
        "RequestPanel",
        "ResponsePanel",
        "LoggingPanel",
        "VersionsPanel",
        "HeadersPanel",
        "SettingsPanel",
        "TemplatesPanel",
        "AlertsPanel",
        "MemoryPanel",
        "AsyncProfilerPanel",
    }
    assert expected_panels <= set(panel_data)


def test_templates_panel_records_jinja2_render_on_index_page(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        client.get("/")
        requests_response = client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = client.get(f"/_debug_toolbar/api/requests/{request_id}")

    templates_stats = detail_response.json()["panel_data"]["TemplatesPanel"]
    assert templates_stats["total_renders"] >= 1
    assert "jinja2" in templates_stats["engines_used"]


def test_headers_panel_records_request_headers(litestar_basic: ModuleType) -> None:
    with TestClient(litestar_basic.app) as client:
        client.get("/")
        requests_response = client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = client.get(f"/_debug_toolbar/api/requests/{request_id}")

    headers_stats = detail_response.json()["panel_data"]["HeadersPanel"]
    assert headers_stats
