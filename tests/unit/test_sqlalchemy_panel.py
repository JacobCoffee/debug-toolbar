"""Tests for the SQLAlchemy panel."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from debug_toolbar.extras.advanced_alchemy.panel import (
    QueryTracker,
    SQLAlchemyPanel,
    SQLNormalizer,
    _tracker,
    track_queries,
)

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


@pytest.fixture
def query_tracker() -> QueryTracker:
    """Create a fresh query tracker."""
    return QueryTracker()


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


@pytest.fixture
def sqlalchemy_panel(mock_toolbar: MagicMock) -> SQLAlchemyPanel:
    """Create a SQLAlchemy panel instance."""
    return SQLAlchemyPanel(mock_toolbar, engine=None, slow_threshold_ms=100.0)


class TestQueryTracker:
    """Tests for QueryTracker."""

    def test_initial_state(self, query_tracker: QueryTracker) -> None:
        """Test initial state is disabled."""
        assert not query_tracker.enabled
        assert query_tracker.queries == []

    def test_start_enables_tracking(self, query_tracker: QueryTracker) -> None:
        """Test start enables tracking."""
        query_tracker.start()
        assert query_tracker.enabled
        assert query_tracker.queries == []

    def test_stop_disables_tracking(self, query_tracker: QueryTracker) -> None:
        """Test stop disables tracking."""
        query_tracker.start()
        query_tracker.stop()
        assert not query_tracker.enabled

    def test_before_cursor_execute_when_disabled(self, query_tracker: QueryTracker) -> None:
        """Test before_cursor_execute does nothing when disabled."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        query_tracker.before_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        assert len(query_tracker._query_start_times) == 0

    def test_before_cursor_execute_when_enabled(self, query_tracker: QueryTracker) -> None:
        """Test before_cursor_execute records start time."""
        query_tracker.start()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        query_tracker.before_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        assert len(query_tracker._query_start_times) == 1

    def test_after_cursor_execute_when_disabled(self, query_tracker: QueryTracker) -> None:
        """Test after_cursor_execute does nothing when disabled."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        query_tracker.after_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        assert len(query_tracker.queries) == 0

    def test_after_cursor_execute_records_query(self, query_tracker: QueryTracker) -> None:
        """Test after_cursor_execute records query details."""
        query_tracker.start()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        query_tracker.before_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        query_tracker.after_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        assert len(query_tracker.queries) == 1
        assert query_tracker.queries[0]["sql"] == "SELECT 1"
        assert "duration" in query_tracker.queries[0]
        assert "duration_ms" in query_tracker.queries[0]

    def test_after_cursor_execute_with_dict_params(self, query_tracker: QueryTracker) -> None:
        """Test parameter formatting with dict params."""
        query_tracker.start()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        params = {"id": 1, "name": "test"}
        query_tracker.before_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users WHERE id = :id", params, None, False
        )
        query_tracker.after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users WHERE id = :id", params, None, False
        )
        assert len(query_tracker.queries) == 1
        assert "id" in query_tracker.queries[0]["parameters"]

    def test_after_cursor_execute_with_tuple_params(self, query_tracker: QueryTracker) -> None:
        """Test parameter formatting with tuple params."""
        query_tracker.start()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        params = (1, "test")
        query_tracker.before_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users WHERE id = ?", params, None, False
        )
        query_tracker.after_cursor_execute(
            mock_conn, mock_cursor, "SELECT * FROM users WHERE id = ?", params, None, False
        )
        assert len(query_tracker.queries) == 1
        assert "1" in query_tracker.queries[0]["parameters"]

    def test_format_parameters_none(self, query_tracker: QueryTracker) -> None:
        """Test _format_parameters with None."""
        result = query_tracker._format_parameters(None)
        assert result == ""

    def test_truncate_long_string(self, query_tracker: QueryTracker) -> None:
        """Test _truncate with long string."""
        long_string = "a" * 200
        result = query_tracker._truncate(long_string, max_length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_truncate_long_bytes(self, query_tracker: QueryTracker) -> None:
        """Test _truncate with long bytes."""
        long_bytes = b"a" * 200
        result = query_tracker._truncate(long_bytes, max_length=100)
        assert len(result) == 103
        assert result.endswith(b"...")

    def test_truncate_short_value(self, query_tracker: QueryTracker) -> None:
        """Test _truncate with short value."""
        short_string = "hello"
        result = query_tracker._truncate(short_string, max_length=100)
        assert result == "hello"

    def test_truncate_non_string(self, query_tracker: QueryTracker) -> None:
        """Test _truncate with non-string value."""
        result = query_tracker._truncate(12345)
        assert result == 12345


class TestTrackQueries:
    """Tests for track_queries context manager."""

    def test_track_queries_without_engine(self) -> None:
        """Test track_queries without engine."""
        with track_queries() as tracker:
            assert tracker.enabled
        assert not tracker.enabled

    @patch("debug_toolbar.extras.advanced_alchemy.panel._setup_event_listeners")
    @patch("debug_toolbar.extras.advanced_alchemy.panel._remove_event_listeners")
    def test_track_queries_with_engine(self, mock_remove: MagicMock, mock_setup: MagicMock) -> None:
        """Test track_queries with engine."""
        mock_engine = MagicMock()
        with track_queries(mock_engine) as tracker:
            assert tracker.enabled
            mock_setup.assert_called_once_with(mock_engine)
        mock_remove.assert_called_once_with(mock_engine)


class TestSQLAlchemyPanel:
    """Tests for SQLAlchemyPanel."""

    def test_panel_attributes(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test panel class attributes."""
        assert SQLAlchemyPanel.panel_id == "SQLAlchemyPanel"
        assert SQLAlchemyPanel.title == "SQL"
        assert SQLAlchemyPanel.has_content is True

    def test_panel_initialization(self, mock_toolbar: MagicMock) -> None:
        """Test panel initialization."""
        panel = SQLAlchemyPanel(mock_toolbar, slow_threshold_ms=50.0)
        assert panel._slow_threshold_ms == 50.0
        assert panel._engine is None

    @patch("debug_toolbar.extras.advanced_alchemy.panel._setup_event_listeners")
    def test_panel_initialization_with_engine(self, mock_setup: MagicMock, mock_toolbar: MagicMock) -> None:
        """Test panel initialization with engine."""
        mock_engine = MagicMock()
        SQLAlchemyPanel(mock_toolbar, engine=mock_engine)
        mock_setup.assert_called_once_with(mock_engine)

    @pytest.mark.asyncio
    async def test_process_request(self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext) -> None:
        """Test process_request starts tracking."""
        _tracker.stop()  # Ensure clean state
        await sqlalchemy_panel.process_request(request_context)
        assert _tracker.enabled

    @pytest.mark.asyncio
    async def test_process_response(self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext) -> None:
        """Test process_response stops tracking."""
        _tracker.start()
        await sqlalchemy_panel.process_response(request_context)
        assert not _tracker.enabled

    @pytest.mark.asyncio
    async def test_generate_stats_empty(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats with no queries."""
        _tracker.start()
        _tracker.queries = []
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["query_count"] == 0
        assert stats["total_time"] == 0
        assert stats["duplicate_count"] == 0
        assert stats["slow_count"] == 0
        assert not stats["has_issues"]

    @pytest.mark.asyncio
    async def test_generate_stats_with_queries(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats with queries."""
        _tracker.start()
        _tracker.queries = [
            {"sql": "SELECT 1", "parameters": "", "duration": 0.001, "duration_ms": 1.0, "executemany": False},
            {"sql": "SELECT 2", "parameters": "", "duration": 0.002, "duration_ms": 2.0, "executemany": False},
        ]
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["query_count"] == 2
        assert stats["total_time"] == 0.003
        assert stats["total_time_ms"] == 3.0

    @pytest.mark.asyncio
    async def test_generate_stats_with_duplicates(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats detects duplicates."""
        _tracker.start()
        _tracker.queries = [
            {"sql": "SELECT 1", "parameters": "", "duration": 0.001, "duration_ms": 1.0, "executemany": False},
            {"sql": "SELECT 1", "parameters": "", "duration": 0.001, "duration_ms": 1.0, "executemany": False},
        ]
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["duplicate_count"] == 1
        assert "SELECT 1" in stats["duplicates"]
        assert stats["has_issues"]

    @pytest.mark.asyncio
    async def test_generate_stats_with_slow_queries(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats detects slow queries."""
        _tracker.start()
        _tracker.queries = [
            {"sql": "SELECT 1", "parameters": "", "duration": 0.150, "duration_ms": 150.0, "executemany": False},
        ]
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["slow_count"] == 1
        assert stats["has_issues"]
        assert stats["queries"][0]["is_slow"]

    def test_generate_server_timing_empty(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing with no stats."""
        result = sqlalchemy_panel.generate_server_timing(request_context)
        assert result == {}

    def test_generate_server_timing_with_stats(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_server_timing with stats."""
        request_context.store_panel_data("SQLAlchemyPanel", "total_time", 0.5)
        result = sqlalchemy_panel.generate_server_timing(request_context)
        assert result == {"sql": 0.5}

    def test_find_duplicates_none(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test _find_duplicates with no duplicates."""
        result = sqlalchemy_panel._find_duplicates(["SELECT 1", "SELECT 2"])
        assert result == set()

    def test_find_duplicates_found(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test _find_duplicates with duplicates."""
        result = sqlalchemy_panel._find_duplicates(["SELECT 1", "SELECT 1", "SELECT 2"])
        assert result == {"SELECT 1"}

    def test_get_nav_subtitle(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test get_nav_subtitle."""
        assert sqlalchemy_panel.get_nav_subtitle() == ""

    @pytest.mark.asyncio
    async def test_generate_stats_with_n_plus_one(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test generate_stats detects N+1 patterns."""
        _tracker.start()
        _tracker.queries = [
            {
                "sql": "SELECT * FROM users WHERE id = 1",
                "parameters": "",
                "duration": 0.001,
                "duration_ms": 1.0,
                "executemany": False,
                "pattern_hash": "abc123",
                "origin_key": "test.py:10:get_users",
                "stack": [],
            },
            {
                "sql": "SELECT * FROM users WHERE id = 2",
                "parameters": "",
                "duration": 0.001,
                "duration_ms": 1.0,
                "executemany": False,
                "pattern_hash": "abc123",
                "origin_key": "test.py:10:get_users",
                "stack": [],
            },
            {
                "sql": "SELECT * FROM users WHERE id = 3",
                "parameters": "",
                "duration": 0.001,
                "duration_ms": 1.0,
                "executemany": False,
                "pattern_hash": "abc123",
                "origin_key": "test.py:10:get_users",
                "stack": [],
            },
        ]
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["n_plus_one_count"] == 1
        assert len(stats["n_plus_one_groups"]) == 1
        assert stats["n_plus_one_groups"][0]["count"] == 3
        assert stats["has_issues"]
        for query in stats["queries"]:
            assert query["is_n_plus_one"]

    @pytest.mark.asyncio
    async def test_generate_stats_no_n_plus_one_different_origins(
        self, sqlalchemy_panel: SQLAlchemyPanel, request_context: RequestContext
    ) -> None:
        """Test that same pattern from different origins is not N+1."""
        _tracker.start()
        _tracker.queries = [
            {
                "sql": "SELECT * FROM users WHERE id = 1",
                "parameters": "",
                "duration": 0.001,
                "duration_ms": 1.0,
                "executemany": False,
                "pattern_hash": "abc123",
                "origin_key": "test.py:10:func_a",
                "stack": [],
            },
            {
                "sql": "SELECT * FROM users WHERE id = 2",
                "parameters": "",
                "duration": 0.001,
                "duration_ms": 1.0,
                "executemany": False,
                "pattern_hash": "abc123",
                "origin_key": "test.py:20:func_b",
                "stack": [],
            },
        ]
        stats = await sqlalchemy_panel.generate_stats(request_context)
        assert stats["n_plus_one_count"] == 0

    def test_detect_n_plus_one_threshold(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test N+1 detection respects threshold."""
        queries = [
            {"sql": "SELECT 1", "pattern_hash": "abc", "origin_key": "test:1:f"},
        ]
        result = sqlalchemy_panel._detect_n_plus_one(queries, threshold=2)
        assert len(result) == 0

        queries = [
            {"sql": "SELECT 1", "pattern_hash": "abc", "origin_key": "test:1:f"},
            {"sql": "SELECT 2", "pattern_hash": "abc", "origin_key": "test:1:f"},
        ]
        result = sqlalchemy_panel._detect_n_plus_one(queries, threshold=2)
        assert len(result) == 1

    def test_get_fix_suggestion_select_with_where(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test fix suggestion for SELECT with WHERE clause."""
        suggestion = sqlalchemy_panel._get_fix_suggestion("SELECT * FROM users WHERE id = ?", 5)
        assert "eager loading" in suggestion.lower() or "joinedload" in suggestion.lower()
        assert "5 times" in suggestion

    def test_get_fix_suggestion_generic_select(self, sqlalchemy_panel: SQLAlchemyPanel) -> None:
        """Test fix suggestion for generic SELECT."""
        suggestion = sqlalchemy_panel._get_fix_suggestion("SELECT * FROM users", 3)
        assert "3 times" in suggestion


class TestSQLNormalizer:
    """Tests for SQLNormalizer."""

    def test_normalize_string_literals(self) -> None:
        """Test normalization of string literals."""
        sql = "SELECT * FROM users WHERE name = 'John'"
        result = SQLNormalizer.normalize(sql)
        assert result == "SELECT * FROM users WHERE name = '?'"

    def test_normalize_numeric_literals(self) -> None:
        """Test normalization of numeric literals."""
        sql = "SELECT * FROM users WHERE id = 123"
        result = SQLNormalizer.normalize(sql)
        assert result == "SELECT * FROM users WHERE id = ?"

    def test_normalize_named_parameters(self) -> None:
        """Test normalization of named parameters."""
        sql = "SELECT * FROM users WHERE id = :user_id AND name = :name"
        result = SQLNormalizer.normalize(sql)
        assert result == "SELECT * FROM users WHERE id = :? AND name = :?"

    def test_normalize_whitespace(self) -> None:
        """Test normalization of whitespace."""
        sql = "SELECT  *   FROM   users   WHERE    id = 1"
        result = SQLNormalizer.normalize(sql)
        assert "  " not in result

    def test_normalize_complex_query(self) -> None:
        """Test normalization of complex query."""
        sql = """
            SELECT u.id, u.name
            FROM users u
            WHERE u.id = 42
            AND u.email = 'test@example.com'
            LIMIT 10
        """
        result = SQLNormalizer.normalize(sql)
        assert "42" not in result
        assert "test@example.com" not in result
        assert "?" in result

    def test_get_pattern_hash_same_pattern(self) -> None:
        """Test that same patterns get same hash."""
        sql1 = "SELECT * FROM users WHERE id = 1"
        sql2 = "SELECT * FROM users WHERE id = 2"
        hash1 = SQLNormalizer.get_pattern_hash(sql1)
        hash2 = SQLNormalizer.get_pattern_hash(sql2)
        assert hash1 == hash2

    def test_get_pattern_hash_different_patterns(self) -> None:
        """Test that different patterns get different hashes."""
        sql1 = "SELECT * FROM users WHERE id = 1"
        sql2 = "SELECT * FROM posts WHERE id = 1"
        hash1 = SQLNormalizer.get_pattern_hash(sql1)
        hash2 = SQLNormalizer.get_pattern_hash(sql2)
        assert hash1 != hash2

    def test_get_origin_key_with_stack(self) -> None:
        """Test get_origin_key with stack frames."""
        stack = [
            {"file": "/app/views.py", "line": 42, "function": "get_user", "code": ""},
        ]
        result = SQLNormalizer.get_origin_key(stack)
        assert "views.py" in result
        assert "42" in result
        assert "get_user" in result

    def test_get_origin_key_empty_stack(self) -> None:
        """Test get_origin_key with empty stack."""
        result = SQLNormalizer.get_origin_key([])
        assert result == "unknown"

    def test_capture_stack_filters_library_frames(self) -> None:
        """Test that capture_stack filters out library frames."""
        stack = SQLNormalizer.capture_stack()
        for frame in stack:
            assert "sqlalchemy" not in frame["file"]
            assert "debug_toolbar" not in frame["file"]


class TestQueryTrackerNPlusOne:
    """Tests for N+1 related QueryTracker functionality."""

    def test_tracker_captures_pattern_hash(self) -> None:
        """Test that tracker captures pattern hash."""
        tracker = QueryTracker()
        tracker._capture_stacks = False
        tracker.start()

        mock_conn = MagicMock()
        mock_conn.dialect.name = "postgresql"
        mock_cursor = MagicMock()

        tracker.before_cursor_execute(mock_conn, mock_cursor, "SELECT * FROM users WHERE id = 1", None, None, False)
        tracker.after_cursor_execute(mock_conn, mock_cursor, "SELECT * FROM users WHERE id = 1", None, None, False)

        assert len(tracker.queries) == 1
        assert "pattern_hash" in tracker.queries[0]
        assert "origin_key" in tracker.queries[0]

    def test_tracker_same_pattern_different_values(self) -> None:
        """Test that same pattern with different values get same hash."""
        tracker = QueryTracker()
        tracker._capture_stacks = False
        tracker.start()

        mock_conn = MagicMock()
        mock_conn.dialect.name = "postgresql"
        mock_cursor1 = MagicMock()
        mock_cursor2 = MagicMock()

        tracker.before_cursor_execute(mock_conn, mock_cursor1, "SELECT * FROM users WHERE id = 1", None, None, False)
        tracker.after_cursor_execute(mock_conn, mock_cursor1, "SELECT * FROM users WHERE id = 1", None, None, False)

        tracker.before_cursor_execute(mock_conn, mock_cursor2, "SELECT * FROM users WHERE id = 2", None, None, False)
        tracker.after_cursor_execute(mock_conn, mock_cursor2, "SELECT * FROM users WHERE id = 2", None, None, False)

        assert len(tracker.queries) == 2
        assert tracker.queries[0]["pattern_hash"] == tracker.queries[1]["pattern_hash"]

    def test_tracker_captures_stack_when_enabled(self) -> None:
        """Test that tracker captures stack when enabled."""
        tracker = QueryTracker()
        tracker.start()

        mock_conn = MagicMock()
        mock_conn.dialect.name = "postgresql"
        mock_cursor = MagicMock()

        tracker.before_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)
        tracker.after_cursor_execute(mock_conn, mock_cursor, "SELECT 1", None, None, False)

        assert len(tracker.queries) == 1
        assert "stack" in tracker.queries[0]
        assert isinstance(tracker.queries[0]["stack"], list)
