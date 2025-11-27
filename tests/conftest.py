"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig, RequestContext


@pytest.fixture
def config() -> DebugToolbarConfig:
    """Create a default configuration."""
    return DebugToolbarConfig()


@pytest.fixture
def toolbar(config: DebugToolbarConfig) -> DebugToolbar:
    """Create a toolbar instance."""
    return DebugToolbar(config)


@pytest.fixture
def context() -> RequestContext:
    """Create a request context."""
    return RequestContext()


@pytest.fixture
def request_context() -> RequestContext:
    """Create a request context (alias for context)."""
    return RequestContext()
