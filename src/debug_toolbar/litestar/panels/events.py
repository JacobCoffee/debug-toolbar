"""Events panel for displaying Litestar lifecycle events and handlers."""

from __future__ import annotations

import inspect
import traceback
from typing import TYPE_CHECKING, Any, ClassVar, cast

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from collections.abc import Callable

    from debug_toolbar.core.context import RequestContext


def _get_handler_info(handler: Callable[..., Any] | None) -> dict[str, Any]:
    """Extract information about a handler function.

    Args:
        handler: The handler function to inspect, or None.

    Returns:
        Dictionary containing name, module, file, line, and qualname information.
    """
    if handler is None:
        return {"name": "None", "module": "", "file": "", "line": 0, "qualname": ""}

    func: Any = handler
    if hasattr(handler, "__wrapped__"):
        func = handler.__wrapped__
    if hasattr(handler, "func"):
        func = handler.func

    name = getattr(func, "__name__", str(func))
    module = getattr(func, "__module__", "")

    try:
        file = inspect.getfile(func)  # type: ignore[arg-type]
        _, line = inspect.getsourcelines(func)  # type: ignore[arg-type]
    except (TypeError, OSError):
        file = ""
        line = 0

    return {
        "name": name,
        "module": module,
        "file": file,
        "line": line,
        "qualname": getattr(func, "__qualname__", name),
    }


def _get_stack_frames(skip: int = 2, limit: int = 10) -> list[dict[str, Any]]:
    """Capture the current call stack.

    Args:
        skip: Number of most recent frames to skip (default: 2).
        limit: Maximum number of frames to return (default: 10).

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


class EventsPanel(Panel):
    """Panel displaying Litestar lifecycle events and handlers.

    Shows:
    - Application lifecycle hooks (on_startup, on_shutdown)
    - Request lifecycle hooks (before_request, after_request, after_response)
    - Exception handlers registered at app/controller/route level
    - Execution timing for hooks that ran during the request
    """

    panel_id: ClassVar[str] = "EventsPanel"
    title: ClassVar[str] = "Events"
    template: ClassVar[str] = "panels/events.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Events"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate event statistics from context metadata."""
        events_data = context.metadata.get("events", {})

        lifecycle_hooks = events_data.get("lifecycle_hooks", {})
        request_hooks = events_data.get("request_hooks", {})
        exception_handlers = events_data.get("exception_handlers", [])
        executed_hooks = events_data.get("executed_hooks", [])

        total_hooks = (
            len(lifecycle_hooks.get("on_startup", []))
            + len(lifecycle_hooks.get("on_shutdown", []))
            + len(request_hooks.get("before_request", []))
            + len(request_hooks.get("after_request", []))
            + len(request_hooks.get("after_response", []))
        )

        total_executed = len(executed_hooks)
        total_time_ms = sum(h.get("duration_ms", 0) for h in executed_hooks)

        return {
            "lifecycle_hooks": lifecycle_hooks,
            "request_hooks": request_hooks,
            "exception_handlers": exception_handlers,
            "executed_hooks": executed_hooks,
            "total_hooks": total_hooks,
            "total_executed": total_executed,
            "total_time_ms": total_time_ms,
            "total_exception_handlers": len(exception_handlers),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""


def collect_events_metadata(app: Any, context: RequestContext) -> None:
    """Collect event/lifecycle metadata from a Litestar app.

    This function should be called from the middleware to populate
    the context with event information.

    Args:
        app: The Litestar application instance.
        context: The request context to populate.
    """
    events_data: dict[str, Any] = {
        "lifecycle_hooks": {},
        "request_hooks": {},
        "exception_handlers": [],
        "executed_hooks": [],
    }

    events_data["lifecycle_hooks"]["on_startup"] = [_get_handler_info(h) for h in getattr(app, "on_startup", []) or []]
    events_data["lifecycle_hooks"]["on_shutdown"] = [
        _get_handler_info(h) for h in getattr(app, "on_shutdown", []) or []
    ]

    before_request = getattr(app, "before_request", None)
    after_request = getattr(app, "after_request", None)
    after_response = getattr(app, "after_response", None)

    events_data["request_hooks"]["before_request"] = [_get_handler_info(before_request)] if before_request else []
    events_data["request_hooks"]["after_request"] = [_get_handler_info(after_request)] if after_request else []
    events_data["request_hooks"]["after_response"] = [_get_handler_info(after_response)] if after_response else []

    exception_handlers = getattr(app, "exception_handlers", {}) or {}
    for exc_type, handler in exception_handlers.items():
        exc_name = exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type)
        handler_info = _get_handler_info(handler)
        events_data["exception_handlers"].append(
            {
                "exception_type": exc_name,
                "handler": handler_info,
            }
        )

    context.metadata["events"] = events_data


def record_hook_execution(
    context: RequestContext,
    hook_type: str,
    handler: Callable[..., Any] | None,
    duration_ms: float,
    *,
    success: bool = True,
    error: str | None = None,
) -> None:
    """Record that a hook was executed during the request.

    Args:
        context: The request context.
        hook_type: Type of hook (e.g., "before_request", "after_request").
        handler: The handler function that was executed.
        duration_ms: Execution time in milliseconds.
        success: Whether the hook executed successfully.
        error: Error message if the hook failed.
    """
    if "events" not in context.metadata:
        context.metadata["events"] = {
            "lifecycle_hooks": {},
            "request_hooks": {},
            "exception_handlers": [],
            "executed_hooks": [],
        }

    handler_info = _get_handler_info(handler)
    execution_record = {
        "hook_type": hook_type,
        "handler": handler_info,
        "duration_ms": duration_ms,
        "success": success,
        "error": error,
        "stack": _get_stack_frames() if not success else [],
    }

    cast("list[dict[str, Any]]", context.metadata["events"]["executed_hooks"]).append(execution_record)
