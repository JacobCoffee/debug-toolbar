# Advanced-Alchemy Skill

Quick reference for Advanced-Alchemy patterns in this project.

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="advanced-alchemy")
# Returns: /litestar-org/advanced-alchemy

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/advanced-alchemy",
    topic="repository",
    mode="code"
)
```

## Project-Specific Patterns

### SQL Panel Implementation

Location: `src/debug_toolbar/extras/advanced_alchemy/panel.py`

The Advanced-Alchemy panel tracks SQL queries, execution time, and N+1 detection.

```python
"""SQLAlchemy/Advanced-Alchemy panel pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class SQLAlchemyPanel(Panel):
    """Panel for SQLAlchemy query monitoring."""

    panel_id: ClassVar[str] = "SQLAlchemyPanel"
    title: ClassVar[str] = "SQL"
    template: ClassVar[str] = "panels/sql.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate SQL statistics."""
        return {
            "queries": [],
            "query_count": 0,
            "total_time": 0.0,
        }
```

### Event Listener Pattern

```python
"""SQLAlchemy event listener pattern."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.engine import Engine


def setup_query_logging(engine: Engine) -> None:
    """Set up query logging events."""

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Record query start
        pass

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Record query end and duration
        pass
```

## Testing Patterns

### Database Testing

```python
"""Database testing pattern."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async test session."""
    async with AsyncSession(async_engine) as session:
        yield session
```

### N+1 Detection Testing

```python
"""N+1 detection testing pattern."""

from __future__ import annotations

import pytest


class TestNPlusOneDetection:
    """Tests for N+1 query detection."""

    @pytest.mark.asyncio
    async def test_detects_n_plus_one(self) -> None:
        """Should detect N+1 query patterns."""
        # Setup: Create parent with children
        # Act: Access children in loop
        # Assert: N+1 warning recorded
```

## Related Files

- `src/debug_toolbar/extras/advanced_alchemy/__init__.py`
- `src/debug_toolbar/extras/advanced_alchemy/panel.py`
- `tests/unit/test_sqlalchemy_panel.py`
- `examples/litestar_advanced_alchemy/`

## Dependencies

This skill requires optional dependencies:

```bash
uv sync --extra advanced-alchemy
```

Or in pyproject.toml:

```toml
[project.optional-dependencies]
advanced-alchemy = [
    "advanced-alchemy>=0.10.0",
    "aiosqlite>=0.19.0",
    "sqlalchemy>=2.0.0",
]
```
