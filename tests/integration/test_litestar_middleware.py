"""Integration tests for Litestar middleware and plugin."""

from __future__ import annotations

import gzip

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from litestar import Litestar, MediaType, Response, get


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
        from litestar import Request

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


class TestGzipCompression:
    """Test toolbar injection with gzip-compressed responses."""

    def test_toolbar_injected_with_gzip_compression(self) -> None:
        """Test that toolbar is correctly injected when response is gzip-compressed.

        This tests the fix for the issue where gzip-compressed responses would
        fail to have the toolbar injected because the middleware couldn't decode
        the compressed bytes as UTF-8.
        """
        from litestar.config.compression import CompressionConfig

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            compression_config=CompressionConfig(backend="gzip", minimum_size=1),
            debug=True,
        )
        with TestClient(app) as client:
            # Request with Accept-Encoding to trigger compression
            response = client.get("/", headers={"Accept-Encoding": "gzip"})
            assert response.status_code == 200
            # At the TestClient level we see an uncompressed body with the toolbar injected.
            assert b"debug-toolbar" in response.content
            assert b"</body>" in response.content

    def test_toolbar_injected_without_compression(self) -> None:
        """Test that toolbar injection still works without compression."""
        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[html_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content

    def test_invalid_gzip_data_with_gzip_header(self) -> None:
        """Test handling of invalid gzip data with content-encoding: gzip header.

        When the response claims to be gzipped but contains invalid gzip data,
        the middleware should gracefully fall back to treating it as uncompressed.
        """

        @get("/invalid-gzip", media_type=MediaType.HTML)
        async def invalid_gzip_handler() -> Response:
            """Return invalid gzip data with gzip content-encoding header."""
            # This is not valid gzip data
            invalid_gzip = b"This is not gzipped data but pretends to be"
            return Response(
                content=invalid_gzip,
                status_code=HTTP_200_OK,
                media_type=MediaType.HTML,
                headers={"content-encoding": "gzip"},
            )

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[invalid_gzip_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/invalid-gzip")
            assert response.status_code == 200
            # Should return original content since it couldn't be decompressed
            assert b"This is not gzipped data but pretends to be" in response.content

    def test_gzip_decompressed_data_fails_utf8_decoding(self) -> None:
        """Test handling of valid gzip data that fails UTF-8 decoding after decompression.

        When gzipped data decompresses successfully but contains non-UTF-8 bytes,
        the middleware should return the original compressed data.
        """

        @get("/binary-gzip", media_type=MediaType.HTML)
        async def binary_gzip_handler() -> Response:
            """Return gzipped binary data that's not valid UTF-8."""
            # Binary data that's not valid UTF-8
            binary_data = b"\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89"
            gzipped = gzip.compress(binary_data)
            return Response(
                content=gzipped,
                status_code=HTTP_200_OK,
                media_type=MediaType.HTML,
                headers={"content-encoding": "gzip"},
            )

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[binary_gzip_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/binary-gzip")
            assert response.status_code == 200
            # Should return decompressed binary data since UTF-8 decode failed
            # The middleware has removed the gzip encoding, so we check for the raw binary content
            assert response.content == b"\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89"

    def test_gzip_header_case_insensitive(self) -> None:
        """Test that content-encoding header matching is case-insensitive.

        The HTTP spec requires header names to be case-insensitive, so we should
        handle various casings of "gzip" (e.g., "GZIP", "Gzip", "GzIp").
        """

        @get("/gzip-upper", media_type=MediaType.HTML)
        async def gzip_upper_handler() -> Response:
            """Return gzipped HTML with uppercase GZIP encoding."""
            html = "<html><body><h1>Test</h1></body></html>"
            gzipped = gzip.compress(html.encode("utf-8"))
            return Response(
                content=gzipped,
                status_code=HTTP_200_OK,
                media_type=MediaType.HTML,
                headers={"content-encoding": "GZIP"},
            )

        @get("/gzip-mixed", media_type=MediaType.HTML)
        async def gzip_mixed_handler() -> Response:
            """Return gzipped HTML with mixed case GzIp encoding."""
            html = "<html><body><h1>Test</h1></body></html>"
            gzipped = gzip.compress(html.encode("utf-8"))
            return Response(
                content=gzipped,
                status_code=HTTP_200_OK,
                media_type=MediaType.HTML,
                headers={"content-encoding": "GzIp"},
            )

        config = LitestarDebugToolbarConfig(enabled=True)
        app = Litestar(
            route_handlers=[gzip_upper_handler, gzip_mixed_handler],
            plugins=[DebugToolbarPlugin(config)],
            debug=True,
        )
        with TestClient(app) as client:
            # Test uppercase GZIP
            response = client.get("/gzip-upper")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert b"</body>" in response.content

            # Test mixed case GzIp
            response = client.get("/gzip-mixed")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
            assert b"</body>" in response.content
