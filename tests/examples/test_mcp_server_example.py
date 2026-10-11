"""Tests for the ``examples.mcp_server_example`` application."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from litestar.testing import TestClient

from debug_toolbar import FileToolbarStorage
from debug_toolbar.mcp import create_mcp_server
from debug_toolbar.mcp.server import MCPContext

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import ModuleType

    import pytest


def _load_app(
    import_example: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> ModuleType:
    monkeypatch.chdir(tmp_path)
    return import_example("examples.mcp_server_example")


class TestHtmlPages:
    def test_html_pages_render_with_toolbar(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        app = app_module.create_app()
        with TestClient(app) as client:
            for path in ("/", "/slow", "/users", "/compute", "/error-demo"):
                response = client.get(path)
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/html")
                assert 'id="debug-toolbar"' in response.text


class TestJsonApiEndpoints:
    def test_api_data_returns_json_without_toolbar_markup(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        app = app_module.create_app()
        with TestClient(app) as client:
            response = client.get("/api/data")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            assert data["total"] == 2
            assert {u["name"] for u in data["users"]} == {"Alice", "Bob"}
            assert 'id="debug-toolbar"' not in response.text

    def test_api_create_returns_json_without_toolbar_markup(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        app = app_module.create_app()
        with TestClient(app) as client:
            response = client.post("/api/create", json={"name": "widget"})
            assert response.status_code == 201
            assert response.headers["content-type"].startswith("application/json")
            assert response.json() == {"created": True, "data": {"name": "widget"}}
            assert 'id="debug-toolbar"' not in response.text


class TestSharedFileStorage:
    def test_requests_are_persisted_to_shared_storage_file(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        app = app_module.create_app()
        with TestClient(app) as client:
            client.get("/")
            client.get("/users")

        storage_path = tmp_path / app_module.STORAGE_FILE
        assert storage_path.exists()
        raw = json.loads(storage_path.read_text())
        assert len(raw) >= 2
        assert all("request_id" in entry and "data" in entry for entry in raw)
        paths = {entry["data"]["metadata"]["path"] for entry in raw}
        assert {"/", "/users"} <= paths


class TestMcpToolRegistry:
    def test_expected_tools_are_registered(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        storage = FileToolbarStorage(app_module.STORAGE_FILE)
        mcp = create_mcp_server(storage=storage, toolbar=None, server_name="test-debug-toolbar")

        tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}
        assert tool_names == {
            "get_request_history",
            "analyze_performance_bottlenecks",
            "detect_n_plus_one_queries",
            "get_query_explain_plan",
            "analyze_security_alerts",
            "compare_requests",
            "get_graphql_operations",
            "get_async_task_profile",
            "generate_optimization_report",
            "clear_request_history",
        }


class TestMcpToolInvocation:
    def test_tools_analyze_real_requests_from_shared_storage(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        app = app_module.create_app()
        with TestClient(app) as client:
            response = client.get("/slow")
            assert response.status_code == 200

        storage = FileToolbarStorage(app_module.STORAGE_FILE)
        mcp = create_mcp_server(storage=storage, toolbar=None, server_name="test-debug-toolbar")
        fake_ctx = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=MCPContext(storage=storage)))

        history_tool = mcp._tool_manager.get_tool("get_request_history")
        history: list[dict[str, Any]] = history_tool.fn(fake_ctx, limit=20)
        assert history
        slow_entry = next(entry for entry in history if entry["path"] == "/slow")
        assert slow_entry["method"] == "GET"
        assert slow_entry["status_code"] == 200
        assert slow_entry["duration_ms"] > 0

        bottleneck_tool = mcp._tool_manager.get_tool("analyze_performance_bottlenecks")
        analysis: dict[str, Any] = bottleneck_tool.fn(fake_ctx, request_id=slow_entry["request_id"])
        assert "error" not in analysis
        assert analysis["total_requests_analyzed"] == 1

        n_plus_one_tool = mcp._tool_manager.get_tool("detect_n_plus_one_queries")
        n_plus_one: dict[str, Any] = n_plus_one_tool.fn(fake_ctx, request_id=slow_entry["request_id"], threshold=1)
        assert n_plus_one == {
            "n_plus_one_detected": False,
            "patterns_found": 0,
            "threshold_used": 1,
            "patterns": [],
            "recommendations": [],
        }
