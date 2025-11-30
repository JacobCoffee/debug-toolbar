# Session Recovery Guide: GraphQL Panel

**Feature Slug**: `graphql-panel`
**Status**: PRD Complete, Ready for Implementation
**Last Updated**: 2025-11-29

---

## Quick Context

This workspace contains the PRD for a GraphQL panel with Strawberry integration for the Litestar debug-toolbar project. The panel tracks GraphQL operations, resolver timing, and detects N+1 patterns.

---

## Workspace Structure

```
specs/active/graphql-panel/
├── prd.md                  # Comprehensive PRD (7,814 words)
├── research/
│   └── plan.md             # Research notes and planning (2,247 words)
├── tmp/
│   └── new-patterns.md     # Pattern discovery (created during implementation)
└── RECOVERY.md             # This file
```

---

## Current Status

**Phase**: PRD Complete
**Next Phase**: Implementation (Checkpoint 2)

### Completed Work

- ✅ Competitor analysis (FastAPI Debug Toolbar)
- ✅ Strawberry SchemaExtension API research
- ✅ Pattern analysis (SQLAlchemyPanel, TimerPanel, RequestPanel)
- ✅ Architecture design (Two-Tracker Pattern)
- ✅ Data model design (TrackedOperation, TrackedResolver)
- ✅ N+1 detection algorithm design
- ✅ Comprehensive PRD (3200+ words requirement met)
- ✅ Research documentation (2000+ words requirement met)

### Pending Work

Checkpoints 2-8 (see PRD section "Implementation Checkpoints"):
1. ✅ Research & PRD
2. ⏳ Implement tracker classes (models.py)
3. ⏳ Implement SchemaExtension (extension.py)
4. ⏳ Implement GraphQLPanel (panel.py)
5. ⏳ Implement analyzers (N+1 detection)
6. ⏳ Write unit tests (90%+ coverage)
7. ⏳ Write integration tests
8. ⏳ Review & pattern extraction

---

## Key Decisions Made

### 1. Technology Selection
- **Chosen**: Strawberry GraphQL (Context7 ID: `/strawberry-graphql/strawberry`)
- **Rationale**: Best Python GraphQL library, async-native, type-safe, strong extension system
- **Benchmark Score**: 92.6 (High reputation)

### 2. Architecture Pattern
- **Two-Tracker Pattern**: Separate trackers for operations and resolvers
- **Inspired by**: SQLAlchemyPanel's QueryTracker pattern
- **Storage**: RequestContext via contextvars (thread-safe)

### 3. Integration Approach
- **Location**: `src/debug_toolbar/extras/strawberry/` (optional integration)
- **Installation**: `pip install debug-toolbar[strawberry]`
- **User Setup**: Add `DebugToolbarExtension` to Strawberry schema

### 4. N+1 Detection
- **Threshold**: 3+ resolver calls (configurable)
- **Algorithm**: Group by `(parent_type, field_name, arg_signature)`
- **Suggestion**: Recommend DataLoader for batching

### 5. Known Issues to Handle
- **Strawberry Issue #3413**: FIFO lifecycle hook ordering (use `resolve()` for timing)
- **Strawberry Issue #3414**: Exception short-circuiting (wrap in try/except)
- **Strawberry Issue #3148**: Context isolation (store in RequestContext, not instance)

---

## Files to Create (Implementation Phase)

### Source Files (~610 lines total)

```
src/debug_toolbar/extras/strawberry/
├── __init__.py                    # 20 lines - Public exports
├── panel.py                       # 150 lines - GraphQLPanel class
├── extension.py                   # 200 lines - DebugToolbarExtension
├── models.py                      # 80 lines - TrackedOperation, TrackedResolver
├── analyzers.py                   # 120 lines - N1Analyzer, DuplicateDetector
└── utils.py                       # 60 lines - Stack capture, formatting
```

### Test Files (~940 lines total)

