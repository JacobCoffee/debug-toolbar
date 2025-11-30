# Spec: PR #9 - MCP Server Integration

## Metadata
- **PR Number**: 9
- **Priority**: P2
- **Complexity**: High
- **Estimated Files**: 8-10
- **Dependencies**: None
- **Implementation Order**: 8

---

## Problem Statement

AI-assisted development is rapidly becoming standard practice. Tools like Claude Code, Cursor, and GitHub Copilot benefit enormously from context about the running application.

The Model Context Protocol (MCP) allows tools to expose their data to AI assistants. By implementing an MCP server, we enable AI assistants to:
- Understand current request context
- Analyze database query performance
- Identify bottlenecks without manual inspection
- Suggest fixes based on actual runtime data

Sentry Spotlight already has MCP integration - we need parity and can go beyond.

---

## Goals

1. Implement MCP server exposing debug toolbar data
2. Provide tools for common debugging tasks
3. Expose resources for current request state
4. Enable Claude Code and Cursor integration
5. Document integration process

---

## Non-Goals

- Real-time streaming (polling only)
- Write operations (read-only access)
- Authentication/authorization (development tool)

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│ MCP Client (Claude/Cursor)                      │
└─────────────────────────────────────────────────┘
         │
         │ stdio/HTTP transport
         ▼
┌─────────────────────────────────────────────────┐
│ debug_toolbar/mcp/server.py                     │
├─────────────────────────────────────────────────┤
│ - MCP server implementation                     │
│ - Tool handlers                                 │
│ - Resource providers                            │
└─────────────────────────────────────────────────┘
         │
         │ reads from
         ▼
┌─────────────────────────────────────────────────┐
│ debug_toolbar/core/storage.py                   │
├─────────────────────────────────────────────────┤
│ - Request history                               │
│ - Panel data                                    │
└─────────────────────────────────────────────────┘
```

### MCP Server Implementation

```python
# src/debug_toolbar/mcp/server.py
from mcp.server import Server
from mcp.types import Tool, Resource

class DebugToolbarMCPServer:
    """MCP server exposing debug toolbar data."""

    def __init__(self, storage: ToolbarStorage):
        self.storage = storage
        self.server = Server("debug-toolbar")
        self._register_tools()
        self._register_resources()

    def _register_tools(self):
        @self.server.tool("get_request_history")
        async def get_request_history(limit: int = 10) -> list[dict]:
            """Get recent request history with timing and status."""
            return self.storage.get_history(limit=limit)

        @self.server.tool("get_slow_queries")
        async def get_slow_queries(request_id: str | None = None, threshold_ms: float = 100) -> list[dict]:
            """Find database queries exceeding threshold."""
            # Implementation

        @self.server.tool("get_n_plus_one_issues")
        async def get_n_plus_one_issues(request_id: str | None = None) -> list[dict]:
            """Find N+1 query patterns in recent requests."""
            # Implementation

        @self.server.tool("get_performance_summary")
        async def get_performance_summary(request_id: str | None = None) -> dict:
            """Get performance breakdown for a request."""
            # Implementation

        @self.server.tool("get_error_context")
        async def get_error_context(request_id: str) -> dict:
            """Get full context for a failed request."""
            # Implementation

    def _register_resources(self):
        @self.server.resource("debug://current-request")
        async def current_request() -> dict:
            """Current/latest request data."""
            return self.storage.get_latest()

        @self.server.resource("debug://alerts")
        async def current_alerts() -> list[dict]:
            """Active alerts from AlertsPanel."""
            # Implementation
```

### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_request_history` | Recent requests | `limit: int` |
| `get_slow_queries` | Queries > threshold | `request_id?, threshold_ms` |
| `get_n_plus_one_issues` | N+1 patterns | `request_id?` |
| `get_performance_summary` | Timing breakdown | `request_id?` |
| `get_error_context` | Full error info | `request_id` |
| `explain_query` | EXPLAIN plan | `request_id, query_index` |
| `get_memory_allocations` | Top allocations | `request_id?, limit` |

### Resources

