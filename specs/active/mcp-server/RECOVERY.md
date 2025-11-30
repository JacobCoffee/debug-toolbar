# Session Recovery Guide: MCP Server Integration

**Feature**: MCP Server Integration
**Slug**: `mcp-server`
**Status**: PRD Complete, Ready for Implementation
**Last Updated**: 2025-11-29

---

## Quick Context

### What is This Feature?

An MCP (Model Context Protocol) server that exposes debug-toolbar data to AI coding assistants like Claude Code and Cursor. This enables developers to debug performance issues, analyze queries, and get AI-powered optimization suggestions without leaving their code editor.

### Why This Matters

- **Parity**: Sentry Spotlight has MCP integration (launched Aug 2025)
- **Differentiation**: We focus on performance (N+1 queries, slow queries, profiling) vs Sentry's error focus
- **Developer Experience**: Zero context-switching between editor and browser
- **AI Integration**: Claude Code can directly query request history, analyze slow queries, suggest optimizations

### Current State

- [x] PRD completed (5,847 words)
- [x] Research plan completed (2,487 words)
- [x] Codebase patterns analyzed (4 similar implementations)
- [x] MCP SDK research completed
- [x] Sentry competitive analysis completed
- [ ] Implementation started
- [ ] Tests written
- [ ] Documentation written

---

## Workspace Structure

```
specs/active/mcp-server/
├── prd.md                    # Full PRD (this is the source of truth)
├── research/
│   └── plan.md              # Research findings and decisions
├── tmp/
│   └── new-patterns.md      # Patterns discovered during implementation (create during work)
└── RECOVERY.md              # This file (session recovery guide)
```

---

## Key Decisions Made

### 1. MCP SDK Choice

**Decision**: Use official `mcp` Python SDK (v1.22.0+), not FastMCP

**Rationale**:
- Official Anthropic SDK with full protocol support
- More stable than third-party alternatives
- Better documentation and community support
- Full transport support (stdio, HTTP, SSE)

### 2. Storage Integration (v1.0)

**Decision**: Use HTTP API approach (MCP server calls existing REST endpoints)

**Alternatives Considered**:
- Shared file: Stale data, race conditions
- Redis backend: Best for production, but adds dependency

**Rationale**:
- Works immediately without new dependencies
- Leverages existing `/api/requests` endpoints
- Acceptable latency for local development (~5-10ms)
- Can migrate to Redis in v1.1 if needed

### 3. Transport Priority

**Decision**: Stdio (v1.0), HTTP/SSE (v1.1)

**Rationale**:
- Stdio is simpler, zero-config for local development
- Native support in Claude Code and Cursor
- No authentication needed for local use
- HTTP/SSE deferred for team debugging features

### 4. Tool/Resource Split

**Tools** (7 total):
- `get_request_history`, `get_request_details`
- `get_slow_queries`, `get_n_plus_one_issues`
- `get_performance_summary`, `get_error_context`
- `explain_query`

**Resources** (5 total):
- `debug://current-request`, `debug://alerts`
- `debug://request/{id}`, `debug://queries/slow`
- `debug://queries/n-plus-one`

**Rationale**: Tools for parametric queries, Resources for simple data retrieval

---

## Implementation Entry Points

### If Starting Implementation

1. **Read PRD First**: `/home/cody/code/litestar/debug-toolbar/specs/active/mcp-server/prd.md`
   - Section "Technical Approach" has code examples
   - Section "Files to Create/Modify" lists all work

2. **Review Research**: `/home/cody/code/litestar/debug-toolbar/specs/active/mcp-server/research/plan.md`
   - Pattern analysis explains reuse opportunities
   - Storage integration strategy is critical

3. **Create Module Structure**:
```bash
mkdir -p src/debug_toolbar/mcp
touch src/debug_toolbar/mcp/{__init__.py,__main__.py,server.py,tools.py,resources.py,config.py}
```

4. **Start with Server Core**: Implement `server.py` first
   - Creates MCP Server instance
   - Registers tools and resources
   - Handles stdio transport

5. **Then Tools**: Implement `tools.py`
   - Start with `get_request_history` (simplest)
   - Use HTTP client to call `/_debug_toolbar/api/requests`
   - Add error handling

6. **Then Resources**: Implement `resources.py`
   - Start with `debug://current-request`
   - Return JSON from storage

7. **CLI Last**: Implement `__main__.py`
   - Argument parsing
   - Logging setup
   - Server launch

### If Resuming Implementation

**Check what exists**:
```bash
ls -la src/debug_toolbar/mcp/
```

