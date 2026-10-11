"""Integration tests for the FastAPI dependency injection panel."""

from __future__ import annotations

from typing import Annotated

from fastapi.testclient import TestClient

from debug_toolbar.fastapi import FastAPIDebugToolbarConfig, setup_debug_toolbar
from fastapi import Depends, FastAPI


def get_settings() -> dict:
    return {"debug": True}


def get_current_user(settings: Annotated[dict, Depends(get_settings)]) -> dict:
    return {"id": 1, "debug": settings["debug"]}


def make_app() -> tuple[FastAPI, object]:
    app = FastAPI()
    config = FastAPIDebugToolbarConfig(enabled=True, track_dependency_injection=True)
    toolbar = setup_debug_toolbar(app, config)

    @app.get("/users/me")
    def read_current_user(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        return user

    return app, toolbar


def make_shared_dependency_app() -> tuple[FastAPI, object]:
    """A route that uses the same dependency twice, directly and via another dependency."""
    app = FastAPI()
    config = FastAPIDebugToolbarConfig(enabled=True, track_dependency_injection=True)
    toolbar = setup_debug_toolbar(app, config)

    @app.get("/shared")
    def read_shared(
        settings: Annotated[dict, Depends(get_settings)],
        user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        return {"settings": settings, "user": user}

    return app, toolbar


class TestDependenciesPanelIntegration:
    def test_resolved_dependencies_populated_for_depends_route(self) -> None:
        """A route using Depends() must report non-empty resolved_dependencies."""
        app, toolbar = make_app()
        client = TestClient(app)

        response = client.get("/users/me")
        assert response.status_code == 200

        _request_id, data = toolbar.storage.get_all()[0]
        panel_stats = data["panel_data"]["DependencyInjectionPanel"]

        resolved = panel_stats["resolved_dependencies"]
        assert resolved != []

        names = {dep["name"] for dep in resolved}
        assert "get_current_user" in names
        assert "get_settings" in names
        assert panel_stats["total_count"] == len(resolved)

    def test_shared_dependency_is_marked_cached_on_second_use(self) -> None:
        """A dependency used twice in the same route is only resolved once; the
        second (shared) use is reported as cached.
        """
        app, toolbar = make_shared_dependency_app()
        client = TestClient(app)

        response = client.get("/shared")
        assert response.status_code == 200

        _request_id, data = toolbar.storage.get_all()[0]
        resolved = data["panel_data"]["DependencyInjectionPanel"]["resolved_dependencies"]

        settings_entries = [dep for dep in resolved if dep["name"] == "get_settings"]
        assert len(settings_entries) == 2
        assert sorted(dep["cached"] for dep in settings_entries) == [False, True]