| Resource URI | Description |
|--------------|-------------|
| `debug://current-request` | Latest request data |
| `debug://alerts` | Current alerts |
| `debug://request/{id}` | Specific request |
| `debug://request/{id}/queries` | SQL queries |
| `debug://request/{id}/profiling` | Profile data |

### Files to Create

```
src/debug_toolbar/mcp/
├── __init__.py
├── server.py         # MCP server
├── tools.py          # Tool implementations
├── resources.py      # Resource providers
└── cli.py            # Standalone server CLI

tests/unit/
└── test_mcp_server.py

docs/integrations/
├── mcp.md
├── claude-code.md
└── cursor.md

examples/
└── mcp_integration.py
```

---

## Acceptance Criteria

- [ ] MCP server implements required protocol
- [ ] All tools return valid JSON
- [ ] Resources accessible via URI
- [ ] Works with Claude Code
- [ ] Works with Cursor
- [ ] Standalone CLI mode for testing
- [ ] HTTP transport option
- [ ] Documentation for integration
- [ ] 90%+ test coverage

---

## Testing Strategy

### Unit Tests
```python
class TestMCPServer:
    async def test_get_request_history(self):
        """Should return recent requests."""

    async def test_get_slow_queries(self):
        """Should find queries above threshold."""

    async def test_get_n_plus_one_issues(self):
        """Should identify N+1 patterns."""

    async def test_resource_current_request(self):
        """Should return latest request."""

class TestMCPTools:
    async def test_explain_query(self):
        """Should return EXPLAIN output."""

    async def test_error_context(self):
        """Should include full error info."""
```

### Integration Tests
```python
class TestMCPIntegration:
    async def test_stdio_transport(self):
        """Test stdio communication."""

    async def test_with_running_app(self):
        """Test with actual debug data."""
```

---

## CLI Usage

```bash
# Start MCP server (stdio mode for Claude Code)
python -m debug_toolbar.mcp.cli

# Start MCP server (HTTP mode for Cursor)
python -m debug_toolbar.mcp.cli --transport http --port 8765

# With custom storage path
python -m debug_toolbar.mcp.cli --storage /path/to/storage.db
```

---

## Claude Code Configuration

```json
// .claude/settings.json
{
  "mcpServers": {
    "debug-toolbar": {
      "command": "python",
      "args": ["-m", "debug_toolbar.mcp.cli"]
    }
  }
}
```

---

## Cursor Configuration

```json
// .cursor/mcp.json
{
  "servers": {
    "debug-toolbar": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

---

## Example Tool Responses

### get_slow_queries
```json
{
  "queries": [
    {
      "sql": "SELECT * FROM users WHERE ...",
      "duration_ms": 245.3,
      "request_id": "abc123",
      "file": "api/users.py",
      "line": 42,
      "explain_available": true
    }
  ],
  "total_count": 3,
  "threshold_ms": 100
}
```

### get_performance_summary
```json
{
  "request_id": "abc123",
  "total_time_ms": 523.4,
  "breakdown": {
    "python": 156.2,
    "database": 312.1,
    "templates": 45.3,
    "other": 9.8
  },
  "bottleneck": "database",
  "suggestions": [
    "3 slow queries detected (>100ms)",
    "N+1 pattern found in users.py:42"
  ]
}
```

---

## Implementation Notes

1. **MCP SDK**: Use official `mcp` package
2. **Storage Access**: MCP server needs read access to storage
3. **Concurrent Access**: Handle multiple clients safely
4. **Memory**: Don't load all history at once
5. **Versioning**: Pin MCP protocol version

### Transport Modes

```python
# Stdio for Claude Code (default)
async def run_stdio():
    async with stdio_server() as (read, write):
        await server.run(read, write)

# HTTP for Cursor
from mcp.server.sse import SseServerTransport

async def run_http(port: int):
    transport = SseServerTransport("/mcp")
    # ... HTTP server setup
```

---

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Sentry Spotlight MCP](https://spotlightjs.com/) - competitor reference
- [Claude Code MCP Docs](https://docs.anthropic.com/claude-code/mcp)
