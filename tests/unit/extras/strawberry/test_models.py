"""Tests for GraphQL data models."""

from __future__ import annotations

from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver


class TestTrackedResolver:
    """Tests for TrackedResolver dataclass."""

    def test_create_resolver_with_required_fields(self) -> None:
        """Should create resolver with required fields."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
        )

        assert resolver.resolver_id == "r1"
        assert resolver.field_name == "user"
        assert resolver.field_path == "Query.user"
        assert resolver.resolver_function == "Query.user"
        assert resolver.parent_type == "Query"
        assert resolver.return_type == "User"

    def test_resolver_default_values(self) -> None:
        """Should have correct default values."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
        )

        assert resolver.arguments == {}
        assert resolver.start_time == 0.0
        assert resolver.end_time == 0.0
        assert resolver.duration_ms == 0.0
        assert resolver.stack_trace is None
        assert resolver.is_slow is False

    def test_resolver_with_timing(self) -> None:
        """Should store timing information."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
            start_time=100.0,
            end_time=100.05,
            duration_ms=50.0,
            is_slow=True,
        )

        assert resolver.start_time == 100.0
        assert resolver.end_time == 100.05
        assert resolver.duration_ms == 50.0
        assert resolver.is_slow is True

    def test_resolver_with_arguments(self) -> None:
        """Should store resolver arguments."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
            arguments={"id": 1, "name": "test"},
        )

        assert resolver.arguments == {"id": 1, "name": "test"}

    def test_resolver_with_stack_trace(self) -> None:
        """Should store stack trace."""
        stack = [
            {"file": "app.py", "line": 10, "function": "get_user", "code": "return user"},
        ]
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
            stack_trace=stack,
        )

        assert resolver.stack_trace == stack

    def test_resolver_to_dict(self) -> None:
        """Should convert to dictionary."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
            arguments={"id": 1},
            duration_ms=50.0,
            is_slow=True,
        )

        result = resolver.to_dict()

        assert result["resolver_id"] == "r1"
        assert result["field_name"] == "user"
        assert result["field_path"] == "Query.user"
        assert result["arguments"] == {"id": 1}
        assert result["duration_ms"] == 50.0
        assert result["is_slow"] is True


class TestTrackedOperation:
    """Tests for TrackedOperation dataclass."""

    def test_create_operation_with_required_fields(self) -> None:
        """Should create operation with required fields."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=100.0,
        )

        assert operation.operation_id == "op1"
        assert operation.query == "query { user(id: 1) { name } }"
        assert operation.variables == {}
        assert operation.operation_name is None
        assert operation.operation_type == "query"
        assert operation.start_time == 100.0

    def test_operation_default_values(self) -> None:
        """Should have correct default values."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=100.0,
        )

        assert operation.end_time == 0.0
        assert operation.duration_ms == 0.0
        assert operation.resolvers == []
        assert operation.errors is None
        assert operation.result_data is None

    def test_operation_with_variables(self) -> None:
        """Should store operation variables."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query GetUser($id: ID!) { user(id: $id) { name } }",
            variables={"id": "123"},
            operation_name="GetUser",
            operation_type="query",
            start_time=100.0,
        )

        assert operation.variables == {"id": "123"}
        assert operation.operation_name == "GetUser"

    def test_operation_types(self) -> None:
        """Should accept different operation types."""
        for op_type in ["query", "mutation", "subscription"]:
            operation = TrackedOperation(
                operation_id="op1",
                query=f"{op_type} {{ test }}",
                variables={},
                operation_name=None,
                operation_type=op_type,  # type: ignore[arg-type]
                start_time=100.0,
            )
            assert operation.operation_type == op_type

    def test_operation_with_resolvers(self) -> None:
        """Should store resolvers list."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
        )

        operation = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=100.0,
            resolvers=[resolver],
        )

        assert len(operation.resolvers) == 1
        assert operation.resolvers[0].field_name == "user"

    def test_operation_with_errors(self) -> None:
        """Should store GraphQL errors."""
        errors = [
            {"message": "Not found", "path": ["user"], "locations": [{"line": 1, "column": 3}]},
        ]

        operation = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=100.0,
            errors=errors,
        )

        assert operation.errors == errors

    def test_operation_to_dict(self) -> None:
        """Should convert to dictionary with nested resolvers."""
        resolver = TrackedResolver(
            resolver_id="r1",
            field_name="user",
            field_path="Query.user",
            resolver_function="Query.user",
            parent_type="Query",
            return_type="User",
        )

        operation = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={"id": 1},
            operation_name="GetUser",
            operation_type="query",
            start_time=100.0,
            end_time=100.15,
            duration_ms=150.0,
            resolvers=[resolver],
        )

        result = operation.to_dict()

        assert result["operation_id"] == "op1"
        assert result["query"] == "query { user }"
        assert result["variables"] == {"id": 1}
        assert result["operation_name"] == "GetUser"
        assert result["operation_type"] == "query"
        assert result["duration_ms"] == 150.0
        assert len(result["resolvers"]) == 1
        assert result["resolvers"][0]["field_name"] == "user"
