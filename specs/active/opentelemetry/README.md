# OpenTelemetry Integration Workspace

**Status**: PRD Complete - Ready for Implementation
**Created**: 2025-11-29
**Priority**: P2 (Enterprise Appeal)
**Complexity**: High (12 checkpoints)

---

## Quick Start

### Read First
1. **PRD**: `prd.md` (5,690 words) - Complete specification
2. **Research**: `research/plan.md` (1,233 words) - Research findings
3. **Recovery**: `RECOVERY.md` - Session recovery guide

### Implementation
```bash
# Read the PRD
cat prd.md

# Start implementation
git checkout -b feature/opentelemetry-integration

# Create first module (Checkpoint 1)
mkdir -p src/debug_toolbar/extras/opentelemetry
# Follow PRD Technical Approach section
```

---

## Workspace Structure

```
specs/active/opentelemetry/
├── README.md              # This file
├── prd.md                 # Complete PRD (5,690 words)
├── RECOVERY.md            # Recovery guide
├── research/
│   └── plan.md           # Research plan (1,233 words)
└── tmp/                  # For new patterns during implementation
```

---

## Document Overview

### prd.md (5,690 words)

**Sections**:
1. Metadata (complexity, checkpoints, effort)
2. Intelligence Context (pattern analysis, research)
3. Problem Statement (why OpenTelemetry)
4. Goals and Non-Goals
5. Acceptance Criteria (functional and non-functional)
6. Technical Approach (architecture, modules, code examples)
7. Files to Create/Modify (8-10 new files)
8. Testing Strategy (90%+ coverage)
9. Configuration Examples
10. Implementation Checkpoints (12 checkpoints)
11. Risk Mitigation
12. Success Metrics
13. Future Enhancements
14. Appendix (research sources, glossary)

**Key Highlights**:
- Complete architecture diagrams
- Code examples for all modules
- Test examples and patterns
- Configuration examples
- Integration testing strategy (Jaeger, Zipkin)

### research/plan.md (1,233 words)

**Sections**:
1. Pattern Analysis (SQLAlchemyPanel, LoggingPanel, ProfilingPanel)
2. OpenTelemetry Research (SDK, OTLP, W3C Trace Context)
3. Architecture Design
4. Data Conversion Strategy
5. Testing Strategy
6. Similar Implementations
7. Dependencies

**Key Findings**:
- OTLP protocols (gRPC vs HTTP)
- W3C Trace Context format
- Span data structure
- Best practices from OpenTelemetry community
- Jaeger/Zipkin integration details

### RECOVERY.md

**Purpose**: Session recovery and handoff guide

**Contents**:
- Current phase and completed work
- How to resume work
- Checkpoint progress tracking
- Common issues and solutions
- Quick reference commands
- Next agent handoff instructions

---

## Key Features

### What This Integration Does

1. **OTLP Export**: Exports debug toolbar data to OTLP endpoints (gRPC/HTTP)
2. **Trace Context Propagation**: W3C Trace Context header support
3. **Span Visualization**: Waterfall view of spans in debug panel
4. **Panel Data Conversion**: Converts timer, SQL, profiling data to spans
5. **Jaeger Integration**: Export to Jaeger, link to Jaeger UI
6. **Zipkin Integration**: Export to Zipkin, link to Zipkin UI
7. **Flexible Configuration**: Environment variables, custom endpoints

### What Success Looks Like

- 90%+ test coverage
- Working Jaeger integration
- Working Zipkin integration
- W3C Trace Context propagation
- OTLP export (gRPC and HTTP)
- Clear documentation and examples

---

## Implementation Checkpoints

### Phase 1: Foundation (4 checkpoints)
1. ✅ Create `config.py` with `OpenTelemetryConfig`
2. ✅ Create `propagation.py` with trace context utilities
3. ✅ Create `exporter.py` with `ToolbarSpanExporter`
4. ✅ Create `span_processor.py` with `ToolbarSpanProcessor`

### Phase 2: Conversion (2 checkpoints)
5. ✅ Create `converter.py` (Timer, SQL panels)
6. ✅ Extend `converter.py` (Profiling, Logging, Template panels)

### Phase 3: Panel (2 checkpoints)
7. ✅ Create `panel.py` with `OpenTelemetryPanel`
8. ✅ Create panel template (waterfall, details)

### Phase 4: Integration (2 checkpoints)
9. ✅ Jaeger integration testing
10. ✅ Zipkin integration testing

### Phase 5: Polish (2 checkpoints)
11. ✅ Documentation (installation, config, examples)
12. ✅ Final review and pattern extraction

**Total**: 12 checkpoints

---

## Files to Create

### Source Files (8 files)
```
src/debug_toolbar/extras/opentelemetry/
├── __init__.py           # Public exports
├── config.py             # OpenTelemetryConfig
├── exporter.py           # ToolbarSpanExporter
├── span_processor.py     # ToolbarSpanProcessor
├── propagation.py        # W3C Trace Context utilities
├── converter.py          # Panel data → Span conversion
├── panel.py              # OpenTelemetryPanel
└── utils.py              # Utilities
```

