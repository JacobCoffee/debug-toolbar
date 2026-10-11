"""Tests for the ``examples.litestar_advanced_alchemy`` application."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

_CREATE_USER_SCRIPT = """
import json
import os
import sys

sys.path.insert(0, {repo_root!r})
os.chdir({tmp_dir!r})

from examples.litestar_advanced_alchemy import app as app_module
from litestar.testing import TestClient

with TestClient(app_module.app) as client:
    create_response = client.post(
        "/api/users",
        data={{"name": "Frank Castle", "email": "frank@example.com"}},
    )
    users = client.get("/api/users").json()

print(json.dumps({{
    "create_status": create_response.status_code,
    "create_text": create_response.text,
    "users": users,
}}))
"""

_DELETE_USER_SCRIPT = """
import json
import os
import sys

sys.path.insert(0, {repo_root!r})
os.chdir({tmp_dir!r})

from examples.litestar_advanced_alchemy import app as app_module
from litestar.testing import TestClient

with TestClient(app_module.app) as client:
    users_before = client.get("/api/users").json()
    target = next(u for u in users_before if u["name"] == "Eve Wilson")
    delete_response = client.delete(f"/api/users/{{target['id']}}")
    users_after = client.get("/api/users").json()

print(json.dumps({{
    "delete_status": delete_response.status_code,
    "target_id": target["id"],
    "users_before": users_before,
    "users_after": users_after,
}}))
"""


def _run_isolated_script(script_template: str, tmp_dir: Path) -> dict[str, Any]:
    """Run a script in a fresh subprocess, isolated from this process's SQLAlchemy state.

    Advanced-Alchemy's declarative models register themselves against global
    SQLAlchemy registries (``advanced_alchemy.base.orm_registry``) that are not reset
    when ``import_example`` evicts and reimports the example module. Repeated in-process
    reimports of this particular example therefore corrupt write visibility for later
    requests. Running each mutation in its own interpreter sidesteps that corruption.
    """
    script = script_template.format(repo_root=str(_REPO_ROOT), tmp_dir=str(tmp_dir))
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def _latest_request_id(client: TestClient, path: str) -> str:
    """Return the ``request_id`` of the most recent recorded request to ``path``."""
    requests = client.get("/_debug_toolbar/api/requests").json()
    matches = [r for r in requests if r["metadata"]["path"] == path]
    assert matches, f"no recorded request for {path}"
    return matches[-1]["request_id"]


def _panel_data(client: TestClient, path: str) -> dict[str, Any]:
    """Return the ``panel_data`` dict for the most recent request to ``path``."""
    request_id = _latest_request_id(client, path)
    detail = client.get(f"/_debug_toolbar/api/requests/{request_id}").json()
    return detail["panel_data"]


def _load_app(
    import_example: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> ModuleType:
    monkeypatch.chdir(tmp_path)
    return import_example("examples.litestar_advanced_alchemy.app")


class TestHtmlPages:
    def test_index_page(
        self,
        import_example: Callable[[str], ModuleType],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert 'id="debug-toolbar"' in response.text

    def test_users_page(
        self,
        import_example: Callable[[str], ModuleType],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/users")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert 'id="debug-toolbar"' in response.text

    def test_posts_page(
        self,
        import_example: Callable[[str], ModuleType],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/posts")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert 'id="debug-toolbar"' in response.text


class TestApiListEndpoints:
    def test_list_users_returns_seeded_data(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/api/users")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            users = response.json()
            assert len(users) == 5
            names = {u["name"] for u in users}
            assert names == {"Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Ross", "Eve Wilson"}
            alice = next(u for u in users if u["name"] == "Alice Johnson")
            assert alice["email"] == "alice@example.com"

    def test_list_posts_returns_seeded_data(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/api/posts")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            posts = response.json()
            assert len(posts) == 7
            titles = {p["title"] for p in posts}
            assert "Getting Started with Litestar" in titles
            alice_post = next(p for p in posts if p["title"] == "Getting Started with Litestar")
            assert alice_post["author"] == "Alice Johnson"


class TestCreateAndDeleteUser:
    def test_create_user_appears_in_list(self, tmp_path: Path) -> None:
        result = _run_isolated_script(_CREATE_USER_SCRIPT, tmp_path)

        assert result["create_status"] == 201
        assert "Frank Castle" in result["create_text"]

        names = {u["name"] for u in result["users"]}
        assert "Frank Castle" in names
        assert len(result["users"]) == 6

    def test_delete_user_removes_it(self, tmp_path: Path) -> None:
        result = _run_isolated_script(_DELETE_USER_SCRIPT, tmp_path)

        assert result["delete_status"] == 204
        assert len(result["users_before"]) == 5

        remaining_ids = {u["id"] for u in result["users_after"]}
        assert result["target_id"] not in remaining_ids
        assert len(result["users_after"]) == 4


class TestNPlusOneDetection:
    def test_n_plus_one_demo_is_flagged_by_sqlalchemy_panel(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            bad_response = client.get("/api/users-with-posts-bad")
            assert bad_response.status_code == 200

            baseline_response = client.get("/api/users")
            assert baseline_response.status_code == 200

            bad_panel_data = _panel_data(client, "/api/users-with-posts-bad")
            baseline_panel_data = _panel_data(client, "/api/users")

            bad_sql_stats = bad_panel_data["SQLAlchemyPanel"]
            baseline_sql_stats = baseline_panel_data["SQLAlchemyPanel"]

            assert bad_sql_stats["n_plus_one_count"] > 0
            assert len(bad_sql_stats["n_plus_one_groups"]) > 0
            assert bad_sql_stats["has_issues"] is True
            assert bad_sql_stats["query_count"] > baseline_sql_stats["query_count"]


class TestAsyncProfilerPanel:
    def test_async_demo_reports_task_stats(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            response = client.get("/async-demo")
            assert response.status_code == 200

            panel_data = _panel_data(client, "/async-demo")
            async_stats = panel_data["AsyncProfilerPanel"]

            assert async_stats["summary"]["total_tasks"] == 5
            assert async_stats["summary"]["completed_tasks"] == 5


class TestOtherPanelsPresent:
    def test_settings_headers_alerts_memory_panels_present(
        self, import_example: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        app_module = _load_app(import_example, monkeypatch, tmp_path)
        with TestClient(app_module.app) as client:
            client.get("/")
            panel_data = _panel_data(client, "/")

            assert "SettingsPanel" in panel_data
            assert "HeadersPanel" in panel_data
            assert "AlertsPanel" in panel_data
            assert "MemoryPanel" in panel_data
