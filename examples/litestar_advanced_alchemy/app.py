"""Litestar + Advanced-Alchemy application with debug toolbar.

This example demonstrates using debug-toolbar with Advanced-Alchemy
for SQLAlchemy integration and query tracking.

UI Features:
- Toolbar position: Click the arrow buttons to move the toolbar (left/right/top/bottom)
- Request history: Visit /_debug_toolbar/ to see all recorded requests
- Panel details: Click panel buttons to expand and view detailed data

Run with: litestar --app examples.litestar_advanced_alchemy.app:app run --reload
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from advanced_alchemy.extensions.litestar import (
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
    async_autocommit_before_send_handler,
)
from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from litestar import Litestar, MediaType, delete, get, post
from litestar.di import Provide
from litestar.enums import RequestEncodingType
from litestar.params import Body, Parameter

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

from .models import Post, User

if TYPE_CHECKING:
    from litestar import Request, Response
    from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class UserRepository(SQLAlchemyAsyncRepository[User]):
    """User repository."""

    model_type = User


class PostRepository(SQLAlchemyAsyncRepository[Post]):
    """Post repository."""

    model_type = Post


async def provide_user_repo(db_session: AsyncSession) -> UserRepository:
    """Provide user repository."""
    return UserRepository(session=db_session)


async def provide_post_repo(db_session: AsyncSession) -> PostRepository:
    """Provide post repository."""
    return PostRepository(session=db_session)


@get("/", media_type=MediaType.HTML)
async def index() -> str:
    """Home page."""
    logger.info("Home page accessed")
    return """<!DOCTYPE html>
<html>
<head><title>Litestar + Advanced-Alchemy Debug Toolbar</title></head>
<body>
    <h1>Litestar + Advanced-Alchemy Debug Toolbar</h1>
    <p>This example demonstrates SQL query tracking with the SQLAlchemy panel and memory profiling with the Memory panel.</p>
    <h2>Navigation</h2>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/users">Users List</a></li>
        <li><a href="/posts">Posts List</a></li>
        <li><a href="/async-demo">Async Profiler Demo</a></li>
    </ul>
    <h2>API Endpoints</h2>
    <ul>
        <li><a href="/api/users">GET /api/users</a> - List users (JSON)</li>
        <li><a href="/api/posts">GET /api/posts</a> - List posts (JSON)</li>
        <li>POST /api/users - Create user</li>
        <li>POST /api/posts - Create post</li>
        <li>DELETE /api/users/{id} - Delete user</li>
    </ul>
    <h2>Async Profiler Demo</h2>
    <p style="background: rgba(78, 205, 196, 0.15); padding: 10px; border: 1px solid #4ecdc4; border-radius: 6px;">
        <a href="/async-demo"><strong>View Async Demo</strong></a> -
        This page creates concurrent async tasks to demonstrate the Async Profiler Panel!
    </p>
    <h2>N+1 Query Demo</h2>
    <p style="background: rgba(239, 68, 68, 0.15); padding: 10px; border: 1px solid #ef4444; border-radius: 6px;">
        <a href="/api/users-with-posts-bad"><strong>View N+1 Demo</strong></a> -
        This page deliberately triggers N+1 queries. Create a few users first, then visit to see the detection!
    </p>
    <p>Check the debug toolbar's SQLAlchemy panel to see query statistics and Memory panel for allocation tracking!</p>
    <p><strong>Note:</strong> The Alerts Panel will automatically warn you about N+1 queries and other issues!</p>
    <h2>Profiling & Flame Graphs</h2>
    <p>The Profiling Panel generates interactive flame graph visualizations:</p>
    <ul>
        <li>Automatically generated for each profiled request (when enabled)</li>
        <li>Visualize performance bottlenecks and call stacks</li>
        <li>Access via: <code>/_debug_toolbar/api/flamegraph/{request_id}</code></li>
        <li>Download as .speedscope.json and view at <a href="https://www.speedscope.app/" target="_blank">speedscope.app</a></li>
    </ul>
    <h2>Available Panels</h2>
    <ul>
        <li><strong>SQLAlchemy Panel</strong> - Query tracking with N+1 detection</li>
        <li><strong>Headers Panel</strong> - HTTP header inspection</li>
        <li><strong>Settings Panel</strong> - Configuration viewer</li>
        <li><strong>Profiling Panel</strong> - Request profiling with flame graphs</li>
        <li><strong>Alerts Panel</strong> - Proactive issue detection</li>
        <li><strong>Memory Panel</strong> - Memory allocation tracking</li>
        <li><strong>Async Profiler Panel</strong> - Async task tracking, blocking call detection</li>
        <li><strong>GraphQL Panel</strong> - Strawberry GraphQL operations with N+1 detection</li>
    </ul>
    <h2>Toolbar Controls</h2>
    <ul>
        <li>Use arrow buttons (&lt; &gt; ^ v) to move the toolbar to different positions</li>
        <li><a href="/_debug_toolbar/">View Request History</a></li>
    </ul>
