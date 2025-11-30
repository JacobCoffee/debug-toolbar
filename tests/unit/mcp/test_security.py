"""Tests for MCP security utilities."""

from __future__ import annotations

import pytest

from debug_toolbar.mcp.security import (
    REDACTED,
    is_sensitive_key,
    redact_dict,
    redact_headers,
    redact_sql_parameters,
    redact_value,
)


class TestIsSensitiveKey:
    """Tests for is_sensitive_key function."""

    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "PASSWORD",
            "user_password",
            "secret",
            "SECRET_KEY",
            "api_key",
            "API_KEY",
            "apiKey",
            "auth_token",
            "access_token",
            "refresh_token",
            "private_key",
            "credit_card",
            "ssn",
            "bearer",
        ],
    )
    def test_detects_sensitive_keys(self, key: str) -> None:
        """Should detect various sensitive key patterns."""
        assert is_sensitive_key(key) is True

    @pytest.mark.parametrize(
        "key",
        [
            "username",
            "email",
            "name",
            "id",
            "count",
            "status",
            "path",
            "method",
        ],
    )
    def test_allows_non_sensitive_keys(self, key: str) -> None:
        """Should allow non-sensitive keys."""
        assert is_sensitive_key(key) is False


class TestRedactValue:
    """Tests for redact_value function."""

    def test_redacts_sensitive_value(self) -> None:
        """Should redact value when key is sensitive."""
        assert redact_value("my-secret", key="password") == REDACTED

    def test_preserves_non_sensitive_value(self) -> None:
        """Should preserve value when key is not sensitive."""
        assert redact_value("hello", key="greeting") == "hello"

    def test_no_key_preserves_value(self) -> None:
        """Should preserve value when no key provided."""
        assert redact_value("test") == "test"


class TestRedactDict:
    """Tests for redact_dict function."""

    def test_redacts_top_level_sensitive_keys(self) -> None:
        """Should redact sensitive keys at top level."""
        data = {"username": "john", "password": "secret123"}
        result = redact_dict(data)

        assert result["username"] == "john"
        assert result["password"] == REDACTED

    def test_redacts_nested_sensitive_keys(self) -> None:
        """Should redact sensitive keys in nested dicts."""
        data = {
            "user": {
                "name": "john",
                "api_key": "abc123",
            }
        }
        result = redact_dict(data, deep=True)

        assert result["user"]["name"] == "john"
        assert result["user"]["api_key"] == REDACTED

    def test_redacts_in_lists(self) -> None:
        """Should redact sensitive keys in list items."""
        data = {
            "users": [
                {"name": "john", "password": "secret1"},
                {"name": "jane", "password": "secret2"},
            ]
        }
        result = redact_dict(data, deep=True)

        assert result["users"][0]["name"] == "john"
        assert result["users"][0]["password"] == REDACTED
        assert result["users"][1]["name"] == "jane"
        assert result["users"][1]["password"] == REDACTED

    def test_shallow_mode_skips_nested(self) -> None:
        """Should not redact nested dicts in shallow mode."""
        data = {
            "user": {
                "password": "secret123",
            }
        }
        result = redact_dict(data, deep=False)

        assert result["user"]["password"] == "secret123"


class TestRedactSqlParameters:
    """Tests for redact_sql_parameters function."""

    def test_redacts_dict_params(self) -> None:
        """Should redact sensitive dict parameters."""
        params = {"user_id": 1, "password": "secret"}
        result = redact_sql_parameters(params)

        assert result["user_id"] == 1
        assert result["password"] == REDACTED

    def test_handles_tuple_params(self) -> None:
        """Should handle tuple parameters."""
        params = ({"password": "secret"},)
        result = redact_sql_parameters(params)

        assert isinstance(result, tuple)
        assert result[0]["password"] == REDACTED

    def test_handles_list_params(self) -> None:
        """Should handle list parameters."""
        params = [{"api_key": "abc123"}]
        result = redact_sql_parameters(params)

        assert isinstance(result, list)
        assert result[0]["api_key"] == REDACTED

    def test_handles_none(self) -> None:
        """Should handle None parameters."""
        assert redact_sql_parameters(None) is None


class TestRedactHeaders:
    """Tests for redact_headers function."""

    def test_redacts_authorization_header(self) -> None:
        """Should redact Authorization header."""
        headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}
        result = redact_headers(headers)

        assert result["Authorization"] == REDACTED
        assert result["Content-Type"] == "application/json"

    def test_redacts_cookie_headers(self) -> None:
        """Should redact cookie headers."""
        headers = {"Cookie": "session=abc123", "Host": "example.com"}
        result = redact_headers(headers)

        assert result["Cookie"] == REDACTED
        assert result["Host"] == "example.com"

    @pytest.mark.parametrize(
        "header",
        [
            "x-api-key",
            "X-API-KEY",
            "x-auth-token",
            "x-csrf-token",
            "set-cookie",
        ],
    )
    def test_redacts_sensitive_custom_headers(self, header: str) -> None:
        """Should redact known sensitive headers."""
        headers = {header: "some-value"}
        result = redact_headers(headers)

        assert result[header] == REDACTED
