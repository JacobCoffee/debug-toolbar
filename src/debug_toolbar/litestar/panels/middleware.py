"""Middleware panel showing the Litestar v3 middleware stack and per-request bypass decisions.

This panel relies on :class:`~litestar.middleware.base.ASGIMiddleware`, its
``should_bypass_for_handler``/``should_bypass_for_scope`` hooks, and
:class:`~litestar.middleware.constraints.MiddlewareConstraints`, all introduced in
Litestar 3. It has no equivalent on Litestar 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from litestar.types import Scope

    from debug_toolbar.core.context import RequestContext


def _middleware_name(middleware: Any) -> str:
    """Return a dotted ``module.Qualname`` for a middleware instance or class."""
    cls = middleware if isinstance(middleware, type) else type(middleware)
    module = getattr(cls, "__module__", "")
    qualname = getattr(cls, "__qualname__", cls.__name__)
    return f"{module}.{qualname}" if module else qualname


def _constraint_target_name(target: Any) -> str:
    """Return a readable name for a constraint's ``before``/``after`` target."""
    forward_ref_target = getattr(target, "target", None)
    if forward_ref_target is not None and hasattr(target, "resolve"):
        return str(forward_ref_target)
    return _middleware_name(target)


def _collect_constraints(middleware: Any) -> dict[str, Any] | None:
    """Return the declared :class:`MiddlewareConstraints` for ``middleware``, if any."""
    constraints = getattr(middleware, "constraints", None)
    if constraints is None:
        return None

    before = [_constraint_target_name(target) for target in getattr(constraints, "before", ())]
    after = [_constraint_target_name(target) for target in getattr(constraints, "after", ())]
    first = bool(getattr(constraints, "first", False))
    last = bool(getattr(constraints, "last", False))
    unique = getattr(constraints, "unique", None)

    if not (before or after or first or last or unique):
        return None

    return {"before": before, "after": after, "first": first, "last": last, "unique": unique}


def collect_middleware_metadata(scope: Scope, context: RequestContext) -> None:
    """Collect the resolved middleware stack for the matched route and this request's bypass decisions.

    Args:
        scope: The ASGI connection scope for the current request.
        context: The request context to populate.
    """
    try:
        from litestar.middleware.base import ASGIMiddleware
    except ImportError:
        # Litestar 2 has no ASGIMiddleware - this panel has nothing to show.
        context.metadata["middleware"] = []
        return

    route_handler = scope.get("route_handler")
    middleware_list = list(getattr(route_handler, "middleware", ()) or ())

    entries: list[dict[str, Any]] = []
    for middleware in middleware_list:
        entry: dict[str, Any] = {
            "name": _middleware_name(middleware),
            "ran": True,
            "skip_reason": None,
            "constraints": _collect_constraints(middleware),
        }

        if isinstance(middleware, ASGIMiddleware):
            if route_handler is not None and middleware.should_bypass_for_handler(route_handler):
                entry["ran"] = False
                entry["skip_reason"] = "excluded for this route (scope type, exclude_opt_key, or exclude_path_pattern)"
            elif middleware.should_bypass_for_scope is not None and middleware.should_bypass_for_scope(scope):
                entry["ran"] = False
                entry["skip_reason"] = "excluded dynamically for this request (should_bypass_for_scope)"

        entries.append(entry)

    context.metadata["middleware"] = entries


class MiddlewarePanel(Panel):
    """Panel displaying the middleware stack for the matched route handler (Litestar 3 only).

    Shows:
    - Every middleware configured on the application, router, controller, or handler layers
      for the route that matched this request, in the order it runs
    - Any ordering rules (``before``/``after``/``first``/``last``/``unique``) a middleware
      declares via :class:`~litestar.middleware.constraints.MiddlewareConstraints`
    - Whether each middleware actually ran for this request, or was skipped, and why
    """

    panel_id: ClassVar[str] = "MiddlewarePanel"
    title: ClassVar[str] = "Middleware"
    template: ClassVar[str] = "panels/middleware.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Middleware"

    __slots__ = ("_middleware_count", "_skipped_count")

    def __init__(self, toolbar: Any) -> None:
        """Initialize the middleware panel."""
        super().__init__(toolbar)
        self._middleware_count = 0
        self._skipped_count = 0

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate middleware stack statistics."""
        middleware = context.metadata.get("middleware", [])
        self._middleware_count = len(middleware)
        self._skipped_count = sum(1 for entry in middleware if not entry["ran"])

        return {
            "middleware": middleware,
            "middleware_count": self._middleware_count,
            "skipped_count": self._skipped_count,
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing middleware counts."""
        if not self._middleware_count:
            return ""
        if self._skipped_count:
            return f"{self._middleware_count} ({self._skipped_count} skipped)"
        return str(self._middleware_count)
