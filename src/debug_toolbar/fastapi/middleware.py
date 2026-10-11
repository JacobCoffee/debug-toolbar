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


def _dependency_internals_supported(fastapi_dependency_utils: Any, dependant_cls: Any) -> bool:
    """Check whether the FastAPI internals this instrumentation relies on are present.

    FastAPI has reshaped these internals more than once (e.g. moving
    ``Dependant.cache_key`` to a module-level ``_get_cache_key()`` helper and
    dropping ``is_coroutine_callable``/``is_gen_callable``/``is_async_gen_callable``
    in later releases); both the older and newer ``cache_key`` shapes are accepted,
    but the callable-kind attributes must still be present.
    """
    has_cache_key_support = hasattr(dependant_cls, "cache_key") or hasattr(fastapi_dependency_utils, "_get_cache_key")
    has_callable_kind_support = all(
        hasattr(dependant_cls, attr)
        for attr in ("is_coroutine_callable", "is_gen_callable", "is_async_gen_callable", "use_cache")
    )
    return has_cache_key_support and has_callable_kind_support and hasattr(fastapi_dependency_utils, "_solve_generator")


def _make_instrumented_solve_dependencies(original: Any, dependant_cache_key: Any) -> Any:
    """Build the ``solve_dependencies`` wrapper: tracks tree depth, and records
    cached/coroutine-function resolutions directly since they have no other
    interceptable call site.
    """

    async def instrumented_solve_dependencies(*, request: Any, dependant: Any, **kwargs: Any) -> Any:
        depth_key = "_debug_toolbar_dependency_depth"
        depth = request.scope.get(depth_key, 0) + 1
        request.scope[depth_key] = depth
        dependency_cache = kwargs.get("dependency_cache") or {}
        already_cached = bool(dependant.use_cache) and dependant_cache_key(dependant) in dependency_cache
        try:
            result = await original(request=request, dependant=dependant, **kwargs)
        finally:
            request.scope[depth_key] = depth - 1

        # depth == 1 is the route handler's own top-level dependant, not a Depends().
        if depth > 1 and dependant.call is not None and _dependency_tracking.get() is not None:
            if already_cached:
                track_dependency(dependant.call, cached=True, duration_ms=0.0)
            elif dependant.is_coroutine_callable:
                track_dependency(dependant.call, cached=False, duration_ms=None)
            # Sync functions/classes are timed via run_in_threadpool; generator
            # dependencies are timed via _solve_generator.

        return result

    return instrumented_solve_dependencies


def _make_instrumented_run_in_threadpool(original: Any, time_module: Any) -> Any:
    """Build the ``run_in_threadpool`` wrapper that times sync function/class dependencies."""

    async def instrumented_run_in_threadpool(func: Any, *args: Any, **kwargs: Any) -> Any:
        start = time_module.perf_counter()
        try:
            return await original(func, *args, **kwargs)
        finally:
            if _dependency_tracking.get() is not None:
                duration_ms = (time_module.perf_counter() - start) * 1000
                track_dependency(func, cached=False, duration_ms=duration_ms)

    return instrumented_run_in_threadpool


def _make_instrumented_solve_generator(original: Any, time_module: Any) -> Any:
    """Build the ``_solve_generator`` wrapper that times generator-based dependencies."""

    async def instrumented_solve_generator(*, dependant: Any, stack: Any, sub_values: Any) -> Any:
        start = time_module.perf_counter()
        try:
            return await original(dependant=dependant, stack=stack, sub_values=sub_values)
        finally:
            if dependant.call is not None and _dependency_tracking.get() is not None:
                duration_ms = (time_module.perf_counter() - start) * 1000
                track_dependency(dependant.call, cached=False, duration_ms=duration_ms)

    return instrumented_solve_generator


def _install_dependency_instrumentation() -> None:
    """Monkeypatch FastAPI's dependency solver to record each resolved dependency.

    FastAPI resolves ``Depends()`` callables internally with no public hook for
    observing resolutions, so this wraps three of its internals:

    - ``solve_dependencies`` (both where it is defined and where ``fastapi.routing``
      imported it): tracks tree depth and records cached resolutions directly, since
      cached dependencies are never actually re-invoked.
    - ``run_in_threadpool``: times plain sync function/class dependencies, which
      FastAPI invokes through it.
    - ``_solve_generator``: times generator-based dependencies (e.g. ``yield`` based
      session managers), which FastAPI invokes through it.

    Coroutine-function dependencies are awaited inline inside ``solve_dependencies``
    with no interceptable call site, so their duration is reported as ``None``
    rather than measuring the wrong thing.

    These internals only exist in this shape between FastAPI 0.121 and some later
    releases that reshaped them again; see ``_dependency_internals_supported``. On
    unsupported versions this is a no-op and the panel stays empty, same as before
    this fix.
    """
    import time as time_module

    from fastapi.dependencies import utils as fastapi_dependency_utils
    from fastapi.dependencies.models import Dependant as FastAPIDependant

    from fastapi import routing as fastapi_routing

    if fastapi_dependency_utils.solve_dependencies.__name__ == "instrumented_solve_dependencies":
        return

    if not _dependency_internals_supported(fastapi_dependency_utils, FastAPIDependant):
        logger.debug(
            "FastAPI dependency injection tracking requires internals introduced in "
            "FastAPI 0.121; skipping instrumentation for this FastAPI version."
        )
        return

    get_cache_key = getattr(fastapi_dependency_utils, "_get_cache_key", None)

    def dependant_cache_key(dependant: Any) -> Any:
        if get_cache_key is not None:
            return get_cache_key(dependant=dependant)
        return dependant.cache_key

    instrumented_solve_dependencies = _make_instrumented_solve_dependencies(
        fastapi_dependency_utils.solve_dependencies, dependant_cache_key
    )
    instrumented_run_in_threadpool = _make_instrumented_run_in_threadpool(
        fastapi_dependency_utils.run_in_threadpool, time_module
    )
    instrumented_solve_generator = _make_instrumented_solve_generator(
        fastapi_dependency_utils._solve_generator,  # noqa: SLF001
        time_module,
    )

    fastapi_dependency_utils.solve_dependencies = instrumented_solve_dependencies  # type: ignore[invalid-assignment]
    fastapi_routing.solve_dependencies = instrumented_solve_dependencies  # type: ignore[invalid-assignment]
    fastapi_dependency_utils.run_in_threadpool = instrumented_run_in_threadpool  # type: ignore[invalid-assignment]
    fastapi_dependency_utils._solve_generator = instrumented_solve_generator  # type: ignore[invalid-assignment]  # noqa: SLF001


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
    duration_ms: float | None,
    module: str | None = None,
    cache_key: str | None = None,
    params: dict[str, Any] | None = None,
) -> None:
    """Record a dependency resolution event.

    Args:
        name: Name of the dependency function/class.
        dependency_type: Type of dependency (function, class, generator).
        cached: Whether the result came from cache.
        duration_ms: Resolution time in milliseconds, or ``None`` if it could not
            be measured (e.g. coroutine-function dependencies, which FastAPI
            invokes with no interceptable call site).
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
    duration_ms: float | None = 0.0,
) -> None:
    """Helper function to track a dependency resolution.

    This can be used in custom dependency wrappers to track resolution.

    Args:
        dependency_callable: The dependency function/class being resolved.
        cached: Whether the result came from cache.
        duration_ms: Resolution time in milliseconds, or ``None`` if unknown.
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
