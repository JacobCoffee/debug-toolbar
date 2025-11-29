# Pytest Skill

Quick reference for pytest patterns in this project.

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="pytest")
# Returns: /pytest-dev/pytest

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/pytest-dev/pytest",
    topic="fixtures",
    mode="code"
)
```

## Project Configuration

Location: `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
addopts = ["-ra", "-q", "--strict-markers"]
markers = [
    "integration: marks tests as integration tests",
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::pytest.PytestUnraisableExceptionWarning",
]
```

## Project Fixtures

Location: `tests/conftest.py`

```python
"""Available fixtures."""

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
    """Create a request context (alias)."""
    return RequestContext()
```

## Test Patterns

### Unit Test Pattern

```python
"""Unit test pattern."""

from __future__ import annotations

import pytest


class TestClassName:
    """Tests for ClassName."""

    def test_method_basic(self) -> None:
        """Should describe expected behavior."""
        # Arrange
        value = create_something()

        # Act
        result = value.method()

        # Assert
        assert result == expected
```

### Async Test Pattern

```python
"""Async test pattern."""

from __future__ import annotations

import pytest

from debug_toolbar.core.context import set_request_context


class TestAsyncClass:
    """Async tests."""

    @pytest.mark.asyncio
    async def test_async_method(self, context) -> None:
        """Should handle async operation."""
        set_request_context(None)  # Setup - clean slate

        # Arrange
        # Act
        result = await async_operation()
        # Assert

        set_request_context(None)  # Cleanup - prevent leaks
```

### Parametrized Test Pattern

```python
"""Parametrized test pattern."""

from __future__ import annotations

import pytest


class TestParametrized:
    """Parametrized tests."""

    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            (1, "one"),
            (2, "two"),
            (3, "three"),
        ],
    )
    def test_with_params(self, input_value: int, expected: str) -> None:
        """Should handle various inputs."""
        result = convert(input_value)
        assert result == expected
```

### Exception Testing Pattern

```python
"""Exception testing pattern."""

from __future__ import annotations

import pytest


class TestExceptions:
    """Exception tests."""

    def test_raises_value_error(self) -> None:
        """Should raise ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid"):
            process_invalid_input()
```

### Fixture Override Pattern

```python
"""Fixture override pattern."""

from __future__ import annotations

import pytest

from debug_toolbar import DebugToolbarConfig


class TestWithCustomConfig:
    """Tests with custom configuration."""

    @pytest.fixture
    def config(self) -> DebugToolbarConfig:
        """Override default config."""
        return DebugToolbarConfig(
            enabled=False,
            max_request_history=10,
        )

    def test_with_custom_config(self, config, toolbar) -> None:
        """Should use custom config."""
        assert toolbar.config.enabled is False
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run unit tests only (fast)
make test-fast

# Run in parallel
make test-parallel

# Run specific test file
uv run pytest tests/unit/test_toolbar.py

# Run specific test class
uv run pytest tests/unit/test_toolbar.py::TestDebugToolbar

# Run specific test method
uv run pytest tests/unit/test_toolbar.py::TestDebugToolbar::test_default_config

# Run with verbose output
make test-debug
```

## Related Files

- `tests/conftest.py`
- `tests/unit/`
- `tests/integration/`
- `pyproject.toml` (pytest config)
