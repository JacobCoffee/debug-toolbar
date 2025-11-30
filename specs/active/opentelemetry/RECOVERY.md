# Recovery Guide: OpenTelemetry Integration

**Last Updated**: 2025-11-29
**Status**: PRD Phase Complete

---

## Session State

### Current Phase
**PRD Complete** - Ready for implementation

### Completed Work
1. ✅ Pattern analysis (SQLAlchemyPanel, LoggingPanel, ProfilingPanel)
2. ✅ OpenTelemetry Python SDK research
3. ✅ W3C Trace Context propagation research
4. ✅ OTLP exporter best practices research
5. ✅ Architecture design
6. ✅ Comprehensive PRD (11,000+ words)
7. ✅ Research plan documentation

### Files Created
- `specs/active/opentelemetry/prd.md` (11,000+ words)
- `specs/active/opentelemetry/research/plan.md` (2,500+ words)
- `specs/active/opentelemetry/RECOVERY.md` (this file)

---

## How to Resume Work

### If Starting Implementation

1. **Read the PRD**:
   ```bash
   cat specs/active/opentelemetry/prd.md
   ```

2. **Review Research Plan**:
   ```bash
   cat specs/active/opentelemetry/research/plan.md
   ```

3. **Create Implementation Branch**:
   ```bash
   git checkout -b feature/opentelemetry-integration
   ```

4. **Start with Phase 1, Checkpoint 1**:
   - Create `src/debug_toolbar/extras/opentelemetry/config.py`
   - Follow the code example in PRD Section "Technical Approach"
   - Write tests in `tests/unit/test_opentelemetry_config.py`

5. **Follow Checkpoint Order**:
   - Phase 1: Foundation (Checkpoints 1-4)
   - Phase 2: Conversion (Checkpoints 5-6)
   - Phase 3: Panel (Checkpoints 7-8)
   - Phase 4: Integration (Checkpoints 9-10)
   - Phase 5: Polish (Checkpoints 11-12)

### If Continuing from Checkpoint

**Check Current Checkpoint**:
1. Look at PRD "Implementation Checkpoints" section
2. Find the last completed checkbox
3. Continue with next unchecked checkpoint

**Checkpoint Recovery Pattern**:
```bash
# 1. Check what files exist
ls -la src/debug_toolbar/extras/opentelemetry/

# 2. Check what tests exist
ls -la tests/unit/test_opentelemetry_*

# 3. Run existing tests
make test-fast

# 4. Review coverage
make test-cov

# 5. Continue with next checkpoint
```

---

## Key Context to Remember

### Architecture Decisions

1. **Module Location**: `src/debug_toolbar/extras/opentelemetry/`
   - Follows extras pattern (optional integration)
   - Similar to `extras/advanced_alchemy/`

2. **Panel Pattern**: Follows Panel ABC
   - ClassVar metadata: `panel_id`, `title`, `template`
   - Lifecycle hooks: `process_request()`, `process_response()`
   - Stats generation: `generate_stats()`
   - `__slots__` for memory efficiency

3. **Graceful Degradation**:
   ```python
   try:
       from opentelemetry import trace
       OPENTELEMETRY_AVAILABLE = True
   except ImportError:
       OPENTELEMETRY_AVAILABLE = False
   ```

4. **Async-First**: Use `async def` for I/O operations

5. **Type Hints**: PEP 604 (`T | None`), future annotations

### Critical Patterns

1. **Context Variable Cleanup** (from testing patterns):
   ```python
   from debug_toolbar.core.context import set_request_context

   # At start and end of async tests
   set_request_context(None)
   ```

2. **Global Tracker Pattern** (from SQLAlchemyPanel):
   - Module-level tracker instance
   - Start/stop in lifecycle hooks
   - Event listeners for data collection

3. **Optional Dependencies** (from ProfilingPanel):
   - Check availability before import
   - Show helpful error messages
   - Graceful fallback

