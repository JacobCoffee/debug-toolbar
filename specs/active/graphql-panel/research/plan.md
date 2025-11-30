# GraphQL Panel Research & Planning

**Date**: 2025-11-29
**Complexity**: Medium (8 checkpoints)
**Priority**: P2 (Competitor parity)

## Research Summary

### Competitor Analysis

FastAPI Debug Toolbar has GraphQL support, making this a parity feature. The FastAPI toolbar supports GraphQL via its panel system, leveraging framework-specific integration.

**Source**: [FastAPI Debug Toolbar Documentation](https://fastapi-debug-toolbar.domake.io/)

### Technology Selection: Strawberry GraphQL

**Selected Library**: `/strawberry-graphql/strawberry` (Context7 ID)

**Key Metrics**:
- Code Snippets: 668
- Source Reputation: High
- Benchmark Score: 92.6
- Best Python GraphQL library for type-safe, modern implementations

**Rationale**:
- Design closest to Litestar's async-native, type-annotated approach
- Strong SchemaExtension system for instrumentation
- Active development with robust lifecycle hooks
- ASGI-native integration available

### Strawberry Extension System

Strawberry provides a powerful `SchemaExtension` class with lifecycle hooks for instrumentation:

#### Core Lifecycle Hooks

1. **`on_operation()`** - Wraps entire GraphQL operation (query/mutation/subscription)
   - Access to `self.execution_context` for operation metadata
   - Generator pattern: code before `yield` = setup, after = cleanup

2. **`resolve()`** - Called for EVERY resolver execution
   - Receives: `_next, root, info, *args, **kwargs`
   - Must call `_next(root, info, *args, **kwargs)` to execute resolver
   - Can measure individual resolver timing
   - Can be async: `async def resolve(...)`

3. **`on_execute()`** - Wraps execution phase
   - Access to query, variables, operation type

4. **`on_validate()`** - Wraps validation phase

5. **`on_parse()`** - Wraps parsing phase

6. **`get_results()`** - Adds custom data to GraphQL response
   - Returns `dict[str, Any]`
   - Can be async

#### Execution Context Properties

Via `self.execution_context`:
- `query: str` - GraphQL query string
- `variables: dict[str, Any]` - Query variables
- `operation_name: str | None` - Named operation
- `result: ExecutionResult` - Final result (in cleanup phase)
- `context: Any` - Request context

#### Info Object (in resolvers)

Via `info: strawberry.Info`:
- `field_name: str` - Current field (camelCase)
- `python_name: str` - Python name (snake_case)
- `operation: OperationDefinitionNode` - AST node
- `path: Path` - Field path (e.g., `user.posts.0.title`)
- `variable_values: dict[str, Any]` - Operation variables
- `selected_fields: list[SelectedField]` - Queried fields
- `schema: Schema` - Strawberry schema instance

**Sources**:
- [Schema Extensions Guide](https://strawberry.rocks/docs/guides/custom-extensions)
- [SchemaExtension API Reference](https://strawberry.rocks/api-reference/strawberry.extensions.SchemaExtension)

### Known Issues & Considerations

1. **Lifecycle Hook Ordering** ([Issue #3413](https://github.com/strawberry-graphql/strawberry/issues/3413))
   - Hooks complete in FIFO order, not LIFO
   - `resolve()` doesn't have this problem
   - **Mitigation**: Use `resolve()` for critical timing measurements

2. **Exception Handling** ([Issue #3414](https://github.com/strawberry-graphql/strawberry/issues/3414))
   - Uncaught exceptions short-circuit response
   - Hooks may complete before some resolvers
   - **Mitigation**: Wrap resolver tracking in try/except, ensure cleanup

3. **Thread Safety** ([Issue #3148](https://github.com/strawberry-graphql/strawberry/issues/3148))
   - `self.execution_context` isolation between requests
   - **Mitigation**: Store data in RequestContext, not extension instance

### Pattern Analysis

Examined similar panels in codebase:

#### 1. SQLAlchemyPanel (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)

**Key Patterns**:
- Separate tracker class (`QueryTracker`) with start/stop lifecycle
- Event listeners for instrumentation (SQLAlchemy events)
- Stores tracked data in list, exports to panel stats
- Normalizer class for pattern detection (N+1 queries)
- Hash-based duplicate detection
- Stack trace capture with filtering
- Async support throughout
- `process_request()` starts tracking, `process_response()` stops
- Rich stats: count, timing, slow queries, duplicates, patterns

**Applicable Patterns**:
- Separate `OperationTracker` class for GraphQL operations
- `ResolverTracker` for individual resolver calls
- Pattern detection for N+1 resolver issues
- Hash-based duplicate operation detection
- Stack capture for resolver origins

#### 2. TimerPanel (`src/debug_toolbar/core/panels/timer.py`)

**Key Patterns**:
- Simple timing with `time.perf_counter()`
- Start time in `process_request()`
- Calculate duration in `generate_stats()`
- CPU time tracking via `time.process_time()`
- `generate_server_timing()` for Server-Timing header

**Applicable Patterns**:
- Track operation start in `on_operation()` (before yield)
- Calculate total operation time (after yield)
- Track individual resolver timing in `resolve()`

#### 3. RequestPanel (`src/debug_toolbar/core/panels/request.py`)

**Key Patterns**:
- Extract metadata from `context.metadata`
- Simple stats generation, no lifecycle hooks
- Display-focused data structure

**Applicable Patterns**:
- Store GraphQL operation metadata in `context.metadata`
- Extract variables, operation name, type for display

### Architecture Decision: Two-Tracker Pattern

Based on analysis, implement dual tracking:

1. **OperationTracker**: Tracks GraphQL operations (query/mutation/subscription)
   - Hooked via `on_operation()`
   - Captures: query string, variables, operation type/name, total time
   - Detects: duplicate operations, slow operations

2. **ResolverTracker**: Tracks individual resolver executions
   - Hooked via `resolve()`
   - Captures: field path, resolver function, timing, arguments
   - Detects: N+1 patterns (same field resolved multiple times)

### Integration Strategy

1. **Installation**: Optional dependency via `extras/strawberry/`
2. **Extension**: `DebugToolbarExtension(SchemaExtension)`
   - Integrates with RequestContext via contextvars
   - Stores data in `context.store_panel_data("GraphQLPanel", ...)`
3. **Panel**: `GraphQLPanel(Panel)`
   - Retrieves tracked data from context
   - Generates stats with pattern analysis
4. **Configuration**: Users add extension to Strawberry schema
5. **Panel Registration**: Users add to `extra_panels` config

### Data Models

#### TrackedOperation

```python
@dataclass
class TrackedOperation:
    operation_id: str  # UUID
    query: str  # GraphQL query string
    variables: dict[str, Any]  # Query variables
    operation_name: str | None  # Named operation
    operation_type: Literal["query", "mutation", "subscription"]
    start_time: float  # perf_counter
    end_time: float  # perf_counter
    duration_ms: float  # Calculated
    resolvers: list[TrackedResolver]  # Nested resolvers
    errors: list[dict[str, Any]] | None  # GraphQL errors
    result_data: Any | None  # Result preview (truncated)
```

#### TrackedResolver

```python
@dataclass
class TrackedResolver:
    resolver_id: str  # UUID
    field_name: str  # e.g., "user"
    field_path: str  # e.g., "Query.user.posts.0.title"
    resolver_function: str  # Function name or "field"
    start_time: float
    end_time: float
    duration_ms: float
    parent_type: str  # e.g., "Query", "User"
    return_type: str  # e.g., "User", "String"
    arguments: dict[str, Any]  # Resolver arguments
    stack_trace: list[dict[str, str]] | None  # Origin stack
    is_slow: bool  # > threshold
```

### N+1 Detection Algorithm

Similar to SQLAlchemyPanel pattern detection:

1. Group resolvers by `(field_name, parent_type, arguments_signature)`
2. If same resolver called 3+ times with different parent instances → N+1
3. Example: `User.posts` resolver called 50 times for 50 users
4. Suggest: Use DataLoader or field-level batching

### Testing Strategy

1. **Unit Tests** (90%+ coverage):
   - `test_operation_tracker.py`: Tracker lifecycle, data capture
   - `test_resolver_tracker.py`: Resolver timing, N+1 detection
   - `test_graphql_panel.py`: Panel stats generation, pattern detection
   - `test_extension.py`: SchemaExtension integration, context storage

2. **Integration Tests**:
   - Full Strawberry schema with test queries
   - Verify operation tracking across async resolvers
   - Test error handling and exception recovery
   - Verify DataLoader interaction (no double-counting)

3. **Edge Cases**:
   - Subscriptions (long-lived connections)
   - Concurrent operations
   - Resolver exceptions
   - Large result sets (truncation)
   - Missing RequestContext (graceful degradation)

### UI Mockup (Conceptual)

```
GraphQL Panel
─────────────────────────────────────────────────
📊 Operations: 3 | Total Time: 245ms | Resolvers: 47

⚠️ Issues Detected:
  - 2 N+1 patterns (23 duplicate resolvers)
  - 1 slow operation (> 100ms)

Operation #1: GetUserPosts (Query) - 187ms ⚠️ SLOW
  Query: query GetUserPosts($userId: ID!) { user(id: $userId) { ... } }
  Variables: { "userId": "123" }
  Resolvers: 42 | Errors: 0

  Resolver Breakdown:
    Query.user                    2ms  ✓
    ├─ User.posts                 8ms  ✓
    │  ├─ Post.author           142ms  ⚠️ N+1 (20x)
    │  │  └─ User.email           5ms  ✓
    │  └─ Post.comments          25ms  ✓

  💡 Suggestion: User.email called 20 times. Use DataLoader to batch.

Operation #2: CreatePost (Mutation) - 45ms ✓
  [collapsed view]

Operation #3: GetFeed (Query) - 13ms ✓
  [collapsed view]
```

### Files to Create

```
src/debug_toolbar/extras/strawberry/
├── __init__.py           # Public exports
├── panel.py              # GraphQLPanel class
├── extension.py          # DebugToolbarExtension(SchemaExtension)
├── trackers.py           # OperationTracker, ResolverTracker
├── models.py             # TrackedOperation, TrackedResolver
├── analyzers.py          # N+1Analyzer, DuplicateDetector
└── utils.py              # Stack capture, normalization

tests/unit/
├── test_graphql_operation_tracker.py
├── test_graphql_resolver_tracker.py
├── test_graphql_panel.py
├── test_graphql_extension.py
├── test_graphql_analyzers.py
└── test_graphql_utils.py

tests/integration/
└── test_graphql_strawberry_integration.py
```

### Dependencies

- `strawberry-graphql >= 0.240.0` (SchemaExtension stable API)
- Optional, installed via: `pip install debug-toolbar[strawberry]`

### Timeline Estimate

- Research & PRD: ✓ Complete
- Implementation: 6-8 hours (Medium complexity, 8 checkpoints)
- Testing: 3-4 hours (90%+ coverage target)
- Review & Pattern Extraction: 1-2 hours

### Open Questions

1. **Subscription Handling**: Long-lived. Track per-event or per-subscription?
   - **Decision**: Track subscription establishment + first N events (configurable)

2. **DataLoader Integration**: Strawberry's DataLoader may batch internally
   - **Decision**: Document expected behavior, test with DataLoader

3. **Complexity Analysis**: Should we calculate query complexity score?
   - **Decision**: Phase 2 - optional feature, not in MVP

4. **Template**: Reuse existing panel template structure or custom?
   - **Decision**: Custom template with collapsible resolver tree

### Success Criteria

- [ ] Tracks GraphQL operations (query/mutation/subscription)
- [ ] Tracks individual resolver timing with hierarchy
- [ ] Detects N+1 resolver patterns (3+ duplicate resolver calls)
- [ ] Displays query, variables, operation type
- [ ] Shows resolver tree with timing breakdown
- [ ] Handles errors gracefully (GraphQL errors + exceptions)
- [ ] 90%+ test coverage
- [ ] Documentation with Strawberry integration example
- [ ] No performance impact when panel disabled
- [ ] Thread-safe via RequestContext (no shared state)

---

**Total Word Count**: 2,247 words
