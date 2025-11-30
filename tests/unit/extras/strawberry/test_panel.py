"""Tests for GraphQLPanel."""

from __future__ import annotations

import pytest

from debug_toolbar.core.config import DebugToolbarConfig
from debug_toolbar.core.context import RequestContext, set_request_context
from debug_toolbar.core.toolbar import DebugToolbar
from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver
from debug_toolbar.extras.strawberry.panel import GraphQLPanel


@pytest.fixture
def toolbar() -> DebugToolbar:
    """Create toolbar instance."""
    config = DebugToolbarConfig(enabled=True)
    return DebugToolbar(config=config)


@pytest.fixture
def panel(toolbar: DebugToolbar) -> GraphQLPanel:
    """Create GraphQLPanel instance."""
    return GraphQLPanel(toolbar)


@pytest.fixture
def context() -> RequestContext:
    """Create request context."""
    ctx = RequestContext()
    set_request_context(ctx)
    yield ctx
    set_request_context(None)


class TestGraphQLPanelInit:
    """Tests for GraphQLPanel initialization."""

    def test_panel_id(self, panel: GraphQLPanel) -> None:
        """Should have correct panel ID."""
        assert panel.get_panel_id() == "GraphQLPanel"

    def test_panel_title(self, panel: GraphQLPanel) -> None:
        """Should have correct title."""
        assert panel.title == "GraphQL"

    def test_default_thresholds(self, toolbar: DebugToolbar) -> None:
        """Should use default threshold values."""
        panel = GraphQLPanel(toolbar)
        assert panel._slow_operation_threshold_ms == 100.0
        assert panel._slow_resolver_threshold_ms == 10.0
        assert panel._n1_threshold == 3

    def test_custom_thresholds(self, toolbar: DebugToolbar) -> None:
        """Should accept custom threshold values."""
        panel = GraphQLPanel(
            toolbar,
            slow_operation_threshold_ms=200.0,
            slow_resolver_threshold_ms=20.0,
            n1_threshold=5,
        )
        assert panel._slow_operation_threshold_ms == 200.0
        assert panel._slow_resolver_threshold_ms == 20.0
        assert panel._n1_threshold == 5


