"""Timeline generation for async profiling visualization."""

from __future__ import annotations

from typing import Any

from debug_toolbar.core.panels.async_profiler.models import TimelineEvent


def generate_timeline(
    tasks: list[dict[str, Any]],
    blocking_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate timeline data for visualization.

    Converts raw task events and blocking calls into a format suitable
    for rendering a Gantt-style timeline visualization.

    Args:
        tasks: List of task event dictionaries.
        blocking_calls: List of blocking call dictionaries.

    Returns:
        Dictionary containing timeline data with:
            - events: List of timeline events
            - total_duration_ms: Total request duration
            - max_concurrent: Maximum concurrent tasks
    """
    timeline_events: list[TimelineEvent] = []
    task_start_times: dict[str, float] = {}
    task_end_times: dict[str, float] = {}

    for task in tasks:
        task_id = task.get("task_id", "")
        event_type = task.get("event_type", "")
        timestamp = task.get("timestamp", 0.0)

        if event_type == "created":
            task_start_times[task_id] = timestamp
        elif event_type in ("completed", "cancelled", "error"):
            task_end_times[task_id] = timestamp

    for task in tasks:
        if task.get("event_type") != "created":
            continue

        task_id = task.get("task_id", "")
        start_time = task_start_times.get(task_id, 0.0)
        end_time = task_end_times.get(task_id)

        completion_event = next(
            (
                t
                for t in tasks
                if t.get("task_id") == task_id and t.get("event_type") in ("completed", "cancelled", "error")
            ),
            None,
        )

        if completion_event:
            status = completion_event.get("event_type", "completed")
        else:
            status = "running"

        event = TimelineEvent(
            id=task_id,
            name=task.get("task_name", "unknown"),
            event_type="task",
            start_time=start_time * 1000,
            end_time=end_time * 1000 if end_time is not None else None,
            status=status,  # type: ignore[arg-type]
            parent_id=task.get("parent_task_id"),
            details={
                "coro_name": task.get("coro_name", ""),
                "duration_ms": task.get("duration_ms", 0),
            },
        )
        timeline_events.append(event)

    for blocking_call in blocking_calls:
        timestamp = blocking_call.get("timestamp", 0.0)
        duration_ms = blocking_call.get("duration_ms", 0.0)

        event = TimelineEvent(
            id=f"blocking_{timestamp}",
            name=blocking_call.get("function_name", "blocking call"),
            event_type="blocking",
            start_time=timestamp * 1000,
            end_time=(timestamp * 1000) + duration_ms,
            status="blocking",
            details={
                "file": blocking_call.get("file", ""),
                "line": blocking_call.get("line", 0),
                "duration_ms": duration_ms,
            },
        )
        timeline_events.append(event)

    timeline_events.sort(key=lambda e: e.start_time)

    all_times = []
    for event in timeline_events:
        all_times.append(event.start_time)
        if event.end_time is not None:
            all_times.append(event.end_time)

    total_duration_ms = max(all_times) - min(all_times) if all_times else 0.0

    max_concurrent = _calculate_max_concurrent(timeline_events)

    events_data = []
    for event in timeline_events:
        events_data.append(
            {
                "id": event.id,
                "name": event.name,
                "event_type": event.event_type,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "status": event.status,
                "parent_id": event.parent_id,
                "details": event.details,
            }
        )

    return {
        "events": events_data,
        "total_duration_ms": total_duration_ms,
        "max_concurrent": max_concurrent,
    }


def _calculate_max_concurrent(events: list[TimelineEvent]) -> int:
    """Calculate the maximum number of concurrent tasks.

    Args:
        events: List of timeline events.

    Returns:
        Maximum number of tasks running at the same time.
    """
    if not events:
        return 0

    task_events = [e for e in events if e.event_type == "task"]
    if not task_events:
        return 0

    time_points: list[tuple[float, int]] = []

    for event in task_events:
        time_points.append((event.start_time, 1))
        if event.end_time is not None:
            time_points.append((event.end_time, -1))

    # Sort by (timestamp, delta) so that end events (delta=-1) are processed before
    # start events (delta=1) at the same timestamp. This ensures that a task ending
    # and another starting at the same time are not both counted as running concurrently.
    time_points.sort(key=lambda x: (x[0], x[1]))

    current_concurrent = 0
    max_concurrent = 0

    for _, delta in time_points:
        current_concurrent += delta
        max_concurrent = max(max_concurrent, current_concurrent)

    return max_concurrent
