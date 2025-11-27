"""Integration tests for debug toolbar routes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from litestar.testing import TestClient

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from litestar import Litestar, MediaType, get


@get("/", media_type=MediaType.HTML)
async def html_handler() -> str:
    return "<html><body><h1>Test</h1></body></html>"


@get("/json")
async def json_handler() -> dict:
    return {"message": "hello"}


@pytest.fixture
def toolbar_config() -> LitestarDebugToolbarConfig:
    return LitestarDebugToolbarConfig(
        enabled=True,
        exclude_paths=[],
        show_on_errors=True,
    )


@pytest.fixture
def plugin(toolbar_config: LitestarDebugToolbarConfig) -> DebugToolbarPlugin:
    return DebugToolbarPlugin(toolbar_config)


@pytest.fixture
def app(plugin: DebugToolbarPlugin) -> Litestar:
    return Litestar(
        route_handlers=[html_handler, json_handler],
        plugins=[plugin],
        debug=True,
    )


@pytest.fixture
def client(app: Litestar) -> TestClient:
    return TestClient(app)


class TestToolbarIndexRoute:
    def test_toolbar_index_returns_html(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    def test_toolbar_index_contains_history_title(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/")
        assert b"Debug Toolbar" in response.content
        assert b"Request History" in response.content

    def test_toolbar_index_shows_empty_state(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/")
        assert b"No requests recorded yet" in response.content

    def test_toolbar_index_shows_requests_after_html_request(self, client: TestClient) -> None:
        client.get("/")
        response = client.get("/_debug_toolbar/")
        assert response.status_code == 200
        assert b"No requests recorded yet" not in response.content
        assert b"GET" in response.content


class TestToolbarDetailRoute:
    def test_detail_returns_404_for_unknown_request(self, client: TestClient) -> None:
        unknown_id = uuid4()
        response = client.get(f"/_debug_toolbar/{unknown_id}")
        assert response.status_code == 404

    def test_detail_returns_html_for_known_request(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        client.get("/")
        storage = plugin.toolbar.storage
        requests = storage.get_all()
        assert len(requests) > 0
        request_id, _ = requests[0]
        response = client.get(f"/_debug_toolbar/{request_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert b"Request Details" in response.content

    def test_detail_shows_request_metadata(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        client.get("/")
        storage = plugin.toolbar.storage
        requests = storage.get_all()
        request_id, _ = requests[0]
        response = client.get(f"/_debug_toolbar/{request_id}")
        assert b"Request Metadata" in response.content
        assert b"Method" in response.content
        assert b"Path" in response.content

    def test_detail_shows_panels_section(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        client.get("/")
        storage = plugin.toolbar.storage
        requests = storage.get_all()
        request_id, _ = requests[0]
        response = client.get(f"/_debug_toolbar/{request_id}")
        assert b"Panels" in response.content


class TestToolbarApiRoutes:
    def test_api_requests_returns_json(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/api/requests")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert isinstance(data, list)

    def test_api_requests_returns_empty_list_initially(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/api/requests")
        data = response.json()
        assert data == []

    def test_api_requests_returns_requests_after_html_request(self, client: TestClient) -> None:
        client.get("/")
        response = client.get("/_debug_toolbar/api/requests")
        data = response.json()
        assert len(data) >= 1
        assert "request_id" in data[0]
        assert "metadata" in data[0]
        assert "timing" in data[0]

    def test_api_request_detail_returns_404_for_unknown(self, client: TestClient) -> None:
        unknown_id = uuid4()
        response = client.get(f"/_debug_toolbar/api/requests/{unknown_id}")
        assert response.status_code == 404

    def test_api_request_detail_returns_json_for_known(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        client.get("/")
        storage = plugin.toolbar.storage
        requests = storage.get_all()
        request_id, _ = requests[0]
        response = client.get(f"/_debug_toolbar/api/requests/{request_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["request_id"] == str(request_id)
        assert "panel_data" in data
        assert "timing_data" in data
        assert "metadata" in data


class TestToolbarStaticAssets:
    def test_css_returns_stylesheet(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/static/toolbar.css")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/css")
        assert b"debug-toolbar" in response.content

    def test_css_contains_expected_classes(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/static/toolbar.css")
        assert b".toolbar-page" in response.content
        assert b".toolbar-header" in response.content
        assert b".panel" in response.content

    def test_js_returns_javascript(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/static/toolbar.js")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/javascript")

    def test_js_contains_toolbar_class(self, client: TestClient) -> None:
        response = client.get("/_debug_toolbar/static/toolbar.js")
        assert b"DebugToolbar" in response.content
        assert b"togglePanel" in response.content


class TestToolbarRouteExclusion:
    def test_toolbar_routes_not_injected_into_toolbar_pages(self, client: TestClient) -> None:
        client.get("/")
        response = client.get("/_debug_toolbar/")
        content = response.content.decode()
        assert content.count('id="debug-toolbar"') == 0


class TestToolbarIntegration:
    def test_full_workflow(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert b"debug-toolbar" in response.content

        response = client.get("/_debug_toolbar/")
        assert response.status_code == 200
        assert b"GET" in response.content

        storage = plugin.toolbar.storage
        requests = storage.get_all()
        assert len(requests) >= 1
        request_id, _ = requests[0]

        response = client.get(f"/_debug_toolbar/{request_id}")
        assert response.status_code == 200
        assert b"Request Details" in response.content

        response = client.get(f"/_debug_toolbar/api/requests/{request_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == str(request_id)

    def test_multiple_requests_tracked(self, client: TestClient, plugin: DebugToolbarPlugin) -> None:
        client.get("/")
        client.get("/json")

        storage = plugin.toolbar.storage
        requests = storage.get_all()
        assert len(requests) >= 2

        paths = [req[1].get("metadata", {}).get("path") for req in requests]
        assert "/" in paths
        assert "/json" in paths
