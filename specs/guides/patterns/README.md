# Pattern Library

This directory contains reusable patterns extracted from completed features.

## How Patterns Are Captured

1. During implementation, new patterns are documented in `tmp/new-patterns.md`
2. During review, patterns are extracted to this directory
3. Future PRD phases consult this library first

## Pattern Categories

### Panel Patterns
- Abstract panel base class (`Panel` ABC)
- Panel lifecycle hooks (`process_request`, `process_response`)
- Statistics generation (`generate_stats`)
- Template rendering patterns

### Type Handling Patterns
- PEP 604 union types (`T | None`)
- Future annotations (`from __future__ import annotations`)
- ClassVar for panel metadata
- TYPE_CHECKING imports

### Testing Patterns
- Fixture patterns (config, toolbar, context)
- Async test structure with cleanup
- Class-based test organization
- Context variable cleanup

### Plugin Patterns
- Litestar `InitPluginProtocol` implementation
- Middleware integration
- Route handler registration
- Configuration inheritance

### Error Handling Patterns
- Graceful degradation for optional dependencies
- Logging warnings for import failures
- None returns for missing resources

## Using Patterns

When starting a new feature:

1. Search this directory for similar patterns
2. Read pattern documentation before implementation
3. Follow established conventions
4. Add new patterns during review phase

## Core Patterns

### Panel Implementation Pattern

```python
"""Panel implementation pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class ExamplePanel(Panel):
    """Panel description."""

    panel_id: ClassVar[str] = "ExamplePanel"
    title: ClassVar[str] = "Example"
    template: ClassVar[str] = "panels/example.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate statistics."""
        return {"key": "value"}
```

### Test Pattern

```python
"""Test pattern."""

from __future__ import annotations

import pytest

from debug_toolbar.core.context import set_request_context


class TestPanel:
    """Test class for panel."""

    @pytest.mark.asyncio
    async def test_generate_stats(self, context) -> None:
        """Test generate_stats method."""
        set_request_context(None)  # Setup

        # Test implementation

        set_request_context(None)  # Cleanup
```

### Plugin Pattern

```python
"""Plugin pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class ExamplePlugin(InitPluginProtocol):
    """Plugin implementation."""

    __slots__ = ("_config",)

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application."""
        # Modify app_config
        return app_config
```