**If server.py exists**: Continue with tool implementation
**If tools.py exists**: Add remaining tools or start resources
**If all source complete**: Focus on tests

### If Writing Tests

**Test Structure**:
```
tests/mcp/
├── conftest.py              # Fixtures (storage, mcp_server)
├── test_server.py           # Server lifecycle, transport tests
├── test_tools.py            # Each tool has 2-3 tests
├── test_resources.py        # Each resource has 2-3 tests
└── test_integration.py      # Claude Code config validation
```

**Coverage Target**: 90%+

**Key Fixtures Needed** (in `conftest.py`):
- `storage`: Empty ToolbarStorage
- `storage_with_requests`: Storage with 10 sample requests
- `storage_with_n_plus_one`: Storage with N+1 query pattern
- `mcp_server`: DebugToolbarMCPServer instance
- `mock_http_client`: Mock httpx client for API calls

### If Writing Documentation

**Priority Order**:
1. `docs/mcp-server.md` - Main guide (installation, setup, usage)
2. `docs/integrations/claude-code.md` - Claude Code config with screenshots
3. `docs/integrations/cursor.md` - Cursor config
4. README.md updates - Add MCP section with quick start
5. Inline docstrings - All public functions

**Documentation Checklist**:
- [ ] All 7 tools documented with examples
- [ ] All 5 resources documented with sample outputs
- [ ] Claude Code configuration tested
- [ ] Cursor configuration tested
- [ ] Example prompts provided (e.g., "Show me slow queries")
- [ ] Troubleshooting section

---

## Critical Code References

### Reuse These Implementations

1. **SQLAlchemy Panel** (`src/debug_toolbar/extras/advanced_alchemy/panel.py`):
   - `ExplainExecutor.execute_explain()` - For `explain_query` tool
   - `_detect_n_plus_one()` - For `get_n_plus_one_issues` tool
   - `SQLNormalizer.normalize()` - Already handles pattern detection

2. **ToolbarStorage** (`src/debug_toolbar/core/storage.py`):
   - `get_all()` - For `get_request_history`
   - `get(request_id)` - For `get_request_details`, resources
   - `store_from_context()` - Understand data structure

3. **API Routes** (`src/debug_toolbar/litestar/routes/handlers.py`):
   - `/api/requests` endpoint logic - Mirror in tools
   - `/api/explain` endpoint - Reuse in `explain_query` tool
   - Error handling patterns - Apply to MCP errors

4. **Config** (`src/debug_toolbar/core/config.py`):
   - Extend with MCP fields:
     ```python
     mcp_enabled: bool = True
     mcp_transport: Literal["stdio", "http"] = "stdio"
     mcp_slow_query_threshold_ms: float = 100.0
     ```

### Follow These Patterns

1. **Type Hints**: PEP 604 (`T | None` not `Optional[T]`)
2. **Future Annotations**: `from __future__ import annotations` at top
3. **Docstrings**: Google style with Args/Returns
4. **Async**: Use `async def` for I/O operations
5. **Error Handling**: Descriptive messages, proper exception types
6. **Logging**: To stderr (not stdout) in stdio mode

---

## Common Pitfalls

### 1. Stdio Logging

**Problem**: Logging to stdout breaks JSON-RPC communication

**Solution**: Always log to stderr
```python
logging.basicConfig(stream=sys.stderr)
```

### 2. Storage Access

**Problem**: MCP server can't access in-memory storage from separate process

**Solution**: Use HTTP API client
```python
async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8000/_debug_toolbar/api/requests")
```

### 3. Tool Schema Validation

**Problem**: MCP SDK is strict about JSON Schema format

**Solution**: Test with real Claude Code, not just unit tests
```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "default": 10
    }
  }
}
```

### 4. Resource URI Format

**Problem**: Invalid URI format (`debug:/current-request` missing second slash)

**Solution**: Always use `debug://` prefix
```python
uri = "debug://current-request"  # Correct
uri = "debug:/current-request"   # Wrong
```

### 5. EXPLAIN Injection

**Problem**: SQL injection via `explain_query` tool

**Solution**: Use parameterized queries
```python
from sqlalchemy import text
explain_sql = text(f"EXPLAIN {sql}")
result = await conn.execute(explain_sql, parameters)
```

---

## Testing Checklist

### Unit Tests (90%+ coverage)

- [ ] `test_server.py`
  - [ ] Server initialization
  - [ ] Tool registration
  - [ ] Resource registration
  - [ ] Stdio transport setup

