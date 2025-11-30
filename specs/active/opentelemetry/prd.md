# PRD: OpenTelemetry Integration for Debug Toolbar

**Document Version**: 1.0
**Created**: 2025-11-29
**Status**: Ready for Implementation
**Priority**: P2 (Enterprise Appeal)

---

## Metadata

| Field | Value |
|-------|-------|
| **Slug** | `opentelemetry` |
| **Complexity** | High (10+ checkpoints) |
| **Estimated Files** | 8-10 |
| **Dependencies** | None (optional packages) |
| **Checkpoints** | 12 |
| **Implementation Order** | 9 |
| **Estimated Effort** | 5-7 days |
| **Target Coverage** | 90%+ |

---

## Intelligence Context

### Complexity Assessment

**Complexity Level**: High (12 checkpoints)

**Triggers**:
- New framework integration (OpenTelemetry SDK)
- Multi-component architecture (exporter, processor, panel, propagation)
- External system integration (Jaeger, Zipkin, OTLP collectors)
- Complex data transformation (panel stats → OpenTelemetry spans)
- Distributed tracing concepts (trace context propagation)
- Optional dependency management
- Multiple export protocols (gRPC, HTTP)

### Pattern Analysis

**Similar Implementations Studied**:

1. **SQLAlchemyPanel** (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)
   - Lines: 588
   - Pattern: External system integration with event hooks
   - Relevance: Shows how to integrate with external libraries, use global trackers, and handle optional dependencies
   - Key Learnings: Event listener pattern, graceful degradation, context-based data storage

2. **LoggingPanel** (`src/debug_toolbar/core/panels/logging.py`)
   - Lines: 96
   - Pattern: Handler-based data collection
   - Relevance: Demonstrates lightweight request-scoped data capture
   - Key Learnings: Custom handler implementation, lifecycle hook usage, minimal overhead

3. **ProfilingPanel** (`src/debug_toolbar/core/panels/profiling.py`)
   - Lines: 250+
   - Pattern: Multiple backend support with optional dependencies
   - Relevance: Shows how to support multiple backends (cProfile, pyinstrument)
   - Key Learnings: Backend abstraction, optional dependency handling, feature detection

**Pattern Compliance**:
- ✅ Panel ABC pattern (ClassVar metadata, generate_stats, lifecycle hooks)
- ✅ Extras module structure (optional integration in `extras/opentelemetry/`)
- ✅ Type hints (PEP 604: `T | None`, future annotations)
- ✅ Async-first (async def for I/O operations)
- ✅ Context variable management (RequestContext for data storage)
- ✅ Graceful degradation (check for optional dependencies)

### Research Summary

**OpenTelemetry Python SDK** (2000+ words):

**Core Architecture**:
- `TracerProvider`: Central point for creating tracers, manages span processors
- `SpanProcessor`: Processes spans as they're created/ended (e.g., `BatchSpanProcessor`)
- `SpanExporter`: Exports spans to backend systems (OTLP, Jaeger, Zipkin)
- `Resource`: Represents the entity producing telemetry (service name, version, environment)
- `Tracer`: Creates spans to represent operations
- `Span`: Represents a unit of work with timing, attributes, events, and links

**OTLP Export Protocols**:
1. **gRPC** (default):
   - Endpoint: `http://localhost:4317`
   - Binary protobuf over HTTP/2
   - Better performance for high-volume scenarios
   - Requires gRPC infrastructure

2. **HTTP**:
   - Endpoint: `http://localhost:4318/v1/traces`
   - Protobuf over HTTP/1.1
   - Easier integration with proxies/firewalls
   - Standard HTTP retry semantics

**W3C Trace Context Propagation**:
- **traceparent header**: `version-trace_id-parent_id-trace_flags`
  - Example: `00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01`
  - Version: 2 hex digits (currently `00`)
  - Trace ID: 32 hex digits (128-bit)
  - Parent ID: 16 hex digits (64-bit span ID)
  - Trace flags: 2 hex digits (sampled flag)

- **tracestate header**: Vendor-specific trace information
  - Format: `vendor1=value1,vendor2=value2`
  - Optional, used for vendor-specific propagation

**Span Data Structure**:
```python
{
    "name": "http.request",
    "kind": SpanKind.SERVER,  # INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER
    "start_time": 1638360000000000000,  # nanoseconds
    "end_time": 1638360001000000000,
    "attributes": {
        "http.method": "GET",
        "http.url": "/api/users",
        "http.status_code": 200,
    },
    "events": [
        {
            "name": "exception",
            "timestamp": 1638360000500000000,
            "attributes": {"exception.message": "error"},
        }
    ],
    "links": [],  # Links to other spans
    "status": {"code": "OK"},
    "trace_id": "0af7651916cd43dd8448eb211c80319c",
    "span_id": "b7ad6b7169203331",
    "parent_span_id": "00f067aa0ba902b7",
}
```

