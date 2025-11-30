"""Tests for GraphQL analyzers."""

from __future__ import annotations

from debug_toolbar.extras.strawberry.analyzers import DuplicateDetector, N1Analyzer
from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver


class TestN1Analyzer:
    """Tests for N1Analyzer."""

    def test_init_default_threshold(self) -> None:
        """Should initialize with default threshold of 3."""
        analyzer = N1Analyzer()
        assert analyzer._threshold == 3

    def test_init_custom_threshold(self) -> None:
        """Should accept custom threshold."""
        analyzer = N1Analyzer(threshold=5)
        assert analyzer._threshold == 5

    def test_detects_n_plus_one_pattern(self) -> None:
        """Should detect N+1 pattern when resolver called 3+ times."""
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
            resolvers=resolvers,
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 1
        assert patterns[0]["count"] == 5
        assert patterns[0]["field_name"] == "posts"
        assert patterns[0]["parent_type"] == "User"
        assert "DataLoader" in patterns[0]["suggestion"]

    def test_ignores_below_threshold(self) -> None:
        """Should not flag resolvers called below threshold."""
        resolvers = [
            TrackedResolver(
                resolver_id=f"r{i}",
                field_name="name",
                field_path=f"Query.users.{i}.name",
                resolver_function="User.name",
                parent_type="User",
                return_type="String",
                duration_ms=1.0,
            )
            for i in range(2)
        ]

        operation = TrackedOperation(
            operation_id="op1",
            query="query { users { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=resolvers,
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 0

    def test_analyzes_multiple_operations(self) -> None:
        """Should analyze patterns across multiple operations."""
        resolver1 = TrackedResolver(
            resolver_id="r1",
            field_name="author",
            field_path="Query.posts.0.author",
            resolver_function="Post.author",
            parent_type="Post",
            return_type="User",
            duration_ms=5.0,
        )

        resolver2 = TrackedResolver(
            resolver_id="r2",
            field_name="author",
            field_path="Query.posts.1.author",
            resolver_function="Post.author",
            parent_type="Post",
            return_type="User",
            duration_ms=5.0,
        )

        resolver3 = TrackedResolver(
            resolver_id="r3",
            field_name="author",
            field_path="Query.posts.2.author",
            resolver_function="Post.author",
            parent_type="Post",
            return_type="User",
            duration_ms=5.0,
        )

        operation = TrackedOperation(
            operation_id="op1",
            query="query { posts { author } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=[resolver1, resolver2, resolver3],
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 1
        assert patterns[0]["count"] == 3
        assert patterns[0]["total_duration_ms"] == 15.0

    def test_calculates_total_duration(self) -> None:
        """Should calculate total duration for pattern."""
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
            for i in range(3)
        ]

        operation = TrackedOperation(
            operation_id="op1",
            query="query { users { posts } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=resolvers,
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert patterns[0]["total_duration_ms"] == 30.0

    def test_sorts_patterns_by_count(self) -> None:
        """Should sort patterns by count descending."""
        resolvers = []
        for i in range(5):
            resolvers.append(
                TrackedResolver(
                    resolver_id=f"r_posts_{i}",
                    field_name="posts",
                    field_path=f"Query.users.{i}.posts",
                    resolver_function="User.posts",
                    parent_type="User",
                    return_type="[Post]",
                    duration_ms=1.0,
                )
            )

        for i in range(3):
            resolvers.append(
                TrackedResolver(
                    resolver_id=f"r_email_{i}",
                    field_name="email",
                    field_path=f"Query.users.{i}.email",
                    resolver_function="User.email",
                    parent_type="User",
                    return_type="String",
                    duration_ms=1.0,
                )
            )

        operation = TrackedOperation(
            operation_id="op1",
            query="query { users { posts email } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=resolvers,
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 2
        assert patterns[0]["count"] == 5
        assert patterns[0]["field_name"] == "posts"
        assert patterns[1]["count"] == 3
        assert patterns[1]["field_name"] == "email"

    def test_empty_operations_list(self) -> None:
        """Should return empty list for no operations."""
        analyzer = N1Analyzer()
        patterns = analyzer.analyze([])

        assert patterns == []

    def test_no_resolvers(self) -> None:
        """Should return empty list when operations have no resolvers."""
        operation = TrackedOperation(
            operation_id="op1",
            query="query { __typename }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=[],
        )

        analyzer = N1Analyzer()
        patterns = analyzer.analyze([operation])

        assert patterns == []


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""

    def test_detects_duplicate_operations(self) -> None:
        """Should detect operations with same query and variables."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 2
        assert "op1" in duplicates
        assert "op2" in duplicates

    def test_no_duplicates_different_queries(self) -> None:
        """Should not flag different queries as duplicates."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query { user(id: 2) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 0

    def test_no_duplicates_different_variables(self) -> None:
        """Should not flag operations with different variables as duplicates."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query GetUser($id: ID!) { user(id: $id) { name } }",
            variables={"id": "1"},
            operation_name="GetUser",
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query GetUser($id: ID!) { user(id: $id) { name } }",
            variables={"id": "2"},
            operation_name="GetUser",
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 0

    def test_normalizes_whitespace(self) -> None:
        """Should normalize whitespace when comparing queries."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query  {  user(id: 1)  {  name  }  }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 2

    def test_multiple_duplicates(self) -> None:
        """Should detect multiple groups of duplicates."""
        ops = [
            TrackedOperation(
                operation_id="op1",
                query="query { user(id: 1) }",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=0.0,
            ),
            TrackedOperation(
                operation_id="op2",
                query="query { user(id: 1) }",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=0.1,
            ),
            TrackedOperation(
                operation_id="op3",
                query="query { posts }",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=0.2,
            ),
            TrackedOperation(
                operation_id="op4",
                query="query { posts }",
                variables={},
                operation_name=None,
                operation_type="query",
                start_time=0.3,
            ),
        ]

        detector = DuplicateDetector()
        duplicates = detector.detect(ops)

        assert len(duplicates) == 4
        assert all(op_id in duplicates for op_id in ["op1", "op2", "op3", "op4"])

    def test_empty_operations_list(self) -> None:
        """Should return empty list for no operations."""
        detector = DuplicateDetector()
        duplicates = detector.detect([])

        assert duplicates == []

    def test_single_operation(self) -> None:
        """Should return empty list for single operation."""
        op = TrackedOperation(
            operation_id="op1",
            query="query { user }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op])

        assert duplicates == []
