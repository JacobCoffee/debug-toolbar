"""Data models for async profiling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TaskEvent:
    """Represents an async task lifecycle event."""

    task_id: str
    task_name: str
    event_type: Literal["created", "completed", "cancelled", "error", "unknown"]
    timestamp: float
    coro_name: str
    parent_task_id: str | None = None
    stack_frames: list[dict[str, str | int]] = field(default_factory=list)
    duration_ms: float | None = None
    error: str | None = None


@dataclass
class BlockingCall:
    """Represents a detected blocking call in async context."""

    timestamp: float
    duration_ms: float
    function_name: str
    file: str
    line: int
    stack_frames: list[dict[str, str | int]] = field(default_factory=list)


@dataclass
class LagSample:
    """Represents an event loop lag measurement."""

    timestamp: float
    expected_delta: float
    actual_delta: float
    lag_ms: float


@dataclass
class TimelineEvent:
    """Represents an event in the timeline visualization."""

    id: str
    name: str
    event_type: Literal["task", "blocking"]
    start_time: float
    end_time: float | None
    status: Literal["running", "completed", "cancelled", "error", "blocking", "unknown"]
    parent_id: str | None = None
    details: dict[str, str | float | int] = field(default_factory=dict)
