"""Tests for the ``examples/fastapi_basic`` example.

The dependency-injection panel's stats are the subject of an in-flight fix
(branch ``fix/fastapi-dependencies-panel``); these tests assert the panel key
is present in a request's panel data without asserting on its contents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from starlette.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


@pytest.fixture
def fastapi_basic(import_example: Callable[[str], ModuleType]) -> ModuleType:
    return import_example("examples.fastapi_basic.app")


def test_home_page_returns_toolbar_injected_page(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="debug-toolbar"' in response.text
    assert "/_debug_toolbar/static/toolbar.css" in response.text
    assert "/_debug_toolbar/static/toolbar.js" in response.text


def test_get_user_returns_json_without_toolbar_markup(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/users/123")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["user"]["username"] == "alice"
    assert data["requested_by"] == "alice"
    assert 'id="debug-toolbar"' not in response.text


def test_get_user_unknown_id_returns_404(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/users/999")

    assert response.status_code == 404


def test_list_items_returns_json_without_toolbar_markup(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/items", params={"skip": 10, "limit": 20})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["skip"] == 10
    assert data["limit"] == 20
    assert 'id="debug-toolbar"' not in response.text


def test_settings_returns_json_without_toolbar_markup(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "settings" in response.json()
    assert 'id="debug-toolbar"' not in response.text


def test_static_css_asset(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/_debug_toolbar/static/toolbar.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert response.text


def test_static_js_asset(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        response = client.get("/_debug_toolbar/static/toolbar.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert response.text


def test_history_api_lists_requests_after_html_requests(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        client.get("/")
        client.get("/users/123")
        response = client.get("/_debug_toolbar/api/requests")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_request_detail_contains_multiple_panels(fastapi_basic: ModuleType) -> None:
    with TestClient(fastapi_basic.app) as client:
        client.get("/")
        requests_response = client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = client.get(f"/_debug_toolbar/api/requests/{request_id}")

    assert detail_response.status_code == 200
    assert detail_response.headers["content-type"].startswith("application/json")
    detail = detail_response.json()

    panel_data = detail["panel_data"]
    expected_panels = {"TimerPanel", "RequestPanel", "ResponsePanel", "LoggingPanel", "VersionsPanel"}
    assert expected_panels <= set(panel_data)

    request_stats = panel_data["RequestPanel"]
    assert request_stats["method"] == "GET"
    assert request_stats["path"] == "/"


def test_dependency_injection_panel_is_present(fastapi_basic: ModuleType) -> None:
    """Only asserts the panel key exists; its stats are covered by an in-flight fix."""
    with TestClient(fastapi_basic.app) as client:
        client.get("/users/123")
        requests_response = client.get("/_debug_toolbar/api/requests")
        request_id = requests_response.json()[0]["request_id"]
        detail_response = client.get(f"/_debug_toolbar/api/requests/{request_id}")

    assert "DependencyInjectionPanel" in detail_response.json()["panel_data"]