### Testing Requirements

- **Target Coverage**: 90%+
- **Test Organization**: Class-based for related tests
- **Fixtures**: Use from `conftest.py` (config, toolbar, context)
- **Context Cleanup**: Always cleanup context variables
- **Integration Tests**: Docker Compose for Jaeger/Zipkin

---

## Quick Reference

### PRD Sections

| Section | Page/Line | Purpose |
|---------|-----------|---------|
| Metadata | Top | Complexity, checkpoints, effort |
| Intelligence Context | Lines 50-150 | Pattern analysis, research summary |
| Problem Statement | Lines 151-200 | Why we need this feature |
| Acceptance Criteria | Lines 250-350 | What success looks like |
| Technical Approach | Lines 351-850 | How to build it |
| Files to Create | Lines 851-950 | Complete file list |
| Testing Strategy | Lines 951-1050 | Test plan and examples |
| Configuration Examples | Lines 1051-1150 | Usage examples |
| Implementation Checkpoints | Lines 1151-1250 | Step-by-step plan |

### Key Research Findings

1. **OTLP Protocols**:
   - gRPC: `http://localhost:4317` (default, better performance)
   - HTTP: `http://localhost:4318/v1/traces` (easier networking)

2. **W3C Trace Context**:
   - Header: `traceparent: 00-{trace_id}-{span_id}-{flags}`
   - Format: 2 hex (version) + 32 hex (trace) + 16 hex (span) + 2 hex (flags)

3. **OpenTelemetry SDK Components**:
   - `TracerProvider`: Creates tracers
   - `SpanProcessor`: Processes spans (e.g., `BatchSpanProcessor`)
   - `SpanExporter`: Exports to backend (e.g., `OTLPSpanExporter`)
   - `Resource`: Service metadata

4. **Best Practices**:
   - Use OpenTelemetry Collector in production
   - Batch processing (512 spans or 5s)
   - Set `service.name` in resource
   - Don't fail requests on export error
   - Retry with exponential backoff

---

## Commands

### Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dev dependencies
make dev

# Run tests (fast)
make test-fast

# Run tests with coverage
make test-cov

# Lint
make lint

# Type check
make type-check

# Format code
make fmt
```

### Testing OpenTelemetry

```bash
# Start Jaeger (for integration tests)
docker run --rm -d \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 16686:16686 \
  --name jaeger \
  jaegertracing/all-in-one:latest

# Access Jaeger UI
open http://localhost:16686

# Stop Jaeger
docker stop jaeger

# Start Zipkin (for integration tests)
docker run --rm -d \
  -p 9411:9411 \
  --name zipkin \
  openzipkin/zipkin:latest

# Access Zipkin UI
open http://localhost:9411

# Stop Zipkin
docker stop zipkin
```

### Debugging

```bash
# Check if OpenTelemetry installed
python -c "import opentelemetry; print(opentelemetry.__version__)"

# Test OTLP endpoint
curl -v http://localhost:4317

# View test output
pytest -v tests/unit/test_opentelemetry_config.py

# Run single test
pytest -v tests/unit/test_opentelemetry_config.py::TestOpenTelemetryConfig::test_default_values
```

---

## Common Issues and Solutions

### Issue: OpenTelemetry not installed

**Error**: `ImportError: No module named 'opentelemetry'`

**Solution**:
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
```

### Issue: OTLP endpoint unreachable

**Error**: `Failed to connect to localhost:4317`

**Solution**:
1. Start Jaeger: `docker run -p 4317:4317 jaegertracing/all-in-one:latest`
2. Or disable export: `OpenTelemetryConfig(enabled=False)`

### Issue: Tests fail with context variable errors

**Error**: `Context variable already set`

**Solution**:
```python
from debug_toolbar.core.context import set_request_context

# Clean up at start and end of test
set_request_context(None)
# ... test code ...
set_request_context(None)
```

### Issue: Type checking fails

