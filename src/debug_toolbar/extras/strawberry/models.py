"""Data models for GraphQL tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TrackedResolver:
    """Represents a tracked GraphQL resolver execution.

    Attributes:
        resolver_id: Unique identifier for this resolver execution.
        field_name: GraphQL field name (camelCase).
        field_path: Dot-separated path (e.g., 'Query.user.posts.0.title').
        resolver_function: Function name or field reference.
        parent_type: Parent GraphQL type (e.g., 'Query', 'User').
        return_type: Expected return type.
        arguments: Resolver arguments (kwargs).
        start_time: Start timestamp (perf_counter).
        end_time: End timestamp (perf_counter).
        duration_ms: Execution duration in milliseconds.
        stack_trace: Call stack trace (if captured).
        is_slow: Whether duration exceeds threshold.
    """

    resolver_id: str
    field_name: str
    field_path: str
    resolver_function: str
    parent_type: str
    return_type: str
    arguments: dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    stack_trace: list[dict[str, Any]] | None = None
    is_slow: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "resolver_id": self.resolver_id,
            "field_name": self.field_name,
            "field_path": self.field_path,
            "resolver_function": self.resolver_function,
            "parent_type": self.parent_type,
            "return_type": self.return_type,
            "arguments": self.arguments,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "stack_trace": self.stack_trace,
            "is_slow": self.is_slow,
        }


@dataclass
class TrackedOperation:
    """Represents a tracked GraphQL operation.

    Attributes:
        operation_id: Unique identifier for this operation.
        query: GraphQL query string.
        variables: Operation variables.
        operation_name: Named operation (if provided).
        operation_type: Type of operation (query, mutation, subscription).
        start_time: Start timestamp (perf_counter).
        end_time: End timestamp (perf_counter).
        duration_ms: Total operation duration in milliseconds.
        resolvers: List of tracked resolvers executed.
        errors: GraphQL errors (if any).
        result_data: Preview of result data (truncated).
    """

    operation_id: str
    query: str
    variables: dict[str, Any]
    operation_name: str | None
    operation_type: Literal["query", "mutation", "subscription"]
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    resolvers: list[TrackedResolver] = field(default_factory=list)
    errors: list[dict[str, Any]] | None = None
    result_data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "operation_id": self.operation_id,
            "query": self.query,
            "variables": self.variables,
            "operation_name": self.operation_name,
            "operation_type": self.operation_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "resolvers": [r.to_dict() for r in self.resolvers],
            "errors": self.errors,
            "result_data": self.result_data,
        }
