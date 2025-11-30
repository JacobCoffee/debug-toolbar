---
description: Explore the codebase to understand architecture and patterns
allowed-tools: Read, Glob, Grep, Bash, Task, mcp__zen__analyze
---

# Codebase Exploration

You are exploring: **$ARGUMENTS**

## Exploration Strategy

Use the Task tool with `subagent_type=Explore` for thorough codebase exploration.

## Quick Reference

### Architecture Overview

```
src/debug_toolbar/
├── __init__.py              # Public API exports
├── core/                    # Framework-agnostic core
│   ├── panel.py             # Panel ABC
│   ├── toolbar.py           # DebugToolbar manager
│   ├── config.py            # DebugToolbarConfig
│   ├── context.py           # RequestContext
│   ├── storage.py           # ToolbarStorage
│   └── panels/              # Built-in panels
├── litestar/                # Litestar integration
│   ├── plugin.py            # DebugToolbarPlugin
│   ├── middleware.py        # ASGI middleware
│   ├── config.py            # LitestarDebugToolbarConfig
│   ├── routes/              # API routes
│   └── panels/              # Litestar-specific panels
└── extras/                  # Optional integrations
    └── advanced_alchemy/    # SQLAlchemy/AA integration
```

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `Panel` | core/panel.py | Abstract base for all panels |
| `DebugToolbar` | core/toolbar.py | Main toolbar manager |
| `DebugToolbarConfig` | core/config.py | Core configuration |
| `RequestContext` | core/context.py | Request-scoped data |
| `DebugToolbarPlugin` | litestar/plugin.py | Litestar integration |

### Common Exploration Tasks

**Find all panels:**

```bash
grep -r "class.*Panel" src/debug_toolbar/
```

**Find all configs:**

```bash
grep -r "class.*Config" src/debug_toolbar/
```

**Find all tests for a module:**

```bash
find tests/ -name "test_*.py" | xargs grep -l "{module_name}"
```

**Find usage of a class:**

```bash
grep -r "ClassName" src/ tests/
```

### Deep Exploration

For complex exploration, use:

```
Task(
    subagent_type="Explore",
    prompt="Explore {topic} in the codebase. Find:
    1. All related files
    2. Key patterns used
    3. How components connect
    4. Testing approaches"
)
```

### Pattern Analysis

To understand a pattern:

1. Find all implementations:

   ```bash
   grep -r "pattern_name" src/
   ```

2. Read 3-5 examples
3. Document common structure
4. Note variations

## Output Format

```
Exploration Results: {topic}

Files Found:
- path/to/file1.py - Description
- path/to/file2.py - Description

Patterns Identified:
- Pattern 1: Description
- Pattern 2: Description

Key Insights:
- Insight 1
- Insight 2

Related Tests:
- tests/unit/test_*.py
```
