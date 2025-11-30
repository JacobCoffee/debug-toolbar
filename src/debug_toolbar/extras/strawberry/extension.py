"""Strawberry SchemaExtension for debug toolbar integration."""

from __future__ import annotations

import inspect
import logging
import time
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver
from debug_toolbar.extras.strawberry.utils import StackCapture, get_operation_type_from_query

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo
    from strawberry.types import ExecutionContext
    from strawberry.utils.await_maybe import AwaitableOrValue

    from debug_toolbar.core.context import RequestContext

logger = logging.getLogger(__name__)

try:
    from strawberry.extensions import SchemaExtension as _SchemaExtension

    STRAWBERRY_AVAILABLE = True
except ImportError:
    STRAWBERRY_AVAILABLE = False
    _SchemaExtension = object  # type: ignore[assignment, misc]


class DebugToolbarExtension(_SchemaExtension):  # type: ignore[misc]
    """Strawberry extension for tracking GraphQL operations and resolvers.

    Integrates with debug toolbar's RequestContext to store operation and
    resolver timing data for display in the GraphQL panel.

    Usage:
        schema = strawberry.Schema(
            query=Query,
            extensions=[DebugToolbarExtension()],
        )

    Args:
        slow_operation_threshold_ms: Threshold for marking operations as slow.
        slow_resolver_threshold_ms: Threshold for marking resolvers as slow.
        capture_stacks: Whether to capture stack traces for resolvers.
    """

    __slots__ = (
        "_capture_stacks",
        "_slow_operation_threshold_ms",
        "_slow_resolver_threshold_ms",
    )

    def __init__(
        self,
        *,
        slow_operation_threshold_ms: float = 100.0,
        slow_resolver_threshold_ms: float = 10.0,
        capture_stacks: bool = True,
    ) -> None:
        """Initialize the extension.

        Args:
            slow_operation_threshold_ms: Threshold for marking operations as slow.
            slow_resolver_threshold_ms: Threshold for marking resolvers as slow.
            capture_stacks: Whether to capture stack traces for resolvers.
        """
        self._slow_operation_threshold_ms = slow_operation_threshold_ms
        self._slow_resolver_threshold_ms = slow_resolver_threshold_ms
        self._capture_stacks = capture_stacks
        if STRAWBERRY_AVAILABLE:
            super().__init__()

    def _get_debug_context(self) -> RequestContext | None:
        """Get the debug toolbar context from contextvar or Strawberry context.

        Returns:
            RequestContext if available, None otherwise.
        """
        from debug_toolbar.core.context import get_request_context

        # First try contextvar
        context = get_request_context()
        if context is not None:
            logger.debug("_get_debug_context: found context from contextvar")
            return context

        # Fall back to Strawberry's execution context
        exec_ctx: ExecutionContext = self.execution_context
        logger.debug("_get_debug_context: exec_ctx.context=%s", getattr(exec_ctx, "context", None))
        if hasattr(exec_ctx, "context") and exec_ctx.context:
            strawberry_ctx = exec_ctx.context
            # Check if debug_toolbar_context was injected
            if hasattr(strawberry_ctx, "debug_toolbar_context"):
                logger.debug("_get_debug_context: found context from attr")
                return strawberry_ctx.debug_toolbar_context
            # Check dict-like context
            if isinstance(strawberry_ctx, dict):
                result = strawberry_ctx.get("debug_toolbar_context")
                logger.debug("_get_debug_context: found context from dict: %s", result)
                return result

        logger.debug("_get_debug_context: no context found")
        return None

    def on_operation(self) -> Generator[None, None, None]:
        """Track GraphQL operation (query/mutation/subscription).

        Runs before and after the entire GraphQL operation executes.

        Yields:
            None
        """
        context = self._get_debug_context()
        if context is None:
            yield
            return

        exec_ctx: ExecutionContext = self.execution_context
        query = exec_ctx.query or ""

        operation = TrackedOperation(
            operation_id=str(uuid4()),
            query=query,
            variables=exec_ctx.variables or {},
            operation_name=exec_ctx.operation_name,
            operation_type=get_operation_type_from_query(query),  # type: ignore[arg-type]
            start_time=time.perf_counter(),
        )

        context.store_panel_data("GraphQLPanel", "current_operation", operation)

        try:
            yield
        finally:
            operation.end_time = time.perf_counter()
            operation.duration_ms = (operation.end_time - operation.start_time) * 1000

            if hasattr(exec_ctx, "result") and exec_ctx.result is not None:
                result = exec_ctx.result
                if hasattr(result, "errors") and result.errors:
                    operation.errors = [
                        {
                            "message": str(getattr(err, "message", str(err))),
                            "path": list(err.path) if hasattr(err, "path") and err.path else None,
                            "locations": (
                                [{"line": loc.line, "column": loc.column} for loc in (err.locations or [])]
                                if hasattr(err, "locations")
                                else None
                            ),
                        }
                        for err in result.errors
                    ]

            panel_data = context.get_panel_data("GraphQLPanel")
            operations = panel_data.get("operations", [])
            operations.append(operation)
            context.store_panel_data("GraphQLPanel", "operations", operations)
            context.store_panel_data("GraphQLPanel", "current_operation", None)

    def resolve(
        self,
        _next: Callable[..., Any],
        root: Any,
        info: GraphQLResolveInfo,
        *args: str,
        **kwargs: Any,
    ) -> AwaitableOrValue[object]:
        """Track individual resolver execution.

        Called for every field resolver. Measures timing and captures metadata.
        Handles both sync and async resolvers correctly.

        Args:
            _next: Next resolver in chain.
            root: Parent object.
            info: GraphQL resolve info.
            *args: Positional arguments to resolver.
            **kwargs: Keyword arguments to resolver.

        Returns:
            Resolver result.
        """
        context = self._get_debug_context()
        if context is None:
            return _next(root, info, *args, **kwargs)

        start_time = time.perf_counter()

        parent_type_name = "Unknown"
        if info.parent_type is not None:
            parent_type_name = info.parent_type.name

        field_name = info.field_name
        field_path = self._build_field_path(info)
        return_type_str = str(info.return_type) if info.return_type else "Unknown"

        resolver = TrackedResolver(
            resolver_id=str(uuid4()),
            field_name=field_name,
            field_path=field_path,
            resolver_function=f"{parent_type_name}.{field_name}",
            parent_type=parent_type_name,
            return_type=return_type_str,
            arguments=dict(kwargs),
        )

        if self._capture_stacks:
            resolver.stack_trace = StackCapture.capture()

        def _record_resolver() -> None:
            """Record resolver timing and add to current operation."""
            resolver.end_time = time.perf_counter()
            resolver.duration_ms = (resolver.end_time - start_time) * 1000
            resolver.is_slow = resolver.duration_ms >= self._slow_resolver_threshold_ms

            current_op = context.get_panel_data("GraphQLPanel").get("current_operation")
            if current_op:
                current_op.resolvers.append(resolver)

        try:
            result = _next(root, info, *args, **kwargs)
        except Exception:
            _record_resolver()
            raise

        if inspect.isawaitable(result):

            async def _wrap_async() -> Any:
                try:
                    return await result
                finally:
                    _record_resolver()

            return _wrap_async()

        _record_resolver()
        return result

    def _build_field_path(self, info: GraphQLResolveInfo) -> str:
        """Build field path from Info.path.

        Args:
            info: GraphQL resolve info.

        Returns:
            Dot-separated field path (e.g., 'Query.user.posts.0.title').
        """
        path_parts = []
        current = info.path
        while current:
            if current.key is not None:
                path_parts.append(str(current.key))
            current = current.prev
        return ".".join(reversed(path_parts)) if path_parts else info.field_name

    @classmethod
    def is_available(cls) -> bool:
        """Check if Strawberry is available.

        Returns:
            True if strawberry-graphql is installed.
        """
        return STRAWBERRY_AVAILABLE
