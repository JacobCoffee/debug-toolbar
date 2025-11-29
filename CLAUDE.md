# AI Agent Guidelines for debug-toolbar

**Version**: 2.0 (Intelligent Edition) | **Updated**: 2025-11-29

Async-native debug toolbar for Python ASGI frameworks with optional Litestar integration. This library provides a plugin-based panel system for debugging, profiling, and monitoring ASGI applications.

---

## Intelligence Layer

This project uses an **intelligent agent system** that:

1. **Learns from codebase** before making changes
2. **Adapts workflow depth** based on feature complexity
3. **Accumulates knowledge** in pattern library
4. **Selects tools** based on task requirements

### Pattern Library

Reusable patterns in `specs/guides/patterns/`:

- Consult before implementing similar features
- Add new patterns during review phase

### Complexity-Based Checkpoints

| Complexity | Checkpoints | Triggers |
|------------|-------------|----------|
| Simple | 6 | CRUD, config change, single file |
| Medium | 8 | New panel, API endpoint, 2-3 files |
| Complex | 10+ | Architecture change, multi-component, new framework integration |

---

## Quick Reference

### Technology Stack

| Category | Technology |
|----------|------------|
| Framework | Litestar 2.x (optional integration) |
| ORM | SQLAlchemy 2.x / Advanced-Alchemy (optional) |
| Python | 3.10 - 3.13 |
| Testing | pytest, pytest-asyncio |
| Linting | ruff, ty (type checking) |
| Package Manager | uv |
| Frontend Lint | biome |

### Essential Commands

```bash
make dev          # Install all dependencies (dev mode)
make test         # Run all tests
make test-fast    # Run unit tests only (no integration)
make test-cov     # Run tests with coverage
make lint         # Run ruff linter
make lint-fix     # Run ruff with auto-fix
make fmt          # Format code with ruff
make type-check   # Run ty type checker
```

---

## Code Standards (Critical)

### Python Style

| Rule | Standard |
|------|----------|
| Type hints | PEP 604 (`T \| None` not `Optional[T]`) |
| Future annotations | `from __future__ import annotations` at top of every file |
| Docstrings | Google style with Args/Returns sections |
| Tests | Class-based for related tests, function-based for simple |
| Line length | 120 characters |
| Async | Prefer `async def` for I/O-bound operations |

### Anti-Patterns (Must Avoid)

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| `Optional[T]` | Use `T \| None` (PEP 604) |
| Missing future annotations | Add `from __future__ import annotations` |
| Blocking I/O in async | Use async equivalents |
| Type: ignore without reason | Add specific error code: `# type: ignore[arg-type]` |
| Tests without cleanup | Always clean up context vars: `set_request_context(None)` |

### Architecture Patterns

This project uses a **Panel Plugin Architecture**:

1. **Core Module** (`src/debug_toolbar/core/`):
   - `panel.py`: Abstract `Panel` base class with `generate_stats()` abstract method
   - `toolbar.py`: `DebugToolbar` orchestrates panels and request lifecycle
   - `config.py`: `DebugToolbarConfig` dataclass with defaults
   - `context.py`: `RequestContext` for request-scoped data
   - `storage.py`: `ToolbarStorage` for request history

2. **Panels** (`src/debug_toolbar/core/panels/`):
   - Each panel extends `Panel` ABC
   - Override `generate_stats(context)` to collect data
   - Optional: `process_request()`, `process_response()` lifecycle hooks

3. **Framework Integrations** (`src/debug_toolbar/litestar/`):
   - `plugin.py`: `DebugToolbarPlugin` implements `InitPluginProtocol`
   - `middleware.py`: ASGI middleware for request interception
   - `config.py`: Framework-specific config extending core config

4. **Extras** (`src/debug_toolbar/extras/`):
   - Optional integrations (e.g., `advanced_alchemy/`)
   - Follow same panel pattern

### Creating a New Panel

