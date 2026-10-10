"""FastAPI application with debug toolbar example.

This example demonstrates the debug toolbar integration with FastAPI,
showcasing the dependency injection panel with various dependency patterns.

Run with:
    uvicorn examples.fastapi_basic.app:app --reload

Then visit:
    http://localhost:8000/
    http://localhost:8000/users/123
    http://localhost:8000/items?skip=10&limit=20
    http://localhost:8000/settings
    http://localhost:8000/_debug_toolbar/  (request history)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse

from debug_toolbar.fastapi import FastAPIDebugToolbarConfig, setup_debug_toolbar

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_db():
    """Get database session.

    This is a generator dependency that yields a database connection.
    The cleanup code after yield runs after the request completes.
    """
    db = {
        "users": {
            123: {"id": 123, "username": "alice", "email": "alice@example.com"},
            456: {"id": 456, "username": "bob", "email": "bob@example.com"},
        },
        "items": [
            {"id": 1, "name": "Widget"},
            {"id": 2, "name": "Gadget"},
            {"id": 3, "name": "Doohickey"},
        ],
    }
    try:
        yield db
    finally:
        pass


async def get_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Extract and validate authentication token."""
    if not authorization:
        return "anonymous"
    return authorization


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    db: Annotated[dict, Depends(get_db)],
) -> dict:
    """Get current authenticated user.

    Demonstrates nested dependencies:
    - Depends on get_token (authentication)
    - Depends on get_db (data access)
    """
    return list(db["users"].values())[0]


class CommonQueryParams:
    """Common pagination and search parameters.

    This is a class-based dependency. FastAPI will instantiate it
    and inject the query parameters.
    """

    def __init__(
        self,
        q: str | None = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
    ):
        self.q = q
        self.skip = skip
        self.limit = limit


_settings_cache: dict | None = None


def get_settings() -> dict:
    """Get application settings.

    This dependency uses manual caching to demonstrate cache behavior.
    """
    global _settings_cache

    if _settings_cache is None:
        _settings_cache = {
            "app_name": "Debug Toolbar Example",
            "version": "1.0.0",
            "debug": True,
        }

    return _settings_cache


app = FastAPI(
    title="Debug Toolbar Example",
    description="Example FastAPI app with debug toolbar",
)

config = FastAPIDebugToolbarConfig(
    enabled=True,
    track_dependency_injection=True,
    exclude_paths=[
        "/_debug_toolbar",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)
setup_debug_toolbar(app, config)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """Home page with simple HTML."""
    return f"""<!DOCTYPE html>
<html>
<head><title>FastAPI Debug Toolbar Example</title></head>
<body>
    <h1>FastAPI Debug Toolbar Example</h1>
    <p>Check the debug toolbar at the bottom of the page!</p>
    <p>Current time: {datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
    <ul>
        <li><a href="/users/123">View User 123</a> - Shows auth + DB dependencies</li>
        <li><a href="/items?skip=10&limit=20">List Items</a> - Shows pagination dependency</li>
        <li><a href="/settings">Settings</a> - Shows cached dependency</li>
    </ul>
    <p><a href="/_debug_toolbar/">View Request History</a></p>
</body>
</html>"""


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: dict = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get user by ID - demonstrates auth + database dependencies.

    Dependencies:
    - get_db: Database session (generator with yield)
    - get_current_user: Current authenticated user (depends on get_db)
    """
    if user_id not in db["users"]:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user": db["users"][user_id],
        "requested_by": current_user["username"],
    }


@app.get("/items")
async def list_items(
    commons: CommonQueryParams = Depends(),
    db: dict = Depends(get_db),
) -> dict:
    """List items with pagination - demonstrates class-based dependency.

    Dependencies:
    - CommonQueryParams: Class-based dependency with q, skip, limit
    - get_db: Database session
    """
    items = db["items"]

    if commons.q:
        items = [item for item in items if commons.q.lower() in item["name"].lower()]

    paginated = items[commons.skip : commons.skip + commons.limit]

    return {
        "items": paginated,
        "total": len(items),
        "skip": commons.skip,
        "limit": commons.limit,
    }


@app.get("/settings")
async def get_app_settings(settings: dict = Depends(get_settings)) -> dict:
    """Get application settings - demonstrates cached dependency.

    Dependencies:
    - get_settings: Cached application settings (uses default caching)
    """
    return {"settings": settings}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
