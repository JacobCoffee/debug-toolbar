---
description: Quality gate verification and pattern extraction
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__zen__analyze
---

# Review Workflow

You are reviewing the implementation of: **$ARGUMENTS**

## Pre-Review Checklist

1. Load PRD from `specs/active/{slug}/prd.md`
2. Load quality gates from `specs/guides/quality-gates.yaml`
3. Review all modified files
4. Check test coverage

## Critical Rules

1. **ALL GATES MUST PASS** - No exceptions
2. **PATTERN EXTRACTION** - Capture new patterns
3. **ANTI-PATTERN SCAN** - Check for violations
4. **DOCUMENTATION UPDATE** - Update CLAUDE.md if needed

---

## Phase 1: Quality Gate Verification

**Run all quality gates:**

```bash
make test          # All tests pass
make lint          # Zero linting errors
make type-check    # Type checking passes
make fmt-check     # Formatting correct
```

**Verify coverage:**

```bash
make test-cov
# Check: Modified modules >= 90%
```

**Output**: "✓ Phase 1 complete - All quality gates passed"

---

## Phase 2: Anti-Pattern Scan

**Check for anti-patterns:**

1. **Optional[T]** - Should use `T | None`

   ```bash
   grep -r "Optional\[" src/ tests/
   ```

2. **Missing future annotations**

   ```bash
   for f in $(find src/ -name "*.py"); do
     head -5 "$f" | grep -q "from __future__ import annotations" || echo "Missing: $f"
   done
   ```

3. **Type ignore without code**

   ```bash
   grep -r "# type: ignore$" src/ tests/
   ```

4. **Context var cleanup missing**

   ```bash
   grep -A5 "@pytest.mark.asyncio" tests/ | grep -v "set_request_context(None)"
   ```

**Fix any violations before proceeding.**

**Output**: "✓ Phase 2 complete - No anti-patterns found"

---

## Phase 3: Pattern Extraction

**Review new patterns from implementation:**

1. Read `specs/active/{slug}/tmp/new-patterns.md`
2. Identify reusable patterns
3. Extract to `specs/guides/patterns/`

**For each new pattern:**

```markdown
# Pattern: {Name}

## Context
When to use this pattern.

## Implementation
```python
# Code example
```

## Usage
How to apply this pattern.
```

**Output**: "✓ Phase 3 complete - Patterns extracted"

---

## Phase 4: Documentation Review

**Check if CLAUDE.md needs updates:**

- New architectural patterns?
- New commands or workflows?
- Updated anti-patterns?

**Check if pattern library needs updates:**

- New reusable patterns?
- Updates to existing patterns?

**Output**: "✓ Phase 4 complete - Documentation reviewed"

---

## Phase 5: PRD Completion

**Verify all acceptance criteria met:**

1. Read PRD acceptance criteria
2. Verify each criterion
3. Document any deviations

**Update PRD status:**

```bash
echo "## Completion Status" >> specs/active/{slug}/prd.md
echo "Completed: $(date)" >> specs/active/{slug}/prd.md
echo "All acceptance criteria met: [YES/NO]" >> specs/active/{slug}/prd.md
```

**Output**: "✓ Phase 5 complete - PRD acceptance criteria verified"

---

## Phase 6: Archive Workspace

**Move completed workspace to archive:**

```bash
mv specs/active/{slug} specs/archive/{slug}
```

**Output**: "✓ Phase 6 complete - Workspace archived"

---

## Final Summary

```
Review Phase Complete ✓

Quality Gates:
- ✓ All tests passing
- ✓ Linting clean
- ✓ Type checking passed
- ✓ Coverage: XX%

Anti-Patterns:
- ✓ None found

Patterns Extracted:
- {list of new patterns}

Documentation:
- ✓ CLAUDE.md [updated/no changes needed]
- ✓ Pattern library [updated/no changes needed]

Feature Status: COMPLETE
Workspace: specs/archive/{slug}/
```