- [ ] `test_tools.py`
  - [ ] `get_request_history` - valid input, empty storage, limit validation
  - [ ] `get_request_details` - found, not found, invalid UUID
  - [ ] `get_slow_queries` - threshold filtering, limit, no slow queries
  - [ ] `get_n_plus_one_issues` - pattern detection, min_count threshold
  - [ ] `get_performance_summary` - timing aggregation, missing request
  - [ ] `get_error_context` - error extraction, no errors
  - [ ] `explain_query` - PostgreSQL, SQLite, unsupported dialect, injection attempt

- [ ] `test_resources.py`
  - [ ] `debug://current-request` - present, empty storage
  - [ ] `debug://alerts` - with alerts, no alerts
  - [ ] `debug://request/{id}` - found, not found
  - [ ] `debug://queries/slow` - filtered list
  - [ ] `debug://queries/n-plus-one` - patterns list

### Integration Tests

- [ ] Claude Code config validation (JSON syntax)
- [ ] Cursor config validation
- [ ] Stdio transport communication (JSON-RPC compliance)
- [ ] HTTP API client integration

### Performance Tests

- [ ] Tool latency < 50ms (p95)
- [ ] Resource latency < 20ms (p95)
- [ ] Concurrent requests (10+ simultaneous)

---

## Dependencies

### Required

- `mcp>=1.22.0` - MCP Python SDK (add to `pyproject.toml`)
- `httpx` - Async HTTP client for API calls (if not already present)

### Optional (Future)

- `redis>=5.0` - For v1.1 storage backend
- `fastapi` - For HTTP/SSE transport (v1.1)

---

## Configuration Examples

### Claude Code (`.clauderc`)

```json
{
  "mcpServers": {
    "debug-toolbar": {
      "command": "python",
      "args": ["-m", "debug_toolbar.mcp"],
      "env": {
        "DEBUG_TOOLBAR_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "servers": {
    "debug-toolbar": {
      "command": "python -m debug_toolbar.mcp",
      "description": "Litestar Debug Toolbar MCP Server"
    }
  }
}
```

---

## Next Steps

### Immediate Actions

1. **Add MCP dependency**:
```bash
# In pyproject.toml
mcp = ">=1.22.0"
```

2. **Create module structure**:
```bash
mkdir -p src/debug_toolbar/mcp tests/mcp
```

3. **Implement server core** (`server.py`)
4. **Implement first tool** (`get_request_history`)
5. **Write tests** for first tool
6. **Iterate** through remaining tools/resources

### Verification Steps

After each milestone:
1. Run `make test` - All tests pass
2. Run `make lint` - No linting errors
3. Run `make type-check` - Type hints valid
4. Manual test with Claude Code (if applicable)

---

## Useful Commands

```bash
# Run MCP server (after implementation)
python -m debug_toolbar.mcp

# Run MCP server in debug mode
python -m debug_toolbar.mcp --debug

# Run tests for MCP module
pytest tests/mcp/ -v

# Run tests with coverage
pytest tests/mcp/ --cov=src/debug_toolbar/mcp --cov-report=term-missing

# Test specific tool
pytest tests/mcp/test_tools.py::test_get_slow_queries -v

# Type check MCP module
ty src/debug_toolbar/mcp/
```

---

## Resources

### Documentation

- PRD: `/home/cody/code/litestar/debug-toolbar/specs/active/mcp-server/prd.md`
- Research: `/home/cody/code/litestar/debug-toolbar/specs/active/mcp-server/research/plan.md`
- Patterns: `/home/cody/code/litestar/debug-toolbar/specs/guides/patterns/README.md`

### External

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.io/docs/sdk)
- [Building MCP Servers](https://scrapfly.io/blog/posts/how-to-build-an-mcp-server-in-python-a-complete-guide)

### Codebase

- ToolbarStorage: `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/core/storage.py`
- SQLAlchemy Panel: `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/extras/advanced_alchemy/panel.py`
- API Routes: `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/litestar/routes/handlers.py`

---

## Success Criteria Reminder

Implementation succeeds when:

1. [ ] Claude Code can call all 7 tools via MCP
2. [ ] Cursor can access all 5 resources
3. [ ] `python -m debug_toolbar.mcp` starts server successfully
4. [ ] All tests pass with 90%+ coverage
5. [ ] Documentation complete (MCP guide + integration guides)
6. [ ] Tool latency < 50ms (p95)
7. [ ] No P0 bugs in manual testing
8. [ ] Pattern compliance verified

---

**Last Update**: 2025-11-29
**Next Reviewer**: Review PRD and research plan before starting implementation