```python
"""Example panel implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class MyPanel(Panel):
    """Description of what this panel displays."""

    panel_id: ClassVar[str] = "MyPanel"
    title: ClassVar[str] = "My Panel"
    template: ClassVar[str] = "panels/my_panel.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate statistics for this panel."""
        return {
            "metric_name": self._collect_metric(),
        }

    def _collect_metric(self) -> int:
        """Private helper for data collection."""
        return 42
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/prd [feature]` | Create PRD with pattern learning |
| `/implement [slug]` | Pattern-guided implementation |
| `/test [slug]` | Testing with 90%+ coverage |
| `/review [slug]` | Quality gate and pattern extraction |
| `/explore [topic]` | Explore codebase |
| `/fix-issue [#]` | Fix GitHub issue |
| `/bootstrap` | Re-bootstrap (alignment mode) |

---

## Subagents

| Agent | Mission |
|-------|---------|
| `prd` | PRD creation with pattern recognition |
| `expert` | Implementation with pattern compliance |
| `testing` | Test creation (90%+ coverage) |
| `docs-vision` | Quality gates and pattern extraction |

---

## Development Workflow

### For New Features (Pattern-First)

1. **PRD**: `/prd [feature]` - Analyzes similar panels/features first
2. **Implement**: `/implement [slug]` - Follows identified patterns
3. **Test**: Auto-invoked - Tests pattern compliance
4. **Review**: Auto-invoked - Extracts new patterns to library

### For New Panels

1. Check existing panels in `src/debug_toolbar/core/panels/`
2. Follow the `Panel` ABC interface
3. Add to default panels in `DebugToolbarConfig` or document as extra panel
4. Write tests covering `generate_stats()` and lifecycle hooks
5. Add template if `has_content=True`

### Quality Gates

All code must pass:

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes (ty)
- [ ] 90%+ coverage for modified modules
- [ ] Pattern compliance verified
- [ ] No anti-patterns

---

## MCP Tools

### Tool Selection

Consult `.claude/mcp-strategy.md` for task-based tool selection.

### Context7 (Library Docs)

```python
mcp__context7__resolve-library-id(libraryName="litestar")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="plugins",
    mode="code"
)
```

### Sequential Thinking (Analysis)

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: ...",
    thoughtNumber=1,
    totalThoughts=15,  # Adapt to complexity
    nextThoughtNeeded=True
)
```

### Zen Tools

- `mcp__zen__planner` - Multi-phase planning
- `mcp__zen__thinkdeep` - Deep analysis
- `mcp__zen__analyze` - Code analysis
- `mcp__zen__debug` - Debugging

---

## Testing Patterns

### Unit Test Structure

```python
"""Tests for the my_panel module."""

from __future__ import annotations

import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig, RequestContext


class TestMyPanel:
    """Tests for MyPanel class."""

    def test_panel_id(self) -> None:
        """Should have correct panel ID."""
        # Test implementation

    @pytest.mark.asyncio
    async def test_generate_stats(self, context: RequestContext) -> None:
        """Should generate expected statistics."""
        # Always clean up context vars
        from debug_toolbar.core.context import set_request_context
        set_request_context(None)

        # Test implementation

        set_request_context(None)  # Cleanup
```

### Fixture Usage

Use fixtures from `conftest.py`:

- `config` - Default `DebugToolbarConfig`
- `toolbar` - `DebugToolbar` instance
- `context` / `request_context` - `RequestContext` instance

---

## File Organization

```
src/debug_toolbar/
├── __init__.py              # Public API exports
├── core/
│   ├── __init__.py
│   ├── panel.py             # Panel ABC
│   ├── toolbar.py           # DebugToolbar manager
│   ├── config.py            # DebugToolbarConfig
│   ├── context.py           # RequestContext
│   ├── storage.py           # ToolbarStorage
│   └── panels/              # Built-in panels
│       ├── __init__.py
│       ├── timer.py
│       ├── request.py
│       ├── response.py
│       └── ...
├── litestar/                # Litestar integration
│   ├── __init__.py
│   ├── plugin.py            # DebugToolbarPlugin
│   ├── middleware.py
│   ├── config.py
│   ├── routes/
│   └── panels/              # Litestar-specific panels
└── extras/                  # Optional integrations
    └── advanced_alchemy/
```

---

## Pattern Library

Location: `specs/guides/patterns/`

### Using Patterns

1. Search pattern library before implementation
2. Follow established conventions
3. Document deviations with rationale

### Adding Patterns

1. Document in `tmp/new-patterns.md` during implementation
2. Extract to pattern library during review
3. Update this guide if architectural patterns
