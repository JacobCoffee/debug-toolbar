---
description: Testing with 90%+ coverage target
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
---

# Testing Workflow

You are writing tests for: **$ARGUMENTS**

## Pre-Testing Checklist

1. Load PRD from `specs/active/{slug}/prd.md`
2. Identify files to test from implementation
3. Read existing test patterns from `tests/`
4. Check coverage requirements (90%+)

## Critical Rules

1. **90%+ COVERAGE** - For all modified modules
2. **PATTERN COMPLIANCE** - Follow existing test structure
3. **ASYNC CLEANUP** - Always clean up context vars
4. **FIXTURE USAGE** - Use conftest.py fixtures
5. **ISOLATION** - Tests must work in parallel

---

## Phase 1: Test Planning

**Identify test scope:**

```bash
# List modified files
git diff --name-only HEAD~1

# Check current coverage
make test-cov
```

**For each module, identify:**

- Public methods to test
- Edge cases
- Error conditions
- Integration points

**Output**: "✓ Phase 1 complete - Test scope identified"

---

## Phase 2: Unit Tests

**Follow the test pattern:**

```python
"""Tests for the {module} module."""

from __future__ import annotations

import pytest

from debug_toolbar.core.context import set_request_context


class TestClassName:
    """Tests for ClassName."""

    def test_method_basic(self) -> None:
        """Should describe expected behavior."""
        # Arrange
        # Act
        # Assert

    @pytest.mark.asyncio
    async def test_async_method(self, context) -> None:
        """Should describe async behavior."""
        set_request_context(None)  # Setup

        # Arrange
        # Act
        # Assert

        set_request_context(None)  # Cleanup
```

**Key test patterns for debug-toolbar:**

1. **Panel tests:**
   - Test `generate_stats()` returns expected structure
   - Test `process_request()` and `process_response()` lifecycle
   - Test `get_panel_id()` returns correct ID

2. **Config tests:**
   - Test default values
   - Test custom values
   - Test `get_all_panels()` with extras/excludes

3. **Toolbar tests:**
   - Test panel loading
   - Test request/response lifecycle
   - Test data collection

**Output**: "✓ Phase 2 complete - Unit tests written"

---

## Phase 3: Integration Tests

**Place in `tests/integration/`:**

```python
"""Integration tests for {feature}."""

from __future__ import annotations

import pytest
from litestar import Litestar
from litestar.testing import TestClient


class TestFeatureIntegration:
    """Integration tests."""

    @pytest.mark.integration
    def test_full_workflow(self) -> None:
        """Test complete feature workflow."""
        # Setup app
        # Make request
        # Verify response
```

**Output**: "✓ Phase 3 complete - Integration tests written"

---

## Phase 4: Coverage Verification

**Check coverage:**

```bash
make test-cov
```

**Target: 90%+ for modified modules**

**If below 90%:**

1. Identify uncovered lines
2. Add tests for edge cases
3. Add tests for error paths
4. Re-run coverage

**Output**: "✓ Phase 4 complete - Coverage: XX%"

---

## Phase 5: Parallel Test Verification

**Ensure tests work in parallel:**

```bash
make test-parallel
```

**Common issues:**

- Shared state between tests
- Context vars not cleaned up
- File system conflicts

**Output**: "✓ Phase 5 complete - Parallel tests passing"

---

## Phase 6: Test Documentation

**Update test docstrings:**

- Clear description of what's being tested
- Any special setup requirements
- Expected outcomes

**Output**: "✓ Phase 6 complete - Tests documented"

---

## Final Summary

```
Testing Phase Complete ✓

Tests written:
- tests/unit/test_{module}.py
- tests/integration/test_{feature}.py

Coverage:
- Modified modules: XX%
- Overall: XX%

All tests passing in:
- ✓ Sequential mode
- ✓ Parallel mode

Next: Run `/review {slug}`
```
