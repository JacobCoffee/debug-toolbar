---
description: Pattern-guided implementation with quality gates
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__zen__thinkdeep, mcp__zen__debug
---

# Intelligent Implementation Workflow

You are implementing the feature from PRD: **$ARGUMENTS**

## Pre-Implementation Checklist

1. Load PRD from `specs/active/{slug}/prd.md`
2. Load pattern analysis from `specs/active/{slug}/patterns/`
3. Read similar implementations identified in PRD
4. Consult pattern library at `specs/guides/patterns/`

## Critical Rules

1. **PATTERN COMPLIANCE** - Follow patterns from similar features
2. **NO OVER-ENGINEERING** - Only implement what's in the PRD
3. **TYPE SAFETY** - Use PEP 604 (`T | None`), future annotations
4. **TEST READY** - Design for testability
5. **INCREMENTAL** - Commit logically, not at the end

---

## Phase 1: Context Loading

**Load intelligence context:**

```bash
# Verify PRD exists
cat specs/active/{slug}/prd.md

# Load patterns
cat specs/active/{slug}/patterns/analysis.md

# Load research
cat specs/active/{slug}/research/plan.md
```

**Read similar implementations:**
- Read files identified in PRD's "Similar Implementations" section
- Extract exact patterns to follow

**Output**: "✓ Phase 1 complete - Context loaded"

---

## Phase 2: Implementation Planning

**Break down into atomic tasks:**

For each file to create/modify:
1. Identify dependencies
2. Plan implementation order
3. Note patterns to apply

**Update workspace:**
```bash
echo "## Implementation Plan" >> specs/active/{slug}/tmp/progress.md
```

**Output**: "✓ Phase 2 complete - Implementation planned"

---

## Phase 3: Core Implementation

**Follow the Panel pattern if creating a panel:**

```python
"""Panel implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class NewPanel(Panel):
    """Description."""

    panel_id: ClassVar[str] = "NewPanel"
    title: ClassVar[str] = "New Panel"
    template: ClassVar[str] = "panels/new_panel.html"
    has_content: ClassVar[bool] = True

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate statistics."""
        return {}
```

**Follow the Plugin pattern if creating an integration:**

```python
"""Plugin implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class NewPlugin(InitPluginProtocol):
    """Description."""

    __slots__ = ("_config",)

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure the application."""
        return app_config
```

**Verify after each file:**
```bash
make lint && make type-check
```

**Output**: "✓ Phase 3 complete - Core implementation done"

---

## Phase 4: Quality Verification

**Run quality gates:**

```bash
make lint          # Must pass
make type-check    # Must pass
make fmt-check     # Must pass
```

**Fix any issues before proceeding.**

**Output**: "✓ Phase 4 complete - Quality gates passed"

---

## Phase 5: Pattern Documentation

**Document any new patterns discovered:**

```bash
echo "## New Pattern: {name}" >> specs/active/{slug}/tmp/new-patterns.md
```

**If deviating from established patterns, document rationale.**

**Output**: "✓ Phase 5 complete - Patterns documented"

---

## Phase 6: Test Agent Invocation

**Automatically invoke the testing agent:**

```
Task(
    subagent_type="testing",
    prompt="Write comprehensive tests for the {slug} feature implementation.

    PRD location: specs/active/{slug}/prd.md
    Files modified: [list modified files]

    Requirements:
    - 90%+ coverage for modified modules
    - Follow test patterns from tests/
    - Clean up context vars in async tests
    - Use fixtures from conftest.py"
)
```

**Output**: "✓ Phase 6 complete - Testing agent invoked"

---

## Phase 7: Final Verification

**Verify all tests pass:**

```bash
make test
```

**Verify coverage:**

```bash
make test-cov
```

**Update progress:**

```bash
echo "Implementation complete: $(date)" >> specs/active/{slug}/tmp/progress.md
```

**Output**: "✓ Phase 7 complete - All tests passing"

---

## Final Summary

```
Implementation Phase Complete ✓

Files created/modified:
- src/debug_toolbar/...
- tests/unit/...

Quality gates:
- ✓ Linting passed
- ✓ Type checking passed
- ✓ Tests passing
- ✓ Coverage: XX%

Next: Run `/review {slug}`
```
