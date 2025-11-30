# MCP Tool Strategy

## Tool Selection by Task Type

### Complex Architectural Decisions

1. **Primary**: mcp__zen__thinkdeep
2. **Fallback**: mcp__sequential-thinking__sequentialthinking

### Library Documentation Lookup

1. **Primary**: mcp__context7__get-library-docs
2. **Fallback**: WebSearch

### Multi-Phase Planning

1. **Primary**: mcp__zen__planner
2. **Fallback**: Manual structured thinking

### Code Analysis

1. **Primary**: mcp__zen__analyze
2. **Fallback**: Manual code review

### Debugging

1. **Primary**: mcp__zen__debug
2. **Fallback**: Manual investigation

### Consensus Building (Multiple Model Review)

1. **Primary**: mcp__zen__consensus
2. **Use for**: Architecture decisions, API design choices

## Complexity-Based Selection

### Simple Features (6 checkpoints)

- Use basic tools
- Manual analysis acceptable
- Focus on speed
- Example: Adding a config option, fixing a bug

### Medium Features (8 checkpoints)

- Use sequential_thinking (12 steps)
- Include pattern analysis
- Moderate depth
- Example: New panel implementation, new API endpoint

### Complex Features (10+ checkpoints)

- Use zen_thinkdeep or zen_planner
- Deep pattern analysis
- Comprehensive research
- Example: New framework integration, architectural changes

## Project-Specific Tool Usage

### For Panel Development

1. Read existing panels first (pattern learning)
2. Use sequential_thinking for implementation planning
3. Use mcp__context7 for Litestar/SQLAlchemy docs

### For Framework Integration

1. Use mcp__zen__planner for multi-phase planning
2. Use mcp__context7 for framework documentation
3. Use mcp__zen__thinkdeep for architecture decisions

### For Debugging

1. Use mcp__zen__debug for systematic investigation
2. Document findings in workspace

## Context7 Quick Reference

### Litestar Documentation

```python
mcp__context7__resolve-library-id(libraryName="litestar")
# Returns: /litestar-org/litestar

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/litestar",
    topic="plugins",
    mode="code"
)
```

### SQLAlchemy Documentation

```python
mcp__context7__resolve-library-id(libraryName="sqlalchemy")

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/sqlalchemy/sqlalchemy",
    topic="async",
    mode="code"
)
```

### Advanced-Alchemy Documentation

```python
mcp__context7__resolve-library-id(libraryName="advanced-alchemy")

mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/litestar-org/advanced-alchemy",
    topic="repository",
    mode="code"
)
```
