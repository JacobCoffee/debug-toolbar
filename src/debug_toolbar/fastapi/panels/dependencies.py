"""Dependency Injection panel for FastAPI debug toolbar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class DependencyInjectionPanel(Panel):
    """Panel displaying FastAPI dependency injection information.

    Shows:
    - All resolved dependencies for the current request
    - Cache status (cached vs fresh) for each dependency
    - Resolution time in milliseconds
    - Dependency type (function, class, generator)
    - Cache hit/miss statistics
    """

    panel_id: ClassVar[str] = "DependencyInjectionPanel"
    title: ClassVar[str] = "Dependencies"
    template: ClassVar[str] = ""
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Dependencies"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate dependency injection statistics.

        Args:
            context: The current request context.

        Returns:
            Dictionary containing dependency information.
        """
        dependencies_data = context.metadata.get("dependencies", {})

        resolved = dependencies_data.get("resolved", [])
        dependency_tree = dependencies_data.get("tree", {})
        cache_stats = dependencies_data.get("cache_stats", {})

        total_time_ms = sum(d.get("duration_ms", 0) for d in resolved)
        cached_count = sum(1 for d in resolved if d.get("cached", False))
        total_count = len(resolved)

        cache_hit_rate = (cached_count / total_count * 100) if total_count > 0 else 0

        return {
            "resolved_dependencies": resolved,
            "dependency_tree": dependency_tree,
            "total_count": total_count,
            "cached_count": cached_count,
            "fresh_count": total_count - cached_count,
            "cache_hit_rate": cache_hit_rate,
            "total_time_ms": total_time_ms,
            "cache_stats": cache_stats,
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing dependency count."""
        return ""


def collect_dependency_metadata(context: RequestContext) -> None:
    """Initialize dependency metadata in the context.

    Args:
        context: The request context to initialize.
    """
    context.metadata["dependencies"] = {
        "resolved": [],
        "tree": {},
        "cache_stats": {"hits": 0, "misses": 0, "total": 0},
    }


def record_dependency_resolution(
    context: RequestContext,
    dependency_name: str,
    dependency_type: str,
    *,
    cached: bool,
    duration_ms: float,
    module: str | None = None,
    cache_key: str | None = None,
    params: dict[str, Any] | None = None,
    dependency_path: list[str] | None = None,
) -> None:
    """Record a dependency resolution event to the context.

    Args:
        context: The request context.
        dependency_name: Name of the dependency.
        dependency_type: Type of dependency (function, class, generator).
        cached: Whether the result came from cache.
        duration_ms: Resolution time in milliseconds.
        module: Module where the dependency is defined.
        cache_key: Cache key used by FastAPI.
        params: Parameters passed to the dependency.
        dependency_path: Path in the dependency tree.
    """
    if "dependencies" not in context.metadata:
        collect_dependency_metadata(context)

    resolution_record = {
        "name": dependency_name,
        "type": dependency_type,
        "cached": cached,
        "duration_ms": duration_ms,
        "module": module or "",
        "cache_key": cache_key or "",
        "params": params or {},
        "dependency_path": dependency_path or [dependency_name],
    }

    context.metadata["dependencies"]["resolved"].append(resolution_record)

    stats = context.metadata["dependencies"]["cache_stats"]
    stats["total"] += 1
    if cached:
        stats["hits"] += 1
    else:
        stats["misses"] += 1


def _get_dependency_info(dependency: Any) -> dict[str, Any]:
    """Extract information about a dependency callable.

    Args:
        dependency: The dependency function/class.

    Returns:
        Dictionary with dependency information.
    """
    import inspect

    name = getattr(dependency, "__name__", str(dependency))
    module = getattr(dependency, "__module__", "")

    if inspect.isgeneratorfunction(dependency) or inspect.isasyncgenfunction(dependency):
        dep_type = "generator"
    elif inspect.isclass(dependency):
        dep_type = "class"
    elif inspect.iscoroutinefunction(dependency):
        dep_type = "async_function"
    else:
        dep_type = "function"

    try:
        source_file = inspect.getfile(dependency)
        source_lines = inspect.getsourcelines(dependency)
        source_line = source_lines[1] if source_lines else None
    except (TypeError, OSError):
        source_file = None
        source_line = None

    return {
        "name": name,
        "module": module,
        "type": dep_type,
        "source_file": source_file,
        "source_line": source_line,
    }
