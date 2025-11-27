"""Tests for the request context module."""

from __future__ import annotations

from debug_toolbar.core.context import (
    RequestContext,
    ensure_request_context,
    get_request_context,
    set_request_context,
)


class TestRequestContext:
    """Tests for RequestContext class."""

    def test_creates_unique_request_id(self) -> None:
        """Each context should have a unique request ID."""
        ctx1 = RequestContext()
        ctx2 = RequestContext()
        assert ctx1.request_id != ctx2.request_id

    def test_store_panel_data(self) -> None:
        """Should store panel data correctly."""
        ctx = RequestContext()
        ctx.store_panel_data("TestPanel", "key1", "value1")
        ctx.store_panel_data("TestPanel", "key2", 42)

        data = ctx.get_panel_data("TestPanel")
        assert data == {"key1": "value1", "key2": 42}

    def test_get_panel_data_empty(self) -> None:
        """Should return empty dict for missing panel."""
        ctx = RequestContext()
        assert ctx.get_panel_data("NonexistentPanel") == {}

    def test_record_timing(self) -> None:
        """Should record timing measurements."""
        ctx = RequestContext()
        ctx.record_timing("test_op", 0.123)

        assert ctx.get_timing("test_op") == 0.123
        assert ctx.get_timing("nonexistent") is None


class TestContextVars:
    """Tests for context variable management."""

    def test_get_set_context(self) -> None:
        """Should get and set context."""
        ctx = RequestContext()
        set_request_context(ctx)

        assert get_request_context() is ctx

        set_request_context(None)
        assert get_request_context() is None

    def test_ensure_context_creates_new(self) -> None:
        """Should create new context if none exists."""
        set_request_context(None)

        ctx = ensure_request_context()
        assert ctx is not None
        assert get_request_context() is ctx

        set_request_context(None)

    def test_ensure_context_returns_existing(self) -> None:
        """Should return existing context if present."""
        existing = RequestContext()
        set_request_context(existing)

        ctx = ensure_request_context()
        assert ctx is existing

        set_request_context(None)
