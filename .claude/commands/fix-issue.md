---
description: Fix a GitHub issue with pattern-guided implementation
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebFetch, mcp__zen__debug
---

# Fix GitHub Issue

You are fixing issue: **$ARGUMENTS**

## Workflow

### Phase 1: Issue Analysis

**Fetch issue details:**

```bash
gh issue view {issue_number}
```

**Understand the issue:**

1. What is the problem?
2. What is the expected behavior?
3. What is the actual behavior?
4. Can it be reproduced?

**Output**: "✓ Phase 1 complete - Issue understood"

---

### Phase 2: Root Cause Investigation

**Use debug tools:**

```
mcp__zen__debug(
    step="Investigating issue #{issue_number}",
    step_number=1,
    total_steps=3,
    next_step_required=True,
    findings="Initial investigation..."
)
```

**Search codebase:**

```bash
# Find related code
grep -r "{keyword}" src/

# Find related tests
grep -r "{keyword}" tests/
```

**Output**: "✓ Phase 2 complete - Root cause identified"

---

### Phase 3: Fix Implementation

**Follow existing patterns:**

1. Read similar fixes in git history
2. Follow code style from `CLAUDE.md`
3. Maintain type safety

**Implement fix:**

1. Make minimal necessary changes
2. Don't over-engineer
3. Add or update tests

**Output**: "✓ Phase 3 complete - Fix implemented"

---

### Phase 4: Testing

**Write test for the fix:**

```python
"""Test for issue #{issue_number} fix."""

from __future__ import annotations

import pytest


class TestIssueNumber:
    """Test that issue #{issue_number} is fixed."""

    def test_issue_scenario(self) -> None:
        """Should not exhibit the bug behavior."""
        # Arrange: Set up the scenario from the issue
        # Act: Perform the action that caused the bug
        # Assert: Verify the fix works
```

**Run tests:**

```bash
make test
```

**Output**: "✓ Phase 4 complete - Tests passing"

---

### Phase 5: Quality Verification

**Run quality gates:**

```bash
make lint
make type-check
make fmt-check
```

**Output**: "✓ Phase 5 complete - Quality gates passed"

---

### Phase 6: Commit

**Create commit with issue reference:**

```bash
git add -A
git commit -m "fix: description of fix

Fixes #{issue_number}"
```

**Output**: "✓ Phase 6 complete - Committed"

---

## Final Summary

```
Issue Fix Complete ✓

Issue: #{issue_number}
Root Cause: {description}

Files Modified:
- path/to/file.py

Tests Added:
- tests/unit/test_issue_{number}.py

Quality:
- ✓ All tests passing
- ✓ Linting clean
- ✓ Type checking passed

Commit: {hash}
```
