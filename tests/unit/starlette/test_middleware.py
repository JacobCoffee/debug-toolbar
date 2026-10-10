"""Tests for Starlette debug toolbar middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from debug_toolbar.core import DebugToolbar
from debug_toolbar.starlette.config import StarletteDebugToolbarConfig
from debug_toolbar.starlette.middleware import DebugToolbarMiddleware, ResponseState


class TestResponseState:
    """Tests for ResponseState dataclass."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        state = ResponseState()
        assert state.started is False
        assert state.body_chunks == []
        assert state.headers == {}
        assert state.status_code == 200
        assert state.is_html is False
        assert state.headers_sent is False
        assert state.original_headers == []

    def test_mutable_defaults(self) -> None:
        """Should have independent mutable defaults."""
        state1 = ResponseState()
        state2 = ResponseState()
        state1.body_chunks.append(b"test")
        assert len(state2.body_chunks) == 0


class TestDebugToolbarMiddleware:
    """Tests for DebugToolbarMiddleware class."""

    def test_init_with_defaults(self) -> None:
        """Should initialize with default config."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)
        assert middleware.app is app
        assert middleware.config is not None
        assert middleware.toolbar is not None

    def test_init_with_custom_config(self) -> None:
        """Should accept custom config."""
        app = AsyncMock()
        config = StarletteDebugToolbarConfig(enabled=False)
        middleware = DebugToolbarMiddleware(app, config=config)
        assert middleware.config is config
        assert middleware.config.enabled is False

    def test_init_with_shared_toolbar(self) -> None:
        """Should accept shared toolbar instance."""
        app = AsyncMock()
        config = StarletteDebugToolbarConfig()
        toolbar = DebugToolbar(config)
        middleware = DebugToolbarMiddleware(app, config=config, toolbar=toolbar)
        assert middleware.toolbar is toolbar

    @pytest.mark.asyncio
    async def test_call_non_http(self) -> None:
        """Should pass through non-HTTP requests."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)
        scope = {"type": "lifespan", "path": "/"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_excluded_path(self) -> None:
        """Should pass through excluded paths."""
        app = AsyncMock()
        config = StarletteDebugToolbarConfig()
        middleware = DebugToolbarMiddleware(app, config=config)

        scope = {
            "type": "http",
            "path": "/_debug_toolbar/",
            "query_string": b"",
            "headers": [],
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("starlette.requests.Request") as mock_request_class:
            mock_request = MagicMock()
            mock_request.url.path = "/_debug_toolbar/"
            mock_request.headers.get.return_value = ""
            mock_request_class.return_value = mock_request

            await middleware(scope, receive, send)

        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_disabled(self) -> None:
        """Should pass through when disabled."""
        app = AsyncMock()
        config = StarletteDebugToolbarConfig(enabled=False)
        middleware = DebugToolbarMiddleware(app, config=config)

        scope = {
            "type": "http",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "method": "GET",
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("starlette.requests.Request") as mock_request_class:
            mock_request = MagicMock()
            mock_request.url.path = "/"
            mock_request_class.return_value = mock_request

            await middleware(scope, receive, send)

        app.assert_called_once_with(scope, receive, send)

    def test_render_toolbar(self) -> None:
        """Should render toolbar HTML."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)
        data = {
            "panels": [{"panel_id": "TestPanel", "nav_title": "Test", "nav_subtitle": "sub"}],
            "timing": {"total_time": 0.1},
            "request_id": "test-123",
        }

        html = middleware._render_toolbar(data)

        assert 'id="debug-toolbar"' in html
        assert 'data-request-id="test-123"' in html
        assert "100.00ms" in html
        assert "Test" in html

    def test_inject_toolbar_html(self) -> None:
        """Should inject toolbar before </body>."""
        app = AsyncMock()
        from debug_toolbar.starlette.config import StarletteDebugToolbarConfig

        config = StarletteDebugToolbarConfig(insert_before="</body>")
        middleware = DebugToolbarMiddleware(app, config=config)

        from debug_toolbar.core.context import RequestContext

        context = RequestContext()
        body = b"<html><body><h1>Hello</h1></body></html>"

        result = middleware._inject_toolbar(body, context)

        assert b"debug-toolbar" in result
        assert b"</body>" in result

    def test_inject_toolbar_no_body_tag(self) -> None:
        """Should return original when insert_before not found."""
        app = AsyncMock()
        from debug_toolbar.starlette.config import StarletteDebugToolbarConfig

        config = StarletteDebugToolbarConfig(insert_before="</body>")
        middleware = DebugToolbarMiddleware(app, config=config)

        from debug_toolbar.core.context import RequestContext

        context = RequestContext()
        body = b"<html><h1>Hello</h1></html>"

        result = middleware._inject_toolbar(body, context)

        assert result == body

    def test_inject_toolbar_binary(self) -> None:
        """Should handle non-UTF8 content."""
        app = AsyncMock()
        middleware = DebugToolbarMiddleware(app)

        from debug_toolbar.core.context import RequestContext

        context = RequestContext()
        body = b"\xff\xfe\x00\x01"

        result = middleware._inject_toolbar(body, context)

        assert result == body