class TestGraphQLPanelGenerateStats:
    """Tests for generate_stats method."""

    @pytest.mark.asyncio
    async def test_no_operations(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should return empty stats when no operations tracked."""
        stats = await panel.generate_stats(context)

        assert stats["operation_count"] == 0
        assert stats["total_time_ms"] == 0.0
        assert stats["resolver_count"] == 0
        assert stats["n_plus_one_patterns"] == []
        assert stats["n_plus_one_count"] == 0
        assert stats["duplicate_operations"] == []
        assert stats["duplicate_count"] == 0
        assert stats["slow_operations"] == []
        assert stats["slow_operation_count"] == 0
        assert stats["has_issues"] is False

    @pytest.mark.asyncio
    async def test_with_single_operation(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should calculate stats from single operation."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name="GetUser",
            operation_type="query",
            start_time=0.0,
            end_time=0.15,
            duration_ms=150.0,
            resolvers=[
                TrackedResolver(
                    resolver_id="r1",
                    field_name="user",
                    field_path="Query.user",
                    resolver_function="Query.user",
                    parent_type="Query",
                    return_type="User",
                    duration_ms=150.0,
                )
            ],
        )

        context.store_panel_data("GraphQLPanel", "operations", [operation])

        stats = await panel.generate_stats(context)

        assert stats["operation_count"] == 1
        assert stats["total_time_ms"] == 150.0
        assert stats["resolver_count"] == 1
        assert stats["slow_operation_count"] == 1

    @pytest.mark.asyncio
    async def test_with_multiple_operations(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should aggregate stats from multiple operations."""
        operations = [
            TrackedOperation(
                operation_id=f"op{i}",
                query=f"query {{ user(id: {i}) {{ name }} }}",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=0.0,
                duration_ms=50.0,
                resolvers=[
                    TrackedResolver(
                        resolver_id=f"r{i}",
                        field_name="user",
                        field_path="Query.user",
                        resolver_function="Query.user",
                        parent_type="Query",
                        return_type="User",
                        duration_ms=50.0,
                    )
                ],
            )
            for i in range(3)
        ]

        context.store_panel_data("GraphQLPanel", "operations", operations)

        stats = await panel.generate_stats(context)

        assert stats["operation_count"] == 3
        assert stats["total_time_ms"] == 150.0
        assert stats["resolver_count"] == 3

    @pytest.mark.asyncio
    async def test_detects_n_plus_one(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should detect N+1 patterns."""
        resolvers = [
            TrackedResolver(
                resolver_id=f"r{i}",
                field_name="posts",
                field_path=f"Query.users.{i}.posts",
                resolver_function="User.posts",
                parent_type="User",
                return_type="[Post]",
                duration_ms=10.0,
            )
            for i in range(5)
        ]

        operation = TrackedOperation(
            operation_id="op1",
            query="query { users { posts } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            duration_ms=50.0,
            resolvers=resolvers,
        )

        context.store_panel_data("GraphQLPanel", "operations", [operation])

        stats = await panel.generate_stats(context)

        assert stats["n_plus_one_count"] >= 1
        assert stats["has_issues"] is True

    @pytest.mark.asyncio
    async def test_detects_duplicates(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should detect duplicate operations."""
        operations = [
            TrackedOperation(
                operation_id=f"op{i}",
                query="query { user(id: 1) { name } }",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=float(i) * 0.1,
                duration_ms=50.0,
            )
            for i in range(2)
        ]

        context.store_panel_data("GraphQLPanel", "operations", operations)

        stats = await panel.generate_stats(context)

        assert stats["duplicate_count"] > 0
        assert stats["has_issues"] is True

    @pytest.mark.asyncio
    async def test_marks_slow_resolvers(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should mark slow resolvers."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { user { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            duration_ms=150.0,
            resolvers=[
                TrackedResolver(
                    resolver_id="r1",
                    field_name="user",
                    field_path="Query.user",
                    resolver_function="Query.user",
                    parent_type="Query",
                    return_type="User",
                    duration_ms=15.0,
                ),
                TrackedResolver(
                    resolver_id="r2",
                    field_name="name",
                    field_path="Query.user.name",
                    resolver_function="User.name",
                    parent_type="User",
                    return_type="String",
                    duration_ms=5.0,
                ),
            ],
        )

        context.store_panel_data("GraphQLPanel", "operations", [operation])

        await panel.generate_stats(context)

        slow_resolver = next(r for r in operation.resolvers if r.resolver_id == "r1")
        fast_resolver = next(r for r in operation.resolvers if r.resolver_id == "r2")

        assert slow_resolver.is_slow is True
        assert fast_resolver.is_slow is False


class TestGraphQLPanelResolverTree:
    """Tests for resolver tree building."""

    def test_build_simple_tree(self, panel: GraphQLPanel) -> None:
        """Should build simple resolver tree."""
        resolvers = [
            TrackedResolver(
                resolver_id="r1",
                field_name="user",
                field_path="Query.user",
                resolver_function="Query.user",
                parent_type="Query",
                return_type="User",
            ),
            TrackedResolver(
                resolver_id="r2",
                field_name="name",
                field_path="Query.user.name",
                resolver_function="User.name",
                parent_type="User",
                return_type="String",
            ),
        ]

        tree = panel._build_resolver_tree(resolvers)

        assert len(tree) == 1
        assert tree[0]["resolver"]["field_name"] == "user"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["resolver"]["field_name"] == "name"

    def test_build_tree_with_multiple_roots(self, panel: GraphQLPanel) -> None:
        """Should handle multiple root resolvers."""
        resolvers = [
            TrackedResolver(
                resolver_id="r1",
                field_name="user",
                field_path="Query.user",
                resolver_function="Query.user",
                parent_type="Query",
                return_type="User",
            ),
            TrackedResolver(
                resolver_id="r2",
                field_name="posts",
                field_path="Query.posts",
                resolver_function="Query.posts",
                parent_type="Query",
                return_type="[Post]",
            ),
        ]

        tree = panel._build_resolver_tree(resolvers)

        assert len(tree) == 2

    def test_build_tree_empty_resolvers(self, panel: GraphQLPanel) -> None:
        """Should handle empty resolvers list."""
        tree = panel._build_resolver_tree([])
        assert tree == []


class TestGraphQLPanelServerTiming:
    """Tests for Server-Timing generation."""

    @pytest.mark.asyncio
    async def test_generate_server_timing(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should generate Server-Timing header data."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            duration_ms=150.0,
        )

        context.store_panel_data("GraphQLPanel", "operations", [operation])

        stats = await panel.generate_stats(context)
        panel.record_stats(context, stats)

        timing = panel.generate_server_timing(context)

        assert "graphql" in timing
        assert timing["graphql"] == 0.15

    def test_generate_server_timing_no_stats(self, panel: GraphQLPanel, context: RequestContext) -> None:
        """Should return empty dict when no stats."""
        timing = panel.generate_server_timing(context)
        assert timing == {}


class TestGraphQLPanelNavSubtitle:
    """Tests for nav subtitle."""

    def test_get_nav_subtitle(self, panel: GraphQLPanel) -> None:
        """Should return empty string."""
        subtitle = panel.get_nav_subtitle()
        assert subtitle == ""
