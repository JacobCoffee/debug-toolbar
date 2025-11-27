"""Cache panel for tracking cache operations during requests."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from collections.abc import Generator

    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


CacheOperation = Literal["GET", "SET", "DELETE", "INCR", "DECR", "MGET", "MSET", "EXISTS", "EXPIRE", "OTHER"]


@dataclass
class CacheOperationRecord:
    """Record of a single cache operation."""

    operation: CacheOperation
    key: str | list[str]
    hit: bool | None
    duration: float
    timestamp: float
    backend: str
    extra: dict[str, Any] = field(default_factory=dict)


_patch_lock = threading.Lock()


class CacheTracker:
    """Tracks cache operations for Redis and memcached."""

    def __init__(self) -> None:
        self.operations: list[CacheOperationRecord] = []
        self._original_redis_methods: dict[str, Any] = {}
        self._original_memcache_methods: dict[str, Any] = {}
        self._tracking_enabled = False

    def start_tracking(self) -> None:
        """Start tracking cache operations by patching client methods."""
        if self._tracking_enabled:
            return

        self._tracking_enabled = True
        with _patch_lock:
            self._patch_redis()
            self._patch_memcache()

    def stop_tracking(self) -> None:
        """Stop tracking and restore original methods."""
        if not self._tracking_enabled:
            return

        with _patch_lock:
            self._unpatch_redis()
            self._unpatch_memcache()
        self._tracking_enabled = False

    def clear(self) -> None:
        """Clear tracked operations."""
        self.operations = []

    def _patch_redis(self) -> None:
        """Patch Redis client methods to track operations."""
        try:
            import redis  # type: ignore[import-untyped]
        except ImportError:
            return

        if hasattr(redis.Redis, "_debug_toolbar_patched"):
            return

        methods_to_patch = {
            "get": ("GET", True),
            "set": ("SET", False),
            "delete": ("DELETE", False),
            "mget": ("MGET", True),
            "mset": ("MSET", False),
            "incr": ("INCR", False),
            "decr": ("DECR", False),
            "exists": ("EXISTS", True),
            "expire": ("EXPIRE", False),
            "setex": ("SET", False),
            "setnx": ("SET", False),
            "getset": ("GET", True),
            "hget": ("GET", True),
            "hset": ("SET", False),
            "hdel": ("DELETE", False),
            "sadd": ("SET", False),
            "srem": ("DELETE", False),
            "lpush": ("SET", False),
            "rpush": ("SET", False),
            "lpop": ("GET", True),
            "rpop": ("GET", True),
        }

        for method_name, (operation, is_read) in methods_to_patch.items():
            original_method = getattr(redis.Redis, method_name, None)
            if original_method is None:
                continue

            self._original_redis_methods[method_name] = original_method

            def create_wrapper(
                orig_method: Any,
                op: CacheOperation,
                check_hit: bool,  # noqa: FBT001
            ) -> Any:
                def wrapper(self_redis: Any, *args: Any, **kwargs: Any) -> Any:
                    start = time.perf_counter()
                    result = orig_method(self_redis, *args, **kwargs)
                    duration = time.perf_counter() - start

                    key = args[0] if args else kwargs.get("name", "unknown")
                    hit = None
                    if check_hit:
                        hit = result is not None

                    tracker = _get_tracker()
                    if tracker:
                        tracker._record_operation(  # noqa: SLF001
                            operation=op,
                            key=key,
                            hit=hit,
                            duration=duration,
                            backend="redis",
                        )

                    return result

                return wrapper

            setattr(
                redis.Redis,
                method_name,
                create_wrapper(original_method, operation, is_read),  # type: ignore[arg-type]
            )

        redis.Redis._debug_toolbar_patched = True  # type: ignore[attr-defined]  # noqa: SLF001

    def _unpatch_redis(self) -> None:
        """Restore original Redis methods."""
        try:
            import redis  # type: ignore[import-untyped]
        except ImportError:
            return

        if not hasattr(redis.Redis, "_debug_toolbar_patched"):
            return

        for method_name, original_method in self._original_redis_methods.items():
            setattr(redis.Redis, method_name, original_method)

        delattr(redis.Redis, "_debug_toolbar_patched")
        self._original_redis_methods.clear()

    def _patch_memcache(self) -> None:
        """Patch pymemcache client methods to track operations."""
        try:
            from pymemcache.client.base import Client  # type: ignore[import-untyped]
        except ImportError:
            return

        if hasattr(Client, "_debug_toolbar_patched"):
            return

        methods_to_patch = {
            "get": ("GET", True),
            "set": ("SET", False),
            "delete": ("DELETE", False),
            "get_multi": ("MGET", True),
            "set_multi": ("MSET", False),
            "delete_multi": ("DELETE", False),
            "incr": ("INCR", False),
            "decr": ("DECR", False),
            "add": ("SET", False),
            "replace": ("SET", False),
            "append": ("SET", False),
            "prepend": ("SET", False),
        }

        for method_name, (operation, is_read) in methods_to_patch.items():
            original_method = getattr(Client, method_name, None)
            if original_method is None:
                continue

            self._original_memcache_methods[method_name] = original_method

            def create_wrapper(
                orig_method: Any,
                op: CacheOperation,
                check_hit: bool,  # noqa: FBT001
            ) -> Any:
                def wrapper(self_client: Any, *args: Any, **kwargs: Any) -> Any:
                    start = time.perf_counter()
                    result = orig_method(self_client, *args, **kwargs)
                    duration = time.perf_counter() - start

                    key = args[0] if args else "unknown"
                    hit = None
                    if check_hit:
                        if isinstance(result, dict):
                            hit = len(result) > 0
                        else:
                            hit = result is not None

                    tracker = _get_tracker()
                    if tracker:
                        tracker._record_operation(  # noqa: SLF001
                            operation=op,
                            key=key,
                            hit=hit,
                            duration=duration,
                            backend="memcached",
                        )

                    return result

                return wrapper

            setattr(
                Client,
                method_name,
                create_wrapper(original_method, operation, is_read),  # type: ignore[arg-type]
            )

        Client._debug_toolbar_patched = True  # type: ignore[attr-defined]  # noqa: SLF001

    def _unpatch_memcache(self) -> None:
        """Restore original pymemcache methods."""
        try:
            from pymemcache.client.base import Client  # type: ignore[import-untyped]
        except ImportError:
            return

        if not hasattr(Client, "_debug_toolbar_patched"):
            return

        for method_name, original_method in self._original_memcache_methods.items():
            setattr(Client, method_name, original_method)

        delattr(Client, "_debug_toolbar_patched")
        self._original_memcache_methods.clear()

    def _record_operation(
        self,
        operation: CacheOperation,
        key: str | list[str],
        hit: bool | None,  # noqa: FBT001
        duration: float,
        backend: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Record a cache operation."""
        self.operations.append(
            CacheOperationRecord(
                operation=operation,
                key=key,
                hit=hit,
                duration=duration,
                timestamp=time.time(),
                backend=backend,
                extra=extra or {},
            )
        )

    @contextmanager
    def track_operation(
        self,
        operation: CacheOperation,
        key: str | list[str],
        backend: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager for tracking custom cache operations."""
        start = time.perf_counter()
        extra: dict[str, Any] = {}
        yield extra

        duration = time.perf_counter() - start
        hit = extra.get("hit")

        self._record_operation(
            operation=operation,
            key=key,
            hit=hit,
            duration=duration,
            backend=backend,
            extra=extra,
        )


_active_tracker: ContextVar[CacheTracker | None] = ContextVar("_active_tracker", default=None)


def _get_tracker() -> CacheTracker | None:
    """Get the currently active cache tracker."""
    return _active_tracker.get()


def _set_tracker(tracker: CacheTracker | None) -> None:
    """Set the active cache tracker."""
    _active_tracker.set(tracker)


class CachePanel(Panel):
    """Panel displaying cache operations during the request.

    Tracks:
    - Cache operations (GET, SET, DELETE, etc.)
    - Hit/miss status
    - Operation duration
    - Backend type (Redis, memcached)
    - Aggregate statistics
    """

    panel_id: ClassVar[str] = "CachePanel"
    title: ClassVar[str] = "Cache"
    template: ClassVar[str] = "panels/cache.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Cache"

    __slots__ = ("_tracker",)

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._tracker = CacheTracker()

    async def process_request(self, context: RequestContext) -> None:
        """Start tracking cache operations."""
        self._tracker.clear()
        _set_tracker(self._tracker)
        self._tracker.start_tracking()

    async def process_response(self, context: RequestContext) -> None:
        """Stop tracking cache operations."""
        self._tracker.stop_tracking()
        _set_tracker(None)

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate cache statistics."""
        operations = self._tracker.operations

        total_operations = len(operations)
        hits = sum(1 for op in operations if op.hit is True)
        misses = sum(1 for op in operations if op.hit is False)
        total_time = sum(op.duration for op in operations)

        hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0.0
        avg_time = total_time / total_operations if total_operations > 0 else 0.0

        backends = sorted({op.backend for op in operations})

        operation_list = [
            {
                "operation": op.operation,
                "key": op.key if isinstance(op.key, str) else ",".join(op.key),
                "hit": op.hit,
                "duration": op.duration,
                "duration_ms": op.duration * 1000,
                "timestamp": op.timestamp,
                "backend": op.backend,
                "extra": op.extra,
            }
            for op in operations
        ]

        by_operation: dict[str, int] = {}
        by_backend: dict[str, int] = {}
        for op in operations:
            by_operation[op.operation] = by_operation.get(op.operation, 0) + 1
            by_backend[op.backend] = by_backend.get(op.backend, 0) + 1

        stats = {
            "operations": operation_list,
            "total_operations": total_operations,
            "hits": hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "total_time": total_time,
            "avg_time": avg_time,
            "backends": backends,
            "by_operation": by_operation,
            "by_backend": by_backend,
        }

        if total_time > 0:
            context.record_timing("cache_time", total_time)

        return stats

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing data for cache operations."""
        stats = self.get_stats(context)
        if not stats:
            return {}

        timing: dict[str, float] = {}

        total_time = stats.get("total_time", 0)
        if total_time > 0:
            timing["cache"] = total_time

        by_backend = stats.get("by_backend", {})
        operations = stats.get("operations", [])

        for backend in by_backend:
            backend_time = sum(op["duration"] for op in operations if op["backend"] == backend)
            if backend_time > 0:
                timing[f"cache-{backend}"] = backend_time

        return timing

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing cache stats."""
        return ""