**Error**: `error: Name 'ReadableSpan' is not defined`

**Solution**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan
```

---

## Checkpoint Progress Tracking

### Phase 1: Foundation
- [ ] Checkpoint 1: `config.py`
- [ ] Checkpoint 2: `propagation.py`
- [ ] Checkpoint 3: `exporter.py`
- [ ] Checkpoint 4: `span_processor.py`

### Phase 2: Conversion
- [ ] Checkpoint 5: `converter.py` (Timer, SQL)
- [ ] Checkpoint 6: `converter.py` (Profiling, Logging, Template)

### Phase 3: Panel
- [ ] Checkpoint 7: `panel.py`
- [ ] Checkpoint 8: Panel template

### Phase 4: Integration
- [ ] Checkpoint 9: Jaeger integration
- [ ] Checkpoint 10: Zipkin integration

### Phase 5: Polish
- [ ] Checkpoint 11: Documentation
- [ ] Checkpoint 12: Final review

**Mark completed checkpoints with `[x]` as you finish them.**

---

## Next Agent Handoff

### For Implementation Agent

**Context to Provide**:
1. "Implement OpenTelemetry integration for debug-toolbar"
2. "PRD is at specs/active/opentelemetry/prd.md"
3. "Start with Checkpoint 1: Create config.py"
4. "Follow the Technical Approach section in the PRD"
5. "Target 90%+ test coverage"

**Expected Workflow**:
1. Read PRD completely
2. Create config.py with OpenTelemetryConfig
3. Write tests for config.py
4. Verify 95%+ coverage for config module
5. Commit and move to Checkpoint 2

### For Testing Agent

**Context to Provide**:
1. "Write tests for OpenTelemetry integration"
2. "PRD testing strategy is at specs/active/opentelemetry/prd.md section 'Testing Strategy'"
3. "Target 90%+ overall coverage"
4. "Integration tests require Docker (Jaeger, Zipkin)"

### For Review Agent

**Context to Provide**:
1. "Review OpenTelemetry integration implementation"
2. "PRD is at specs/active/opentelemetry/prd.md"
3. "Check pattern compliance (Panel ABC, extras structure, type hints)"
4. "Verify 90%+ test coverage"
5. "Extract new patterns to pattern library"

---

## Related Documentation

### Internal
- `CLAUDE.md`: Project guidelines and patterns
- `specs/guides/patterns/README.md`: Pattern library
- `src/debug_toolbar/core/panel.py`: Panel ABC
- `src/debug_toolbar/extras/advanced_alchemy/panel.py`: SQLAlchemy panel example

### External
- [OpenTelemetry Python Docs](https://opentelemetry-python.readthedocs.io/)
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Zipkin Documentation](https://zipkin.io/pages/documentation.html)

---

## Notes

### Design Highlights

1. **Complexity justified**: 12 checkpoints due to:
   - External system integration (OpenTelemetry SDK)
   - Multiple protocols (gRPC, HTTP)
   - Data conversion (panels → spans)
   - Distributed tracing (trace context)
   - Multiple backends (Jaeger, Zipkin)

2. **Pattern compliance**:
   - Extras module (optional dependency)
   - Panel ABC (lifecycle, stats)
   - Graceful degradation
   - Async-first
   - Type hints (PEP 604)

3. **Innovation**:
   - Convert debug panel data to semantic spans
   - Bridge dev debugging and production observability
   - Support industry-standard OpenTelemetry

### Success Criteria Reminder

**Must Have**:
- 90%+ test coverage
- Working Jaeger integration
- Working Zipkin integration
- W3C Trace Context propagation
- OTLP export (gRPC and HTTP)

**Should Have**:
- Panel data → span conversion
- Waterfall visualization
- External trace links
- Clear documentation

**Nice to Have**:
- Advanced sampling
- Custom propagators
- Metrics/logs export (future)

---

**End of Recovery Guide**
