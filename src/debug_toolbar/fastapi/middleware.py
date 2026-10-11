"""Debug toolbar middleware for FastAPI.

This module provides a FastAPI-specific middleware that wraps
the Starlette middleware and adds dependency injection tracking.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from debug_toolbar.core import DebugToolbar, get_request_context
from debug_toolbar.fastapi.config import FastAPIDebugToolbarConfig
from debug_toolbar.starlette.middleware import DebugToolbarMiddleware as StarletteMiddleware

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_dependency_tracking: ContextVar[list[dict[str, Any]] | None] = ContextVar("dependency_tracking", default=None)
_dependency_cache_stats: ContextVar[dict[str, int] | None] = ContextVar("dependency_cache_stats", default=None)


def _install_dependency_instrumentation() -> None:
    """Monkeypatch FastAPI's dependency solver to record each resolved dependency.

    FastAPI resolves ``Depends()`` callables internally with no public hook for
    observing resolutions, so this wraps ``solve_dependencies`` (both where it is
    defined and where ``fastapi.routing`` imported it) to capture each dependency
    resolution into the request-scoped tracking contextvars.
    """
    import time as time_module

    from fastapi.dependencies import utils as fastapi_dependency_utils

    from fastapi import routing as fastapi_routing

    if fastapi_dependency_utils.solve_dependencies.__name__ == "instrumented_solve_dependencies":
        return

    original_solve_dependencies = fastapi_dependency_utils.solve_dependencies

    async def instrumented_solve_dependencies(*, request: Any, dependant: Any, **kwargs: Any) -> Any:
        depth_key = "_debug_toolbar_dependency_depth"
        depth = request.scope.get(depth_key, 0) + 1
        request.scope[depth_key] = depth
        dependency_cache = kwargs.get("dependency_cache") or {}
        already_cached = dependant.cache_key in dependency_cache
        start = time_module.perf_counter()
        try:
            result = await original_solve_dependencies(request=request, dependant=dependant, **kwargs)
        finally:
            request.scope[depth_key] = depth - 1

        # depth == 1 is the route handler's own top-level dependant, not a Depends().
        if depth > 1 and dependant.call is not None and _dependency_tracking.get() is not None:
            duration_ms = (time_module.perf_counter() - start) * 1000
            track_dependency(dependant.call, cached=already_cached, duration_ms=duration_ms)

        return result

    fastapi_dependency_utils.solve_dependencies = instrumented_solve_dependencies  # type: ignore[invalid-assignment]
    fastapi_routing.solve_dependencies = instrumented_solve_dependencies  # type: ignore[invalid-assignment]


def get_dependency_tracking() -> list[dict[str, Any]]:
    """Get the current dependency tracking list."""
    tracking = _dependency_tracking.get()
    if tracking is None:
        tracking = []
        _dependency_tracking.set(tracking)
    return tracking


def get_dependency_cache_stats() -> dict[str, int]:
    """Get the current dependency cache stats."""
    stats = _dependency_cache_stats.get()
    if stats is None:
        stats = {"hits": 0, "misses": 0, "total": 0}
        _dependency_cache_stats.set(stats)
    return stats


def record_dependency_resolution(
    name: str,
    dependency_type: str,
    *,
    cached: bool,
    duration_ms: float,
    module: str | None = None,
    cache_key: str | None = None,
    params: dict[str, Any] | None = None,
) -> None:
    """Record a dependency resolution event.

    Args:
        name: Name of the dependency function/class.
        dependency_type: Type of dependency (function, class, generator).
        cached: Whether the result came from cache.
        duration_ms: Resolution time in milliseconds.
        module: Module where the dependency is defined.
        cache_key: Cache key used by FastAPI.
        params: Parameters passed to the dependency.
    """
    tracking = get_dependency_tracking()
    stats = get_dependency_cache_stats()

    resolution_record = {
        "name": name,
        "type": dependency_type,
        "cached": cached,
        "duration_ms": duration_ms,
        "module": module or "",
        "cache_key": cache_key or "",
        "params": params or {},
    }

    tracking.append(resolution_record)

    stats["total"] += 1
    if cached:
        stats["hits"] += 1
    else:
        stats["misses"] += 1

    context = get_request_context()
    if context is not None:
        context.metadata.setdefault(
            "dependencies",
            {"resolved": tracking, "tree": {}, "cache_stats": stats},
        )


class DebugToolbarMiddleware(StarletteMiddleware):
    """FastAPI-specific middleware for the debug toolbar.

    Extends the Starlette middleware with dependency injection tracking.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: FastAPIDebugToolbarConfig | None = None,
        toolbar: DebugToolbar | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The next ASGI application.
            config: Toolbar configuration. Uses defaults if not provided.
            toolbar: Optional shared toolbar instance. Creates new if not provided.
        """
        config = config or FastAPIDebugToolbarConfig()
        super().__init__(app, config, toolbar)
        self.fastapi_config = config

        if config.track_dependency_injection:
            _install_dependency_instrumentation()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an ASGI request with dependency tracking."""
        if scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return

        if self.fastapi_config.track_dependency_injection:
            _dependency_tracking.set([])
            _dependency_cache_stats.set({"hits": 0, "misses": 0, "total": 0})

        await super().__call__(scope, receive, send)


def track_dependency(
    dependency_callable: Any,
    *,
    cached: bool = False,
    duration_ms: float = 0.0,
) -> None:
    """Helper function to track a dependency resolution.

    This can be used in custom dependency wrappers to track resolution.

    Args:
        dependency_callable: The dependency function/class being resolved.
        cached: Whether the result came from cache.
        duration_ms: Resolution time in milliseconds.
    """
    name = getattr(dependency_callable, "__name__", str(dependency_callable))
    module = getattr(dependency_callable, "__module__", None)

    import inspect

    if inspect.isgeneratorfunction(dependency_callable) or inspect.isasyncgenfunction(dependency_callable):
        dep_type = "generator"
    elif inspect.isclass(dependency_callable):
        dep_type = "class"
    else:
        dep_type = "function"

    record_dependency_resolution(
        name=name,
        dependency_type=dep_type,
        cached=cached,
        duration_ms=duration_ms,
        module=module,
    )
