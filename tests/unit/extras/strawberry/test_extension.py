"""Tests for DebugToolbarExtension."""

from __future__ import annotations

import pytest

from debug_toolbar.extras.strawberry.extension import (
    STRAWBERRY_AVAILABLE,
    DebugToolbarExtension,
)


class TestDebugToolbarExtensionInit:
    """Tests for DebugToolbarExtension initialization."""

    def test_default_thresholds(self) -> None:
        """Should initialize with default thresholds."""
        ext = DebugToolbarExtension()
        assert ext._slow_operation_threshold_ms == 100.0
        assert ext._slow_resolver_threshold_ms == 10.0
        assert ext._capture_stacks is True

    def test_custom_thresholds(self) -> None:
        """Should accept custom threshold values."""
        ext = DebugToolbarExtension(
            slow_operation_threshold_ms=200.0,
            slow_resolver_threshold_ms=20.0,
            capture_stacks=False,
        )
        assert ext._slow_operation_threshold_ms == 200.0
        assert ext._slow_resolver_threshold_ms == 20.0
        assert ext._capture_stacks is False


class TestDebugToolbarExtensionAvailability:
    """Tests for availability checking."""

    def test_is_available_returns_bool(self) -> None:
        """Should return boolean for availability check."""
        result = DebugToolbarExtension.is_available()
        assert isinstance(result, bool)

    def test_is_available_matches_import(self) -> None:
        """Should match STRAWBERRY_AVAILABLE constant."""
        assert DebugToolbarExtension.is_available() == STRAWBERRY_AVAILABLE


@pytest.mark.skipif(not STRAWBERRY_AVAILABLE, reason="Strawberry not installed")
class TestDebugToolbarExtensionWithStrawberry:
    """Tests requiring Strawberry to be installed."""

    def test_extension_is_schema_extension(self) -> None:
        """Should be a Strawberry SchemaExtension."""
        from strawberry.extensions import SchemaExtension

        ext = DebugToolbarExtension()
        assert isinstance(ext, SchemaExtension)
