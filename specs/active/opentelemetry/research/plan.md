# Research Plan: OpenTelemetry Integration

## Research Phase Complete

**Date**: 2025-11-29
**Status**: Research Complete
**Complexity**: High (10+ checkpoints)

---

## Phase 1: Pattern Analysis

### Codebase Patterns Identified

1. **Panel Architecture Pattern** (`src/debug_toolbar/core/panel.py`)
   - Abstract base class with `generate_stats()` abstract method
   - Lifecycle hooks: `process_request()`, `process_response()`
   - ClassVar metadata: `panel_id`, `title`, `template`, `has_content`
   - `__slots__` for memory efficiency
   - Stats storage via `RequestContext`

2. **Extras Module Pattern** (`src/debug_toolbar/extras/advanced_alchemy/`)
   - Optional integrations placed in `extras/` directory
   - Follow same panel patterns as core
   - Graceful degradation for missing dependencies
   - Similar structure: panel.py with supporting utilities

3. **Data Collection Pattern** (from SQLAlchemyPanel)
   - Global tracker for request-scoped data collection
   - Start/stop tracking in lifecycle hooks
   - Event listeners for instrumentation
   - Context manager pattern for isolated tracking

4. **Testing Pattern** (`tests/unit/test_sqlalchemy_panel.py`)
   - Class-based test organization
   - Fixtures for panel, toolbar, context
   - Mock usage for dependencies
   - Context variable cleanup pattern

---

## Phase 2: OpenTelemetry Research

### Key Findings

#### 1. OpenTelemetry Python SDK Architecture

**Core Components**:
- `TracerProvider`: Manages tracers and span processors
- `SpanProcessor`: Processes spans (e.g., `BatchSpanProcessor`)
- `SpanExporter`: Exports spans to backend (e.g., `OTLPSpanExporter`)
- `Resource`: Service metadata (service.name, version, etc.)
- `Tracer`: Creates spans for tracing operations

**Installation**:
```bash
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-exporter-otlp-proto-grpc
pip install opentelemetry-exporter-otlp-proto-http
```

#### 2. OTLP Exporter Configuration

**Best Practices** (from research):
- Use OpenTelemetry Collector as intermediary in production
- Support both gRPC (default) and HTTP protocols
- Default endpoints:
  - gRPC: `http://localhost:4317`
  - HTTP: `http://localhost:4318`
- Environment variables for configuration:
  - `OTEL_EXPORTER_OTLP_ENDPOINT`: Base endpoint URL
  - `OTEL_EXPORTER_OTLP_PROTOCOL`: Protocol (grpc or http/protobuf)
  - `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`: Trace-specific endpoint
  - `OTEL_EXPORTER_OTLP_HEADERS`: Custom headers
- Batch processing for performance
- Automatic retry with exponential backoff
- Queuing for reliability

#### 3. W3C Trace Context Propagation

**Key Concepts**:
- `traceparent` header: Contains trace-id, parent-id, trace-flags
- `tracestate` header: Vendor-specific trace information
- `TraceContextTextMapPropagator`: Default propagator
- `W3CBaggagePropagator`: For baggage propagation
- `CompositePropagator`: Combines multiple propagators

**Implementation Pattern**:
```python
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

set_global_textmap(
    CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
)
```

#### 4. Span Data Structure

**Span Attributes**:
- `name`: Operation name
- `kind`: INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER
- `start_time`: Span start timestamp (nanoseconds)
- `end_time`: Span end timestamp (nanoseconds)
- `attributes`: Key-value metadata
- `events`: Timestamped annotations
- `links`: Relationships to other spans
- `status`: OK, ERROR, UNSET
- `trace_id`: Unique trace identifier
- `span_id`: Unique span identifier
- `parent_span_id`: Parent span identifier

#### 5. Integration with Jaeger/Zipkin

**Jaeger**:
- Docker: `jaegertracing/all-in-one:latest`
- Ports: 4317 (OTLP gRPC), 4318 (OTLP HTTP), 16686 (UI)
- Supports OTLP natively

**Zipkin**:
- Specific exporters available:
  - `opentelemetry-exporter-zipkin-json`
  - `opentelemetry-exporter-zipkin-proto-http`
- HTTP endpoint: `http://localhost:9411/api/v2/spans`

---

## Phase 3: Architecture Design

### Proposed Structure

```
src/debug_toolbar/extras/opentelemetry/
├── __init__.py           # Public exports
├── config.py             # OpenTelemetry configuration
├── exporter.py           # OTLP exporter with panel data conversion
├── propagation.py        # W3C Trace Context helpers
├── span_processor.py     # Custom span processor for debug toolbar
├── panel.py              # OpenTelemetry panel for visualization
└── utils.py              # Utility functions
```

### Key Components

#### 1. OpenTelemetryConfig
- OTLP endpoint configuration
- Protocol selection (gRPC/HTTP)
- Enable/disable tracing
- Service metadata (name, version)
- Headers/authentication
- Batch settings

#### 2. ToolbarSpanExporter
- Exports spans to OTLP endpoint
- Converts panel data to OpenTelemetry spans
- Handles both sync and async operations
- Error handling and logging

#### 3. ToolbarSpanProcessor
- Custom `SpanProcessor` implementation
- Captures spans during request
- Stores spans in `RequestContext`
- Integrates with debug toolbar lifecycle