**Best Practices** (from OpenTelemetry community):
1. Use OpenTelemetry Collector as intermediary in production
2. Enable batch processing for performance (default: 512 spans or 5s)
3. Set resource attributes (service.name is required)
4. Use appropriate span kinds (SERVER for incoming requests)
5. Add semantic attributes following OpenTelemetry conventions
6. Handle errors gracefully (don't fail requests if export fails)
7. Configure retry policies (exponential backoff for transient errors)
8. Use queuing for reliability (in-memory buffer before export)

**Jaeger Integration**:
- Supports OTLP natively (preferred over legacy Jaeger protocol)
- Docker: `jaegertracing/all-in-one:latest`
- Ports:
  - 4317: OTLP gRPC
  - 4318: OTLP HTTP
  - 16686: Jaeger UI
  - 14268: Legacy Jaeger HTTP Thrift
- Query API: `http://localhost:16686/api/traces/{trace_id}`

**Zipkin Integration**:
- Requires specific exporter: `opentelemetry-exporter-zipkin-json`
- Endpoint: `http://localhost:9411/api/v2/spans`
- Less feature-rich than Jaeger for OpenTelemetry
- Good for existing Zipkin infrastructure

---

## Problem Statement

OpenTelemetry is the industry standard for observability in cloud-native applications. It provides a vendor-neutral, open-source framework for collecting traces, metrics, and logs. However, the debug toolbar currently lacks integration with OpenTelemetry, limiting its appeal for:

1. **Enterprise Teams**: Companies standardizing on OpenTelemetry for observability
2. **Microservices Architectures**: Need distributed tracing across service boundaries
3. **Production Correlation**: Ability to correlate debug data with production traces
4. **Observability Platforms**: Integration with Jaeger, Zipkin, Datadog, New Relic, etc.

**Current State**:
- Debug toolbar collects rich performance data (timing, SQL, profiling)
- Data is isolated to individual requests
- No trace context propagation for distributed systems
- No export to external observability backends
- Cannot correlate debug sessions with production traces

**Desired State**:
- Export debug toolbar data as OpenTelemetry traces
- Propagate W3C Trace Context across service boundaries
- Visualize spans in debug toolbar panel
- Link to external trace viewers (Jaeger, Zipkin)
- Enable correlation with production monitoring
- Support both OTLP gRPC and HTTP protocols

**Business Value**:
- **Enterprise Appeal**: OpenTelemetry is adopted by CNCF and major cloud providers
- **Production Readiness**: Bridge gap between development debugging and production observability
- **Vendor Neutrality**: Works with any OpenTelemetry-compatible backend
- **Developer Experience**: Unified observability across dev and prod environments

---

## Goals and Non-Goals

### Goals

1. **OTLP Export**: Export debug toolbar data to OTLP endpoints (gRPC and HTTP)
2. **Trace Context Propagation**: Support W3C Trace Context header propagation
3. **Span Visualization**: Display OpenTelemetry spans in debug toolbar panel
4. **Panel Data Conversion**: Convert panel statistics to semantic OpenTelemetry spans
5. **Jaeger Integration**: Verify integration with Jaeger backend
6. **Zipkin Integration**: Verify integration with Zipkin backend
7. **Configuration**: Flexible configuration for endpoints, protocols, and options
8. **Graceful Degradation**: Work without OpenTelemetry dependencies (show installation prompt)

### Non-Goals

1. **Metrics Export**: Focus on traces only (metrics are future work)
2. **Logs Export**: Focus on traces only (logs are future work)
3. **Auto-Instrumentation**: Not replacing OpenTelemetry auto-instrumentation
4. **Custom Propagators**: Only W3C Trace Context (others are future work)
5. **Sampling**: Use OpenTelemetry SDK default sampling (no custom logic)
6. **Backend-Specific Features**: No Jaeger-specific or Zipkin-specific extensions

---

## Acceptance Criteria

### Functional Requirements

1. **Configuration**
   - [ ] `OpenTelemetryConfig` dataclass with OTLP endpoint, protocol, headers
   - [ ] Support gRPC protocol (`http://localhost:4317`)
   - [ ] Support HTTP protocol (`http://localhost:4318/v1/traces`)
   - [ ] Environment variable configuration (OTEL_EXPORTER_OTLP_*)
   - [ ] Resource attributes (service.name, service.version)
   - [ ] Enable/disable toggle

2. **OTLP Export**
   - [ ] `ToolbarSpanExporter` exports spans to OTLP endpoint
   - [ ] Batch processing (configurable batch size and timeout)
   - [ ] Retry logic for transient failures (exponential backoff)
   - [ ] Error handling and logging (don't fail requests)
   - [ ] Support both sync and async export

3. **Span Conversion**
   - [ ] Convert `TimerPanel` data to root request span
   - [ ] Convert `SQLAlchemyPanel` queries to database spans
   - [ ] Convert `ProfilingPanel` functions to function call spans
   - [ ] Convert `LoggingPanel` records to span events
   - [ ] Convert `TemplatePanel` renders to template spans
   - [ ] Preserve timing relationships (parent-child hierarchy)
   - [ ] Add semantic attributes following OpenTelemetry conventions

4. **Trace Context Propagation**
   - [ ] Extract `traceparent` header from incoming requests
   - [ ] Extract `tracestate` header from incoming requests
   - [ ] Create child spans under incoming trace context
   - [ ] Inject `traceparent` header for outgoing requests (if applicable)
   - [ ] Validate header format
   - [ ] Handle missing/invalid trace context

5. **OpenTelemetry Panel**
   - [ ] Display spans from current request (waterfall view)
   - [ ] Show span hierarchy (parent-child relationships)
   - [ ] Display span attributes and events
   - [ ] Show trace ID and span IDs
   - [ ] Link to external trace viewer (Jaeger, Zipkin)
   - [ ] Show propagation details (incoming trace context)
   - [ ] Display export status (success/failure)

6. **Jaeger Integration**
   - [ ] Export traces to Jaeger all-in-one (OTLP)
   - [ ] Traces visible in Jaeger UI
   - [ ] Panel links to Jaeger trace view
   - [ ] Query Jaeger API for trace verification

7. **Zipkin Integration**
   - [ ] Export traces to Zipkin (using Zipkin exporter)
   - [ ] Traces visible in Zipkin UI
   - [ ] Panel links to Zipkin trace view

### Non-Functional Requirements

1. **Performance**
   - [ ] Minimal overhead when OpenTelemetry disabled (<1ms)
   - [ ] Async export (don't block request)
   - [ ] Batch processing (reduce network overhead)
   - [ ] Configurable batch size (default: 512 spans or 5s)

2. **Reliability**
   - [ ] Graceful degradation if export fails
   - [ ] Logging for troubleshooting
   - [ ] Retry logic with exponential backoff
   - [ ] Circuit breaker for repeated failures (optional)

3. **Developer Experience**
   - [ ] Clear error messages for configuration issues
   - [ ] Installation instructions if dependencies missing
   - [ ] Example configurations in docs
   - [ ] Debug mode for verbose logging

4. **Testing**
   - [ ] 90%+ code coverage
   - [ ] Unit tests for all components
   - [ ] Integration tests with Jaeger
   - [ ] Integration tests with Zipkin
   - [ ] Mock OTLP endpoint tests
   - [ ] Trace context propagation tests

---

## Technical Approach

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│ Debug Toolbar Request Lifecycle                              │
├──────────────────────────────────────────────────────────────┤
│ 1. process_request()                                         │
│    ├─ Extract W3C Trace Context (traceparent/tracestate)    │
│    ├─ Create/Continue trace                                 │
│    └─ Start ToolbarSpanProcessor                            │
│                                                              │
│ 2. Request Processing                                        │
│    ├─ Panels collect data                                   │
│    ├─ ToolbarSpanProcessor captures spans                   │
│    └─ Store spans in RequestContext                         │
│                                                              │
│ 3. process_response()                                        │
│    ├─ Finalize root span                                    │
│    └─ Stop ToolbarSpanProcessor                             │
│                                                              │
│ 4. generate_stats()                                          │
│    ├─ Convert panel data to spans                           │
│    ├─ Export via ToolbarSpanExporter                        │
│    └─ Store for panel visualization                         │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ OTLP Exporter                                                │
├──────────────────────────────────────────────────────────────┤
│ ToolbarSpanExporter                                          │
│ ├─ Batch spans (512 or 5s)                                  │
│ ├─ Serialize to protobuf                                    │
│ ├─ Export via gRPC or HTTP                                  │
│ └─ Retry on failure                                         │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ Observability Backends                                       │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│ │   Jaeger    │  │   Zipkin    │  │  Datadog    │          │
│ │  (OTLP)     │  │  (Zipkin)   │  │   (OTLP)    │          │
│ └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│ │ New Relic   │  │ Honeycomb   │  │    ...      │          │
│ │   (OTLP)    │  │   (OTLP)    │  │             │          │
│ └─────────────┘  └─────────────┘  └─────────────┘          │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│ OpenTelemetry Panel                                          │
├──────────────────────────────────────────────────────────────┤
│ ┌─ Trace Info ────────────────────────────────────────────┐ │
│ │ Trace ID: 0af7651916cd43dd8448eb211c80319c             │ │
│ │ Root Span: b7ad6b7169203331                            │ │
│ │ Link: http://localhost:16686/trace/{trace_id}          │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Span Waterfall ────────────────────────────────────────┐ │
│ │ http.request                    [============] 450ms    │ │
│ │   ├─ db.query (users)          [==]           45ms     │ │
│ │   ├─ db.query (posts)          [==]           42ms     │ │
│ │   ├─ template.render           [====]         80ms     │ │
│ │   └─ function.call (process)   [========]     180ms    │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Span Details ──────────────────────────────────────────┐ │
│ │ Name: http.request                                      │ │
│ │ Kind: SERVER                                            │ │
│ │ Status: OK                                              │ │
│ │ Attributes:                                             │ │
│ │   http.method: GET                                      │ │
│ │   http.url: /api/users                                  │ │
│ │   http.status_code: 200                                 │ │
│ │ Events: 2                                               │ │
│ └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Module Structure

```
src/debug_toolbar/extras/opentelemetry/
├── __init__.py              # Public exports
├── config.py                # OpenTelemetryConfig dataclass
├── exporter.py              # ToolbarSpanExporter (OTLP export)
├── span_processor.py        # ToolbarSpanProcessor (capture spans)
├── propagation.py           # W3C Trace Context utilities
├── converter.py             # Panel data → Span conversion
├── panel.py                 # OpenTelemetryPanel (visualization)
└── utils.py                 # Utility functions
```

### Component Details

#### 1. config.py - OpenTelemetryConfig

```python
"""OpenTelemetry configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class OpenTelemetryConfig:
    """Configuration for OpenTelemetry integration.

    Attributes:
        enabled: Enable OpenTelemetry integration.
        otlp_endpoint: OTLP endpoint URL.
        otlp_protocol: Protocol (grpc or http/protobuf).
        otlp_headers: Custom headers for OTLP requests.
        service_name: Service name for Resource.
        service_version: Service version for Resource.
        service_namespace: Service namespace for Resource.
        export_interval_ms: Batch export interval in milliseconds.
        max_export_batch_size: Maximum batch size.
        max_queue_size: Maximum queue size.
        export_timeout_ms: Export timeout in milliseconds.
        jaeger_ui_url: Jaeger UI base URL (for links).
        zipkin_ui_url: Zipkin UI base URL (for links).
    """

    enabled: bool = True
    otlp_endpoint: str = field(
        default_factory=lambda: os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://localhost:4317"
        )
    )
    otlp_protocol: Literal["grpc", "http/protobuf"] = field(
        default_factory=lambda: os.getenv(
            "OTEL_EXPORTER_OTLP_PROTOCOL",
            "grpc"
        )
    )
    otlp_headers: dict[str, str] = field(default_factory=dict)
    service_name: str = "debug-toolbar"
    service_version: str = "1.0.0"
    service_namespace: str | None = None
    export_interval_ms: int = 5000  # 5 seconds
    max_export_batch_size: int = 512
    max_queue_size: int = 2048
    export_timeout_ms: int = 30000  # 30 seconds
    jaeger_ui_url: str = "http://localhost:16686"
    zipkin_ui_url: str = "http://localhost:9411"
```

**Key Design Decisions**:
- Environment variables take precedence (follows OpenTelemetry conventions)
- Sensible defaults for local development
- Support both Jaeger and Zipkin UI links
- Configurable batch settings for performance tuning

#### 2. exporter.py - ToolbarSpanExporter

```python
"""OTLP span exporter for debug toolbar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export import SpanExporter
    from opentelemetry.sdk.trace import ReadableSpan

logger = logging.getLogger(__name__)

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GRPCExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter as HTTPExporter,
    )
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    GRPCExporter = None  # type: ignore[misc, assignment]
    HTTPExporter = None  # type: ignore[misc, assignment]


class ToolbarSpanExporter:
    """Wrapper around OTLP span exporters with error handling."""

    def __init__(
        self,
        endpoint: str,
        protocol: str = "grpc",
        headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize the exporter.

        Args:
            endpoint: OTLP endpoint URL.
            protocol: Protocol (grpc or http/protobuf).
            headers: Custom headers.
            timeout: Export timeout in seconds.
        """
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning(
                "OpenTelemetry not installed. "
                "Install with: pip install opentelemetry-exporter-otlp"
            )
            self._exporter = None
            return

        if protocol == "grpc":
            self._exporter = GRPCExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout,
            )
        else:  # http/protobuf
            self._exporter = HTTPExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout,
            )

    def export(self, spans: list[ReadableSpan]) -> bool:
        """Export spans to OTLP endpoint.

        Args:
            spans: List of spans to export.

        Returns:
            True if export succeeded, False otherwise.
        """
        if self._exporter is None:
            return False

        try:
            result = self._exporter.export(spans)
            # Check result.value for success (0 = SUCCESS)
            success = result.value == 0
            if not success:
                logger.error(f"OTLP export failed: {result}")
            return success
        except Exception as e:
            logger.exception(f"OTLP export error: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        if self._exporter is not None:
            self._exporter.shutdown()
```

**Key Design Decisions**:
- Graceful degradation if OpenTelemetry not installed
- Support both gRPC and HTTP protocols
- Error handling and logging (don't fail requests)
- Simple wrapper interface for easier testing

#### 3. span_processor.py - ToolbarSpanProcessor

```python
"""Span processor for capturing spans during request."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, Span
    from opentelemetry.context import Context

    from debug_toolbar.core.context import RequestContext

logger = logging.getLogger(__name__)

try:
    from opentelemetry.sdk.trace import SpanProcessor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    SpanProcessor = object  # type: ignore[misc, assignment]


class ToolbarSpanProcessor(SpanProcessor):
    """Custom span processor that stores spans in RequestContext."""

    def __init__(self) -> None:
        """Initialize the processor."""
        self._spans: list[ReadableSpan] = []
        self._enabled = False

    def start(self) -> None:
        """Start capturing spans."""
        self._spans = []
        self._enabled = True

    def stop(self) -> None:
        """Stop capturing spans."""
        self._enabled = False

    def get_spans(self) -> list[ReadableSpan]:
        """Get captured spans."""
        return list(self._spans)

    def on_start(
        self,
        span: Span,
        parent_context: Context | None = None,
    ) -> None:
        """Called when a span starts."""
        pass  # Not needed for now

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends."""
        if self._enabled:
            self._spans.append(span)

    def shutdown(self) -> None:
        """Shutdown the processor."""
        self._enabled = False
        self._spans = []

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush (no-op for in-memory processor)."""
        return True
```

**Key Design Decisions**:
- Implements OpenTelemetry `SpanProcessor` interface
- Stores spans in memory during request
- Start/stop pattern matches panel lifecycle
- Simple get_spans() for retrieval

#### 4. propagation.py - Trace Context Utilities

```python
"""W3C Trace Context propagation utilities."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.trace import SpanContext

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

# W3C Trace Context format: {version}-{trace-id}-{parent-id}-{trace-flags}
TRACEPARENT_REGEX = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)


def extract_trace_context(headers: dict[str, str]) -> SpanContext | None:
    """Extract W3C Trace Context from headers.

    Args:
        headers: HTTP headers dict (case-insensitive keys expected).

    Returns:
        SpanContext if valid trace context found, None otherwise.
    """
    if not OPENTELEMETRY_AVAILABLE:
        return None

    try:
        propagator = TraceContextTextMapPropagator()
        ctx = propagator.extract(carrier=headers)
        span_ctx = trace.get_current_span(ctx).get_span_context()

        if span_ctx.is_valid:
            return span_ctx
    except Exception as e:
        logger.debug(f"Failed to extract trace context: {e}")

    return None


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """Inject W3C Trace Context into headers.

    Args:
        headers: HTTP headers dict to inject into.

    Returns:
        Updated headers dict.
    """
    if not OPENTELEMETRY_AVAILABLE:
        return headers

    try:
        propagator = TraceContextTextMapPropagator()
        propagator.inject(carrier=headers)
    except Exception as e:
        logger.debug(f"Failed to inject trace context: {e}")

    return headers


def parse_traceparent(traceparent: str) -> dict[str, str] | None:
    """Parse traceparent header value.

    Args:
        traceparent: traceparent header value.

    Returns:
        Dict with version, trace_id, parent_id, trace_flags, or None.
    """
    match = TRACEPARENT_REGEX.match(traceparent.strip())
    if not match:
        return None

    return {
        "version": match.group(1),
        "trace_id": match.group(2),
        "parent_id": match.group(3),
        "trace_flags": match.group(4),
    }


def format_trace_id(trace_id: int | str) -> str:
    """Format trace ID as 32-char hex string.

    Args:
        trace_id: Trace ID as int or hex string.

    Returns:
        Formatted trace ID.
    """
    if isinstance(trace_id, int):
        return f"{trace_id:032x}"
    return trace_id.lower().zfill(32)


def format_span_id(span_id: int | str) -> str:
    """Format span ID as 16-char hex string.

    Args:
        span_id: Span ID as int or hex string.

    Returns:
        Formatted span ID.
    """
    if isinstance(span_id, int):
        return f"{span_id:016x}"
    return span_id.lower().zfill(16)
```

**Key Design Decisions**:
- Use OpenTelemetry's built-in propagators
- Provide manual parsing for debugging
- Formatting utilities for display
- Graceful error handling

#### 5. converter.py - Panel Data to Span Conversion

```python
"""Convert panel data to OpenTelemetry spans."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.trace import SpanKind

    from debug_toolbar.core.context import RequestContext

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.trace import SpanKind, Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class PanelDataConverter:
    """Converts panel data to OpenTelemetry spans."""

    def __init__(
        self,
        service_name: str = "debug-toolbar",
        service_version: str = "1.0.0",
    ) -> None:
        """Initialize the converter.

        Args:
            service_name: Service name for Resource.
            service_version: Service version for Resource.
        """
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not available")
            self._tracer = None
            return

        resource = Resource.create({
            SERVICE_NAME: service_name,
            "service.version": service_version,
        })

        provider = TracerProvider(resource=resource)
        self._tracer = provider.get_tracer(__name__)

    def convert_timer_panel(
        self,
        context: RequestContext,
        parent_span: Any = None,
    ) -> ReadableSpan | None:
        """Convert TimerPanel data to root request span.

        Args:
            context: Request context with panel data.
            parent_span: Optional parent span context.

        Returns:
            ReadableSpan or None.
        """
        if self._tracer is None:
            return None

        stats = context.get_panel_data("TimerPanel")
        if not stats:
            return None

        total_time = stats.get("total_time", 0)

        # Create span (simplified - actual implementation needs timing)
        with self._tracer.start_as_current_span(
            "http.request",
            kind=SpanKind.SERVER,
        ) as span:
            span.set_attribute("http.method", "GET")  # From request
            span.set_attribute("http.url", "/")  # From request
            span.set_attribute("http.status_code", 200)  # From response
            span.set_attribute("debug_toolbar.total_time_ms", total_time * 1000)

            return span  # type: ignore[return-value]

    def convert_sql_panel(
        self,
        context: RequestContext,
        parent_span: Any,
    ) -> list[ReadableSpan]:
        """Convert SQLAlchemyPanel queries to database spans.

        Args:
            context: Request context with panel data.
            parent_span: Parent span context.

        Returns:
            List of database query spans.
        """
        if self._tracer is None:
            return []

        stats = context.get_panel_data("SQLAlchemyPanel")
        if not stats:
            return []

        queries = stats.get("queries", [])
        spans = []

        for query in queries:
            with self._tracer.start_as_current_span(
                "db.query",
                kind=SpanKind.CLIENT,
            ) as span:
                span.set_attribute("db.system", query.get("dialect", "sql"))
                span.set_attribute("db.statement", query.get("sql", ""))
                span.set_attribute("db.operation", self._extract_operation(query.get("sql", "")))
                span.set_attribute("debug_toolbar.duration_ms", query.get("duration_ms", 0))

                if query.get("is_slow"):
                    span.set_attribute("debug_toolbar.is_slow", True)
                if query.get("is_n_plus_one"):
                    span.set_attribute("debug_toolbar.is_n_plus_one", True)

                spans.append(span)  # type: ignore[arg-type]

        return spans

    def _extract_operation(self, sql: str) -> str:
        """Extract SQL operation (SELECT, INSERT, etc.)."""
        sql_upper = sql.upper().strip()
        for op in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]:
            if sql_upper.startswith(op):
                return op
        return "UNKNOWN"
```

**Key Design Decisions**:
- Separate converter class for testability
- Create spans with semantic attributes
- Support parent-child relationships
- Handle missing panel data gracefully

#### 6. panel.py - OpenTelemetryPanel

```python
"""OpenTelemetry panel for span visualization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

logger = logging.getLogger(__name__)

try:
    from debug_toolbar.extras.opentelemetry.config import OpenTelemetryConfig
    from debug_toolbar.extras.opentelemetry.exporter import ToolbarSpanExporter
    from debug_toolbar.extras.opentelemetry.span_processor import ToolbarSpanProcessor
    from debug_toolbar.extras.opentelemetry.propagation import (
        extract_trace_context,
        format_trace_id,
        format_span_id,
    )
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class OpenTelemetryPanel(Panel):
    """Panel displaying OpenTelemetry trace information.

    Shows:
    - Trace ID and span IDs
    - Span waterfall visualization
    - Span attributes and events
    - Links to external trace viewers (Jaeger, Zipkin)
    - Export status
    """

    panel_id: ClassVar[str] = "OpenTelemetryPanel"
    title: ClassVar[str] = "OpenTelemetry"
    template: ClassVar[str] = "panels/opentelemetry.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "OTel"

    __slots__ = ("_config", "_exporter", "_processor")

    def __init__(
        self,
        toolbar: DebugToolbar,
        config: OpenTelemetryConfig | None = None,
    ) -> None:
        """Initialize the panel.

        Args:
            toolbar: Parent DebugToolbar instance.
            config: OpenTelemetry configuration.
        """
        super().__init__(toolbar)

        if not OPENTELEMETRY_AVAILABLE:
            logger.warning(
                "OpenTelemetry not installed. "
                "Install with: pip install opentelemetry-exporter-otlp"
            )
            self._config = None
            self._exporter = None
            self._processor = None
            return

        self._config = config or OpenTelemetryConfig()

        if self._config.enabled:
            self._exporter = ToolbarSpanExporter(
                endpoint=self._config.otlp_endpoint,
                protocol=self._config.otlp_protocol,
                headers=self._config.otlp_headers,
                timeout=self._config.export_timeout_ms // 1000,
            )
            self._processor = ToolbarSpanProcessor()
        else:
            self._exporter = None
            self._processor = None

    async def process_request(self, context: RequestContext) -> None:
        """Extract trace context and start span processor."""
        if self._processor is None:
            return

        # Extract incoming trace context from request headers
        # (headers would come from ASGI scope)
        # trace_ctx = extract_trace_context(headers)

        self._processor.start()

    async def process_response(self, context: RequestContext) -> None:
        """Stop span processor."""
        if self._processor is None:
            return

        self._processor.stop()

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate OpenTelemetry statistics."""
        if not OPENTELEMETRY_AVAILABLE:
            return {
                "available": False,
                "message": "OpenTelemetry not installed",
            }

        if not self._config or not self._config.enabled:
            return {
                "available": True,
                "enabled": False,
                "message": "OpenTelemetry disabled",
            }

        # Get captured spans
        spans = self._processor.get_spans() if self._processor else []

        # Export spans
        export_success = False
        if self._exporter and spans:
            export_success = self._exporter.export(spans)

        # Format spans for display
        formatted_spans = self._format_spans(spans)

        # Get trace ID (from first span)
        trace_id = None
        if spans:
            trace_id = format_trace_id(spans[0].context.trace_id)

        # Build trace viewer links
        jaeger_link = None
        zipkin_link = None
        if trace_id and self._config:
            jaeger_link = f"{self._config.jaeger_ui_url}/trace/{trace_id}"
            zipkin_link = f"{self._config.zipkin_ui_url}/traces/{trace_id}"

        return {
            "available": True,
            "enabled": True,
            "trace_id": trace_id,
            "span_count": len(spans),
            "spans": formatted_spans,
            "export_success": export_success,
            "export_endpoint": self._config.otlp_endpoint if self._config else None,
            "export_protocol": self._config.otlp_protocol if self._config else None,
            "jaeger_link": jaeger_link,
            "zipkin_link": zipkin_link,
        }

    def _format_spans(self, spans: list[Any]) -> list[dict[str, Any]]:
        """Format spans for display."""
        formatted = []

        for span in spans:
            formatted.append({
                "name": span.name,
                "span_id": format_span_id(span.context.span_id),
                "parent_span_id": format_span_id(span.parent.span_id) if span.parent else None,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "duration_ms": (span.end_time - span.start_time) / 1_000_000,  # ns to ms
                "kind": span.kind.name,
                "status": span.status.status_code.name,
                "attributes": dict(span.attributes) if span.attributes else {},
                "events": [
                    {
                        "name": event.name,
                        "timestamp": event.timestamp,
                        "attributes": dict(event.attributes) if event.attributes else {},
                    }
                    for event in (span.events or [])
                ],
            })

        return formatted

    def get_nav_subtitle(self) -> str:
        """Get navigation subtitle showing span count."""
        return ""
```

**Key Design Decisions**:
- Graceful degradation if OpenTelemetry not installed
- Extract trace context in process_request
- Format spans for waterfall visualization
- Generate links to Jaeger and Zipkin UIs
- Show export status

---

## Files to Create/Modify

### New Files

1. **`src/debug_toolbar/extras/opentelemetry/__init__.py`**
   - Public exports: `OpenTelemetryPanel`, `OpenTelemetryConfig`
   - Version info

2. **`src/debug_toolbar/extras/opentelemetry/config.py`**
   - `OpenTelemetryConfig` dataclass
   - Environment variable loading
   - Validation logic

3. **`src/debug_toolbar/extras/opentelemetry/exporter.py`**
   - `ToolbarSpanExporter` class
   - OTLP gRPC and HTTP support
   - Error handling and retry logic

4. **`src/debug_toolbar/extras/opentelemetry/span_processor.py`**
   - `ToolbarSpanProcessor` class
   - Implements `SpanProcessor` interface
   - Span capture and storage

5. **`src/debug_toolbar/extras/opentelemetry/propagation.py`**
   - `extract_trace_context()` function
   - `inject_trace_context()` function
   - `parse_traceparent()` function
   - Formatting utilities

6. **`src/debug_toolbar/extras/opentelemetry/converter.py`**
   - `PanelDataConverter` class
   - `convert_timer_panel()` method
   - `convert_sql_panel()` method
   - `convert_profiling_panel()` method
   - `convert_logging_panel()` method (events)
   - `convert_template_panel()` method

7. **`src/debug_toolbar/extras/opentelemetry/panel.py`**
   - `OpenTelemetryPanel` class
   - Span visualization logic
   - Waterfall generation
   - Link generation

8. **`src/debug_toolbar/extras/opentelemetry/utils.py`**
   - Utility functions
   - Constants
   - Helper classes

### Test Files

1. **`tests/unit/test_opentelemetry_config.py`**
   - Config initialization
   - Environment variable loading
   - Validation

2. **`tests/unit/test_opentelemetry_exporter.py`**
   - Export success/failure
   - Protocol selection
   - Retry logic
   - Error handling

3. **`tests/unit/test_opentelemetry_span_processor.py`**
   - Span capture
   - Start/stop lifecycle
   - Span retrieval

4. **`tests/unit/test_opentelemetry_propagation.py`**
   - Extract trace context
   - Inject trace context
   - Parse traceparent
   - Format utilities

5. **`tests/unit/test_opentelemetry_converter.py`**
   - Timer panel conversion
   - SQL panel conversion
   - Span attributes validation

6. **`tests/unit/test_opentelemetry_panel.py`**
   - Stats generation
   - Span formatting
   - Link generation
   - Lifecycle hooks

7. **`tests/integration/test_jaeger_integration.py`**
   - Export to Jaeger
   - Query Jaeger API
   - UI link validation

8. **`tests/integration/test_zipkin_integration.py`**
   - Export to Zipkin
   - Query Zipkin API
   - UI link validation

### Modified Files

1. **`pyproject.toml`**
   - Add `opentelemetry` optional dependency group:
     ```toml
     [project.optional-dependencies]
     opentelemetry = [
         "opentelemetry-api>=1.20.0",
         "opentelemetry-sdk>=1.20.0",
         "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
         "opentelemetry-exporter-otlp-proto-http>=1.20.0",
     ]
     ```

2. **`src/debug_toolbar/extras/__init__.py`**
   - Import OpenTelemetry exports (conditional)

---

## Testing Strategy

### Unit Tests (90%+ Coverage)

#### test_opentelemetry_config.py

```python
"""Tests for OpenTelemetry configuration."""

from __future__ import annotations

import os
import pytest

from debug_toolbar.extras.opentelemetry.config import OpenTelemetryConfig


class TestOpenTelemetryConfig:
    """Tests for OpenTelemetryConfig."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = OpenTelemetryConfig()
        assert config.enabled is True
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.otlp_protocol == "grpc"
        assert config.service_name == "debug-toolbar"

    def test_environment_variable_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load endpoint from environment variable."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://example.com:4317")
        config = OpenTelemetryConfig()
        assert config.otlp_endpoint == "http://example.com:4317"

    def test_environment_variable_protocol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should load protocol from environment variable."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
        config = OpenTelemetryConfig()
        assert config.otlp_protocol == "http/protobuf"

    def test_custom_configuration(self) -> None:
        """Should accept custom configuration."""
        config = OpenTelemetryConfig(
            enabled=False,
            otlp_endpoint="http://custom:4318",
            otlp_protocol="http/protobuf",
            service_name="my-service",
        )
        assert config.enabled is False
        assert config.otlp_endpoint == "http://custom:4318"
        assert config.otlp_protocol == "http/protobuf"
        assert config.service_name == "my-service"
```

#### test_opentelemetry_propagation.py

```python
"""Tests for W3C Trace Context propagation."""

from __future__ import annotations

import pytest

from debug_toolbar.extras.opentelemetry.propagation import (
    extract_trace_context,
    inject_trace_context,
    parse_traceparent,
    format_trace_id,
    format_span_id,
)


class TestPropagation:
    """Tests for trace context propagation."""

    def test_parse_traceparent_valid(self) -> None:
        """Should parse valid traceparent header."""
        traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        result = parse_traceparent(traceparent)

        assert result is not None
        assert result["version"] == "00"
        assert result["trace_id"] == "0af7651916cd43dd8448eb211c80319c"
        assert result["parent_id"] == "b7ad6b7169203331"
        assert result["trace_flags"] == "01"

    def test_parse_traceparent_invalid(self) -> None:
        """Should return None for invalid traceparent."""
        assert parse_traceparent("invalid") is None
        assert parse_traceparent("") is None

    def test_format_trace_id_from_int(self) -> None:
        """Should format trace ID from integer."""
        trace_id = 123456789
        result = format_trace_id(trace_id)
        assert len(result) == 32
        assert result == f"{trace_id:032x}"

    def test_format_trace_id_from_str(self) -> None:
        """Should format trace ID from string."""
        trace_id = "abc123"
        result = format_trace_id(trace_id)
        assert len(result) == 32
        assert result.endswith("abc123")

    def test_format_span_id_from_int(self) -> None:
        """Should format span ID from integer."""
        span_id = 987654321
        result = format_span_id(span_id)
        assert len(result) == 16
        assert result == f"{span_id:016x}"
```

### Integration Tests

#### test_jaeger_integration.py

```python
"""Integration tests with Jaeger backend."""

from __future__ import annotations

import pytest
import httpx

from debug_toolbar.extras.opentelemetry.config import OpenTelemetryConfig
from debug_toolbar.extras.opentelemetry.exporter import ToolbarSpanExporter

pytestmark = pytest.mark.integration


@pytest.fixture
def jaeger_endpoint() -> str:
    """Jaeger OTLP endpoint (requires running Jaeger)."""
    return "http://localhost:4317"


@pytest.fixture
def jaeger_api_url() -> str:
    """Jaeger query API URL."""
    return "http://localhost:16686/api"


class TestJaegerIntegration:
    """Integration tests with Jaeger."""

    @pytest.mark.asyncio
    async def test_export_to_jaeger(
        self,
        jaeger_endpoint: str,
        jaeger_api_url: str,
    ) -> None:
        """Should export traces to Jaeger successfully."""
        # This test requires Jaeger running locally
        # Skip if Jaeger not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{jaeger_api_url}/services")
                response.raise_for_status()
        except Exception:
            pytest.skip("Jaeger not available")

        # Create exporter and export test span
        exporter = ToolbarSpanExporter(
            endpoint=jaeger_endpoint,
            protocol="grpc",
        )

        # Create test span (simplified)
        # In real test, create actual OpenTelemetry span

        # Verify export succeeded
        # Query Jaeger API to verify trace
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{jaeger_api_url}/traces",
                params={"service": "debug-toolbar"},
            )
            assert response.status_code == 200
```

### Test Coverage Goals

| Module | Target Coverage |
|--------|-----------------|
| config.py | 95% |
| exporter.py | 90% |
| span_processor.py | 95% |
| propagation.py | 95% |
| converter.py | 90% |
| panel.py | 90% |
| utils.py | 95% |

**Overall Target**: 90%+

---

## Configuration Examples

### Basic Configuration (Local Development)

```python
from debug_toolbar import DebugToolbarConfig
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig, OpenTelemetryPanel

# Enable OpenTelemetry with defaults (localhost Jaeger)
otel_config = OpenTelemetryConfig()

toolbar_config = DebugToolbarConfig(
    extra_panels=[
        OpenTelemetryPanel(config=otel_config),
    ],
)
```

### Production Configuration (Custom Endpoint)

```python
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig, OpenTelemetryPanel

# Export to production OTLP collector
otel_config = OpenTelemetryConfig(
    enabled=True,
    otlp_endpoint="https://otel-collector.example.com:4317",
    otlp_protocol="grpc",
    otlp_headers={
        "authorization": "Bearer <token>",
    },
    service_name="my-api",
    service_version="2.0.0",
    service_namespace="production",
)

toolbar_config = DebugToolbarConfig(
    extra_panels=[
        OpenTelemetryPanel(config=otel_config),
    ],
)
```

### HTTP Protocol Configuration

```python
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig

# Use HTTP protocol instead of gRPC
otel_config = OpenTelemetryConfig(
    otlp_endpoint="http://localhost:4318/v1/traces",
    otlp_protocol="http/protobuf",
)
```

### Environment Variable Configuration

```bash
# Set via environment variables
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_EXPORTER_OTLP_HEADERS="authorization=Bearer token123"
```

```python
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig

# Environment variables are automatically loaded
otel_config = OpenTelemetryConfig()
```

### Disable OpenTelemetry

```python
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig

# Disable OpenTelemetry (no export)
otel_config = OpenTelemetryConfig(enabled=False)
```

---

## Implementation Checkpoints

### Phase 1: Foundation (Checkpoints 1-4)

- [ ] **Checkpoint 1**: Create `config.py` with `OpenTelemetryConfig`
  - Dataclass with all configuration options
  - Environment variable loading
  - Unit tests (95% coverage)

- [ ] **Checkpoint 2**: Create `propagation.py` with trace context utilities
  - `extract_trace_context()` function
  - `inject_trace_context()` function
  - `parse_traceparent()` function
  - Formatting utilities
  - Unit tests (95% coverage)

- [ ] **Checkpoint 3**: Create `exporter.py` with `ToolbarSpanExporter`
  - Support gRPC protocol
  - Support HTTP protocol
  - Error handling and logging
  - Unit tests (90% coverage)

- [ ] **Checkpoint 4**: Create `span_processor.py` with `ToolbarSpanProcessor`
  - Implement `SpanProcessor` interface
  - Span capture logic
  - Start/stop lifecycle
  - Unit tests (95% coverage)

### Phase 2: Conversion (Checkpoints 5-6)

- [ ] **Checkpoint 5**: Create `converter.py` with `PanelDataConverter`
  - Convert TimerPanel to root span
  - Convert SQLAlchemyPanel to database spans
  - Unit tests (90% coverage)

- [ ] **Checkpoint 6**: Extend `converter.py` with additional conversions
  - Convert ProfilingPanel to function spans
  - Convert LoggingPanel to span events
  - Convert TemplatePanel to template spans
  - Unit tests (90% coverage)

### Phase 3: Panel (Checkpoints 7-8)

- [ ] **Checkpoint 7**: Create `panel.py` with `OpenTelemetryPanel`
  - Panel class with lifecycle hooks
  - Span formatting for display
  - Link generation (Jaeger, Zipkin)
  - Unit tests (90% coverage)

- [ ] **Checkpoint 8**: Create panel template
  - Waterfall visualization
  - Span details display
  - Trace context display
  - External links

### Phase 4: Integration (Checkpoints 9-10)

- [ ] **Checkpoint 9**: Jaeger integration testing
  - Docker Compose for Jaeger
  - Export test traces
  - Query API verification
  - UI link validation
  - Integration tests

- [ ] **Checkpoint 10**: Zipkin integration testing
  - Docker Compose for Zipkin
  - Export test traces
  - Query API verification
  - UI link validation
  - Integration tests

### Phase 5: Polish (Checkpoints 11-12)

- [ ] **Checkpoint 11**: Documentation
  - Installation instructions
  - Configuration guide
  - Examples (Jaeger, Zipkin, Datadog, etc.)
  - Troubleshooting guide
  - API reference

- [ ] **Checkpoint 12**: Final review and quality gates
  - All tests passing
  - 90%+ coverage achieved
  - Code review
  - Pattern extraction
  - Update pattern library

---

## Risk Mitigation

### Technical Risks

1. **OpenTelemetry SDK Complexity**
   - **Risk**: SDK may be difficult to integrate correctly
   - **Mitigation**: Study existing examples, use official SDK patterns
   - **Fallback**: Simplify to basic span export first, iterate

2. **Performance Overhead**
   - **Risk**: Span creation/export may add latency
   - **Mitigation**: Async export, batch processing, configurable
   - **Fallback**: Allow disabling OpenTelemetry completely

3. **OTLP Endpoint Reliability**
   - **Risk**: Export failures should not break requests
   - **Mitigation**: Error handling, retry logic, circuit breaker
   - **Fallback**: Log errors, continue request processing

4. **Version Compatibility**
   - **Risk**: OpenTelemetry SDK may have breaking changes
   - **Mitigation**: Pin minimum version (>=1.20.0), test across versions
   - **Fallback**: Document supported versions

### Integration Risks

1. **Jaeger/Zipkin Availability**
   - **Risk**: Integration tests require running backends
   - **Mitigation**: Docker Compose, skip if unavailable
   - **Fallback**: Mock integration tests

2. **Protocol Compatibility**
   - **Risk**: gRPC vs HTTP protocol differences
   - **Mitigation**: Test both protocols, clear documentation
   - **Fallback**: Recommend gRPC as default

---

## Success Metrics

### Quantitative

1. **Code Coverage**: 90%+ across all OpenTelemetry modules
2. **Test Count**: 50+ unit tests, 10+ integration tests
3. **Performance**: <5ms overhead with OpenTelemetry enabled
4. **Export Success Rate**: >95% under normal conditions

### Qualitative

1. **Developer Experience**: Easy configuration, clear error messages
2. **Documentation Quality**: Complete examples for common backends
3. **Pattern Compliance**: Follows all debug-toolbar patterns
4. **Community Feedback**: Positive reception from early adopters

---

## Future Enhancements

### Phase 2 (Post-MVP)

1. **Metrics Export**
   - Export panel metrics as OpenTelemetry metrics
   - Counter, Histogram, Gauge support
   - Metrics visualization in panel

2. **Logs Export**
   - Export LoggingPanel to OpenTelemetry logs
   - Correlation with traces

3. **Custom Propagators**
   - Support for B3, AWS X-Ray, Jaeger propagators
   - Composite propagator configuration

4. **Advanced Features**
   - Custom sampling strategies
   - Span links for async operations
   - Baggage propagation

5. **Backend-Specific Optimizations**
   - Jaeger-specific attributes
   - Datadog-specific attributes
   - New Relic-specific attributes

---

## Appendix

### Research Sources

- [OpenTelemetry Python Docs](https://opentelemetry-python.readthedocs.io/)
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Uptrace OpenTelemetry Python Guide](https://uptrace.dev/get/opentelemetry-python/propagation)
- [Last9 OpenTelemetry Best Practices](https://last9.io/blog/opentelemetry-context-propagation/)
- [Dash0 OTLP HTTP Exporter Guide](https://www.dash0.com/guides/opentelemetry-otlp-http-exporter)

### OpenTelemetry Semantic Conventions

**HTTP Spans**:
- `http.method`: HTTP request method
- `http.url`: Full HTTP request URL
- `http.status_code`: HTTP response status code
- `http.route`: Matched route (e.g., `/api/users/{id}`)
- `http.target`: Request target (path + query)

**Database Spans**:
- `db.system`: Database system (postgresql, mysql, sqlite)
- `db.statement`: SQL statement
- `db.operation`: Operation name (SELECT, INSERT, etc.)
- `db.name`: Database name

**Span Kinds**:
- `INTERNAL`: Internal operation
- `SERVER`: Incoming request
- `CLIENT`: Outgoing request
- `PRODUCER`: Message producer
- `CONSUMER`: Message consumer

### Glossary

- **OTLP**: OpenTelemetry Protocol (wire protocol for telemetry data)
- **Span**: Unit of work in a trace with timing and metadata
- **Trace**: Collection of spans representing a request through system
- **Trace Context**: Trace ID and span ID propagated across services
- **W3C Trace Context**: Standard for trace context propagation via HTTP headers
- **Propagator**: Component that extracts/injects trace context
- **Exporter**: Component that sends telemetry to backend
- **Processor**: Component that processes spans (batching, filtering, etc.)
- **Resource**: Entity producing telemetry (service name, version, etc.)

---

**End of PRD**
