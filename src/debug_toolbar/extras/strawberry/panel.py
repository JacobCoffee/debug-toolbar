"""GraphQL panel for tracking Strawberry GraphQL operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel
from debug_toolbar.extras.strawberry.analyzers import DuplicateDetector, N1Analyzer

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar
    from debug_toolbar.extras.strawberry.models import TrackedResolver


class GraphQLPanel(Panel):
    """Panel displaying GraphQL operation and resolver information.

    Shows:
    - GraphQL operations (queries, mutations, subscriptions)
    - Resolver execution timing and hierarchy
    - N+1 resolver pattern detection
    - Duplicate operation detection
    - Slow operation/resolver highlighting
    - Error tracking with field paths

    Requires:
    - strawberry-graphql >= 0.240.0
    - DebugToolbarExtension added to Strawberry schema
    """

    panel_id: ClassVar[str] = "GraphQLPanel"
    title: ClassVar[str] = "GraphQL"
    template: ClassVar[str] = "panels/graphql.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "GraphQL"

    __slots__ = (
        "_n1_threshold",
        "_slow_operation_threshold_ms",
        "_slow_resolver_threshold_ms",
    )

    def __init__(
        self,
        toolbar: DebugToolbar,
        slow_operation_threshold_ms: float = 100.0,
        slow_resolver_threshold_ms: float = 10.0,
        n1_threshold: int = 3,
    ) -> None:
        """Initialize the panel.

        Args:
            toolbar: Parent DebugToolbar instance.
            slow_operation_threshold_ms: Threshold for slow operations (ms).
            slow_resolver_threshold_ms: Threshold for slow resolvers (ms).
            n1_threshold: Minimum resolver count for N+1 detection.
        """
        super().__init__(toolbar)
        self._slow_operation_threshold_ms = slow_operation_threshold_ms
        self._slow_resolver_threshold_ms = slow_resolver_threshold_ms
        self._n1_threshold = n1_threshold

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate GraphQL statistics.

        Args:
            context: Request context containing tracked operations.

        Returns:
            Statistics dictionary for template rendering.
        """
        panel_data = context.get_panel_data(self.get_panel_id())
        operations = panel_data.get("operations", [])

        if not operations:
            return {
                "operations": [],
                "operation_count": 0,
                "total_time_ms": 0.0,
                "resolver_count": 0,
                "n_plus_one_patterns": [],
                "n_plus_one_count": 0,
                "duplicate_operations": [],
                "duplicate_count": 0,
                "slow_operations": [],
                "slow_operation_count": 0,
                "slow_operation_threshold_ms": self._slow_operation_threshold_ms,
                "slow_resolver_threshold_ms": self._slow_resolver_threshold_ms,
                "has_issues": False,
            }

        total_time_ms = sum(op.duration_ms for op in operations)
        resolver_count = sum(len(op.resolvers) for op in operations)

        n1_analyzer = N1Analyzer(threshold=self._n1_threshold)
        n_plus_one_patterns = n1_analyzer.analyze(operations)

        duplicate_detector = DuplicateDetector()
        duplicate_op_ids = duplicate_detector.detect(operations)

        slow_operations = [op for op in operations if op.duration_ms >= self._slow_operation_threshold_ms]

        for operation in operations:
            for resolver in operation.resolvers:
                resolver.is_slow = resolver.duration_ms >= self._slow_resolver_threshold_ms

        operations_data = []
        for operation in operations:
            op_data = operation.to_dict()
            op_data["resolver_tree"] = self._build_resolver_tree(operation.resolvers)
            op_data["is_slow"] = operation.duration_ms >= self._slow_operation_threshold_ms
            op_data["is_duplicate"] = operation.operation_id in duplicate_op_ids
            operations_data.append(op_data)

        return {
            "operations": operations_data,
            "operation_count": len(operations),
            "total_time_ms": total_time_ms,
            "resolver_count": resolver_count,
            "n_plus_one_patterns": n_plus_one_patterns,
            "n_plus_one_count": len(n_plus_one_patterns),
            "duplicate_operations": duplicate_op_ids,
            "duplicate_count": len(set(duplicate_op_ids)),
            "slow_operations": [op.to_dict() for op in slow_operations],
            "slow_operation_count": len(slow_operations),
            "slow_operation_threshold_ms": self._slow_operation_threshold_ms,
            "slow_resolver_threshold_ms": self._slow_resolver_threshold_ms,
            "has_issues": bool(n_plus_one_patterns or duplicate_op_ids or slow_operations),
        }

    def _build_resolver_tree(self, resolvers: list[TrackedResolver]) -> list[dict[str, Any]]:
        """Build hierarchical resolver tree from flat list.

        Args:
            resolvers: Flat list of TrackedResolver objects.

        Returns:
            Nested tree structure for template rendering.
        """
        tree_map: dict[str, dict[str, Any]] = {}

        for resolver in resolvers:
            path = resolver.field_path
            tree_map[path] = {
                "resolver": resolver.to_dict(),
                "children": [],
            }

        root_nodes = []
        for path, node in tree_map.items():
            path_parts = path.split(".")
            if len(path_parts) <= 1:
                root_nodes.append(node)
            else:
                # Walk up the path to find the closest existing ancestor
                parent_found = False
                for i in range(len(path_parts) - 1, 0, -1):
                    parent_path = ".".join(path_parts[:i])
                    if parent_path in tree_map:
                        tree_map[parent_path]["children"].append(node)
                        parent_found = True
                        break
                if not parent_found:
                    root_nodes.append(node)

        return root_nodes

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data.

        Args:
            context: Request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats:
            return {}

        total_time_ms = stats.get("total_time_ms", 0.0)
        return {"graphql": total_time_ms / 1000.0}

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle.

        Returns:
            Empty string (subtitle populated by generate_stats).
        """
        return ""