#### 4. OpenTelemetryPanel
- Visualizes spans from current request
- Shows trace hierarchy (waterfall view)
- Displays span attributes and events
- Links to external trace viewer (Jaeger/Zipkin)
- Shows trace context propagation details

#### 5. TraceContextPropagation
- Extract trace context from incoming requests
- Inject trace context into outgoing requests
- Support for custom propagators
- Validation and debugging

---

## Phase 4: Data Conversion Strategy

### Panel Data to Spans Mapping

Each debug toolbar panel can contribute spans to the trace:

1. **TimerPanel** → Root request span
   - `http.server.duration`
   - Attributes: method, path, status_code

2. **SQLAlchemyPanel** → Database query spans
   - `db.query`
   - Attributes: db.system, db.statement, db.operation

3. **ProfilingPanel** → Function call spans
   - `function.call`
   - Attributes: code.function, code.filepath, code.lineno

4. **LoggingPanel** → Span events
   - Events attached to active span
   - Attributes: log.level, log.message

5. **TemplatePanel** → Template render spans
   - `template.render`
   - Attributes: template.name, template.engine

### Conversion Algorithm

1. Create root span from request timing
2. For each panel with timing data:
   - Create child span with panel-specific attributes
   - Set span kind based on operation type
   - Add panel stats as span attributes
3. Export all spans to OTLP endpoint
4. Store spans in context for panel visualization

---

## Phase 5: Testing Strategy

### Unit Tests

1. **test_config.py**
   - Configuration validation
   - Environment variable loading
   - Default values

2. **test_exporter.py**
   - OTLP export success/failure
   - Protocol selection (gRPC/HTTP)
   - Retry logic
   - Error handling

3. **test_span_processor.py**
   - Span capture during request
   - Context storage
   - Lifecycle integration

4. **test_panel.py**
   - Stats generation
   - Waterfall visualization
   - Trace links

5. **test_propagation.py**
   - Extract trace context
   - Inject trace context
   - Header validation

### Integration Tests

1. **test_jaeger_integration.py**
   - Export to Jaeger collector
   - Verify trace in Jaeger UI
   - Query API validation

2. **test_zipkin_integration.py**
   - Export to Zipkin collector
   - Verify trace in Zipkin UI

3. **test_panel_conversion.py**
   - Convert all panel types to spans
   - Verify span hierarchy
   - Validate attributes

### Test Fixtures

- `otel_config`: OpenTelemetryConfig instance
- `mock_exporter`: Mock OTLP exporter
- `span_processor`: ToolbarSpanProcessor instance
- `otel_panel`: OpenTelemetryPanel instance
- `trace_context`: W3C trace context headers

---

## Phase 6: Similar Implementations

### Analyzed Implementations

1. **SQLAlchemyPanel** (`extras/advanced_alchemy/panel.py`)
   - Global tracker pattern
   - Event listeners for instrumentation
   - N+1 detection algorithm
   - Stack trace capture
   - EXPLAIN query execution
   - **Pattern**: External system integration with event hooks

2. **LoggingPanel** (`core/panels/logging.py`)
   - Custom handler for capturing data
   - Start/stop in lifecycle hooks
   - Minimal overhead when disabled
   - **Pattern**: Handler-based collection

3. **ProfilingPanel** (`core/panels/profiling.py`)
   - Multiple backend support (cProfile, pyinstrument)
   - Graceful degradation
   - Optional dependency handling
   - **Pattern**: Pluggable backends

### Key Patterns to Follow

1. **Optional dependency handling**:
   ```python
   try:
       from opentelemetry import trace
       from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
       OPENTELEMETRY_AVAILABLE = True
   except ImportError:
       OPENTELEMETRY_AVAILABLE = False
   ```

2. **Graceful degradation**:
   - Panel shows "OpenTelemetry not installed" if missing
   - Config validation for endpoints
   - Disable export if endpoint unreachable

3. **Performance considerations**:
   - Batch span export (async)
   - Minimal overhead during request
   - Optional features (can disable tracing)

---

## Phase 7: Dependencies

### Required Packages

```toml
[project.optional-dependencies]
opentelemetry = [
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
    "opentelemetry-exporter-otlp-proto-http>=1.20.0",
]
```

### Optional Packages (for specific backends)

- `opentelemetry-exporter-zipkin-json`
- `opentelemetry-exporter-zipkin-proto-http`

---

## Research Sources

### Documentation
- [OpenTelemetry Python Docs](https://opentelemetry-python.readthedocs.io/)
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

### Code Examples
- OpenTelemetry Python GitHub examples
- Uptrace OpenTelemetry Python guides
- Last9 OpenTelemetry best practices

---

## Next Steps

1. Create PRD with:
   - Detailed acceptance criteria
   - Technical approach
   - File-by-file implementation plan
   - Testing strategy
   - Configuration examples

2. Implementation phase:
   - Config module
   - Exporter
   - Span processor
   - Panel
   - Propagation utilities

3. Testing phase:
   - Unit tests (90%+ coverage)
   - Integration tests with Jaeger
   - Integration tests with Zipkin

4. Review phase:
   - Extract new patterns
   - Update pattern library
   - Documentation
