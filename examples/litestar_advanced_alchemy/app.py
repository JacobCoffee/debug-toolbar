"""Litestar + Advanced-Alchemy application with debug toolbar.

This example demonstrates using debug-toolbar with Advanced-Alchemy
for SQLAlchemy integration and query tracking.

Run with: litestar --app examples.litestar_advanced_alchemy.app:app run --reload
"""

from __future__ import annotations

import logging
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
from litestar.params import Parameter

from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

from .models import Post, User

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

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
    <p>This example demonstrates SQL query tracking with the SQLAlchemy panel.</p>
    <h2>Navigation</h2>
    <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/users">Users List</a></li>
        <li><a href="/posts">Posts List</a></li>
    </ul>
    <h2>API Endpoints</h2>
    <ul>
        <li><a href="/api/users">GET /api/users</a> - List users (JSON)</li>
        <li><a href="/api/posts">GET /api/posts</a> - List posts (JSON)</li>
        <li>POST /api/users - Create user</li>
        <li>POST /api/posts - Create post</li>
        <li>DELETE /api/users/{id} - Delete user</li>
    </ul>
    <p>Check the debug toolbar's SQLAlchemy panel to see query statistics!</p>
</body>
</html>"""


@get("/users", media_type=MediaType.HTML)
async def users_page(user_repo: UserRepository) -> str:
    """Users HTML page."""
    logger.info("Users page accessed")
    users = await user_repo.list(LimitOffset(limit=100, offset=0))

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
    posts = await post_repo.list(LimitOffset(limit=100, offset=0))

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


@post("/api/users")
async def create_user(user_repo: UserRepository, data: dict) -> dict:
    """Create a new user."""
    logger.info("Creating user: %s", data.get("name"))
    user = await user_repo.add(User(name=data["name"], email=data["email"]))
    await user_repo.session.commit()
    return {"id": str(user.id), "name": user.name, "email": user.email}


@delete("/api/users/{user_id:uuid}")
async def delete_user(user_repo: UserRepository, user_id: UUID) -> None:
    """Delete a user."""
    logger.info("Deleting user: %s", user_id)
    await user_repo.delete(user_id)
    await user_repo.session.commit()


@get("/api/posts")
async def list_posts(
    post_repo: PostRepository,
    limit: Annotated[int, Parameter(ge=1, le=100)] = 10,
    offset: Annotated[int, Parameter(ge=0)] = 0,
) -> list[dict]:
    """List all posts."""
    logger.info("Listing posts with limit=%d, offset=%d", limit, offset)
    posts = await post_repo.list(LimitOffset(limit=limit, offset=offset))
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
    await post_repo.session.commit()
    return {"id": str(post.id), "title": post.title}


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
    extra_panels=["debug_toolbar.extras.advanced_alchemy.SQLAlchemyPanel"],
)

app = Litestar(
    route_handlers=[
        index,
        users_page,
        posts_page,
        list_users,
        create_user,
        delete_user,
        list_posts,
        create_post,
    ],
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        DebugToolbarPlugin(toolbar_config),
    ],
    dependencies={
        "user_repo": Provide(provide_user_repo),
        "post_repo": Provide(provide_post_repo),
    },
    debug=True,
)
