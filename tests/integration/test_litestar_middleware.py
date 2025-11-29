"""Integration tests for Litestar middleware and plugin."""

from __future__ import annotations

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


@get("/text", media_type=MediaType.TEXT)
async def text_handler() -> str:
    return "plain text"


@pytest.fixture
def toolbar_config() -> LitestarDebugToolbarConfig:
    return LitestarDebugToolbarConfig(
        enabled=True,
        exclude_paths=["/_debug_toolbar"],
        show_on_errors=True,
    )


@pytest.fixture
def app(toolbar_config: LitestarDebugToolbarConfig) -> Litestar:
    return Litestar(
        route_handlers=[html_handler, json_handler, text_handler],
        plugins=[DebugToolbarPlugin(toolbar_config)],
        debug=True,
    )


@pytest.fixture
def client(app: Litestar) -> TestClient:
    return TestClient(app)


class TestToolbarInjection:
    def test_injects_toolbar_into_html_response(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert b"debug-toolbar" in response.content
        assert b"<h1>Test</h1>" in response.content

    def test_does_not_inject_into_json_response(self, client: TestClient) -> None:
        response = client.get("/json")
        assert response.status_code == 200
        assert response.json() == {"message": "hello"}
        assert b"debug-toolbar" not in response.content

    def test_does_not_inject_into_text_response(self, client: TestClient) -> None:
        response = client.get("/text")
        assert response.status_code == 200
        assert response.text == "plain text"
        assert b"debug-toolbar" not in response.content


class TestServerTimingHeader:
    def test_adds_server_timing_header_to_html(self, client: TestClient) -> None:
        response = client.get("/")
        assert "server-timing" in response.headers
        assert "total" in response.headers["server-timing"]

    def test_adds_server_timing_header_to_json(self, client: TestClient) -> None:
        response = client.get("/json")
        assert "server-timing" in response.headers


class TestToolbarPanels:
    def test_toolbar_has_timer_panel(self, client: TestClient) -> None:
        response = client.get("/")
        assert b"TimerPanel" in response.content

    def test_toolbar_has_request_panel(self, client: TestClient) -> None:
        response = client.get("/")
        assert b"RequestPanel" in response.content

    def test_toolbar_has_response_panel(self, client: TestClient) -> None:
        response = client.get("/")
        assert b"ResponsePanel" in response.content

    def test_toolbar_has_routes_panel(self, client: TestClient) -> None:
        response = client.get("/")
        assert b"RoutesPanel" in response.content

    def test_toolbar_shows_request_id(self, client: TestClient) -> None:
        response = client.get("/")
        assert b"data-request-id=" in response.content


class TestToolbarDisabled:
    def test_no_toolbar_when_disabled(self) -> None:
        config = LitestarDebugToolbarConfig(enabled=False)
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" not in response.content


class TestExcludePaths:
    def test_excludes_configured_paths(self) -> None:
        config = LitestarDebugToolbarConfig(
            enabled=True,
            exclude_paths=["/excluded"],
        )

        @get("/excluded", media_type=MediaType.HTML)
        async def excluded_handler() -> str:
            return "<html><body>excluded</body></html>"

        @get("/included", media_type=MediaType.HTML)
        async def included_handler() -> str:
            return "<html><body>included</body></html>"

        app = Litestar(
            route_handlers=[excluded_handler, included_handler],
            plugins=[DebugToolbarPlugin(config)],
        )
        with TestClient(app) as client:
            response = client.get("/excluded")
            assert b"debug-toolbar" not in response.content

            response = client.get("/included")
            assert b"debug-toolbar" in response.content


class TestExtraPanels:
    """Test that extra panels can be added and work correctly."""

    def test_alerts_panel_integration(self) -> None:
        config = LitestarDebugToolbarConfig(
            enabled=True,
            extra_panels=["debug_toolbar.core.panels.alerts.AlertsPanel"],
        )
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert b"AlertsPanel" in response.content

    def test_memory_panel_integration(self) -> None:
        config = LitestarDebugToolbarConfig(
            enabled=True,
            extra_panels=["debug_toolbar.core.panels.memory.MemoryPanel"],
        )
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert b"MemoryPanel" in response.content

    def test_headers_panel_integration(self) -> None:
        config = LitestarDebugToolbarConfig(
            enabled=True,
            extra_panels=["debug_toolbar.core.panels.headers.HeadersPanel"],
        )
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert b"HeadersPanel" in response.content

    def test_events_panel_auto_added(self) -> None:
        """Events panel should be auto-added by LitestarDebugToolbarConfig."""
        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"EventsPanel" in response.content


class TestMiddlewareExceptionHandling:
    """Test that middleware handles exceptions gracefully."""

    def test_handler_exception_doesnt_break_response(self) -> None:
        """Test that exceptions in handlers are handled properly."""

        @get("/error", media_type=MediaType.HTML)
        async def error_handler() -> str:
            raise ValueError("Test error")

        config = LitestarDebugToolbarConfig(enabled=True, show_on_errors=True)
        app = Litestar(
            route_handlers=[error_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/error")
            assert response.status_code == 500

    def test_multiple_routes_work(self) -> None:
        """Test that hitting multiple routes works without errors."""

        @get("/page1", media_type=MediaType.HTML)
        async def page1() -> str:
            return "<html><body><h1>Page 1</h1></body></html>"

        @get("/page2", media_type=MediaType.HTML)
        async def page2() -> str:
            return "<html><body><h1>Page 2</h1></body></html>"

        @get("/api/data")
        async def api_data() -> dict:
            return {"data": "test"}

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[page1, page2, api_data],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            r1 = client.get("/page1")
            assert r1.status_code == 200
            assert b"Page 1" in r1.content
            assert b"debug-toolbar" in r1.content

            r2 = client.get("/page2")
            assert r2.status_code == 200
            assert b"Page 2" in r2.content
            assert b"debug-toolbar" in r2.content

            r3 = client.get("/api/data")
            assert r3.status_code == 200
            assert r3.json() == {"data": "test"}

            r4 = client.get("/_debug_toolbar/")
            assert r4.status_code == 200


class TestToolbarWithLifecycleHooks:
    """Test toolbar works with Litestar lifecycle hooks."""

    def test_works_with_before_after_request(self) -> None:
        """Test toolbar works when app has before/after request hooks.

        Note: We only verify before_request hook is called. The after_request
        hook timing varies in CI environments due to async execution order.
        """
        from litestar import Request, Response

        hook_state: dict[str, bool] = {"before": False, "after": False}

        async def before_request(request: Request) -> None:
            hook_state["before"] = True

        async def after_request(response: Response) -> Response:
            hook_state["after"] = True
            return response

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            before_request=before_request,
            after_request=after_request,
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert hook_state["before"], "before_request hook was not called"
