"""Analyzers for detecting GraphQL performance patterns."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from debug_toolbar.extras.strawberry.models import TrackedOperation


class N1Analyzer:
    """Detects N+1 resolver patterns.

    Identifies cases where the same resolver is called multiple times
    unnecessarily, suggesting the need for DataLoader or batch loading.
    """

    __slots__ = ("_threshold",)

    def __init__(self, threshold: int = 3) -> None:
        """Initialize analyzer.

        Args:
            threshold: Minimum resolver count to flag as N+1.
        """
        self._threshold = threshold

    def analyze(self, operations: list[TrackedOperation]) -> list[dict[str, Any]]:
        """Analyze operations for N+1 patterns.

        Args:
            operations: List of tracked operations.

        Returns:
            List of detected N+1 patterns with metadata.
        """
        patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "resolver_signature": "",
                "field_name": "",
                "parent_type": "",
                "count": 0,
                "total_duration_ms": 0.0,
                "resolver_ids": [],
                "suggestion": "",
            }
        )

        for operation in operations:
            for resolver in operation.resolvers:
                arg_sig = self._get_argument_signature(resolver.arguments)
                signature = f"{resolver.parent_type}.{resolver.field_name}({arg_sig})"

                pattern = patterns[signature]
                pattern["resolver_signature"] = signature
                pattern["field_name"] = resolver.field_name
                pattern["parent_type"] = resolver.parent_type
                pattern["count"] += 1
                pattern["total_duration_ms"] += resolver.duration_ms
                pattern["resolver_ids"].append(resolver.resolver_id)

        n_plus_one_patterns = [
            {
                **pattern,
                "suggestion": self._generate_suggestion(pattern),
            }
            for pattern in patterns.values()
            if pattern["count"] >= self._threshold
        ]

        n_plus_one_patterns.sort(key=lambda p: p["count"], reverse=True)

        return n_plus_one_patterns

    def _get_argument_signature(self, arguments: dict[str, Any]) -> str:
        """Create argument type signature.

        Args:
            arguments: Resolver arguments.

        Returns:
            Comma-separated type signature.
        """
        if not arguments:
            return ""
        arg_types = [type(v).__name__ for v in arguments.values()]
        return ", ".join(arg_types)

    def _generate_suggestion(self, pattern: dict[str, Any]) -> str:
        """Generate fix suggestion for N+1 pattern.

        Args:
            pattern: Pattern metadata.

        Returns:
            Human-readable suggestion string.
        """
        count = pattern["count"]
        field = pattern["field_name"]
        return (
            f"Resolver '{field}' called {count} times. "
            f"Consider using DataLoader to batch these requests into a single operation."
        )


class DuplicateDetector:
    """Detects duplicate GraphQL operations."""

    __slots__ = ()

    def detect(self, operations: list[TrackedOperation]) -> list[str]:
        """Find duplicate operations (same query + variables).

        Args:
            operations: List of tracked operations.

        Returns:
            List of duplicate operation IDs.
        """
        seen: dict[str, list[str]] = defaultdict(list)

        for operation in operations:
            key = self._create_key(operation.query, operation.variables)
            seen[key].append(operation.operation_id)

        duplicates = []
        for op_ids in seen.values():
            if len(op_ids) > 1:
                duplicates.extend(op_ids)

        return duplicates

    def _create_key(self, query: str, variables: dict[str, Any]) -> str:
        """Create hash key for operation.

        Args:
            query: GraphQL query string.
            variables: Operation variables.

        Returns:
            MD5 hash of normalized query + variables.
        """
        normalized_query = " ".join(query.split())

        var_json = json.dumps(variables, sort_keys=True, default=str)

        combined = f"{normalized_query}:{var_json}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()
