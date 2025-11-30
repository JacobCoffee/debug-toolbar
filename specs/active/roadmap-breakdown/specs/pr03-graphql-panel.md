# Spec: PR #3 - GraphQL Panel (Strawberry Integration)

## Metadata
- **PR Number**: 3
- **Priority**: P2
- **Complexity**: Medium
- **Estimated Files**: 5-7
- **Dependencies**: None
- **Implementation Order**: 7

---

## Problem Statement

GraphQL APIs have different debugging needs than REST:
- Query/mutation tracking with operation names
- Resolver-level timing breakdown
- Variable inspection
- Query complexity analysis

FastAPI Debug Toolbar has GraphQL support - we need feature parity.

---

## Goals

1. Track GraphQL queries and mutations
2. Display resolver timing breakdown
3. Show variables and context
4. Error tracking with locations
5. Optional query complexity analysis

---

## Technical Approach

### Strawberry Extension

```python
# src/debug_toolbar/extras/strawberry/extension.py
from strawberry.extensions import SchemaExtension

class DebugToolbarExtension(SchemaExtension):
    async def on_operation(self):
        # Record operation start
        yield
        # Record operation end

    async def resolve(self, _next, root, info, *args, **kwargs):
        start = time.perf_counter()
        result = await _next(root, info, *args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        GraphQLTracker.record_resolver(info.field_name, duration)
        return result
```

### Files to Create

```
src/debug_toolbar/extras/strawberry/
├── __init__.py
├── panel.py
└── extension.py
```

---

## Acceptance Criteria

- [ ] Track GraphQL operations (query/mutation/subscription)
- [ ] Display operation name and type
- [ ] Resolver timing breakdown
- [ ] Variable inspection
- [ ] Error tracking with GraphQL locations
- [ ] Query complexity display (if enabled)
- [ ] 90%+ test coverage
