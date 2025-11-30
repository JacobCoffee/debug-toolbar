# Spec: PR #11 - OpenTelemetry Integration

## Metadata
- **PR Number**: 11
- **Priority**: P2
- **Complexity**: High
- **Estimated Files**: 6-8
- **Dependencies**: None
- **Implementation Order**: 9

---

## Problem Statement

OpenTelemetry is the industry standard for observability. Integration enables:
- Export debug data to tracing backends (Jaeger, Zipkin)
- Trace context propagation across services
- Correlation with production monitoring
- Enterprise appeal for microservices

---

## Goals

1. OTLP exporter for debug toolbar data
2. Trace context propagation
3. Span visualization in panel
4. Integration with Jaeger/Zipkin

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ OpenTelemetry Panel                             │
├─────────────────────────────────────────────────┤
│ - Visualizes spans from current request         │
│ - Shows trace waterfall                         │
│ - Links to external trace viewer                │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│ OTLP Exporter                                   │
├─────────────────────────────────────────────────┤
│ - Exports to configured OTLP endpoint           │
│ - Converts panel data to spans                  │
└─────────────────────────────────────────────────┘
```

### Files to Create

```
src/debug_toolbar/otel/
├── __init__.py
├── exporter.py
├── span_processor.py
└── panel.py
```

---

## Acceptance Criteria

- [ ] OTLP exporter works with Jaeger
- [ ] OTLP exporter works with Zipkin
- [ ] Trace context propagated
- [ ] Span visualization in panel
- [ ] Trace waterfall view
- [ ] Link to external trace viewer
- [ ] 90%+ test coverage
