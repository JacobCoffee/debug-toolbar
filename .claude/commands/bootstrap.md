---
description: Re-bootstrap the project (alignment mode)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Bootstrap Alignment Mode

This command re-bootstraps the project infrastructure, preserving custom content.

## Alignment Workflow

### Phase 1: Inventory Existing Configuration

```bash
# List existing commands
ls .claude/commands/*.md 2>/dev/null

# List existing skills
ls -d .claude/skills/*/ 2>/dev/null

# List existing agents
ls .claude/agents/*.md 2>/dev/null

# Check CLAUDE.md version
head -5 CLAUDE.md 2>/dev/null | grep "Version"

# Check pattern library
ls specs/guides/patterns/*.md 2>/dev/null
```

### Phase 2: Identify Updates

**Core commands (must exist):**

- prd.md
- implement.md
- test.md
- review.md
- explore.md
- fix-issue.md
- bootstrap.md

**Core agents (must exist):**

- prd.md
- expert.md
- testing.md
- docs-vision.md

**Infrastructure (must exist):**

- CLAUDE.md
- .claude/mcp-strategy.md
- specs/guides/quality-gates.yaml
- specs/guides/patterns/README.md

### Phase 3: Preserve Custom Content

Before updating any file:

1. Read existing content
2. Identify custom sections (marked with `## Custom:`)
3. Store for preservation
4. Merge into updated file

### Phase 4: Apply Updates

Update files that are out of date while preserving custom content.

### Phase 5: Report

```
Alignment Complete ✓

Updated:
- CLAUDE.md (version X.X → Y.Y)
- .claude/commands/prd.md

Preserved Custom Content:
- .claude/commands/custom-command.md

No Changes Needed:
- specs/guides/quality-gates.yaml
```