```
tests/unit/
├── test_graphql_extension.py     # 200 lines
├── test_graphql_panel.py          # 250 lines
├── test_graphql_analyzers.py     # 150 lines
├── test_graphql_models.py         # 80 lines
└── test_graphql_utils.py          # 60 lines

tests/integration/
└── test_graphql_strawberry_integration.py  # 200 lines
```

### Documentation (~100 lines)

```
docs/panels/graphql.md             # 100 lines - Usage guide
```

**Total**: ~1,650 lines of new code

---

## Critical Context for Implementation

### 1. Strawberry Extension Hooks

**on_operation()** - Wraps entire operation:
```python
def on_operation(self) -> Generator[None, None, None]:
    # Before operation
    exec_ctx = self.execution_context
    operation = TrackedOperation(...)
    context.store_panel_data("GraphQLPanel", "current_operation", operation)

    yield  # Execute operation

    # After operation
    operation.end_time = time.perf_counter()
    operations.append(operation)
```

**resolve()** - Called for EVERY resolver:
```python
async def resolve(self, _next, root, info, *args, **kwargs):
    start = time.perf_counter()
    resolver = TrackedResolver(...)

    result = await _next(root, info, *args, **kwargs)

    resolver.end_time = time.perf_counter()
    current_op.resolvers.append(resolver)
    return result
```

### 2. RequestContext Integration

**Store data**:
```python
from debug_toolbar.core.context import get_request_context

context = get_request_context()
if context is not None:
    context.store_panel_data("GraphQLPanel", "operations", [operation])
```

**Retrieve data**:
```python
async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
    panel_data = context.get_panel_data(self.get_panel_id())
    operations = panel_data.get("operations", [])
```

### 3. N+1 Detection Algorithm

```python
# Group resolvers by signature
for resolver in operation.resolvers:
    sig = f"{resolver.parent_type}.{resolver.field_name}({arg_types})"
    patterns[sig]["count"] += 1

# Flag if count >= threshold
n_plus_one = [p for p in patterns.values() if p["count"] >= 3]
```

### 4. Error Handling Pattern

```python
try:
    result = await _next(root, info, *args, **kwargs)
except Exception:
    # Still record resolver timing even on exception
    resolver.end_time = time.perf_counter()
    current_op.resolvers.append(resolver)
    raise  # Re-raise to preserve GraphQL error handling
```

---

## Testing Strategy Summary

### Unit Test Coverage Targets (90%+)

1. **Extension Tests** (`test_graphql_extension.py`):
   - Initialization with custom thresholds
   - on_operation() lifecycle (before/after yield)
   - resolve() timing and metadata capture
   - Missing RequestContext graceful handling
   - Exception handling in resolvers

2. **Panel Tests** (`test_graphql_panel.py`):
   - generate_stats() with no operations
   - generate_stats() with operations
   - Slow operation detection
   - Resolver tree building
   - Server-Timing header generation

3. **Analyzer Tests** (`test_graphql_analyzers.py`):
   - N+1 pattern detection (above/below threshold)
   - Duplicate operation detection
   - Suggestion generation

### Integration Test Scenarios

1. **Simple Query**: Track single operation, verify metadata
2. **Nested Resolvers**: Verify hierarchical tracking
3. **N+1 Pattern**: Trigger real N+1, verify detection
4. **Error Handling**: Resolver throws exception, verify tracking
5. **DataLoader**: Ensure batching doesn't break tracking
6. **Concurrent**: Multiple operations, verify isolation

---

## Commands for Next Session

### Start Implementation

```bash
# Navigate to workspace
cd /home/cody/code/litestar/debug-toolbar

# Create source directory structure
mkdir -p src/debug_toolbar/extras/strawberry
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p docs/panels

# Start with models (Checkpoint 2)
# Create: src/debug_toolbar/extras/strawberry/models.py
# Then: tests/unit/test_graphql_models.py
```

### Run Tests During Development