### Test Files (8 files)
```
tests/
├── unit/
│   ├── test_opentelemetry_config.py
│   ├── test_opentelemetry_exporter.py
│   ├── test_opentelemetry_span_processor.py
│   ├── test_opentelemetry_propagation.py
│   ├── test_opentelemetry_converter.py
│   └── test_opentelemetry_panel.py
└── integration/
    ├── test_jaeger_integration.py
    └── test_zipkin_integration.py
```

---

## Research Summary

### Pattern Analysis

**Studied 3 similar implementations**:
1. **SQLAlchemyPanel** (588 lines): External system integration, event hooks
2. **LoggingPanel** (96 lines): Handler-based data collection
3. **ProfilingPanel** (250+ lines): Multiple backend support

**Key Patterns Identified**:
- Panel ABC (ClassVar, generate_stats, lifecycle hooks)
- Extras module (optional dependencies)
- Graceful degradation (check availability)
- Global tracker pattern (request-scoped data)
- Async-first design

### OpenTelemetry Research

**Core Components**:
- TracerProvider, SpanProcessor, SpanExporter
- Resource (service metadata)
- Span (unit of work with timing)
- Trace Context (propagation across services)

**OTLP Protocols**:
- gRPC: `http://localhost:4317` (default)
- HTTP: `http://localhost:4318/v1/traces`

**W3C Trace Context**:
- Header: `traceparent: 00-{trace_id}-{span_id}-{flags}`
- Format: 32 hex trace ID, 16 hex span ID

**Best Practices**:
- Use OpenTelemetry Collector in production
- Batch processing (512 spans or 5s)
- Set service.name in resource
- Don't fail requests on export error

---

## Configuration Examples

### Local Development (Jaeger)
```python
from debug_toolbar.extras.opentelemetry import OpenTelemetryConfig, OpenTelemetryPanel

otel_config = OpenTelemetryConfig()  # Defaults to localhost:4317

toolbar_config = DebugToolbarConfig(
    extra_panels=[OpenTelemetryPanel(config=otel_config)],
)
```

### Production (Custom Endpoint)
```python
otel_config = OpenTelemetryConfig(
    otlp_endpoint="https://otel-collector.example.com:4317",
    otlp_protocol="grpc",
    otlp_headers={"authorization": "Bearer <token>"},
    service_name="my-api",
    service_version="2.0.0",
)
```

### Environment Variables
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
```

---

## Testing

### Run All Tests
```bash
make test
```

### Run Unit Tests Only
```bash
make test-fast
```

### Run with Coverage
```bash
make test-cov
```

### Run Integration Tests (Jaeger)
```bash
# Start Jaeger
docker run -p 4317:4317 -p 16686:16686 jaegertracing/all-in-one:latest

# Run tests
pytest tests/integration/test_jaeger_integration.py
```

### Run Integration Tests (Zipkin)
```bash
# Start Zipkin
docker run -p 9411:9411 openzipkin/zipkin:latest

# Run tests
pytest tests/integration/test_zipkin_integration.py
```

---

## Resources

### Internal Documentation
- `/home/cody/code/litestar/debug-toolbar/CLAUDE.md` - Project guidelines
- `/home/cody/code/litestar/debug-toolbar/specs/guides/patterns/README.md` - Pattern library
- `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/core/panel.py` - Panel ABC

### OpenTelemetry Documentation
- [OpenTelemetry Python Docs](https://opentelemetry-python.readthedocs.io/)
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

### Backend Documentation
- [Jaeger](https://www.jaegertracing.io/docs/)
- [Zipkin](https://zipkin.io/pages/documentation.html)

---

## Next Steps

### For Implementation
1. Read `prd.md` completely
2. Create branch: `git checkout -b feature/opentelemetry-integration`
3. Start Checkpoint 1: Create `config.py`
4. Follow Technical Approach section in PRD
5. Write tests for each module (90%+ coverage)
6. Mark checkpoints as completed in RECOVERY.md

### For Testing
1. Read "Testing Strategy" section in `prd.md`
2. Write unit tests (90%+ coverage target)
3. Set up Docker Compose for Jaeger/Zipkin
4. Write integration tests
5. Verify all acceptance criteria

### For Review
1. Read `prd.md` Acceptance Criteria
2. Verify pattern compliance (Panel ABC, extras structure)
3. Check test coverage (90%+)
4. Extract new patterns to pattern library
5. Update documentation

---

## Contact

**Workspace Created By**: AI Agent (PRD Phase)
**Date**: 2025-11-29
**Workspace Location**: `/home/cody/code/litestar/debug-toolbar/specs/active/opentelemetry/`

For questions or issues, refer to:
1. RECOVERY.md (session recovery)
2. PRD.md (complete specification)
3. research/plan.md (research findings)

---

**End of README**
