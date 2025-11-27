"""SQLAlchemy panel for tracking database queries."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import event, text

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext
    from sqlalchemy.ext.asyncio import AsyncEngine

    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


class ExplainExecutor:
    """Executes EXPLAIN queries for different database dialects."""

    DIALECT_EXPLAIN_PREFIX: ClassVar[dict[str, str]] = {
        "postgresql": "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)",
        "sqlite": "EXPLAIN QUERY PLAN",
        "mysql": "EXPLAIN",
        "mariadb": "EXPLAIN",
        "oracle": "EXPLAIN PLAN FOR",
        "mssql": "SET SHOWPLAN_TEXT ON;",
    }

    SUPPORTED_DIALECTS: ClassVar[set[str]] = {
        "postgresql",
        "sqlite",
        "mysql",
        "mariadb",
    }

    @classmethod
    def supports_explain(cls, dialect_name: str) -> bool:
        """Check if the dialect supports EXPLAIN."""
        return dialect_name.lower() in cls.SUPPORTED_DIALECTS

    @classmethod
    def get_explain_sql(cls, dialect_name: str, sql: str) -> str | None:
        """Generate EXPLAIN SQL for the given dialect."""
        dialect = dialect_name.lower()
        prefix = cls.DIALECT_EXPLAIN_PREFIX.get(dialect)
        if not prefix:
            return None
        return f"{prefix} {sql}"

    @classmethod
    async def execute_explain(
        cls,
        engine: AsyncEngine,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute EXPLAIN query and return results."""
        dialect_name = engine.dialect.name
        if not cls.supports_explain(dialect_name):
            return {"error": f"EXPLAIN not supported for dialect: {dialect_name}"}

        prepared_sql = cls._substitute_parameters(sql, parameters, dialect_name)
        explain_sql = cls.get_explain_sql(dialect_name, prepared_sql)
        if not explain_sql:
            return {"error": "Could not generate EXPLAIN SQL"}

        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(explain_sql))
                rows = result.fetchall()
                plan_lines = [str(row[0]) if len(row) == 1 else str(row) for row in rows]
                return {
                    "dialect": dialect_name,
                    "explain_sql": explain_sql,
                    "plan": "\n".join(plan_lines),
                    "raw_rows": [list(row) for row in rows],
                }
        except Exception as e:
            return {"error": str(e), "explain_sql": explain_sql}

    @classmethod
    def _substitute_parameters(
        cls,
        sql: str,
        parameters: dict[str, Any] | None,
        dialect_name: str,  # noqa: ARG003
    ) -> str:
        """Substitute parameter placeholders with actual values for EXPLAIN.

        This is needed because EXPLAIN requires valid SQL, but we want to show
        the query plan without actually needing the real parameter values.
        """
        if not parameters:
            return sql

        if "_positional" in parameters:
            values = parameters["_positional"]
            result = sql
            for val in values:
                result = result.replace("?", cls._format_value(val), 1)
            return result

        for key, val in parameters.items():
            placeholder = f":{key}"
            result = sql.replace(placeholder, cls._format_value(val))
            sql = result

        return sql

    @classmethod
    def _format_value(cls, value: Any) -> str:
        """Format a value for SQL substitution."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int | float):
            return str(value)
        if isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        return f"'{value}'"


class QueryTracker:
    """Tracks SQL queries executed during a request."""

    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self._query_start_times: dict[int, float] = {}
        self._enabled = False
        self._dialect_name: str = ""

    def start(self) -> None:
        """Start tracking queries."""
        self.queries = []
        self._query_start_times = {}
        self._enabled = True

    def stop(self) -> None:
        """Stop tracking queries."""
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if tracking is enabled."""
        return self._enabled

    def before_cursor_execute(
        self,
        conn: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None,
        context: ExecutionContext | None,
        executemany: bool,  # noqa: FBT001
    ) -> None:
        """Record query start time."""
        if not self._enabled:
            return
        self._query_start_times[id(cursor)] = time.perf_counter()
        self._dialect_name = conn.dialect.name

    def after_cursor_execute(
        self,
        conn: Connection,
        cursor: DBAPICursor,
        statement: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None,
        context: ExecutionContext | None,
        executemany: bool,  # noqa: FBT001
    ) -> None:
        """Record completed query."""
        if not self._enabled:
            return

        start_time = self._query_start_times.pop(id(cursor), None)
        duration = time.perf_counter() - start_time if start_time else 0.0

        query_hash = hashlib.md5(statement.encode(), usedforsecurity=False).hexdigest()[:12]
        dialect = conn.dialect.name

        self.queries.append(
            {
                "sql": statement,
                "parameters": self._format_parameters(parameters),
                "raw_parameters": self._serialize_parameters(parameters),
                "duration": duration,
                "duration_ms": duration * 1000,
                "executemany": executemany,
                "query_hash": query_hash,
                "dialect": dialect,
                "supports_explain": ExplainExecutor.supports_explain(dialect),
            }
        )

    def _serialize_parameters(self, parameters: tuple[Any, ...] | dict[str, Any] | None) -> dict[str, Any] | None:
        """Serialize parameters for EXPLAIN execution."""
        if parameters is None:
            return None
        if isinstance(parameters, dict):
            return {k: self._make_serializable(v) for k, v in parameters.items()}
        return {"_positional": [self._make_serializable(p) for p in parameters]}

    def _make_serializable(self, value: Any) -> Any:
        """Make a value JSON-serializable."""
        if isinstance(value, str | int | float | bool | type(None)):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    def _format_parameters(self, parameters: tuple[Any, ...] | dict[str, Any] | None) -> str:
        """Format parameters for display."""
        if parameters is None:
            return ""
        if isinstance(parameters, dict):
            return str({k: self._truncate(v) for k, v in parameters.items()})
        return str(tuple(self._truncate(p) for p in parameters))

    def _truncate(self, value: Any, max_length: int = 100) -> Any:
        """Truncate long string values."""
        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "..."
        if isinstance(value, bytes) and len(value) > max_length:
            return value[:max_length] + b"..."
        return value