</body>
</html>"""


@get("/users", media_type=MediaType.HTML)
async def users_page(user_repo: UserRepository) -> str:
    """Users HTML page."""
    logger.info("Users page accessed")
    users = await user_repo.list(LimitOffset(limit=100, offset=0), load=[User.posts])

    rows = "".join(
        f"<tr><td>{u.id}</td><td>{u.name}</td><td>{u.email}</td><td>{len(u.posts)} posts</td></tr>" for u in users
    )

    return f"""<!DOCTYPE html>
<html>
<head><title>Users</title></head>
<body>
    <h1>Users</h1>
    <table border="1">
        <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Posts</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="4">No users yet</td></tr>'}</tbody>
    </table>
    <h2>Create User</h2>
    <form action="/api/users" method="post">
        <input name="name" placeholder="Name" required>
        <input name="email" placeholder="Email" type="email" required>
        <button type="submit">Create</button>
    </form>
    <a href="/">Back to Home</a>
</body>
</html>"""


@get("/posts", media_type=MediaType.HTML)
async def posts_page(post_repo: PostRepository) -> str:
    """Posts HTML page."""
    logger.info("Posts page accessed")
    posts = await post_repo.list(LimitOffset(limit=100, offset=0), load=[Post.author])

    rows = "".join(
        f"<tr><td>{p.id}</td><td>{p.title}</td><td>{p.author.name if p.author else 'N/A'}</td>"
        f"<td>{p.published_at or 'Draft'}</td></tr>"
        for p in posts
    )

    return f"""<!DOCTYPE html>
<html>
<head><title>Posts</title></head>
<body>
    <h1>Posts</h1>
    <table border="1">
        <thead><tr><th>ID</th><th>Title</th><th>Author</th><th>Published</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="4">No posts yet</td></tr>'}</tbody>
    </table>
    <a href="/">Back to Home</a>
</body>
</html>"""


@get("/api/users")
async def list_users(
    user_repo: UserRepository,
    limit: Annotated[int, Parameter(ge=1, le=100)] = 10,
    offset: Annotated[int, Parameter(ge=0)] = 0,
) -> list[dict]:
    """List all users."""
    logger.info("Listing users with limit=%d, offset=%d", limit, offset)
    users = await user_repo.list(LimitOffset(limit=limit, offset=offset))
    return [{"id": str(u.id), "name": u.name, "email": u.email} for u in users]


@get("/api/users-with-posts-bad", media_type=MediaType.HTML)
async def list_users_with_posts_n_plus_one(
    user_repo: UserRepository,
    post_repo: PostRepository,
) -> str:
    """Deliberately cause N+1 query problem for demo purposes.

    This endpoint fetches users first, then loops through each user to fetch their posts.
    This is a classic N+1 pattern - 1 query for users + N queries for each user's posts.
    """
    logger.warning("N+1 DEMO: This endpoint deliberately causes N+1 queries!")

    users = await user_repo.list(LimitOffset(limit=10, offset=0))

    # ANTI-PATTERN DEMO: The loop below fetches ALL posts for EVERY user iteration,
    # creating repeated identical queries from the same code location. This is
    # intentionally inefficient to demonstrate N+1 detection. In production,
    # use eager loading (joinedload/selectinload) or batch fetching instead.
    results = []
    for user in users:
        posts = await post_repo.list(LimitOffset(limit=100, offset=0))
        user_posts = [p for p in posts if p.author_id == user.id]
        results.append(
            {
                "user": user,
                "posts": user_posts,
            }
        )

    rows = ""
    for r in results:
        user = r["user"]
        post_count = len(r["posts"])
        rows += f"<tr><td>{user.id}</td><td>{user.name}</td><td>{user.email}</td><td>{post_count}</td></tr>"

    return f"""<!DOCTYPE html>
