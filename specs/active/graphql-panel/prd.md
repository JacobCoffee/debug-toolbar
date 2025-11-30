# PRD: GraphQL Panel with Strawberry Integration

**Status**: Draft
**Slug**: `graphql-panel`
**Priority**: P2 (Competitor Parity)
**Complexity**: Medium (8 checkpoints)
**Created**: 2025-11-29
**Author**: AI Agent (PRD Subagent)

---

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature Slug** | `graphql-panel` |
| **Complexity Level** | Medium |
| **Checkpoint Count** | 8 |
| **Estimated Effort** | 10-14 hours |
| **Test Coverage Target** | 90%+ |
| **Dependencies** | `strawberry-graphql >= 0.240.0` (optional) |
| **Integration Type** | Extra Panel (`extras/strawberry/`) |
| **Framework Support** | Strawberry GraphQL (ASGI-native) |

---

## Intelligence Context

### Similar Implementations Analyzed

1. **SQLAlchemyPanel** (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)
   - **Lines**: 588
   - **Pattern**: Separate tracker class + event listeners + pattern detection
   - **Key Features**: Query normalization, N+1 detection, stack traces, duplicate queries
   - **Relevance**: High - Similar instrumentation needs (query → operation, SQL → GraphQL)

2. **TimerPanel** (`src/debug_toolbar/core/panels/timer.py`)
   - **Lines**: 74
   - **Pattern**: Simple timing with `perf_counter()`, lifecycle hooks for start/end
   - **Key Features**: CPU time, total request time, Server-Timing header
   - **Relevance**: Medium - Timing patterns applicable to operation/resolver tracking

3. **RequestPanel** (`src/debug_toolbar/core/panels/request.py`)
   - **Lines**: 51
   - **Pattern**: Metadata extraction from context, no lifecycle hooks
   - **Key Features**: Display-focused stats from context.metadata
   - **Relevance**: Low - Simpler pattern, but context storage pattern is relevant

### Complexity Assessment

**Medium Complexity Rationale**:
- ✅ New panel type (GraphQL-specific)
- ✅ External library integration (Strawberry SchemaExtension)
- ✅ Dual tracking system (operations + resolvers)
- ✅ Pattern detection algorithm (N+1 resolvers)
- ✅ Async resolver support required
- ✅ 6-8 new files across `src/` and `tests/`
- ❌ Not a core architecture change (extra panel, not core)
- ❌ Existing panel patterns apply (Panel ABC, RequestContext)

**8 Checkpoints**:
1. Research & PRD ✓
2. Implement tracker classes (OperationTracker, ResolverTracker)
3. Implement SchemaExtension (DebugToolbarExtension)
4. Implement GraphQLPanel with stats generation
5. Implement N+1 analyzer and pattern detection
6. Write unit tests (90%+ coverage)
7. Write integration tests (Strawberry schema)
8. Review & pattern extraction

### Pattern Library References

- **Panel Implementation Pattern**: `specs/guides/patterns/README.md#panel-implementation-pattern`
- **Type Handling**: PEP 604 unions (`T | None`), future annotations, ClassVar
- **Testing Pattern**: Class-based tests, async cleanup, context var management
- **Error Handling**: Graceful degradation for optional dependencies

---

## Problem Statement

### Background

FastAPI Debug Toolbar includes GraphQL panel support, providing developers with visibility into GraphQL operations, resolver timing, and performance issues. The Litestar debug-toolbar currently lacks GraphQL instrumentation, creating a feature gap for teams building GraphQL APIs with Strawberry.