_tracker = QueryTracker()
_global_listeners_attached = False


def _setup_event_listeners(engine: Engine) -> None:
    """Set up SQLAlchemy event listeners on an engine."""
    event.listen(engine, "before_cursor_execute", _tracker.before_cursor_execute)
    event.listen(engine, "after_cursor_execute", _tracker.after_cursor_execute)


def _setup_global_listeners() -> bool:
    """Set up global event listeners for all SQLAlchemy engines.

    Returns:
        True if listeners were attached, False otherwise.
    """
    global _global_listeners_attached  # noqa: PLW0603
    if _global_listeners_attached:
        return True

    try:
        from sqlalchemy.engine import Engine as SAEngine

        event.listen(SAEngine, "before_cursor_execute", _tracker.before_cursor_execute)
        event.listen(SAEngine, "after_cursor_execute", _tracker.after_cursor_execute)
        _global_listeners_attached = True
        return True
    except Exception:
        return False


def _remove_event_listeners(engine: Engine) -> None:
    """Remove SQLAlchemy event listeners from an engine."""
    event.remove(engine, "before_cursor_execute", _tracker.before_cursor_execute)
    event.remove(engine, "after_cursor_execute", _tracker.after_cursor_execute)


@contextmanager
def track_queries(engine: Engine | None = None) -> Generator[QueryTracker, None, None]:
    """Context manager to track queries for a specific engine.

    Args:
        engine: The SQLAlchemy engine to track. If None, uses global tracking.

    Yields:
        The QueryTracker instance.
    """
    if engine is not None:
        _setup_event_listeners(engine)

    _tracker.start()
    try:
        yield _tracker
    finally:
        _tracker.stop()
        if engine is not None:
            _remove_event_listeners(engine)


class SQLAlchemyPanel(Panel):
    """Panel displaying SQLAlchemy query information.

    Shows:
    - Number of queries executed
    - Total query time
    - Individual query details (SQL, parameters, timing)
    - Duplicate query detection
    - Slow query highlighting
    """

    panel_id: ClassVar[str] = "SQLAlchemyPanel"
    title: ClassVar[str] = "SQL"
    template: ClassVar[str] = "panels/sqlalchemy.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "SQL"

    __slots__ = ("_engine", "_listeners_attached", "_slow_threshold_ms")

    def __init__(
        self,
        toolbar: DebugToolbar,
        engine: Engine | None = None,
        slow_threshold_ms: float = 100.0,
    ) -> None:
        """Initialize the panel.

        Args:
            toolbar: The parent DebugToolbar instance.
            engine: Optional SQLAlchemy engine to track.
            slow_threshold_ms: Threshold in ms for marking queries as slow.
        """
        super().__init__(toolbar)
        self._engine = engine
        self._slow_threshold_ms = slow_threshold_ms
        self._listeners_attached = False

        if engine is not None:
            _setup_event_listeners(engine)
            self._listeners_attached = True

    async def process_request(self, context: RequestContext) -> None:
        """Start tracking queries."""
        if not self._listeners_attached:
            self._listeners_attached = _setup_global_listeners()
        _tracker.start()

    async def process_response(self, context: RequestContext) -> None:
        """Stop tracking queries."""
        _tracker.stop()

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate SQL statistics."""
        queries = list(_tracker.queries)

        total_time = sum(q["duration"] for q in queries)
        total_time_ms = total_time * 1000

        sql_statements = [q["sql"] for q in queries]
        duplicates = self._find_duplicates(sql_statements)

        slow_queries = [q for q in queries if q["duration_ms"] >= self._slow_threshold_ms]

        for query in queries:
            query["is_slow"] = query["duration_ms"] >= self._slow_threshold_ms
            query["is_duplicate"] = query["sql"] in duplicates

        return {
            "queries": queries,
            "query_count": len(queries),
            "total_time": total_time,
            "total_time_ms": total_time_ms,
            "duplicate_count": len(duplicates),
            "duplicates": list(duplicates),
            "slow_count": len(slow_queries),
            "slow_threshold_ms": self._slow_threshold_ms,
            "has_issues": len(duplicates) > 0 or len(slow_queries) > 0,
        }

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing data for SQL."""
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {"sql": stats.get("total_time", 0)}

    def _find_duplicates(self, statements: list[str]) -> set[str]:
        """Find duplicate SQL statements."""
        seen: dict[str, int] = {}
        for stmt in statements:
            seen[stmt] = seen.get(stmt, 0) + 1

        return {stmt for stmt, count in seen.items() if count > 1}

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle showing query count."""
        return ""
