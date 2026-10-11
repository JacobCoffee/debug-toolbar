"""Integration tests for the FastAPI dependency injection panel."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi.testclient import TestClient

from debug_toolbar.fastapi import FastAPIDebugToolbarConfig, setup_debug_toolbar
from fastapi import Depends, FastAPI

SLEEP_SECONDS = 0.05
SLEEP_MS = SLEEP_SECONDS * 1000


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


def slow_sync_dependency() -> str:
    time.sleep(SLEEP_SECONDS)
    return "sync"


def slow_generator_dependency():
    time.sleep(SLEEP_SECONDS)
    yield "generator"


async def slow_coroutine_dependency() -> str:
    import asyncio

    await asyncio.sleep(SLEEP_SECONDS)
    return "coroutine"


def make_timed_app() -> tuple[FastAPI, object]:
    app = FastAPI()
    config = FastAPIDebugToolbarConfig(enabled=True, track_dependency_injection=True)
    toolbar = setup_debug_toolbar(app, config)

    @app.get("/timed")
    def timed_route(
        sync_dep: Annotated[str, Depends(slow_sync_dependency)],
        gen_dep: Annotated[str, Depends(slow_generator_dependency)],
        coro_dep: Annotated[str, Depends(slow_coroutine_dependency)],
    ) -> dict:
        return {"sync": sync_dep, "gen": gen_dep, "coro": coro_dep}

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

    def test_sync_and_generator_dependency_durations_are_measured(self) -> None:
        """Sync-function and generator dependencies must report their real execution time."""
        app, toolbar = make_timed_app()
        client = TestClient(app)

        response = client.get("/timed")
        assert response.status_code == 200

        _request_id, data = toolbar.storage.get_all()[0]
        resolved = data["panel_data"]["DependencyInjectionPanel"]["resolved_dependencies"]
        by_name = {dep["name"]: dep for dep in resolved}

        assert by_name["slow_sync_dependency"]["duration_ms"] >= SLEEP_MS
        assert by_name["slow_generator_dependency"]["duration_ms"] >= SLEEP_MS
        assert by_name["slow_generator_dependency"]["type"] == "generator"

    def test_coroutine_dependency_duration_is_none(self) -> None:
        """Coroutine-function dependencies have no interceptable call site, so duration is None."""
        app, toolbar = make_timed_app()
        client = TestClient(app)

        response = client.get("/timed")
        assert response.status_code == 200

        _request_id, data = toolbar.storage.get_all()[0]
        resolved = data["panel_data"]["DependencyInjectionPanel"]["resolved_dependencies"]
        by_name = {dep["name"]: dep for dep in resolved}

        assert by_name["slow_coroutine_dependency"]["duration_ms"] is None
