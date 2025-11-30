"""Tests for GraphQL utility functions."""

from __future__ import annotations

from debug_toolbar.extras.strawberry.utils import (
    StackCapture,
    format_variables,
    get_operation_type_from_query,
    truncate_query,
)


class TestStackCapture:
    """Tests for StackCapture utility."""

    def test_capture_returns_list(self) -> None:
        """Should return a list of frame dicts."""
        frames = StackCapture.capture()
        assert isinstance(frames, list)

    def test_capture_frames_have_expected_keys(self) -> None:
        """Should return frames with expected keys."""
        frames = StackCapture.capture()
        if frames:
            frame = frames[-1]
            assert "file" in frame
            assert "line" in frame
            assert "function" in frame
            assert "code" in frame

    def test_max_frames_limit(self) -> None:
        """Should respect MAX_FRAMES limit."""
        frames = StackCapture.capture()
        assert len(frames) <= StackCapture.MAX_FRAMES

    def test_ignored_frames(self) -> None:
        """Should filter out ignored frames."""
        frames = StackCapture.capture()
        for frame in frames:
            for ignored in StackCapture.IGNORED_FRAMES:
                if ignored == "site-packages":
                    continue
                assert ignored not in frame["file"]


class TestTruncateQuery:
    """Tests for truncate_query function."""

    def test_short_query_not_truncated(self) -> None:
        """Should not truncate queries under limit."""
        query = "query { user { name } }"
        result = truncate_query(query, max_length=1000)
        assert result == query

    def test_long_query_truncated(self) -> None:
        """Should truncate queries over limit."""
        query = "a" * 2000
        result = truncate_query(query, max_length=100)
        assert len(result) == 103
        assert result.endswith("...")

    def test_query_at_limit(self) -> None:
        """Should not truncate query exactly at limit."""
        query = "a" * 100
        result = truncate_query(query, max_length=100)
        assert result == query
        assert len(result) == 100

    def test_custom_max_length(self) -> None:
        """Should respect custom max_length."""
        query = "query { " + "a" * 100 + " }"
        result = truncate_query(query, max_length=50)
        assert len(result) == 53
        assert result.endswith("...")

    def test_default_max_length(self) -> None:
        """Should use default max_length of 1000."""
        query = "a" * 2000
        result = truncate_query(query)
        assert len(result) == 1003


class TestFormatVariables:
    """Tests for format_variables function."""

    def test_simple_variables(self) -> None:
        """Should format simple variables unchanged."""
        variables = {"id": 1, "name": "test"}
        result = format_variables(variables)
        assert result == {"id": 1, "name": "test"}

    def test_nested_dict(self) -> None:
        """Should format nested dicts."""
        variables = {"input": {"name": "test", "email": "test@test.com"}}
        result = format_variables(variables)
        assert result == {"input": {"name": "test", "email": "test@test.com"}}

    def test_deeply_nested_dict_truncated(self) -> None:
        """Should truncate deeply nested dicts."""
        variables = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "value",
                    },
                },
            },
        }
        result = format_variables(variables, max_depth=3)
        assert result["level1"]["level2"]["level3"] == {"...": "max depth reached"}

    def test_list_values(self) -> None:
        """Should format list values."""
        variables = {"ids": [1, 2, 3]}
        result = format_variables(variables)
        assert result == {"ids": [1, 2, 3]}

    def test_long_list_truncated(self) -> None:
        """Should truncate lists over 10 items."""
        variables = {"ids": list(range(15))}
        result = format_variables(variables)
        assert len(result["ids"]) == 11
        assert result["ids"][-1] == "..."

    def test_list_with_nested_dicts(self) -> None:
        """Should format lists containing dicts."""
        variables = {"users": [{"name": "a"}, {"name": "b"}]}
        result = format_variables(variables)
        assert result == {"users": [{"name": "a"}, {"name": "b"}]}

    def test_empty_variables(self) -> None:
        """Should handle empty variables."""
        result = format_variables({})
        assert result == {}

    def test_mixed_types(self) -> None:
        """Should handle mixed types."""
        variables = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2],
            "dict": {"nested": "value"},
        }
        result = format_variables(variables)
        assert result["string"] == "test"
        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["none"] is None


class TestGetOperationTypeFromQuery:
    """Tests for get_operation_type_from_query function."""

    def test_query_operation(self) -> None:
        """Should detect query operation."""
        assert get_operation_type_from_query("query { user }") == "query"
        assert get_operation_type_from_query("query GetUser { user }") == "query"

    def test_mutation_operation(self) -> None:
        """Should detect mutation operation."""
        assert get_operation_type_from_query("mutation { createUser }") == "mutation"
        assert get_operation_type_from_query("mutation CreateUser { createUser }") == "mutation"

    def test_subscription_operation(self) -> None:
        """Should detect subscription operation."""
        assert get_operation_type_from_query("subscription { onMessage }") == "subscription"
        assert get_operation_type_from_query("subscription OnMessage { onMessage }") == "subscription"

    def test_default_to_query(self) -> None:
        """Should default to query for shorthand syntax."""
        assert get_operation_type_from_query("{ user }") == "query"

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        assert get_operation_type_from_query("QUERY { user }") == "query"
        assert get_operation_type_from_query("MUTATION { createUser }") == "mutation"
        assert get_operation_type_from_query("SUBSCRIPTION { onMessage }") == "subscription"

    def test_with_whitespace(self) -> None:
        """Should handle leading whitespace."""
        assert get_operation_type_from_query("  query { user }") == "query"
        assert get_operation_type_from_query("\n\nmutation { user }") == "mutation"
