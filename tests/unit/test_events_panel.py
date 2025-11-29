"""Tests for the Events panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from debug_toolbar.core.context import RequestContext
from debug_toolbar.litestar.panels.events import (
    EventsPanel,
    _get_handler_info,
    _get_stack_frames,
    collect_events_metadata,
    record_hook_execution,
)

if TYPE_CHECKING:
    pass


def sample_handler() -> None:
    """A sample handler function for testing."""
    pass


async def async_sample_handler() -> None:
    """An async sample handler function for testing."""
    pass


class TestGetHandlerInfo:
    """Tests for _get_handler_info function."""

    def test_get_handler_info_with_function(self) -> None:
        """Test extracting info from a regular function."""
        info = _get_handler_info(sample_handler)
        assert info["name"] == "sample_handler"
        assert info["module"] == "tests.unit.test_events_panel"
        assert "test_events_panel.py" in info["file"]
        assert info["line"] > 0

    def test_get_handler_info_with_async_function(self) -> None:
        """Test extracting info from an async function."""
        info = _get_handler_info(async_sample_handler)
        assert info["name"] == "async_sample_handler"
        assert info["module"] == "tests.unit.test_events_panel"

    def test_get_handler_info_with_none(self) -> None:
        """Test extracting info when handler is None."""
        info = _get_handler_info(None)
        assert info["name"] == "None"
        assert info["module"] == ""
        assert info["file"] == ""
        assert info["line"] == 0

    def test_get_handler_info_with_lambda(self) -> None:
        """Test extracting info from a lambda function."""
        handler = lambda: None  # noqa: E731
        info = _get_handler_info(handler)
        assert info["name"] == "<lambda>"

    def test_get_handler_info_with_wrapped_function(self) -> None:
        """Test extracting info from a wrapped function."""

        def wrapper(fn: Any) -> Any:
            def inner(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

            inner.__wrapped__ = fn
            return inner

        wrapped = wrapper(sample_handler)
        info = _get_handler_info(wrapped)
        assert info["name"] == "sample_handler"


class TestGetStackFrames:
    """Tests for _get_stack_frames function."""

    def test_get_stack_frames_returns_list(self) -> None:
        """Test that stack frames returns a list."""
        frames = _get_stack_frames()
        assert isinstance(frames, list)

    def test_get_stack_frames_has_expected_keys(self) -> None:
        """Test that each frame has expected keys."""
        frames = _get_stack_frames()
        if frames:
            frame = frames[-1]
            assert "file" in frame
            assert "line" in frame
            assert "function" in frame
            assert "code" in frame

    def test_get_stack_frames_respects_limit(self) -> None:
        """Test that stack frames respects the limit parameter."""
        frames = _get_stack_frames(limit=3)
        assert len(frames) <= 3


class TestCollectEventsMetadata:
    """Tests for collect_events_metadata function."""

    def test_collect_events_metadata_with_empty_app(self) -> None:
        """Test collecting metadata from an app with no hooks."""
        app = MagicMock()
        app.on_startup = []
        app.on_shutdown = []
        app.before_request = None
        app.after_request = None
        app.after_response = None
        app.exception_handlers = {}

        context = RequestContext()
        collect_events_metadata(app, context)

        events = context.metadata["events"]
        assert events["lifecycle_hooks"]["on_startup"] == []
        assert events["lifecycle_hooks"]["on_shutdown"] == []
        assert events["request_hooks"]["before_request"] == []
        assert events["request_hooks"]["after_request"] == []
        assert events["request_hooks"]["after_response"] == []
        assert events["exception_handlers"] == []

    def test_collect_events_metadata_with_startup_hooks(self) -> None:
        """Test collecting metadata with startup hooks."""
        app = MagicMock()
        app.on_startup = [sample_handler]
        app.on_shutdown = []
        app.before_request = None
        app.after_request = None
        app.after_response = None
        app.exception_handlers = {}

        context = RequestContext()
        collect_events_metadata(app, context)

        events = context.metadata["events"]
        assert len(events["lifecycle_hooks"]["on_startup"]) == 1
        assert events["lifecycle_hooks"]["on_startup"][0]["name"] == "sample_handler"

    def test_collect_events_metadata_with_request_hooks(self) -> None:
        """Test collecting metadata with request lifecycle hooks."""
        app = MagicMock()
        app.on_startup = []
        app.on_shutdown = []
        app.before_request = sample_handler
        app.after_request = sample_handler
        app.after_response = sample_handler
        app.exception_handlers = {}

        context = RequestContext()
        collect_events_metadata(app, context)

        events = context.metadata["events"]
        assert len(events["request_hooks"]["before_request"]) == 1
        assert len(events["request_hooks"]["after_request"]) == 1
        assert len(events["request_hooks"]["after_response"]) == 1

    def test_collect_events_metadata_with_exception_handlers(self) -> None:
        """Test collecting metadata with exception handlers."""
        app = MagicMock()
        app.on_startup = []
        app.on_shutdown = []
        app.before_request = None
        app.after_request = None
        app.after_response = None
        app.exception_handlers = {ValueError: sample_handler}

        context = RequestContext()
        collect_events_metadata(app, context)

        events = context.metadata["events"]
        assert len(events["exception_handlers"]) == 1
        assert events["exception_handlers"][0]["exception_type"] == "ValueError"
        assert events["exception_handlers"][0]["handler"]["name"] == "sample_handler"

    def test_collect_events_metadata_with_none_attributes(self) -> None:
        """Test collecting metadata when app attributes are None."""
        app = MagicMock()
        app.on_startup = None
        app.on_shutdown = None
        app.before_request = None
        app.after_request = None
        app.after_response = None
        app.exception_handlers = None

        context = RequestContext()
        collect_events_metadata(app, context)

        events = context.metadata["events"]
        assert events["lifecycle_hooks"]["on_startup"] == []
        assert events["lifecycle_hooks"]["on_shutdown"] == []


class TestRecordHookExecution:
    """Tests for record_hook_execution function."""

    def test_record_hook_execution_success(self) -> None:
        """Test recording a successful hook execution."""
        context = RequestContext()
        record_hook_execution(
            context,
            hook_type="before_request",
            handler=sample_handler,
            duration_ms=1.5,
            success=True,
        )

        events = context.metadata["events"]
        assert len(events["executed_hooks"]) == 1
        hook = events["executed_hooks"][0]
        assert hook["hook_type"] == "before_request"
        assert hook["handler"]["name"] == "sample_handler"
        assert hook["duration_ms"] == 1.5
        assert hook["success"] is True
        assert hook["error"] is None
        assert hook["stack"] == []

    def test_record_hook_execution_failure(self) -> None:
        """Test recording a failed hook execution."""
        context = RequestContext()
        record_hook_execution(
            context,
            hook_type="after_request",
            handler=sample_handler,
            duration_ms=0.5,
            success=False,
            error="Something went wrong",
        )

        events = context.metadata["events"]
        assert len(events["executed_hooks"]) == 1
        hook = events["executed_hooks"][0]
        assert hook["hook_type"] == "after_request"
        assert hook["success"] is False
        assert hook["error"] == "Something went wrong"
        assert isinstance(hook["stack"], list)

    def test_record_hook_execution_initializes_events_metadata(self) -> None:
        """Test that recording initializes events metadata if missing."""
        context = RequestContext()
        assert "events" not in context.metadata

        record_hook_execution(
            context,
            hook_type="before_request",
            handler=sample_handler,
            duration_ms=1.0,
        )

        assert "events" in context.metadata
        assert "executed_hooks" in context.metadata["events"]

    def test_record_multiple_hook_executions(self) -> None:
        """Test recording multiple hook executions."""
        context = RequestContext()
        context.metadata["events"] = {
            "lifecycle_hooks": {},
            "request_hooks": {},
            "exception_handlers": [],
            "executed_hooks": [],
        }

        record_hook_execution(context, "before_request", sample_handler, 1.0)
        record_hook_execution(context, "after_request", sample_handler, 2.0)

        events = context.metadata["events"]
        assert len(events["executed_hooks"]) == 2
        assert events["executed_hooks"][0]["hook_type"] == "before_request"
        assert events["executed_hooks"][1]["hook_type"] == "after_request"


@pytest.fixture
def mock_toolbar() -> MagicMock:
    """Create a mock toolbar."""
    return MagicMock(spec=["config"])


class TestEventsPanel:
    """Tests for EventsPanel class."""

    def test_panel_class_attributes(self, mock_toolbar: MagicMock) -> None:
        """Test panel class attributes are set correctly."""
        panel = EventsPanel(mock_toolbar)
        assert panel.get_panel_id() == "EventsPanel"
        assert panel.title == "Events"
        assert panel.has_content is True
        assert panel.get_nav_title() == "Events"

    @pytest.mark.asyncio
    async def test_generate_stats_with_empty_events(self, mock_toolbar: MagicMock) -> None:
        """Test generate_stats with no events data."""
        panel = EventsPanel(mock_toolbar)
        context = RequestContext()
        context.metadata["events"] = {
            "lifecycle_hooks": {"on_startup": [], "on_shutdown": []},
            "request_hooks": {
                "before_request": [],
                "after_request": [],
                "after_response": [],
            },
            "exception_handlers": [],
            "executed_hooks": [],
        }

        stats = await panel.generate_stats(context)

        assert stats["total_hooks"] == 0
        assert stats["total_executed"] == 0
        assert stats["total_time_ms"] == 0
        assert stats["total_exception_handlers"] == 0

    @pytest.mark.asyncio
    async def test_generate_stats_with_hooks(self, mock_toolbar: MagicMock) -> None:
        """Test generate_stats with various hooks registered."""
        panel = EventsPanel(mock_toolbar)
        context = RequestContext()
        context.metadata["events"] = {
            "lifecycle_hooks": {
                "on_startup": [{"name": "startup_1"}, {"name": "startup_2"}],
                "on_shutdown": [{"name": "shutdown_1"}],
            },
            "request_hooks": {
                "before_request": [{"name": "before_1"}],
                "after_request": [{"name": "after_1"}],
                "after_response": [],
            },
            "exception_handlers": [{"exception_type": "ValueError", "handler": {"name": "handler_1"}}],
            "executed_hooks": [
                {"hook_type": "before_request", "duration_ms": 1.5},
                {"hook_type": "after_request", "duration_ms": 2.5},
            ],
        }

        stats = await panel.generate_stats(context)

        assert stats["total_hooks"] == 5
        assert stats["total_executed"] == 2
        assert stats["total_time_ms"] == 4.0
        assert stats["total_exception_handlers"] == 1

    @pytest.mark.asyncio
    async def test_generate_stats_with_missing_events(self, mock_toolbar: MagicMock) -> None:
        """Test generate_stats when events metadata is missing."""
        panel = EventsPanel(mock_toolbar)
        context = RequestContext()

        stats = await panel.generate_stats(context)

        assert stats["total_hooks"] == 0
        assert stats["total_executed"] == 0
        assert stats["total_time_ms"] == 0

    def test_get_nav_subtitle(self, mock_toolbar: MagicMock) -> None:
        """Test nav_subtitle returns empty string."""
        panel = EventsPanel(mock_toolbar)
        assert panel.get_nav_subtitle() == ""