```bash
# Run specific test file
pytest tests/unit/test_graphql_models.py -v

# Run with coverage
pytest tests/unit/test_graphql_models.py --cov=src/debug_toolbar/extras/strawberry

# Run all GraphQL tests
pytest tests/unit/test_graphql_*.py tests/integration/test_graphql_*.py
```

### Quality Checks

```bash
# Lint
make lint

# Type check
make type-check

# Format
make fmt

# Full test suite
make test

# Coverage report
make test-cov
```

---

## Questions for Clarification (if resuming)

1. **Checkpoint Progress**: Which checkpoint are we on? (2-8)
2. **Files Created**: Which files have been implemented?
3. **Test Status**: Current test coverage percentage?
4. **Blockers**: Any implementation challenges encountered?
5. **Pattern Discovery**: Any new patterns to document in `tmp/new-patterns.md`?

---

## References for Quick Lookup

### PRD Sections
- **Architecture Overview**: Line 348 in prd.md
- **Data Flow Diagram**: Line 374 in prd.md
- **DebugToolbarExtension Spec**: Line 421 in prd.md
- **Data Models**: Line 613 in prd.md
- **N+1 Analyzer**: Line 672 in prd.md
- **GraphQLPanel**: Line 756 in prd.md
- **Testing Strategy**: Line 881 in prd.md

### Research Sections
- **Strawberry Extension System**: Line 56 in research/plan.md
- **Known Issues**: Line 130 in research/plan.md
- **Pattern Analysis**: Line 158 in research/plan.md
- **Architecture Decision**: Line 216 in research/plan.md

### External Documentation
- Strawberry Extensions: https://strawberry.rocks/docs/guides/custom-extensions
- SchemaExtension API: https://strawberry.rocks/api-reference/strawberry.extensions.SchemaExtension
- FastAPI Debug Toolbar: https://fastapi-debug-toolbar.domake.io/

---

## Estimated Timeline

- **Checkpoint 2** (Models): 30 minutes
- **Checkpoint 3** (Extension): 3 hours
- **Checkpoint 4** (Panel): 2 hours
- **Checkpoint 5** (Analyzers): 2 hours
- **Checkpoint 6** (Unit Tests): 2 hours
- **Checkpoint 7** (Integration): 2 hours
- **Checkpoint 8** (Review): 1 hour

**Total**: ~12.5 hours (within Medium complexity estimate)

---

## Success Criteria Checklist

### Functional
- [ ] Tracks GraphQL operations (query/mutation/subscription)
- [ ] Tracks individual resolver executions
- [ ] Displays resolver hierarchy
- [ ] Detects N+1 patterns (3+ threshold)
- [ ] Marks slow operations (> 100ms)
- [ ] Marks slow resolvers (> 10ms)
- [ ] Captures GraphQL errors
- [ ] Handles exceptions gracefully

### Non-Functional
- [ ] 90%+ test coverage
- [ ] < 5% performance overhead when enabled
- [ ] Zero impact when disabled
- [ ] Thread-safe (RequestContext storage)
- [ ] No linting errors
- [ ] No type errors
- [ ] Works with async resolvers
- [ ] Compatible with DataLoader

### Documentation
- [ ] Usage guide in docs/panels/graphql.md
- [ ] Integration example in PRD
- [ ] Patterns documented in tmp/new-patterns.md

---

## Recovery Command

To resume work on this feature:

```bash
# Read PRD
cat /home/cody/code/litestar/debug-toolbar/specs/active/graphql-panel/prd.md

# Read research
cat /home/cody/code/litestar/debug-toolbar/specs/active/graphql-panel/research/plan.md

# Check current status
ls -la /home/cody/code/litestar/debug-toolbar/src/debug_toolbar/extras/strawberry/

# Continue from last checkpoint
```

---

**Last Updated**: 2025-11-29
**Next Action**: Implement Checkpoint 2 (models.py)
