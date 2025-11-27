"""Tests for the SQLAlchemy panel."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from debug_toolbar.extras.advanced_alchemy.panel import (
    QueryTracker,
    SQLAlchemyPanel,
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