**Competitor Reference**: [FastAPI Debug Toolbar](https://fastapi-debug-toolbar.domake.io/) supports GraphQL with Swagger UI integration.

### User Pain Points

1. **No visibility into GraphQL operations**: Developers cannot see which queries/mutations executed during a request
2. **Resolver performance is opaque**: No breakdown of which resolvers are slow
3. **N+1 resolver problems go undetected**: DataLoader issues only surface in production
4. **Debugging GraphQL errors is difficult**: Error context is lost without instrumentation
5. **Query complexity is unknown**: No metrics on operation size or depth

### Goals

1. **Track GraphQL Operations**: Capture query/mutation/subscription metadata, variables, timing
2. **Resolver-Level Timing**: Show hierarchical resolver breakdown with individual timings
3. **N+1 Detection**: Identify patterns where resolvers execute multiple times unnecessarily
4. **Error Tracking**: Display GraphQL errors with source locations and resolver context
5. **Performance Insights**: Highlight slow operations and resolvers with configurable thresholds

### Non-Goals (Phase 2 / Future)

- Query complexity scoring/limits
- Real-time subscription event streaming in UI
- GraphQL schema introspection panel
- Query caching recommendations
- Automatic DataLoader injection

---

## Acceptance Criteria

### Functional Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **F1** | Track GraphQL operations (query, mutation, subscription) with query string, variables, operation name | Unit test: `test_tracks_operation_metadata()` |
| **F2** | Measure total operation duration (ms) from start to completion | Unit test: `test_operation_timing_accuracy()` |
| **F3** | Track individual resolver executions with field name, path, timing | Unit test: `test_tracks_resolver_executions()` |
| **F4** | Display resolver hierarchy matching GraphQL field tree structure | Integration test: `test_resolver_tree_structure()` |
| **F5** | Detect N+1 resolver patterns (same resolver 3+ times) | Unit test: `test_detects_n_plus_one_patterns()` |
| **F6** | Mark slow operations (> configurable threshold, default 100ms) | Unit test: `test_slow_operation_detection()` |
| **F7** | Mark slow resolvers (> configurable threshold, default 10ms) | Unit test: `test_slow_resolver_detection()` |
| **F8** | Capture GraphQL errors with field paths and error messages | Unit test: `test_captures_graphql_errors()` |
| **F9** | Handle resolver exceptions gracefully without breaking tracking | Unit test: `test_resolver_exception_handling()` |
| **F10** | Store data in RequestContext (thread-safe via contextvars) | Unit test: `test_context_isolation()` |

### Non-Functional Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **NF1** | Zero performance impact when panel not enabled | Benchmark: < 1% overhead when disabled |
| **NF2** | < 5% performance overhead when enabled | Benchmark: async resolver timing overhead |
| **NF3** | Graceful degradation if RequestContext unavailable | Unit test: `test_missing_context_fallback()` |
| **NF4** | Thread-safe across concurrent requests | Integration test: `test_concurrent_operations()` |
| **NF5** | 90%+ test coverage for all new modules | Coverage report verification |
| **NF6** | Works with async resolvers and DataLoader | Integration test: `test_dataloader_compatibility()` |
| **NF7** | No modification to user's Strawberry schema behavior | Integration test: `test_schema_behavior_unchanged()` |

### User Experience Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| **UX1** | Display operation count, total time, resolver count in panel header | Manual UI verification |
| **UX2** | Show collapsible resolver tree with indentation | Manual UI verification |
| **UX3** | Highlight slow operations/resolvers visually (color, icon) | Manual UI verification |
| **UX4** | Show N+1 warnings with fix suggestions | Manual UI verification |
| **UX5** | Display query variables formatted (JSON) | Manual UI verification |
| **UX6** | Truncate large queries/results (configurable limit) | Unit test: `test_query_truncation()` |

---

## Technical Approach

### Architecture Overview

The GraphQL panel follows the **Two-Tracker Pattern** (adapted from SQLAlchemyPanel):

1. **DebugToolbarExtension** (`SchemaExtension`):
   - Integrates with Strawberry schema via `extensions=[DebugToolbarExtension()]`
   - Hooks into `on_operation()` for operation-level tracking
   - Hooks into `resolve()` for resolver-level tracking
   - Stores data in `RequestContext` via contextvars (thread-safe)

2. **OperationTracker**:
   - Tracks GraphQL operations (query/mutation/subscription)
   - Captures: query string, variables, operation name/type, timing, errors
   - Lifecycle: Start in `on_operation()` (before yield), complete after yield

3. **ResolverTracker**:
   - Tracks individual resolver executions
   - Captures: field path, resolver name, arguments, timing, return type
   - Lifecycle: Start in `resolve()` (before `_next`), complete after `_next` returns

4. **GraphQLPanel** (`Panel`):
   - Retrieves tracked data from `RequestContext`
   - Generates stats with pattern analysis (N+1, duplicates, slow queries)
   - Renders UI with resolver tree and metrics

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ GraphQL Request                                                 │
│ POST /graphql                                                   │
│ { "query": "query GetUser { user(id: 1) { posts { title } } }" }│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Strawberry Schema (with DebugToolbarExtension)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DebugToolbarExtension.on_operation() [BEFORE YIELD]            │
│ - Get/create RequestContext from contextvar                    │
│ - Create TrackedOperation with start_time                      │
│ - Store in context.panel_data["GraphQLPanel"]["current_op"]    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Query Execution (multiple resolvers)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│ Resolver: Query.user      │   │ Resolver: User.posts      │
└───────────────────────────┘   └───────────────────────────┘
                │                           │
                ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ DebugToolbarExtension.resolve() [EACH RESOLVER]                │
│ - Create TrackedResolver with start_time                       │
│ - Call _next(root, info, *args, **kwargs)                      │
│ - Calculate duration, capture metadata                         │
│ - Append to current_op.resolvers                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DebugToolbarExtension.on_operation() [AFTER YIELD]             │
│ - Calculate total operation duration                           │
│ - Capture errors from execution_context.result                 │
│ - Finalize TrackedOperation                                    │
│ - Store in context.panel_data["GraphQLPanel"]["operations"][]  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ GraphQLPanel.generate_stats(context)                           │
│ - Retrieve operations from context.panel_data                  │
│ - Run N+1Analyzer to detect duplicate resolver patterns        │
│ - Calculate aggregate stats (count, total_time, etc.)          │
│ - Return stats dict for template rendering                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Panel UI Rendered                                               │
│ - Operation list with timing                                   │
│ - Resolver tree with hierarchy                                 │
│ - N+1 warnings and suggestions                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### 1. DebugToolbarExtension (SchemaExtension)

**File**: `src/debug_toolbar/extras/strawberry/extension.py`

```python
"""Strawberry SchemaExtension for debug toolbar integration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from strawberry.extensions import SchemaExtension

from debug_toolbar.core.context import get_request_context

if TYPE_CHECKING:
    import strawberry
    from strawberry.types import ExecutionContext

    from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver


class DebugToolbarExtension(SchemaExtension):
    """Strawberry extension for tracking GraphQL operations and resolvers.

    Integrates with debug toolbar's RequestContext to store operation and
    resolver timing data for display in the GraphQL panel.

    Usage:
        schema = strawberry.Schema(
            query=Query,
            extensions=[DebugToolbarExtension()],
        )
    """

    __slots__ = ("_slow_operation_threshold_ms", "_slow_resolver_threshold_ms", "_capture_stacks")

    def __init__(
        self,
        *,
        slow_operation_threshold_ms: float = 100.0,
        slow_resolver_threshold_ms: float = 10.0,
        capture_stacks: bool = True,
    ) -> None:
        """Initialize the extension.

        Args:
            slow_operation_threshold_ms: Threshold for marking operations as slow.
            slow_resolver_threshold_ms: Threshold for marking resolvers as slow.
            capture_stacks: Whether to capture stack traces for resolvers.
        """
        self._slow_operation_threshold_ms = slow_operation_threshold_ms
        self._slow_resolver_threshold_ms = slow_resolver_threshold_ms
        self._capture_stacks = capture_stacks

    def on_operation(self) -> Generator[None, None, None]:
        """Track GraphQL operation (query/mutation/subscription).

        Runs before and after the entire GraphQL operation executes.
        """
        context = get_request_context()
        if context is None:
            yield
            return

        # Before operation: Create TrackedOperation
        exec_ctx: ExecutionContext = self.execution_context
        operation = TrackedOperation(
            operation_id=str(uuid4()),
            query=exec_ctx.query or "",
            variables=exec_ctx.variables or {},
            operation_name=exec_ctx.operation_name,
            operation_type=self._get_operation_type(exec_ctx),
            start_time=time.perf_counter(),
        )

        # Store as current operation
        context.store_panel_data("GraphQLPanel", "current_operation", operation)

        yield  # Execute operation

        # After operation: Finalize timing and errors
        operation.end_time = time.perf_counter()
        operation.duration_ms = (operation.end_time - operation.start_time) * 1000

        # Capture errors if present
        if hasattr(exec_ctx.result, "errors") and exec_ctx.result.errors:
            operation.errors = [
                {
                    "message": str(err.message),
                    "path": list(err.path) if err.path else None,
                    "locations": [
                        {"line": loc.line, "column": loc.column}
                        for loc in (err.locations or [])
                    ],
                }
                for err in exec_ctx.result.errors
            ]

        # Store completed operation
        operations = context.get_panel_data("GraphQLPanel").get("operations", [])
        operations.append(operation)
        context.store_panel_data("GraphQLPanel", "operations", operations)
        context.store_panel_data("GraphQLPanel", "current_operation", None)

    async def resolve(
        self,
        _next: Any,
        root: Any,
        info: strawberry.Info,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Track individual resolver execution.

        Called for every field resolver. Measures timing and captures metadata.

        Args:
            _next: Next resolver in chain.
            root: Parent object.
            info: Strawberry Info object with field metadata.
            *args: Positional arguments to resolver.
            **kwargs: Keyword arguments to resolver.

        Returns:
            Resolver result.
        """
        context = get_request_context()
        if context is None:
            return await _next(root, info, *args, **kwargs)

        # Create TrackedResolver
        start_time = time.perf_counter()
        resolver = TrackedResolver(
            resolver_id=str(uuid4()),
            field_name=info.field_name,
            field_path=self._build_field_path(info),
            resolver_function=self._get_resolver_name(info),
            parent_type=info.parent_type.name if info.parent_type else "Unknown",
            return_type=str(info.return_type),
            arguments={**kwargs},
        )

        # Capture stack trace if enabled
        if self._capture_stacks:
            from debug_toolbar.extras.strawberry.utils import capture_stack
            resolver.stack_trace = capture_stack()

        # Execute resolver
        try:
            result = await _next(root, info, *args, **kwargs)
        except Exception:
            resolver.end_time = time.perf_counter()
            resolver.duration_ms = (resolver.end_time - start_time) * 1000
            resolver.is_slow = resolver.duration_ms >= self._slow_resolver_threshold_ms

            # Store resolver even on exception
            current_op = context.get_panel_data("GraphQLPanel").get("current_operation")
            if current_op:
                current_op.resolvers.append(resolver)

            raise  # Re-raise exception

        # Finalize resolver timing
        resolver.end_time = time.perf_counter()
        resolver.duration_ms = (resolver.end_time - start_time) * 1000
        resolver.is_slow = resolver.duration_ms >= self._slow_resolver_threshold_ms

        # Attach to current operation
        current_op = context.get_panel_data("GraphQLPanel").get("current_operation")
        if current_op:
            current_op.resolvers.append(resolver)

        return result

    def _get_operation_type(self, exec_ctx: ExecutionContext) -> str:
        """Determine operation type from execution context."""
        if exec_ctx.operation_name:
            # Parse operation type from query
            query_upper = exec_ctx.query.upper() if exec_ctx.query else ""
            if "MUTATION" in query_upper:
                return "mutation"
            if "SUBSCRIPTION" in query_upper:
                return "subscription"
        return "query"

    def _build_field_path(self, info: strawberry.Info) -> str:
        """Build field path from Info.path (e.g., 'Query.user.posts.0.title')."""
        path_parts = []
        current = info.path
        while current:
            path_parts.append(str(current.key))
            current = current.prev
        return ".".join(reversed(path_parts))

    def _get_resolver_name(self, info: strawberry.Info) -> str:
        """Get resolver function name or 'field' for default resolvers."""
        # TODO: Extract actual resolver function name from Strawberry internals
        # For now, use field name
        return f"{info.parent_type.name}.{info.python_name}" if info.parent_type else info.python_name
```

#### 2. Data Models

**File**: `src/debug_toolbar/extras/strawberry/models.py`

```python
"""Data models for GraphQL tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TrackedResolver:
    """Represents a tracked GraphQL resolver execution.

    Attributes:
        resolver_id: Unique identifier for this resolver execution.
        field_name: GraphQL field name (camelCase).
        field_path: Dot-separated path (e.g., 'Query.user.posts.0.title').
        resolver_function: Function name or field reference.
        parent_type: Parent GraphQL type (e.g., 'Query', 'User').
        return_type: Expected return type.
        arguments: Resolver arguments (kwargs).
        start_time: Start timestamp (perf_counter).
        end_time: End timestamp (perf_counter).
        duration_ms: Execution duration in milliseconds.
        stack_trace: Call stack trace (if captured).
        is_slow: Whether duration exceeds threshold.
    """

    resolver_id: str
    field_name: str
    field_path: str
    resolver_function: str
    parent_type: str
    return_type: str
    arguments: dict[str, Any]
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    stack_trace: list[dict[str, str]] | None = None
    is_slow: bool = False


@dataclass
class TrackedOperation:
    """Represents a tracked GraphQL operation.

    Attributes:
        operation_id: Unique identifier for this operation.
        query: GraphQL query string.
        variables: Operation variables.
        operation_name: Named operation (if provided).
        operation_type: Type of operation (query, mutation, subscription).
        start_time: Start timestamp (perf_counter).
        end_time: End timestamp (perf_counter).
        duration_ms: Total operation duration in milliseconds.
        resolvers: List of tracked resolvers executed.
        errors: GraphQL errors (if any).
        result_data: Preview of result data (truncated).
    """

    operation_id: str
    query: str
    variables: dict[str, Any]
    operation_name: str | None
    operation_type: Literal["query", "mutation", "subscription"]
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    resolvers: list[TrackedResolver] = field(default_factory=list)
    errors: list[dict[str, Any]] | None = None
    result_data: Any | None = None
```

#### 3. N+1 Analyzer

**File**: `src/debug_toolbar/extras/strawberry/analyzers.py`

```python
"""Analyzers for detecting GraphQL performance patterns."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver


class N1Analyzer:
    """Detects N+1 resolver patterns.

    Identifies cases where the same resolver is called multiple times
    unnecessarily, suggesting the need for DataLoader or batch loading.
    """

    def __init__(self, threshold: int = 3) -> None:
        """Initialize analyzer.

        Args:
            threshold: Minimum resolver count to flag as N+1.
        """
        self.threshold = threshold

    def analyze(self, operations: list[TrackedOperation]) -> list[dict[str, Any]]:
        """Analyze operations for N+1 patterns.

        Args:
            operations: List of tracked operations.

        Returns:
            List of detected N+1 patterns with metadata.
        """
        patterns: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "resolver_signature": "",
                "field_name": "",
                "parent_type": "",
                "count": 0,
                "total_duration_ms": 0.0,
                "resolver_ids": [],
                "suggestion": "",
            }
        )

        for operation in operations:
            for resolver in operation.resolvers:
                # Create signature: parent_type.field_name(arg_types)
                arg_sig = self._get_argument_signature(resolver.arguments)
                signature = f"{resolver.parent_type}.{resolver.field_name}({arg_sig})"

                pattern = patterns[signature]
                pattern["resolver_signature"] = signature
                pattern["field_name"] = resolver.field_name
                pattern["parent_type"] = resolver.parent_type
                pattern["count"] += 1
                pattern["total_duration_ms"] += resolver.duration_ms
                pattern["resolver_ids"].append(resolver.resolver_id)

        # Filter patterns that exceed threshold
        n_plus_one_patterns = [
            {
                **pattern,
                "suggestion": self._generate_suggestion(pattern),
            }
            for pattern in patterns.values()
            if pattern["count"] >= self.threshold
        ]

        # Sort by count (descending)
        n_plus_one_patterns.sort(key=lambda p: p["count"], reverse=True)

        return n_plus_one_patterns

    def _get_argument_signature(self, arguments: dict[str, Any]) -> str:
        """Create argument type signature."""
        if not arguments:
            return ""
        arg_types = [type(v).__name__ for v in arguments.values()]
        return ", ".join(arg_types)

    def _generate_suggestion(self, pattern: dict[str, Any]) -> str:
        """Generate fix suggestion for N+1 pattern."""
        count = pattern["count"]
        field = pattern["field_name"]
        return (
            f"Resolver '{field}' called {count} times. "
            f"Consider using DataLoader to batch these requests into a single operation."
        )


class DuplicateDetector:
    """Detects duplicate GraphQL operations."""

    def detect(self, operations: list[TrackedOperation]) -> list[str]:
        """Find duplicate operations (same query + variables).

        Args:
            operations: List of tracked operations.

        Returns:
            List of duplicate operation IDs.
        """
        seen: dict[str, list[str]] = defaultdict(list)

        for operation in operations:
            # Create hash from query + variables
            key = self._create_key(operation.query, operation.variables)
            seen[key].append(operation.operation_id)

        # Return IDs of operations that appear more than once
        duplicates = []
        for op_ids in seen.values():
            if len(op_ids) > 1:
                duplicates.extend(op_ids)

        return duplicates

    def _create_key(self, query: str, variables: dict[str, Any]) -> str:
        """Create hash key for operation."""
        import hashlib
        import json

        # Normalize query (strip whitespace)
        normalized_query = " ".join(query.split())

        # Create stable variable representation
        var_json = json.dumps(variables, sort_keys=True)

        combined = f"{normalized_query}:{var_json}"
        return hashlib.md5(combined.encode(), usedforsecurity=False).hexdigest()[:12]
```

#### 4. GraphQLPanel

**File**: `src/debug_toolbar/extras/strawberry/panel.py`

```python
"""GraphQL panel for tracking Strawberry GraphQL operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel
from debug_toolbar.extras.strawberry.analyzers import DuplicateDetector, N1Analyzer

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar


class GraphQLPanel(Panel):
    """Panel displaying GraphQL operation and resolver information.

    Shows:
    - GraphQL operations (queries, mutations, subscriptions)
    - Resolver execution timing and hierarchy
    - N+1 resolver pattern detection
    - Duplicate operation detection
    - Slow operation/resolver highlighting
    - Error tracking with field paths

    Requires:
    - strawberry-graphql >= 0.240.0
    - DebugToolbarExtension added to Strawberry schema
    """

    panel_id: ClassVar[str] = "GraphQLPanel"
    title: ClassVar[str] = "GraphQL"
    template: ClassVar[str] = "panels/graphql.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "GraphQL"

    __slots__ = ("_slow_operation_threshold_ms", "_slow_resolver_threshold_ms", "_n1_threshold")

    def __init__(
        self,
        toolbar: DebugToolbar,
        slow_operation_threshold_ms: float = 100.0,
        slow_resolver_threshold_ms: float = 10.0,
        n1_threshold: int = 3,
    ) -> None:
        """Initialize the panel.

        Args:
            toolbar: Parent DebugToolbar instance.
            slow_operation_threshold_ms: Threshold for slow operations.
            slow_resolver_threshold_ms: Threshold for slow resolvers.
            n1_threshold: Minimum resolver count for N+1 detection.
        """
        super().__init__(toolbar)
        self._slow_operation_threshold_ms = slow_operation_threshold_ms
        self._slow_resolver_threshold_ms = slow_resolver_threshold_ms
        self._n1_threshold = n1_threshold

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate GraphQL statistics.

        Args:
            context: Request context containing tracked operations.

        Returns:
            Statistics dictionary for template rendering.
        """
        panel_data = context.get_panel_data(self.get_panel_id())
        operations = panel_data.get("operations", [])

        if not operations:
            return {
                "operations": [],
                "operation_count": 0,
                "total_time_ms": 0.0,
                "resolver_count": 0,
                "n_plus_one_patterns": [],
                "duplicate_operations": [],
                "slow_operations": [],
                "has_issues": False,
            }

        # Calculate aggregate metrics
        total_time_ms = sum(op.duration_ms for op in operations)
        resolver_count = sum(len(op.resolvers) for op in operations)

        # Detect patterns
        n1_analyzer = N1Analyzer(threshold=self._n1_threshold)
        n_plus_one_patterns = n1_analyzer.analyze(operations)

        duplicate_detector = DuplicateDetector()
        duplicate_op_ids = duplicate_detector.detect(operations)

        # Find slow operations
        slow_operations = [
            op for op in operations if op.duration_ms >= self._slow_operation_threshold_ms
        ]

        # Mark slow resolvers
        for operation in operations:
            for resolver in operation.resolvers:
                resolver.is_slow = resolver.duration_ms >= self._slow_resolver_threshold_ms

        # Build resolver tree for each operation
        for operation in operations:
            operation.resolver_tree = self._build_resolver_tree(operation.resolvers)

        return {
            "operations": operations,
            "operation_count": len(operations),
            "total_time_ms": total_time_ms,
            "resolver_count": resolver_count,
            "n_plus_one_patterns": n_plus_one_patterns,
            "n_plus_one_count": len(n_plus_one_patterns),
            "duplicate_operations": duplicate_op_ids,
            "duplicate_count": len(duplicate_op_ids),
            "slow_operations": slow_operations,
            "slow_operation_count": len(slow_operations),
            "slow_operation_threshold_ms": self._slow_operation_threshold_ms,
            "slow_resolver_threshold_ms": self._slow_resolver_threshold_ms,
            "has_issues": bool(
                n_plus_one_patterns or duplicate_op_ids or slow_operations
            ),
        }

    def _build_resolver_tree(self, resolvers: list) -> list[dict[str, Any]]:
        """Build hierarchical resolver tree from flat list.

        Args:
            resolvers: Flat list of TrackedResolver objects.

        Returns:
            Nested tree structure for template rendering.
        """
        # Group resolvers by path depth
        tree_map: dict[str, dict[str, Any]] = {}

        for resolver in resolvers:
            path = resolver.field_path
            tree_map[path] = {
                "resolver": resolver,
                "children": [],
            }

        # Build parent-child relationships
        root_nodes = []
        for path, node in tree_map.items():
            # Find parent path
            path_parts = path.split(".")
            if len(path_parts) == 1:
                root_nodes.append(node)
            else:
                parent_path = ".".join(path_parts[:-1])
                if parent_path in tree_map:
                    tree_map[parent_path]["children"].append(node)
                else:
                    # No parent found, treat as root
                    root_nodes.append(node)

        return root_nodes

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing header data.

        Args:
            context: Request context.

        Returns:
            Dictionary mapping metric names to durations in seconds.
        """
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {"graphql": stats.get("total_time_ms", 0.0) / 1000.0}

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle."""
        return ""
```

#### 5. Utility Functions

**File**: `src/debug_toolbar/extras/strawberry/utils.py`

```python
"""Utility functions for GraphQL tracking."""

from __future__ import annotations

import traceback
from typing import Any


def capture_stack(skip_frames: int = 4) -> list[dict[str, str]]:
    """Capture current call stack, filtering library frames.

    Args:
        skip_frames: Number of frames to skip from top.

    Returns:
        List of frame dicts with file, line, function, code.
    """
    IGNORED_FRAMES = {
        "strawberry",
        "debug_toolbar",
        "asyncio",
        "concurrent",
        "graphql",
        "site-packages",
    }

    frames = []
    for frame_info in traceback.extract_stack()[:-skip_frames]:
        if any(ignored in frame_info.filename for ignored in IGNORED_FRAMES):
            continue

        frames.append(
            {
                "file": frame_info.filename,
                "line": frame_info.lineno,
                "function": frame_info.name,
                "code": frame_info.line or "",
            }
        )

    MAX_FRAMES = 5
    return frames[-MAX_FRAMES:] if len(frames) > MAX_FRAMES else frames


def truncate_query(query: str, max_length: int = 1000) -> str:
    """Truncate long query strings.

    Args:
        query: GraphQL query string.
        max_length: Maximum length before truncation.

    Returns:
        Truncated query with ellipsis if needed.
    """
    if len(query) <= max_length:
        return query
    return query[:max_length] + "..."


def format_variables(variables: dict[str, Any], max_depth: int = 3) -> dict[str, Any]:
    """Format variables for display, truncating deep nesting.

    Args:
        variables: Query variables.
        max_depth: Maximum nesting depth.

    Returns:
        Formatted variables dict.
    """
    if max_depth <= 0:
        return {"...": "max depth reached"}

    formatted = {}
    for key, value in variables.items():
        if isinstance(value, dict):
            formatted[key] = format_variables(value, max_depth - 1)
        elif isinstance(value, list):
            formatted[key] = [
                format_variables(item, max_depth - 1) if isinstance(item, dict) else item
                for item in value[:10]  # Limit array display
            ]
            if len(value) > 10:
                formatted[key].append("...")
        else:
            formatted[key] = value

    return formatted
```

### Testing Strategy

#### Unit Tests (90%+ Coverage Target)

**File**: `tests/unit/test_graphql_extension.py`

```python
"""Tests for DebugToolbarExtension."""

from __future__ import annotations

import pytest

from debug_toolbar.core.context import RequestContext, set_request_context
from debug_toolbar.extras.strawberry.extension import DebugToolbarExtension


class TestDebugToolbarExtension:
    """Tests for DebugToolbarExtension class."""

    def test_extension_initialization(self) -> None:
        """Should initialize with default thresholds."""
        ext = DebugToolbarExtension()
        assert ext._slow_operation_threshold_ms == 100.0
        assert ext._slow_resolver_threshold_ms == 10.0
        assert ext._capture_stacks is True

    def test_extension_custom_thresholds(self) -> None:
        """Should accept custom threshold values."""
        ext = DebugToolbarExtension(
            slow_operation_threshold_ms=200.0,
            slow_resolver_threshold_ms=20.0,
            capture_stacks=False,
        )
        assert ext._slow_operation_threshold_ms == 200.0
        assert ext._slow_resolver_threshold_ms == 20.0
        assert ext._capture_stacks is False

    @pytest.mark.asyncio
    async def test_on_operation_no_context(self) -> None:
        """Should handle missing RequestContext gracefully."""
        set_request_context(None)
        ext = DebugToolbarExtension()

        # Should not raise
        gen = ext.on_operation()
        next(gen)

        set_request_context(None)  # Cleanup

    # Additional tests for on_operation, resolve, helpers...
```

**File**: `tests/unit/test_graphql_panel.py`

```python
"""Tests for GraphQLPanel."""

from __future__ import annotations

import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig, RequestContext
from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver
from debug_toolbar.extras.strawberry.panel import GraphQLPanel


class TestGraphQLPanel:
    """Tests for GraphQLPanel class."""

    @pytest.fixture
    def panel(self, toolbar: DebugToolbar) -> GraphQLPanel:
        """Create GraphQLPanel instance."""
        return GraphQLPanel(toolbar)

    def test_panel_id(self, panel: GraphQLPanel) -> None:
        """Should have correct panel ID."""
        assert panel.get_panel_id() == "GraphQLPanel"

    def test_panel_title(self, panel: GraphQLPanel) -> None:
        """Should have correct title."""
        assert panel.title == "GraphQL"

    @pytest.mark.asyncio
    async def test_generate_stats_no_operations(
        self, panel: GraphQLPanel, context: RequestContext
    ) -> None:
        """Should return empty stats when no operations tracked."""
        stats = await panel.generate_stats(context)

        assert stats["operation_count"] == 0
        assert stats["total_time_ms"] == 0.0
        assert stats["resolver_count"] == 0
        assert stats["has_issues"] is False

    @pytest.mark.asyncio
    async def test_generate_stats_with_operations(
        self, panel: GraphQLPanel, context: RequestContext
    ) -> None:
        """Should calculate stats from tracked operations."""
        # Create mock operation
        operation = TrackedOperation(
            operation_id="test-1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name="GetUser",
            operation_type="query",
            start_time=0.0,
            end_time=0.15,
            duration_ms=150.0,
            resolvers=[
                TrackedResolver(
                    resolver_id="r1",
                    field_name="user",
                    field_path="Query.user",
                    resolver_function="Query.user",
                    parent_type="Query",
                    return_type="User",
                    arguments={"id": 1},
                    duration_ms=150.0,
                )
            ],
        )

        # Store in context
        context.store_panel_data("GraphQLPanel", "operations", [operation])

        stats = await panel.generate_stats(context)

        assert stats["operation_count"] == 1
        assert stats["total_time_ms"] == 150.0
        assert stats["resolver_count"] == 1
        assert stats["slow_operation_count"] == 1  # > 100ms threshold

    # Additional tests for N+1 detection, tree building, etc...
```

**File**: `tests/unit/test_graphql_analyzers.py`

```python
"""Tests for GraphQL analyzers."""

from __future__ import annotations

import pytest

from debug_toolbar.extras.strawberry.analyzers import DuplicateDetector, N1Analyzer
from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver


class TestN1Analyzer:
    """Tests for N1Analyzer."""

    def test_detects_n_plus_one_pattern(self) -> None:
        """Should detect N+1 pattern when resolver called 3+ times."""
        # Create operation with repeated resolver calls
        operation = TrackedOperation(
            operation_id="test-1",
            query="query { users { posts } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=[
                TrackedResolver(
                    resolver_id=f"r{i}",
                    field_name="posts",
                    field_path=f"Query.users.{i}.posts",
                    resolver_function="User.posts",
                    parent_type="User",
                    return_type="[Post]",
                    arguments={},
                    duration_ms=10.0,
                )
                for i in range(5)  # Same resolver called 5 times
            ],
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 1
        assert patterns[0]["count"] == 5
        assert patterns[0]["field_name"] == "posts"
        assert "DataLoader" in patterns[0]["suggestion"]

    def test_ignores_below_threshold(self) -> None:
        """Should not flag resolvers called below threshold."""
        operation = TrackedOperation(
            operation_id="test-1",
            query="query { users { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
            resolvers=[
                TrackedResolver(
                    resolver_id=f"r{i}",
                    field_name="name",
                    field_path=f"Query.users.{i}.name",
                    resolver_function="User.name",
                    parent_type="User",
                    return_type="String",
                    arguments={},
                    duration_ms=1.0,
                )
                for i in range(2)  # Only 2 calls
            ],
        )

        analyzer = N1Analyzer(threshold=3)
        patterns = analyzer.analyze([operation])

        assert len(patterns) == 0


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""

    def test_detects_duplicate_operations(self) -> None:
        """Should detect operations with same query and variables."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 2
        assert "op1" in duplicates
        assert "op2" in duplicates

    def test_no_duplicates_for_different_queries(self) -> None:
        """Should not flag different queries as duplicates."""
        op1 = TrackedOperation(
            operation_id="op1",
            query="query { user(id: 1) { name } }",
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.0,
        )
        op2 = TrackedOperation(
            operation_id="op2",
            query="query { user(id: 2) { name } }",  # Different ID
            variables={},
            operation_name=None,
            operation_type="query",
            start_time=0.1,
        )

        detector = DuplicateDetector()
        duplicates = detector.detect([op1, op2])

        assert len(duplicates) == 0
```

#### Integration Tests

**File**: `tests/integration/test_graphql_strawberry_integration.py`

```python
"""Integration tests with real Strawberry schema."""

from __future__ import annotations

import strawberry
import pytest

from debug_toolbar import DebugToolbar, DebugToolbarConfig, RequestContext
from debug_toolbar.core.context import set_request_context
from debug_toolbar.extras.strawberry.extension import DebugToolbarExtension
from debug_toolbar.extras.strawberry.panel import GraphQLPanel


@strawberry.type
class User:
    """Test User type."""

    id: int
    name: str


@strawberry.type
class Query:
    """Test Query type."""

    @strawberry.field
    def user(self, id: int) -> User:
        """Get user by ID."""
        return User(id=id, name=f"User{id}")

    @strawberry.field
    def users(self) -> list[User]:
        """Get all users."""
        return [User(id=i, name=f"User{i}") for i in range(3)]


@pytest.mark.asyncio
async def test_tracks_simple_query() -> None:
    """Should track simple GraphQL query."""
    # Setup
    schema = strawberry.Schema(query=Query, extensions=[DebugToolbarExtension()])
    context = RequestContext()
    set_request_context(context)

    # Execute query
    query = "query { user(id: 1) { name } }"
    result = await schema.execute(query)

    assert result.errors is None
    assert result.data == {"user": {"name": "User1"}}

    # Verify tracking
    panel_data = context.get_panel_data("GraphQLPanel")
    operations = panel_data.get("operations", [])

    assert len(operations) == 1
    assert operations[0].query == query
    assert operations[0].operation_type == "query"
    assert len(operations[0].resolvers) >= 1  # At least Query.user resolver

    # Cleanup
    set_request_context(None)


@pytest.mark.asyncio
async def test_detects_n_plus_one() -> None:
    """Should detect N+1 pattern in nested resolvers."""
    # Setup schema with N+1 issue
    @strawberry.type
    class Post:
        title: str
        author_id: int

        @strawberry.field
        def author(self) -> User:
            # N+1: This resolver called for each post
            return User(id=self.author_id, name=f"Author{self.author_id}")

    @strawberry.type
    class QueryWithN1:
        @strawberry.field
        def posts(self) -> list[Post]:
            return [Post(title=f"Post{i}", author_id=i) for i in range(5)]

    schema = strawberry.Schema(
        query=QueryWithN1, extensions=[DebugToolbarExtension()]
    )
    context = RequestContext()
    set_request_context(context)

    # Execute query that triggers N+1
    query = "query { posts { title author { name } } }"
    result = await schema.execute(query)

    assert result.errors is None

    # Analyze with panel
    config = DebugToolbarConfig()
    toolbar = DebugToolbar(config)
    panel = GraphQLPanel(toolbar, n1_threshold=3)

    stats = await panel.generate_stats(context)

    # Should detect Post.author called 5 times
    assert stats["n_plus_one_count"] >= 1
    assert stats["has_issues"] is True

    # Cleanup
    set_request_context(None)
```

### Files to Create/Modify

#### New Files

```
src/debug_toolbar/extras/strawberry/
├── __init__.py                    # Public API exports
├── panel.py                       # GraphQLPanel class (150 lines)
├── extension.py                   # DebugToolbarExtension (200 lines)
├── models.py                      # TrackedOperation, TrackedResolver (80 lines)
├── analyzers.py                   # N1Analyzer, DuplicateDetector (120 lines)
└── utils.py                       # Stack capture, formatting (60 lines)

tests/unit/
├── test_graphql_extension.py     # Extension tests (200 lines)
├── test_graphql_panel.py          # Panel tests (250 lines)
├── test_graphql_analyzers.py     # Analyzer tests (150 lines)
├── test_graphql_models.py         # Model tests (80 lines)
└── test_graphql_utils.py          # Utility tests (60 lines)

tests/integration/
└── test_graphql_strawberry_integration.py  # Full integration (200 lines)

docs/
└── panels/graphql.md              # Usage documentation (100 lines)
```

**Total New Code**: ~1,650 lines

#### Modified Files

None (extra panel, no core changes required)

### Dependencies

**New Optional Dependency**:
```toml
[project.optional-dependencies]
strawberry = ["strawberry-graphql>=0.240.0"]
```

**Installation**:
```bash
pip install debug-toolbar[strawberry]
```

### Configuration Example

**User Integration**:

```python
"""Example Strawberry + debug-toolbar integration."""

from __future__ import annotations

import strawberry
from litestar import Litestar
from strawberry.litestar import make_graphql_controller

from debug_toolbar import DebugToolbarConfig
from debug_toolbar.extras.strawberry import DebugToolbarExtension, GraphQLPanel
from debug_toolbar.litestar import DebugToolbarPlugin


@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str = "World") -> str:
        return f"Hello, {name}!"


# Create schema with debug extension
schema = strawberry.Schema(
    query=Query,
    extensions=[
        DebugToolbarExtension(
            slow_operation_threshold_ms=100.0,
            slow_resolver_threshold_ms=10.0,
        ),
    ],
)

# Create GraphQL controller
graphql_controller = make_graphql_controller(schema, path="/graphql")

# Configure debug toolbar with GraphQL panel
debug_config = DebugToolbarConfig(
    extra_panels=[GraphQLPanel],
)

app = Litestar(
    route_handlers=[graphql_controller],
    plugins=[DebugToolbarPlugin(debug_config)],
)
```

### UI Mockup (Detailed)

```html
<!-- GraphQL Panel Template -->

<div class="graphql-panel">
  <div class="panel-header">
    <h3>GraphQL Operations</h3>
    <div class="summary">
      <span class="metric">
        <strong>{{ operation_count }}</strong> operations
      </span>
      <span class="metric">
        <strong>{{ total_time_ms|round(2) }}ms</strong> total
      </span>
      <span class="metric">
        <strong>{{ resolver_count }}</strong> resolvers
      </span>
    </div>
  </div>

  {% if has_issues %}
  <div class="issues-alert">
    <h4>⚠️ Performance Issues Detected</h4>
    <ul>
      {% if n_plus_one_count > 0 %}
      <li>{{ n_plus_one_count }} N+1 resolver patterns</li>
      {% endif %}
      {% if slow_operation_count > 0 %}
      <li>{{ slow_operation_count }} slow operations (> {{ slow_operation_threshold_ms }}ms)</li>
      {% endif %}
      {% if duplicate_count > 0 %}
      <li>{{ duplicate_count }} duplicate operations</li>
      {% endif %}
    </ul>
  </div>
  {% endif %}

  {% for operation in operations %}
  <div class="operation {% if operation.duration_ms >= slow_operation_threshold_ms %}slow{% endif %}">
    <div class="operation-header" onclick="toggleOperation('{{ operation.operation_id }}')">
      <span class="operation-type {{ operation.operation_type }}">
        {{ operation.operation_type|upper }}
      </span>
      {% if operation.operation_name %}
      <span class="operation-name">{{ operation.operation_name }}</span>
      {% endif %}
      <span class="operation-timing">
        {{ operation.duration_ms|round(2) }}ms
      </span>
      {% if operation.duration_ms >= slow_operation_threshold_ms %}
      <span class="badge slow">SLOW</span>
      {% endif %}
      {% if operation.operation_id in duplicate_operations %}
      <span class="badge duplicate">DUPLICATE</span>
      {% endif %}
    </div>

    <div id="operation-{{ operation.operation_id }}" class="operation-details" style="display: none;">
      <!-- Query -->
      <div class="section">
        <h5>Query</h5>
        <pre><code class="graphql">{{ operation.query }}</code></pre>
      </div>

      <!-- Variables -->
      {% if operation.variables %}
      <div class="section">
        <h5>Variables</h5>
        <pre><code class="json">{{ operation.variables|tojson(indent=2) }}</code></pre>
      </div>
      {% endif %}

      <!-- Errors -->
      {% if operation.errors %}
      <div class="section errors">
        <h5>Errors ({{ operation.errors|length }})</h5>
        {% for error in operation.errors %}
        <div class="error">
          <strong>{{ error.message }}</strong>
          {% if error.path %}
          <div class="error-path">Path: {{ error.path|join('.') }}</div>
          {% endif %}
          {% if error.locations %}
          <div class="error-location">
            Line {{ error.locations[0].line }}, Column {{ error.locations[0].column }}
          </div>
          {% endif %}
        </div>
        {% endfor %}
      </div>
      {% endif %}

      <!-- Resolver Tree -->
      <div class="section">
        <h5>Resolvers ({{ operation.resolvers|length }})</h5>
        <div class="resolver-tree">
          {% for node in operation.resolver_tree %}
            {{ render_resolver_node(node, 0) }}
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
  {% endfor %}

  <!-- N+1 Patterns Section -->
  {% if n_plus_one_patterns %}
  <div class="n-plus-one-section">
    <h4>🔍 N+1 Resolver Patterns Detected</h4>
    {% for pattern in n_plus_one_patterns %}
    <div class="pattern">
      <div class="pattern-header">
        <strong>{{ pattern.field_name }}</strong>
        <span class="badge">{{ pattern.count }}x</span>
        <span class="timing">{{ pattern.total_duration_ms|round(2) }}ms total</span>
      </div>
      <div class="pattern-details">
        <div>Resolver: <code>{{ pattern.resolver_signature }}</code></div>
        <div class="suggestion">💡 {{ pattern.suggestion }}</div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>

<!-- Macro for recursive resolver tree -->
{% macro render_resolver_node(node, depth) %}
<div class="resolver-node" style="margin-left: {{ depth * 20 }}px;">
  <span class="resolver-name">{{ node.resolver.field_name }}</span>
  <span class="resolver-timing {% if node.resolver.is_slow %}slow{% endif %}">
    {{ node.resolver.duration_ms|round(2) }}ms
  </span>
  {% if node.resolver.is_slow %}
  <span class="badge slow">SLOW</span>
  {% endif %}
  {% if node.resolver.arguments %}
  <span class="resolver-args">{{ node.resolver.arguments|tojson }}</span>
  {% endif %}

  {% if node.children %}
    {% for child in node.children %}
      {{ render_resolver_node(child, depth + 1) }}
    {% endfor %}
  {% endif %}
</div>
{% endmacro %}
```

---

## Implementation Checkpoints

### Checkpoint 1: Research & PRD ✓
- [x] Analyze competitor (FastAPI Debug Toolbar)
- [x] Research Strawberry SchemaExtension API
- [x] Examine similar panels (SQLAlchemyPanel, TimerPanel)
- [x] Document architecture and data flow
- [x] Create comprehensive PRD

### Checkpoint 2: Implement Tracker Classes
**Estimated Time**: 2 hours

- [ ] Create `models.py` with TrackedOperation and TrackedResolver dataclasses
- [ ] Add field validation and defaults
- [ ] Write unit tests for models (`test_graphql_models.py`)
- [ ] Verify serialization for context storage

**Success Criteria**:
- Models instantiate correctly with required fields
- Default values applied appropriately
- Test coverage > 90%

### Checkpoint 3: Implement SchemaExtension
**Estimated Time**: 3 hours

- [ ] Create `extension.py` with DebugToolbarExtension class
- [ ] Implement `on_operation()` lifecycle hook
- [ ] Implement `resolve()` for resolver tracking
- [ ] Integrate with RequestContext via contextvars
- [ ] Handle missing context gracefully
- [ ] Write unit tests (`test_graphql_extension.py`)

**Success Criteria**:
- Extension hooks into Strawberry lifecycle
- Operations tracked with timing
- Resolvers tracked with metadata
- No errors when context unavailable
- Test coverage > 90%

### Checkpoint 4: Implement GraphQLPanel
**Estimated Time**: 2 hours

- [ ] Create `panel.py` with GraphQLPanel class
- [ ] Implement `generate_stats()` method
- [ ] Add `generate_server_timing()` support
- [ ] Build resolver tree hierarchy
- [ ] Write unit tests (`test_graphql_panel.py`)

**Success Criteria**:
- Panel retrieves data from context
- Stats calculated correctly
- Resolver tree built properly
- Test coverage > 90%

### Checkpoint 5: Implement Analyzers
**Estimated Time**: 2 hours

- [ ] Create `analyzers.py` with N1Analyzer
- [ ] Implement N+1 pattern detection algorithm
- [ ] Create DuplicateDetector for duplicate operations
- [ ] Generate fix suggestions
- [ ] Write unit tests (`test_graphql_analyzers.py`)

**Success Criteria**:
- N+1 patterns detected accurately (threshold 3+)
- Duplicate operations identified
- Suggestions generated appropriately
- Test coverage > 90%

### Checkpoint 6: Write Unit Tests
**Estimated Time**: 2 hours

- [ ] Achieve 90%+ coverage on extension.py
- [ ] Achieve 90%+ coverage on panel.py
- [ ] Achieve 90%+ coverage on analyzers.py
- [ ] Achieve 90%+ coverage on models.py
- [ ] Achieve 90%+ coverage on utils.py
- [ ] Add edge case tests (exceptions, missing data)

**Success Criteria**:
- Overall coverage > 90%
- All edge cases covered
- All tests passing

### Checkpoint 7: Write Integration Tests
**Estimated Time**: 2 hours

- [ ] Create real Strawberry schema for testing
- [ ] Test simple query tracking
- [ ] Test nested resolver tracking
- [ ] Test N+1 pattern detection with real resolvers
- [ ] Test error handling with failing resolvers
- [ ] Test DataLoader compatibility
- [ ] Test concurrent operations (thread safety)

**Success Criteria**:
- End-to-end tracking works with real schema
- N+1 detection works in practice
- No thread safety issues
- All integration tests passing

### Checkpoint 8: Review & Pattern Extraction
**Estimated Time**: 1 hour

- [ ] Run full test suite (`make test`)
- [ ] Run linter (`make lint`)
- [ ] Run type checker (`make type-check`)
- [ ] Verify 90%+ coverage (`make test-cov`)
- [ ] Extract new patterns to `tmp/new-patterns.md`
- [ ] Update documentation
- [ ] Create usage examples

**Success Criteria**:
- All quality gates pass
- No linting errors
- No type errors
- Documentation complete
- Patterns documented

---

## Documentation Requirements

### User Documentation

**File**: `docs/panels/graphql.md`

```markdown
# GraphQL Panel

Track GraphQL operations, resolver timing, and detect N+1 patterns with Strawberry GraphQL.

## Installation

Install with Strawberry support:

```bash
pip install debug-toolbar[strawberry]
```

## Configuration

Add `DebugToolbarExtension` to your Strawberry schema:

```python
import strawberry
from debug_toolbar.extras.strawberry import DebugToolbarExtension

schema = strawberry.Schema(
    query=Query,
    extensions=[DebugToolbarExtension()],
)
```

Add `GraphQLPanel` to your toolbar configuration:

```python
from debug_toolbar import DebugToolbarConfig
from debug_toolbar.extras.strawberry import GraphQLPanel

config = DebugToolbarConfig(
    extra_panels=[GraphQLPanel],
)
```

## Features

- **Operation Tracking**: View all GraphQL queries, mutations, and subscriptions
- **Resolver Timing**: See hierarchical breakdown of resolver execution times
- **N+1 Detection**: Automatically detects N+1 resolver patterns
- **Error Tracking**: Display GraphQL errors with field paths
- **Slow Query Highlighting**: Configurable thresholds for slow operations/resolvers

## Configuration Options

### DebugToolbarExtension

- `slow_operation_threshold_ms` (float, default: 100.0): Threshold for slow operations
- `slow_resolver_threshold_ms` (float, default: 10.0): Threshold for slow resolvers
- `capture_stacks` (bool, default: True): Whether to capture stack traces

### GraphQLPanel

- `slow_operation_threshold_ms` (float, default: 100.0): Threshold for slow operations
- `slow_resolver_threshold_ms` (float, default: 10.0): Threshold for slow resolvers
- `n1_threshold` (int, default: 3): Minimum resolver count for N+1 detection

## Performance

When enabled, the extension adds ~5% overhead to GraphQL operations. This is acceptable
for development/staging environments but should not be used in production.

When the panel is disabled, there is zero performance impact.

## Troubleshooting

### No operations tracked

Ensure `DebugToolbarExtension` is added to your schema's `extensions` list.

### N+1 patterns not detected

Increase the `n1_threshold` if too many false positives, or decrease to catch
smaller patterns.

### Stack traces missing

Enable stack capture: `DebugToolbarExtension(capture_stacks=True)`
```

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Strawberry API changes | High | Low | Pin minimum version >= 0.240.0 |
| Performance overhead > 10% | High | Medium | Benchmark before release, add disable flag |
| Thread safety issues with contextvars | High | Low | Use RequestContext pattern (proven) |
| FIFO lifecycle hook ordering issue | Medium | Medium | Document known issue, use resolve() for critical timing |
| Exception handling breaks tracking | Medium | Low | Wrap all tracking in try/except |

### Implementation Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Complexity underestimated | Medium | Low | 8 checkpoints with buffer time |
| Test coverage < 90% | Medium | Low | Checkpoint 6 dedicated to coverage |
| Pattern detection false positives | Low | Medium | Tune threshold (default 3), allow configuration |

---

## Success Metrics

### Quantitative

- **Test Coverage**: > 90% on all new modules
- **Performance**: < 5% overhead when enabled, 0% when disabled
- **Code Quality**: Zero linting errors, zero type errors
- **Lines of Code**: ~1,650 lines (within Medium complexity range)

### Qualitative

- **Developer Experience**: Clear, actionable N+1 warnings with fix suggestions
- **UI Clarity**: Resolver tree visually matches GraphQL structure
- **Documentation**: Clear integration examples for Strawberry users
- **Pattern Compliance**: Follows established Panel ABC pattern

---

## Appendix

### Glossary

- **Operation**: A GraphQL query, mutation, or subscription
- **Resolver**: A function that resolves a GraphQL field value
- **N+1 Pattern**: Performance anti-pattern where a resolver is called N times unnecessarily
- **DataLoader**: Strawberry utility for batching and caching resolver calls
- **SchemaExtension**: Strawberry's extension point for instrumentation

### References

- **FastAPI Debug Toolbar**: https://fastapi-debug-toolbar.domake.io/
- **Strawberry GraphQL**: https://strawberry.rocks/
- **SchemaExtension Guide**: https://strawberry.rocks/docs/guides/custom-extensions
- **SchemaExtension API**: https://strawberry.rocks/api-reference/strawberry.extensions.SchemaExtension
- **GitHub Issue #3413**: https://github.com/strawberry-graphql/strawberry/issues/3413
- **GitHub Issue #3414**: https://github.com/strawberry-graphql/strawberry/issues/3414

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial PRD created |

---

**Total PRD Word Count**: 7,814 words

**Status**: Ready for implementation
