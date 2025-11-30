---
description: Create a PRD with pattern learning and adaptive complexity
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking, mcp__zen__planner
---

# Intelligent PRD Creation Workflow

You are creating a Product Requirements Document for: **$ARGUMENTS**

## Intelligence Layer (ACTIVATE FIRST)

Before starting checkpoints:

1. **Read MCP Strategy**: Load `.claude/mcp-strategy.md` for tool selection
2. **Learn from Codebase**: Read 3-5 similar implementations
3. **Assess Complexity**: Determine simple/medium/complex
4. **Adapt Workflow**: Adjust checkpoint depth

## Critical Rules

1. **CONTEXT FIRST** - Read existing patterns before planning
2. **NO CODE MODIFICATION** - Planning only
3. **PATTERN LEARNING** - Identify 3-5 similar features
4. **ADAPTIVE DEPTH** - Simple=6, Medium=8, Complex=10+ checkpoints
5. **RESEARCH GROUNDED** - Minimum 2000+ words research
6. **COMPREHENSIVE PRD** - Minimum 3200+ words

---

## Checkpoint 0: Intelligence Bootstrap

**Load project intelligence:**

1. Read `CLAUDE.md`
2. Read `specs/guides/patterns/README.md`
3. Read `.claude/mcp-strategy.md`

**Learn from existing implementations:**

For panels: Read files in `src/debug_toolbar/core/panels/`
For integrations: Read files in `src/debug_toolbar/litestar/`
For extras: Read files in `src/debug_toolbar/extras/`

**Assess complexity:**

- **Simple**: Config change, bug fix, single file → 6 checkpoints
- **Medium**: New panel, API endpoint, 2-3 files → 8 checkpoints
- **Complex**: New integration, architecture change, 5+ files → 10+ checkpoints

**Output**: "✓ Checkpoint 0 complete - Complexity: [level], Checkpoints: [count]"

---

## Checkpoint 1: Pattern Recognition

**Identify similar implementations:**

1. Search for related patterns in `src/debug_toolbar/`
2. Read at least 3 similar files
3. Extract naming patterns
4. Note testing patterns from `tests/`

**Document:**

```markdown
## Similar Implementations

1. `src/path/to/similar1.py` - Description
2. `src/path/to/similar2.py` - Description
3. `src/path/to/similar3.py` - Description

## Patterns Observed

- Class structure: ...
- Naming conventions: ...
- Error handling: ...
```

**Output**: "✓ Checkpoint 1 complete - Patterns identified"

---

## Checkpoint 2: Workspace Creation

```bash
mkdir -p specs/active/{slug}/research
mkdir -p specs/active/{slug}/tmp
mkdir -p specs/active/{slug}/patterns
```

Create initial files:
- `specs/active/{slug}/research/plan.md`
- `specs/active/{slug}/tmp/new-patterns.md`

**Output**: "✓ Checkpoint 2 complete - Workspace at specs/active/{slug}/"

---

## Checkpoint 3: Intelligent Analysis

**Use appropriate tool based on complexity:**

- Simple: 10 structured thoughts
- Medium: Sequential thinking (15 thoughts)
- Complex: zen_planner or thinkdeep

**For panels:** Analyze Panel ABC interface, existing panels, template patterns
**For integrations:** Analyze plugin protocol, middleware patterns, config inheritance

**Document in workspace.**

**Output**: "✓ Checkpoint 3 complete - Analysis using [tool]"

---

## Checkpoint 4: Research (2000+ words)

**Priority order:**

1. Pattern Library: `specs/guides/patterns/`
2. Internal Guides: `specs/guides/`
3. Context7: Litestar/SQLAlchemy documentation
4. WebSearch: Best practices

**For panel development:**
```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="middleware",
    mode="code"
)
```

**Verify:** `wc -w specs/active/{slug}/research/plan.md`

**Output**: "✓ Checkpoint 4 complete - Research (2000+ words)"

---

## Checkpoint 5: Write PRD (3200+ words)

Include:
- Intelligence context (complexity, similar features, patterns)
- Problem statement
- Acceptance criteria (specific, measurable)
- Technical approach with pattern references
- Testing strategy (90%+ coverage target)
- Files to create/modify

**Template:**

```markdown
# PRD: {Feature Name}

## Metadata
- Slug: {slug}
- Complexity: {simple|medium|complex}
- Checkpoints: {6|8|10+}

## Intelligence Context
### Similar Implementations
- ...

### Patterns to Follow
- ...

## Problem Statement
...

## Acceptance Criteria
1. [ ] ...
2. [ ] ...

## Technical Approach
...

## Files to Create/Modify
- `src/debug_toolbar/...`
- `tests/unit/...`

## Testing Strategy
- Coverage target: 90%+
- Key test cases: ...

## Out of Scope
- ...
```

**Verify:** `wc -w specs/active/{slug}/prd.md`

**Output**: "✓ Checkpoint 5 complete - PRD (3200+ words)"

---

## Checkpoint 6: Task Breakdown

Adapt to complexity level.

**Simple (6 checkpoints):**
1. Implement core functionality
2. Add tests
3. Update config if needed

**Medium (8 checkpoints):**
1. Create base class/module
2. Implement core logic
3. Add lifecycle hooks
4. Write unit tests
5. Write integration tests
6. Update documentation

**Complex (10+ checkpoints):**
- Full breakdown with dependencies

**Output**: "✓ Checkpoint 6 complete - Tasks adapted to complexity"

---

## Checkpoint 7: Recovery Guide

Create `specs/active/{slug}/RECOVERY.md` with:
- Intelligence context for session resumption
- Current progress state
- How to continue from any checkpoint

**Output**: "✓ Checkpoint 7 complete - Recovery guide with intelligence context"

---

## Checkpoint 8: Git Verification

```bash
git status --porcelain src/ | grep -v "^??"
```

Verify no source code was modified during PRD phase.

**Output**: "✓ Checkpoint 8 complete - No source code modified"

---

## Final Summary

```
PRD Phase Complete ✓

Workspace: specs/active/{slug}/
Complexity: [simple|medium|complex]
Checkpoints: [6|8|10+] completed

Intelligence:
- ✓ Pattern library consulted
- ✓ Similar features analyzed
- ✓ Tool selection optimized

Next: Run `/implement {slug}`
```
