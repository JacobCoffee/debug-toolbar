"""TaskFactory-based async profiling backend."""

from __future__ import annotations

import asyncio
import sys
import time
import traceback
from collections.abc import Callable, Coroutine
from contextvars import Context
from typing import TYPE_CHECKING, Any

from debug_toolbar.core.panels.async_profiler.base import AsyncProfilerBackend
from debug_toolbar.core.panels.async_profiler.models import TaskEvent

if TYPE_CHECKING:
    TaskFactory = Callable[
        [asyncio.AbstractEventLoop, Coroutine[Any, Any, Any]],
        asyncio.Task[Any],
    ]

DEFAULT_MAX_STACK_DEPTH = 10
STACK_SKIP_FRAMES = 4


def _get_stack_frames(
    skip: int = STACK_SKIP_FRAMES, limit: int = DEFAULT_MAX_STACK_DEPTH
) -> list[dict[str, str | int]]:
    """Capture the current call stack.

    Args:
        skip: Number of most recent frames to skip.
        limit: Maximum number of frames to return.

    Returns:
        List of dictionaries containing frame information.
    """
    frames = []
    for frame_info in traceback.extract_stack()[:-skip][-limit:]:
        frames.append(
            {
                "file": frame_info.filename,
                "line": frame_info.lineno,
                "function": frame_info.name,
                "code": frame_info.line or "",
            }
        )
    return frames


class TaskFactoryBackend(AsyncProfilerBackend):
    """Default async profiling backend using asyncio task factory hooks.

    This backend intercepts task creation by installing a custom task factory
    on the event loop. It tracks:
    - Task creation time
    - Task completion time
    - Task name and coroutine name
    - Creation stack trace

    This is the default backend as it requires no external dependencies.
    """

    __slots__ = (
        "_capture_stacks",
        "_loop",
        "_max_stack_depth",
        "_original_factory",
        "_profiling_overhead",
        "_start_time",
        "_task_events",
    )

    def __init__(
        self,
        *,
        capture_stacks: bool = True,
        max_stack_depth: int = DEFAULT_MAX_STACK_DEPTH,
    ) -> None:
        """Initialize the TaskFactoryBackend.

        Args:
            capture_stacks: Whether to capture stack traces on task creation.
            max_stack_depth: Maximum stack depth to capture.
        """
        self._original_factory: Any = None
        self._task_events: list[TaskEvent] = []
        self._start_time: float = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._profiling_overhead: float = 0.0
        self._capture_stacks = capture_stacks
        self._max_stack_depth = max_stack_depth

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Begin async profiling by installing custom task factory.

        Args:
            loop: The asyncio event loop to monitor.
        """
        start = time.perf_counter()

        self._loop = loop
        self._start_time = loop.time()
        self._task_events = []
        self._original_factory = loop.get_task_factory()
        loop.set_task_factory(self._profiling_task_factory)

        self._profiling_overhead = time.perf_counter() - start

    def _profiling_task_factory(
        self,
        loop: asyncio.AbstractEventLoop,
        coro: Coroutine[Any, Any, Any],
        *,
        name: str | None = None,
        context: Context | None = None,
    ) -> asyncio.Task[Any]:
        """Custom task factory that records task creation.

        Args:
            loop: The event loop.
            coro: The coroutine to wrap in a task.
            name: Optional task name.
            context: Optional context for the task.

        Returns:
            The created Task object.
        """
        # Use original factory if available (e.g., SQLAlchemy's greenlet-based factory)
        # to preserve proper async context setup
        if self._original_factory is not None:
            # Try with kwargs first (Python 3.11+), fall back to positional only
            try:
                task = self._original_factory(loop, coro, name=name, context=context)
            except TypeError:
                task = self._original_factory(loop, coro)
                if name is not None:
                    task.set_name(name)
        elif sys.version_info >= (3, 11):
            task = asyncio.Task(coro, loop=loop, name=name, context=context)
        else:
            task = asyncio.Task(coro, loop=loop, name=name)  # type: ignore[call-arg]
        creation_time = loop.time() - self._start_time

        coro_name = getattr(coro, "__qualname__", str(coro))

        current_task = asyncio.current_task(loop)
        parent_task_id = str(id(current_task)) if current_task else None

        stack_frames = _get_stack_frames(limit=self._max_stack_depth) if self._capture_stacks else []

        event = TaskEvent(
            task_id=str(id(task)),
            task_name=task.get_name(),
            event_type="created",
            timestamp=creation_time,
            coro_name=coro_name,
            parent_task_id=parent_task_id,
            stack_frames=stack_frames,
        )
        self._task_events.append(event)

        task.add_done_callback(lambda t: self._record_task_complete(t, creation_time))

        return task

    def _record_task_complete(self, task: asyncio.Task[Any], creation_time: float) -> None:
        """Record task completion.

        Args:
            task: The completed task.
            creation_time: When the task was created (relative to start).
        """
        if self._loop is None:
            return

        completion_time = self._loop.time() - self._start_time
        duration_ms = (completion_time - creation_time) * 1000

        try:
            exc = task.exception()
            if exc is not None:
                event_type: str = "error"
                error = str(exc)
            else:
                event_type = "completed"
                error = None
        except asyncio.CancelledError:
            event_type = "cancelled"
            error = None
        except asyncio.InvalidStateError:
            event_type = "unknown"
            error = "Task not done"

        event = TaskEvent(
            task_id=str(id(task)),
            task_name=task.get_name(),
            event_type=event_type,  # type: ignore[arg-type]
            timestamp=completion_time,
            coro_name=getattr(task.get_coro(), "__qualname__", "unknown"),
            duration_ms=duration_ms,
            error=error,
        )
        self._task_events.append(event)

    def stop(self) -> None:
        """End async profiling and restore original task factory."""
        start = time.perf_counter()

        if self._loop is not None:
            self._loop.set_task_factory(self._original_factory)

        self._profiling_overhead += time.perf_counter() - start

    def get_stats(self) -> dict[str, Any]:
        """Retrieve async profiling statistics.

        Returns:
            Dictionary containing:
                - tasks: List of task events as dictionaries
                - backend: "taskfactory"
                - profiling_overhead: Time spent on profiling (seconds)
        """
        tasks = []
        for event in self._task_events:
            tasks.append(
                {
                    "task_id": event.task_id,
                    "task_name": event.task_name,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "coro_name": event.coro_name,
                    "parent_task_id": event.parent_task_id,
                    "stack_frames": event.stack_frames,
                    "duration_ms": event.duration_ms,
                    "error": event.error,
                }
            )

        return {
            "tasks": tasks,
            "backend": "taskfactory",
            "profiling_overhead": self._profiling_overhead,
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check if this backend is available.

        Returns:
            Always True - this backend uses only stdlib.
        """
        return True
