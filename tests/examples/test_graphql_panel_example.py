"""Tests for the GraphQL Panel example application."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from litestar.testing import TestClient

from debug_toolbar.extras.strawberry.extension import STRAWBERRY_AVAILABLE

if TYPE_CHECKING:
    from types import ModuleType


@pytest.fixture
def app_module(import_example: Callable[[str], ModuleType]) -> ModuleType:
    return import_example("examples.graphql_panel_example")


def test_index_page_shows_toolbar(app_module: ModuleType) -> None:
    with TestClient(app_module.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'id="debug-toolbar"' in response.text


@pytest.mark.skipif(not STRAWBERRY_AVAILABLE, reason="Strawberry not installed")
class TestGraphQLQueries:
    def test_posts_query_returns_expected_shape(self, app_module: ModuleType) -> None:
        query = """
        query {
            posts {
                id
                title
                author {
                    id
                    name
                }
            }
        }
        """
        with TestClient(app_module.app) as client:
            response = client.post("/graphql", json={"query": query})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data or not data["errors"]
        posts = data["data"]["posts"]
        assert len(posts) == 5
        assert posts[0]["title"] == "GraphQL Basics"
        assert posts[0]["author"]["name"] == "Alice"

    def test_create_user_mutation_succeeds(self, app_module: ModuleType) -> None:
        mutation = """
        mutation {
            createUser(name: "Dave", email: "dave@example.com") {
                id
                name
                email
            }
        }
        """
        with TestClient(app_module.app) as client:
            response = client.post("/graphql", json={"query": mutation})

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data or not data["errors"]
        created = data["data"]["createUser"]
        assert created["name"] == "Dave"
        assert created["email"] == "dave@example.com"
        assert created["id"] == "4"


@pytest.mark.skipif(not STRAWBERRY_AVAILABLE, reason="Strawberry not installed")
def test_graphql_panel_records_resolver_and_n_plus_one_stats(app_module: ModuleType) -> None:
    query = """
    query {
        posts {
            id
            title
            author {
                id
                name
            }
        }
    }
    """
    with TestClient(app_module.app) as client:
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200

        requests = client.get("/_debug_toolbar/api/requests").json()
        graphql_request = next(req for req in requests if req["metadata"].get("path") == "/graphql")

        detail = client.get(f"/_debug_toolbar/api/requests/{graphql_request['request_id']}").json()
        graphql_stats = detail["panel_data"]["GraphQLPanel"]

    assert graphql_stats["operation_count"] >= 1
    assert graphql_stats["resolver_count"] > 0
    assert graphql_stats["n_plus_one_count"] >= 1
    author_patterns = [p for p in graphql_stats["n_plus_one_patterns"] if p["field_name"] == "author"]
    assert author_patterns
    assert author_patterns[0]["count"] >= 3