<html>
<head>
<title>Users (N+1 Demo)</title>
<style>
/* Dark theme (default) */
body {{ background: #1a1a2e; color: #eee; font-family: system-ui, sans-serif; padding: 20px; }}
h1 {{ color: #f5a623; }}
.warning {{ background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.5);
    border-left: 4px solid #eab308; padding: 12px 16px; margin-bottom: 20px; border-radius: 6px; color: #fbbf24; }}
.warning strong {{ color: #fcd34d; }}
table {{ border-collapse: collapse; background: #16213e; }}
th, td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; background: #16213e; color: #e2e8f0; }}
th {{ background: #1e3a5f; color: #93c5fd; }}
a {{ color: #60a5fa; }}
a:hover {{ color: #93c5fd; }}

/* Light theme */
@media (prefers-color-scheme: light) {{
    body {{ background: #f8fafc; color: #1e293b; }}
    h1 {{ color: #b45309; }}
    .warning {{ background: #fef3c7; border: 1px solid #f59e0b;
        border-left: 4px solid #d97706; color: #92400e; }}
    .warning strong {{ color: #78350f; }}
    table {{ background: #fff; }}
    th, td {{ border: 1px solid #e2e8f0; background: #fff; color: #1e293b; }}
    th {{ background: #f1f5f9; color: #1e40af; }}
    a {{ color: #2563eb; }}
    a:hover {{ color: #1d4ed8; }}
}}
</style>
</head>
<body>
    <h1>Users with Posts (N+1 Query Demo)</h1>
    <div class="warning">
        <strong>Warning:</strong> This page deliberately triggers N+1 queries for demonstration!
        <br>Check the SQL panel in the debug toolbar to see the N+1 detection in action.
        <br>Also check the <strong>Alerts Panel</strong> for automatic warnings about the N+1 query pattern!
    </div>
    <table>
        <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Post Count</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="4">No users yet. Create some users first!</td></tr>'}</tbody>
    </table>
    <p><a href="/users">View users (efficient query)</a></p>
    <a href="/">Back to Home</a>
</body>
</html>"""


@post("/api/users", media_type=MediaType.HTML)
async def create_user(
    user_repo: UserRepository,
    data: Annotated[dict, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> str:
    """Create a new user from form submission."""
    logger.info("Creating user: %s", data.get("name"))
    user = await user_repo.add(User(name=data["name"], email=data["email"]))
    return f"""<!DOCTYPE html>
<html>
<head><title>User Created</title></head>
<body>
    <h1>User Created</h1>
    <p>Created user: {user.name} ({user.email})</p>
    <a href="/users">Back to Users</a>
</body>
</html>"""


@delete("/api/users/{user_id:uuid}")
async def delete_user(user_repo: UserRepository, user_id: UUID) -> None:
    """Delete a user."""
    logger.info("Deleting user: %s", user_id)
    await user_repo.delete(user_id)


@get("/api/posts")
async def list_posts(
    post_repo: PostRepository,
    limit: Annotated[int, Parameter(ge=1, le=100)] = 10,
    offset: Annotated[int, Parameter(ge=0)] = 0,
) -> list[dict]:
    """List all posts."""
    logger.info("Listing posts with limit=%d, offset=%d", limit, offset)
    posts = await post_repo.list(LimitOffset(limit=limit, offset=offset), load=[Post.author])
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "author": p.author.name if p.author else None,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]


@post("/api/posts")
async def create_post(
    post_repo: PostRepository,
    user_repo: UserRepository,
    data: dict,
) -> dict:
    """Create a new post."""
    logger.info("Creating post: %s", data.get("title"))
    author_id = UUID(data["author_id"])
    await user_repo.get(author_id)
    post = await post_repo.add(Post(title=data["title"], content=data["content"], author_id=author_id))
    return {"id": str(post.id), "title": post.title}


# ruff: noqa: ASYNC251
@get("/async-demo", media_type=MediaType.HTML)
async def async_demo() -> str:
    """Demonstrate the Async Profiler Panel with concurrent tasks.

    This endpoint creates multiple async tasks to showcase:
    - Task tracking and timing
    - Concurrent execution visualization
    - Blocking call detection (intentional time.sleep)
    """
    logger.info("Async demo page accessed")

    async def fast_task(task_id: int) -> int:
        """A fast async task."""
        await asyncio.sleep(0.05)
        return task_id * 2

    async def slow_task(task_id: int) -> int:
        """A slower async task."""
        await asyncio.sleep(0.15)
        return task_id * 10

    async def blocking_task() -> str:
        """A task with blocking I/O (bad practice demo)."""
        time.sleep(0.1)  # Intentional blocking call for demo
        return "blocked"

    # Create concurrent tasks
    tasks = [
        asyncio.create_task(fast_task(1), name="fast_task_1"),
        asyncio.create_task(fast_task(2), name="fast_task_2"),
        asyncio.create_task(slow_task(3), name="slow_task_1"),
        asyncio.create_task(fast_task(4), name="fast_task_3"),
        asyncio.create_task(blocking_task(), name="blocking_task"),
    ]

    results = await asyncio.gather(*tasks)

    return f"""<!DOCTYPE html>
<html>
<head>
<title>Async Profiler Demo</title>
<style>
/* Dark theme (default) */
body {{ background: #1a1a2e; color: #eee; font-family: system-ui, sans-serif; padding: 20px; }}
h1 {{ color: #4ecdc4; }}
h2 {{ color: #93c5fd; }}
.info {{ background: rgba(78, 205, 196, 0.15); border: 1px solid rgba(78, 205, 196, 0.5);
    padding: 12px 16px; margin-bottom: 20px; border-radius: 6px; color: #4ecdc4; }}
code {{ background: #16213e; padding: 2px 6px; border-radius: 4px; color: #fbbf24; }}
a {{ color: #60a5fa; }}
a:hover {{ color: #93c5fd; }}
ul {{ line-height: 1.8; }}

/* Light theme */
@media (prefers-color-scheme: light) {{
    body {{ background: #f8fafc; color: #1e293b; }}
    h1 {{ color: #0d9488; }}
    h2 {{ color: #1e40af; }}
    .info {{ background: rgba(13, 148, 136, 0.1); border-color: #0d9488; color: #0f766e; }}
    code {{ background: #e2e8f0; color: #92400e; }}
    a {{ color: #2563eb; }}
    a:hover {{ color: #1d4ed8; }}
}}
</style>
</head>
<body>
    <h1>Async Profiler Demo</h1>
    <div class="info">
        <strong>Check the Async panel in the debug toolbar!</strong><br>
        This page created {len(tasks)} concurrent tasks.
    </div>
    <h2>What happened:</h2>
    <ul>
        <li>Created 3x <code>fast_task</code> (50ms each)</li>
        <li>Created 1x <code>slow_task</code> (150ms)</li>
        <li>Created 1x <code>blocking_task</code> with <code>time.sleep()</code> (bad practice!)</li>
    </ul>
    <h2>Results:</h2>
    <ul>
        <li>fast_task_1: {results[0]}</li>
        <li>fast_task_2: {results[1]}</li>
        <li>slow_task_1: {results[2]}</li>
        <li>fast_task_3: {results[3]}</li>
        <li>blocking_task: {results[4]}</li>
    </ul>
    <h2>In the Async Panel you should see:</h2>
    <ul>
        <li><strong>5 tasks</strong> tracked with their durations</li>
        <li><strong>Timeline</strong> showing concurrent execution</li>
        <li><strong>Max concurrent</strong> tasks running at once</li>
    </ul>
    <p><a href="/">Back to Home</a></p>
</body>
</html>"""


db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///./example.db",
    before_send_handler=async_autocommit_before_send_handler,
    create_all=True,
)

toolbar_config = LitestarDebugToolbarConfig(
    enabled=True,
    exclude_paths=["/_debug_toolbar", "/favicon.ico"],
    show_on_errors=True,
    max_request_history=100,
    extra_panels=[
        "debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel",
        "debug_toolbar.core.panels.headers.HeadersPanel",
        "debug_toolbar.core.panels.settings.SettingsPanel",
        "debug_toolbar.core.panels.profiling.ProfilingPanel",
        "debug_toolbar.core.panels.alerts.AlertsPanel",
        "debug_toolbar.core.panels.memory.MemoryPanel",
        "debug_toolbar.core.panels.async_profiler.AsyncProfilerPanel",
    ],
)


async def on_startup(app: Litestar) -> None:
    """Store the database engine and seed sample data."""
    logger.info("Application starting up...")
    app.state.db_engine = db_config.get_engine()
    await seed_sample_data()


async def on_shutdown(app: Litestar) -> None:
    """Clean up resources on shutdown."""
    logger.info("Application shutting down...")


async def before_request_handler(request: "Request") -> None:
    """Log before each request."""
    logger.debug("Before request: %s %s", request.method, request.url.path)


async def after_request_handler(response: "Response") -> "Response":
    """Add custom header after each request."""
    response.headers["X-Debug-Toolbar"] = "enabled"
    return response


async def seed_sample_data() -> None:
    """Seed sample users and posts for demo purposes."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with db_config.get_engine().begin() as conn:
        session = AsyncSession(bind=conn)

        user_result = await session.execute(select(User).limit(1))
        post_result = await session.execute(select(Post).limit(1))
        if user_result.scalar_one_or_none() is not None and post_result.scalar_one_or_none() is not None:
            return

        users = [
            User(name="Alice Johnson", email="alice@example.com"),
            User(name="Bob Smith", email="bob@example.com"),
            User(name="Charlie Brown", email="charlie@example.com"),
            User(name="Diana Ross", email="diana@example.com"),
            User(name="Eve Wilson", email="eve@example.com"),
        ]
        session.add_all(users)
        await session.flush()

        posts = [
            Post(title="Getting Started with Litestar", content="Litestar is awesome!", author_id=users[0].id),
            Post(title="Debug Toolbar Tips", content="Use the SQL panel to find N+1 queries.", author_id=users[0].id),
            Post(title="Python Best Practices", content="Always use type hints.", author_id=users[1].id),
            Post(title="Async Programming", content="async/await makes code clean.", author_id=users[1].id),
            Post(title="SQLAlchemy 2.0", content="The new style is much better.", author_id=users[2].id),
            Post(title="Testing Strategies", content="Test your N+1 queries!", author_id=users[3].id),
            Post(title="Performance Tips", content="Eager loading prevents N+1.", author_id=users[4].id),
        ]
        session.add_all(posts)
        await session.commit()
        logger.info("Seeded %d users and %d posts", len(users), len(posts))


app = Litestar(
    route_handlers=[
        index,
        users_page,
        posts_page,
        list_users,
        list_users_with_posts_n_plus_one,
        create_user,
        delete_user,
        list_posts,
        create_post,
        async_demo,
    ],
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        DebugToolbarPlugin(toolbar_config),
    ],
    dependencies={
        "user_repo": Provide(provide_user_repo),
        "post_repo": Provide(provide_post_repo),
    },
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    before_request=before_request_handler,
    after_request=after_request_handler,
    debug=True,
)
