"""Integration tests for the Litestar 3 Middleware panel and response-cache info.

These features rely on Litestar 3's :class:`~litestar.middleware.base.ASGIMiddleware`,
its bypass hooks, and :class:`~litestar.middleware.constraints.MiddlewareConstraints`,
and have no equivalent on Litestar 2.
"""

from __future__ import annotations

from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.middleware.constraints import MiddlewareConstraints
from litestar.testing import TestClient
from litestar.types import ASGIApp, Receive, Scope, Send

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from litestar import Litestar, MediaType, get


class RecordingMiddleware(ASGIMiddleware):
    """A plain middleware that always runs, used to verify ordering."""

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


class ConstrainedMiddleware(ASGIMiddleware):
    """A middleware that declares an ordering constraint."""

    constraints = MiddlewareConstraints(first=True)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


class ExcludedByPathMiddleware(ASGIMiddleware):
    """A middleware statically excluded from a specific handler path."""

    exclude_path_pattern = "/excluded"

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


class ExcludedByScopeMiddleware(ASGIMiddleware):
    """A middleware dynamically excluded for a specific request path."""

    should_bypass_for_scope = staticmethod(lambda scope: scope["path"].endswith("/dynamic-excluded"))

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        await next_app(scope, receive, send)


def _get_panel_data(plugin: DebugToolbarPlugin, panel_id: str, index: int = 0) -> dict:
    """Get panel data for a stored request. Storage returns newest-first, so index 0 is the latest."""
    storage = plugin.toolbar.storage
    requests = storage.get_all()
    _, data = requests[index]
    return data.get("panel_data", {}).get(panel_id, {})


class TestMiddlewarePanel:
    def test_lists_middleware_in_order_with_constraints(self) -> None:
        @get("/included-1", media_type=MediaType.HTML)
        async def handler() -> str:
            return "<html><body><h1>Included</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(
            route_handlers=[handler],
            middleware=[ConstrainedMiddleware(), RecordingMiddleware()],
            plugins=[plugin],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/included-1")
            assert response.status_code == 200

        middleware_data = _get_panel_data(plugin, "MiddlewarePanel")
        entries = middleware_data["middleware"]
        names = [entry["name"] for entry in entries]

        assert any(name.endswith("RecordingMiddleware") for name in names)
        assert any(name.endswith("ConstrainedMiddleware") for name in names)
        assert all(entry["ran"] for entry in entries)
        assert middleware_data["skipped_count"] == 0

        constrained_entry = next(e for e in entries if e["name"].endswith("ConstrainedMiddleware"))
        assert constrained_entry["constraints"]["first"] is True

    def test_shows_statically_excluded_middleware_as_skipped(self) -> None:
        @get("/excluded", media_type=MediaType.HTML)
        async def excluded_handler() -> str:
            return "<html><body><h1>Excluded</h1></body></html>"

        @get("/included-2", media_type=MediaType.HTML)
        async def included_handler() -> str:
            return "<html><body><h1>Included</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(
            route_handlers=[excluded_handler, included_handler],
            middleware=[ExcludedByPathMiddleware()],
            plugins=[plugin],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/excluded")
            assert response.status_code == 200

            middleware_data = _get_panel_data(plugin, "MiddlewarePanel")
            entries = middleware_data["middleware"]
            excluded_entry = next(e for e in entries if e["name"].endswith("ExcludedByPathMiddleware"))

            assert excluded_entry["ran"] is False
            assert "excluded for this route" in excluded_entry["skip_reason"]
            assert middleware_data["skipped_count"] == 1

            response = client.get("/included-2")
            assert response.status_code == 200

            middleware_data = _get_panel_data(plugin, "MiddlewarePanel")
            entries = middleware_data["middleware"]
            included_entry = next(e for e in entries if e["name"].endswith("ExcludedByPathMiddleware"))
            assert included_entry["ran"] is True
            assert included_entry["skip_reason"] is None

    def test_shows_dynamically_excluded_middleware_as_skipped(self) -> None:
        @get("/dynamic-excluded", media_type=MediaType.HTML)
        async def dynamic_excluded_handler() -> str:
            return "<html><body><h1>Dynamic excluded</h1></body></html>"

        @get("/included-3", media_type=MediaType.HTML)
        async def included_handler() -> str:
            return "<html><body><h1>Included</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(
            route_handlers=[dynamic_excluded_handler, included_handler],
            middleware=[ExcludedByScopeMiddleware()],
            plugins=[plugin],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/dynamic-excluded")
            assert response.status_code == 200

            middleware_data = _get_panel_data(plugin, "MiddlewarePanel")
            entries = middleware_data["middleware"]
            entry = next(e for e in entries if e["name"].endswith("ExcludedByScopeMiddleware"))
            assert entry["ran"] is False
            assert "should_bypass_for_scope" in entry["skip_reason"]

            response = client.get("/included-3")
            assert response.status_code == 200

            middleware_data = _get_panel_data(plugin, "MiddlewarePanel")
            entries = middleware_data["middleware"]
            entry = next(e for e in entries if e["name"].endswith("ExcludedByScopeMiddleware"))
            assert entry["ran"] is True


class TestResponseCacheInfo:
    def test_first_request_stores_to_cache_second_serves_from_cache(self) -> None:
        @get("/cached", media_type=MediaType.HTML, cache=60)
        async def cached_handler() -> str:
            return "<html><body><h1>Cached</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(
            route_handlers=[cached_handler],
            plugins=[plugin],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/cached")
            assert response.status_code == 200

            response_data = _get_panel_data(plugin, "ResponsePanel")
            cache_info = response_data["response_cache"]
            assert cache_info["stored_to_cache"] is True
            assert cache_info["served_from_cache"] is False
            assert cache_info["expires_in"] == 60
            assert cache_info["cache_key"]

            response = client.get("/cached")
            assert response.status_code == 200

            response_data = _get_panel_data(plugin, "ResponsePanel")
            cache_info = response_data["response_cache"]
            assert cache_info["served_from_cache"] is True

    def test_uncached_route_has_no_response_cache_info(self) -> None:
        @get("/not-cached", media_type=MediaType.HTML)
        async def handler() -> str:
            return "<html><body><h1>Not cached</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(
            route_handlers=[handler],
            plugins=[plugin],
            debug=True,
        )
        with TestClient(app) as client:
            response = client.get("/not-cached")
            assert response.status_code == 200

        response_data = _get_panel_data(plugin, "ResponsePanel")
        assert "response_cache" not in response_data


class TestMiddlewarePortedToASGIMiddleware:
    def test_toolbar_middleware_runs_as_asgi_middleware_instance(self) -> None:
        """The toolbar's own middleware should itself be an ASGIMiddleware instance now."""
        from debug_toolbar.litestar.middleware import DebugToolbarMiddleware

        assert issubclass(DebugToolbarMiddleware, ASGIMiddleware)
        assert DebugToolbarMiddleware.scopes == (ScopeType.HTTP, ScopeType.WEBSOCKET)

        @get("/asgi-port", media_type=MediaType.HTML)
        async def handler() -> str:
            return "<html><body><h1>Included</h1></body></html>"

        config = LitestarDebugToolbarConfig(enabled=True, exclude_paths=[])
        plugin = DebugToolbarPlugin(config)
        app = Litestar(route_handlers=[handler], plugins=[plugin], debug=True)

        with TestClient(app) as client:
            response = client.get("/asgi-port")
            assert response.status_code == 200
            assert b"debug-toolbar" in response.content
