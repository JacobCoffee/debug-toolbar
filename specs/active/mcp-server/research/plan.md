# Research Plan: MCP Server Integration

**Feature**: MCP Server Integration
**Slug**: mcp-server
**Date**: 2025-11-29

---

## Research Objectives

1. Understand MCP protocol and Python SDK capabilities
2. Identify integration patterns from existing codebase
3. Analyze Sentry Spotlight MCP implementation for competitive insights
4. Design tool/resource architecture aligned with debug-toolbar patterns
5. Validate transport layer options (stdio, HTTP/SSE)

---

## Research Findings

### 1. MCP Protocol Analysis

**Sources**:
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Official Documentation](https://modelcontextprotocol.io/docs/sdk)
- [PyPI Package](https://pypi.org/project/mcp/)

**Key Findings**:

#### Protocol Overview
- **Version**: MCP 1.22.0 (latest as of Nov 2025)
- **Protocol**: JSON-RPC 2.0 over multiple transports
- **Primitives**: Tools, Resources, Prompts
- **Maintainer**: Anthropic, PBC (official)

#### Tools vs Resources
- **Tools**: Executable functions (like POST endpoints)
  - Input schema validation via JSON Schema
  - Return `TextContent` or `ImageContent`
  - Can have side effects
  - Example: `get_slow_queries(threshold_ms, limit)`

- **Resources**: Read-only data (like GET endpoints)
  - URI-based access (`debug://current-request`)
  - MIME type declaration
  - Should be cacheable when immutable
  - Example: `debug://request/a1b2c3d4`

#### Transport Options
1. **Stdio** (default, local)
   - JSON-RPC via stdin/stdout
   - Process launched by client (Claude Code, Cursor)
   - No authentication needed
   - Best for local development

2. **HTTP/SSE** (remote)
   - HTTP endpoints for JSON-RPC
   - Server-Sent Events for updates
   - Requires authentication (OAuth 2.1 recommended)
   - Best for team/remote debugging

#### SDK Features
- Server class for handling requests
- Type-safe with Pydantic models
- Built-in transport adapters
- Async/await support
- Structured logging support

**Decision**: Use official SDK (not FastMCP) for stability and full transport support.

---

### 2. Codebase Pattern Analysis

#### Pattern 1: API Routes (`src/debug_toolbar/litestar/routes/handlers.py`)

**Observations**:
- RESTful endpoints: `/api/requests`, `/api/requests/{id}`, `/api/explain`
- JSON responses with storage data
- Error handling with `NotFoundException`
- Input validation for request IDs, parameters

**Relevance to MCP**:
- MCP tools will mirror these endpoints
- `get_request_history` ≈ `GET /api/requests`
- `get_request_details` ≈ `GET /api/requests/{id}`
- `explain_query` ≈ `POST /api/explain`

**Reuse Opportunities**:
- Use existing API endpoints internally in MCP server (v1.0 approach)
- Share error handling patterns
- Reuse `_format_value()` for data rendering

#### Pattern 2: SQLAlchemy Panel (`src/debug_toolbar/extras/advanced_alchemy/panel.py`)

**Observations**:
- **SQLNormalizer**: Normalizes queries to detect patterns
  - `normalize()`: Replaces literals with placeholders
  - `get_pattern_hash()`: MD5 of normalized SQL
  - `capture_stack()`: Extracts call stack for origin tracking

- **ExplainExecutor**: Database-agnostic EXPLAIN
  - `supports_explain()`: Checks dialect support
  - `get_explain_sql()`: Generates EXPLAIN query
  - `execute_explain()`: Async execution with result parsing

- **QueryTracker**: Request-scoped query collection
  - Event listeners on `before_cursor_execute`, `after_cursor_execute`
  - Thread-safe query storage
  - Performance metrics (duration, count)

- **N+1 Detection**: `_detect_n_plus_one()`
  - Groups queries by `pattern_hash` and `origin_key`
  - Threshold-based flagging (default: 2+ similar queries)
  - Generates fix suggestions

**Relevance to MCP**:
- `get_slow_queries` tool uses `QueryTracker.queries` filtered by `duration_ms`
- `get_n_plus_one_issues` tool directly uses `_detect_n_plus_one()`
- `explain_query` tool delegates to `ExplainExecutor.execute_explain()`

**Reuse Opportunities**:
- Import and use `ExplainExecutor` directly
- Access `_detect_n_plus_one()` via panel stats
- No need to reimplement query analysis logic

#### Pattern 3: ToolbarStorage (`src/debug_toolbar/core/storage.py`)

**Observations**:
- **LRU Cache**: OrderedDict with automatic eviction
- **Thread-safe**: Uses `threading.Lock`
- **API**:
  - `store(request_id, data)`: Add request
  - `get(request_id)`: Retrieve by ID
  - `get_all()`: List all (newest first)
  - `store_from_context(context)`: Store from RequestContext

**Relevance to MCP**:
- All MCP tools/resources read from this storage
- `debug://current-request` = `storage.get_all()[0]`
- `debug://request/{id}` = `storage.get(UUID(id))`

**Integration Challenge**:
- MCP server runs in separate process
- Storage is in-memory, not shared across processes

**Solutions Evaluated**:
1. **Shared File** (simple but stale data)
2. **Redis** (best for production, but adds dependency)
3. **HTTP API** (pragmatic for v1.0)

**Decision**: v1.0 uses HTTP API approach (MCP server calls REST endpoints)

#### Pattern 4: Panel Architecture (`src/debug_toolbar/core/panel.py`)

**Observations**:
- Abstract `Panel` base class
- `generate_stats()` returns dict of metrics
- `process_request()`, `process_response()` lifecycle hooks
- Panel data stored in RequestContext via `store_panel_data()`

**Relevance to MCP**:
- Tools expose panel stats to AI assistants
- `get_performance_summary` aggregates timing data from multiple panels
- `get_error_context` extracts error info from panels

---

### 3. Sentry Spotlight Competitive Analysis

**Source**: [Sentry MCP Server Launch](https://sentry.io/about/press-releases/sentry-launches-monitoring-tool-for-mcp-servers%20/)

**Sentry's MCP Features**:
1. **AI-Assisted Debugging** (Seer)
   - Trigger Seer analysis from Claude Code
   - Get AI-generated fix recommendations
   - Monitor fix status

2. **Remote Hosted Server** (preferred)
   - OAuth authentication
   - Lower friction than local setup
   - Always up-to-date

3. **MCP Server Monitoring**
   - Track tool usage by transport type
   - Top-used and error-prone tools
   - JSON-RPC call drilldown

4. **Integration**
   - Claude Code native support: `claude mcp add --transport http sentry https://mcp.sentry.dev/mcp`
   - Cursor support via `.cursor/mcp.json`

**Competitive Gaps**:
- Sentry focuses on error monitoring, not performance
- No N+1 query detection
- No profiling data exposure
- No slow query analysis

**Differentiation Opportunities**:
- **Performance-First Tools**: Slow queries, N+1 patterns, profiling
- **Query Optimization**: EXPLAIN plans with AI suggestions
- **Local-First**: Stdio transport for zero-config local dev
- **Open Source**: Community can extend with custom tools

**Parity Requirements**:
- Stdio transport (v1.0)
- HTTP/SSE transport (v1.1)
- Claude Code + Cursor integration
- Clear documentation with examples

---

### 4. Tool/Resource Architecture Design

#### Tool Design Principles

1. **Focused Purpose**: Each tool does one thing well
2. **Composable**: Tools can be combined by AI
3. **Actionable Output**: Include suggestions, not just data
4. **Fast**: < 50ms p95 latency
5. **Type-Safe**: JSON Schema validation

#### Proposed Tools (7 total)

| Tool | Input | Output | Latency Target |
|------|-------|--------|----------------|
| `get_request_history` | `limit: int` | List of requests | < 20ms |
| `get_request_details` | `request_id: str` | Full request data | < 30ms |
| `get_slow_queries` | `threshold_ms: float, limit: int` | Slow queries + stacks | < 40ms |
| `get_n_plus_one_issues` | `min_count: int` | N+1 patterns + suggestions | < 50ms |
| `get_performance_summary` | `request_id: str?` | Timing breakdown | < 20ms |
| `get_error_context` | `request_id: str` | Error details + context | < 30ms |
| `explain_query` | `sql: str, parameters: dict?` | EXPLAIN plan + analysis | < 5000ms |

#### Proposed Resources (5 total)

| Resource | URI | Update Frequency | Cacheable |
|----------|-----|------------------|-----------|
| Current Request | `debug://current-request` | On new request | No |
| Alerts | `debug://alerts` | On new request | No |
| Specific Request | `debug://request/{id}` | Never (immutable) | Yes |
| Slow Queries | `debug://queries/slow` | On new request | No |
| N+1 Patterns | `debug://queries/n-plus-one` | On new request | No |

#### Tool vs Resource Decision Matrix

- **Use Tool** when:
  - Parameters needed (threshold, limit, filters)
  - Computation required (N+1 detection, EXPLAIN)
  - Side effects possible (future: clear cache, reset stats)

- **Use Resource** when:
  - Simple data retrieval
  - No parameters needed
  - Cacheable content
  - Live updates desirable (SSE)

---

### 5. Transport Layer Validation

#### Stdio Transport (v1.0)

**Advantages**:
- Zero configuration for local development
- No network/firewall issues
- Process isolation (crash won't affect app)
- Native support in Claude Code, Cursor

**Limitations**:
- Single user only
- Process must be launched by client
- No remote access
- Logging must go to stderr (not stdout)

**Implementation**:
```python
from mcp.server.stdio import stdio_server

async def run_stdio():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)
```

**Validation**: Test with Claude Code CLI

#### HTTP/SSE Transport (v1.1)

**Advantages**:
- Multi-user support
- Remote access for team debugging
- Persistent connection (SSE for updates)
- Standard HTTP tools for testing

**Limitations**:
- Authentication required
- CORS configuration needed
- More complex deployment
- Rate limiting considerations

**Implementation** (Future):
```python
from mcp.server.sse import sse_server

app = Litestar(
    route_handlers=[
        sse_server(mcp_server, path="/_mcp/sse")
    ]
)
```

**Validation**: Deferred to v1.1

---

### 6. Storage Integration Strategy

#### Challenge

MCP server runs as separate process. How does it access `ToolbarStorage`?

#### Option A: Shared File

```python
# App process
storage.export_to_file("/tmp/debug-toolbar.json")

# MCP process
data = json.loads(Path("/tmp/debug-toolbar.json").read_text())
```

**Pros**: Simple, no dependencies
**Cons**: Stale data, file I/O overhead, race conditions

#### Option B: Redis Backend

```python
# Both processes
storage = ToolbarStorage(backend=RedisBackend("redis://localhost"))
```

**Pros**: Real-time, scalable, production-ready
**Cons**: External dependency, more complex setup

#### Option C: HTTP API (Chosen for v1.0)

```python
# MCP process
async def _get_request_history(args):
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/_debug_toolbar/api/requests")
        return response.json()
```

**Pros**:
- Works immediately
- No new dependencies
- Leverages existing API
- No shared memory issues

**Cons**:
- Requires app running
- HTTP overhead (~5-10ms)
- Not ideal for production

**Decision**: Use HTTP API for v1.0, migrate to Redis in v1.1

---

### 7. Security Considerations

#### Input Validation

**Risk**: SQL injection via `explain_query` tool

**Mitigation**:
- Use parameterized queries (SQLAlchemy `text()`)
- Sanitize user input
- Limit EXPLAIN to SELECT queries only
- Timeout protection (5s max)

#### Authentication

**v1.0** (Stdio): None needed (local process)

**v1.1** (HTTP): API key header
```python
@server.call_tool()
async def call_tool(name, args, meta):
    api_key = meta.get("headers", {}).get("X-Debug-Toolbar-Key")
    if api_key != config.mcp_api_key:
        raise PermissionError("Invalid API key")
```

**v2.0** (Enterprise): OAuth 2.1 (follow Sentry pattern)

#### Data Exposure

**Concern**: Sensitive data in request parameters, query results

**Mitigation**:
- Redact passwords, tokens from query parameters
- Limit EXPLAIN result size (max 1000 lines)
- No access to response bodies (too large, potentially sensitive)

---

## Implementation Roadmap

### Phase 1: Core MCP Server (Week 1)

- [ ] Setup `src/debug_toolbar/mcp/` module structure
- [ ] Implement `server.py` with stdio transport
- [ ] Create CLI entrypoint (`__main__.py`)
- [ ] Add dependency: `mcp>=1.22.0`

### Phase 2: Tool Implementation (Week 1-2)

- [ ] `get_request_history` tool
- [ ] `get_request_details` tool
- [ ] `get_slow_queries` tool (integrate with SQLAlchemy panel)
- [ ] `get_n_plus_one_issues` tool
- [ ] `get_performance_summary` tool
- [ ] `get_error_context` tool
- [ ] `explain_query` tool (use ExplainExecutor)

### Phase 3: Resource Implementation (Week 2)

- [ ] `debug://current-request` resource
- [ ] `debug://alerts` resource
- [ ] `debug://request/{id}` resource
- [ ] `debug://queries/slow` resource
- [ ] `debug://queries/n-plus-one` resource

### Phase 4: Integration (Week 2)

- [ ] HTTP API client for storage access
- [ ] Error handling and logging
- [ ] Configuration integration
- [ ] Performance optimization

### Phase 5: Testing (Week 3)

- [ ] Unit tests for all tools (90%+ coverage)
- [ ] Unit tests for all resources
- [ ] Integration tests (stdio transport)
- [ ] Performance benchmarks
- [ ] Claude Code integration test
- [ ] Cursor integration test

### Phase 6: Documentation (Week 3)

- [ ] MCP server guide (`docs/mcp-server.md`)
- [ ] Claude Code integration (`docs/integrations/claude-code.md`)
- [ ] Cursor integration (`docs/integrations/cursor.md`)
- [ ] README updates
- [ ] Inline docstrings
- [ ] Example prompts

---

## Open Questions

1. **Storage Sync**: Should v1.1 use Redis or continue with HTTP API?
   - **Decision**: Evaluate after v1.0 performance testing

2. **Tool Granularity**: Should `get_performance_summary` be split into panel-specific tools?
   - **Decision**: Keep aggregated for v1.0, add granular tools based on user feedback

3. **Prompts**: Should we expose MCP prompts (reusable templates)?
   - **Decision**: Defer to v1.1, tools are more valuable initially

4. **Real-time Updates**: Should resources support live updates via SSE?
   - **Decision**: Not in v1.0 (stdio doesn't support), add in v1.1 with HTTP transport

5. **Multi-app Support**: How to connect MCP server to multiple running apps?
   - **Decision**: v1.0 assumes single app, v1.1 adds app selection parameter

---

## References

### External Resources
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Protocol Docs](https://modelcontextprotocol.io/docs/sdk)
- [Building MCP Servers](https://scrapfly.io/blog/posts/how-to-build-an-mcp-server-in-python-a-complete-guide)
- [Sentry MCP Launch](https://sentry.io/about/press-releases/sentry-launches-monitoring-tool-for-mcp-servers%20/)

### Internal Code References
- `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/core/storage.py`
- `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/extras/advanced_alchemy/panel.py`
- `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/litestar/routes/handlers.py`
- `/home/cody/code/litestar/debug-toolbar/src/debug_toolbar/core/panel.py`

---

**Research Completion**: 2025-11-29
**Total Research Time**: ~4 hours
**Word Count**: 2,487 words
