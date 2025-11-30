"""GraphQL Panel example with Strawberry integration.

This example demonstrates using the debug toolbar's GraphQL Panel with
Strawberry GraphQL to track operations, resolvers, detect N+1 patterns,
and identify duplicate queries.

Run with: litestar --app examples.graphql_panel_example:app run --reload

Requirements: Install with strawberry extra:
    pip install debug-toolbar[litestar,strawberry]
"""

from __future__ import annotations

import asyncio
import logging
import strawberry
from strawberry.litestar import make_graphql_controller

from debug_toolbar.extras.strawberry import DebugToolbarExtension, GraphQLPanel
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig
from litestar import Litestar, MediaType, Request, get

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def get_context(request: Request) -> dict:
    """Get GraphQL context with debug toolbar request context from scope."""
    ctx = request.scope.get("_debug_toolbar_context")
    logger.info("GraphQL context_getter: scope keys=%s, ctx=%s", list(request.scope.keys()), ctx)
    return {"debug_toolbar_context": ctx}


USERS_DB = [
    {"id": "1", "name": "Alice", "email": "alice@example.com"},
    {"id": "2", "name": "Bob", "email": "bob@example.com"},
    {"id": "3", "name": "Charlie", "email": "charlie@example.com"},
]

POSTS_DB = [
    {"id": "1", "title": "GraphQL Basics", "author_id": "1"},
    {"id": "2", "title": "Strawberry Tutorial", "author_id": "1"},
    {"id": "3", "title": "Python Tips", "author_id": "2"},
    {"id": "4", "title": "Async Patterns", "author_id": "2"},
    {"id": "5", "title": "Debug Toolbar Guide", "author_id": "3"},
]


@strawberry.type
class Post:
    """GraphQL Post type."""

    id: str
    title: str

    @strawberry.field
    async def author(self) -> User:
        """Fetch the author - demonstrates N+1 when not using DataLoader."""
        await asyncio.sleep(0.01)  # Simulate DB lookup
        author_data = next((u for u in USERS_DB if u["id"] == self._author_id), None)
        if author_data:
            return User(
                id=author_data["id"],
                name=author_data["name"],
                email=author_data["email"],
            )
        msg = f"Author {self._author_id} not found"
        raise ValueError(msg)

    def __init__(self, id: str, title: str, author_id: str) -> None:  # noqa: A002
        self.id = id
        self.title = title
        self._author_id = author_id


@strawberry.type
class User:
    """GraphQL User type."""

    id: str
    name: str
    email: str

    @strawberry.field
    async def posts(self) -> list[Post]:
        """Fetch user's posts."""
        await asyncio.sleep(0.01)  # Simulate DB lookup
        return [
            Post(id=p["id"], title=p["title"], author_id=p["author_id"])
            for p in POSTS_DB
            if p["author_id"] == self.id
        ]


@strawberry.type
class Query:
    """GraphQL Query type."""

    @strawberry.field
    async def users(self) -> list[User]:
        """Get all users."""
        await asyncio.sleep(0.02)  # Simulate DB lookup
        return [
            User(id=u["id"], name=u["name"], email=u["email"])
            for u in USERS_DB
        ]

    @strawberry.field
    async def user(self, id: str) -> User | None:  # noqa: A002
        """Get a user by ID."""
        await asyncio.sleep(0.01)  # Simulate DB lookup
        user_data = next((u for u in USERS_DB if u["id"] == id), None)
        if user_data:
            return User(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
            )
        return None

    @strawberry.field
    async def posts(self) -> list[Post]:
        """Get all posts - demonstrates N+1 when resolving authors."""
        await asyncio.sleep(0.02)  # Simulate DB lookup
        return [
            Post(id=p["id"], title=p["title"], author_id=p["author_id"])
            for p in POSTS_DB
        ]


@strawberry.type
class Mutation:
    """GraphQL Mutation type."""

    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> User:
        """Create a new user."""
        await asyncio.sleep(0.01)  # Simulate DB insert
        new_id = str(len(USERS_DB) + 1)
        user_data = {"id": new_id, "name": name, "email": email}
        USERS_DB.append(user_data)
        logger.info("Created user: %s", name)
        return User(id=new_id, name=name, email=email)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DebugToolbarExtension(
            slow_operation_threshold_ms=100.0,
            slow_resolver_threshold_ms=10.0,
            capture_stacks=True,
        ),
    ],
)

GraphQLController = make_graphql_controller(
    schema,
    path="/graphql",
    context_getter=get_context,
)


@get("/", media_type=MediaType.HTML)
async def index() -> str:
    """Home page with GraphQL Playground link."""
    return """<!DOCTYPE html>
<html>
<head><title>GraphQL Debug Toolbar Example</title></head>
<body>
    <h1>GraphQL Debug Toolbar Example</h1>
    <p>This example demonstrates the GraphQL Panel with Strawberry integration.</p>

    <h2>GraphQL Playground</h2>
    <p><a href="/graphql">Open GraphQL Playground</a></p>

    <h2>Try These Queries</h2>

    <h3>1. Simple Query (fast)</h3>
    <pre>
query {
  users {
    id
    name
    email
  }
}
    </pre>

    <h3>2. N+1 Query Pattern (will trigger alert)</h3>
    <pre>
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
    </pre>
    <p><strong>Note:</strong> This query fetches all posts, then for each post
    resolves the author individually. The GraphQL Panel will detect this N+1 pattern!</p>

    <h3>3. Nested Query</h3>
    <pre>
query {
  users {
    id
    name
    posts {
      id
      title
    }
  }
}
    </pre>

    <h3>4. Mutation</h3>
    <pre>
mutation {
  createUser(name: "David", email: "david@example.com") {
    id
    name
    email
  }
}
    </pre>

    <h2>What to Check in the Debug Toolbar</h2>
    <ul>
        <li><strong>GraphQL Panel</strong> - See all operations, resolvers, timing</li>
        <li><strong>N+1 Detection</strong> - Watch for resolver patterns that repeat</li>
        <li><strong>Duplicate Queries</strong> - Run the same query twice to see detection</li>
        <li><strong>Resolver Tree</strong> - Visualize the resolver execution hierarchy</li>
        <li><strong>Stack Traces</strong> - See where each resolver was called from</li>
    </ul>

    <h2>Panel Features</h2>
    <ul>
        <li>Operation tracking (queries, mutations, subscriptions)</li>
        <li>Resolver timing with slow resolver highlighting</li>
        <li>N+1 query pattern detection with fix suggestions</li>
        <li>Duplicate operation detection</li>
        <li>Stack trace capture for resolvers</li>
        <li>Server-Timing header integration</li>
    </ul>

    <p><a href="/_debug_toolbar/">View Request History</a></p>
</body>
</html>"""


toolbar_config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
    extra_panels=[
        GraphQLPanel,
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.core.panels.alerts.AlertsPanel",
    ],
)

app = Litestar(
    route_handlers=[index, GraphQLController],
    plugins=[DebugToolbarPlugin(toolbar_config)],
    debug=True,
)
