# MCP Server Integration

The debug toolbar includes an MCP (Model Context Protocol) server that allows AI assistants like Claude Code to analyze your application's debug data programmatically.

## Installation

Install with MCP support:

```bash
uv add debug-toolbar[mcp]
# or
pip install debug-toolbar[mcp]
```

## Quick Start

### 1. Configure Claude Code

Add to your `~/.claude/settings.json` (global) or `.claude/settings.json` (project):

```json
{
  "mcpServers": {
    "debug-toolbar": {
      "command": "uv",
      "args": ["run", "python", "-m", "debug_toolbar.mcp"]
    }
  }
}
```

### 2. Restart Claude Code

After updating settings, restart Claude Code to load the MCP server.

### 3. Run Your Application

Start your Litestar application with the debug toolbar enabled:

```python
from litestar import Litestar, get
from debug_toolbar.litestar import DebugToolbarPlugin, LitestarDebugToolbarConfig

@get("/")
async def index() -> dict:
    return {"message": "Hello"}

config = LitestarDebugToolbarConfig(enabled=True)
app = Litestar(
    route_handlers=[index],
    plugins=[DebugToolbarPlugin(config)],
)
```

### 4. Ask Claude Code to Analyze

Once you have requests flowing through your app, ask Claude Code questions like:

- "What requests have been made to my application?"
- "Are there any slow endpoints?"
- "Check for security issues in my app"
- "Generate a performance optimization report"
- "Are there any N+1 query patterns?"

## Available MCP Tools

### Request Analysis

| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `get_request_history` | List recent HTTP requests | "What requests have been made?" |
| `get_request_details` | Get detailed info for a specific request | "Show me details for request abc123" |
| `get_panel_data` | Get data from a specific panel | "What does the Timer panel show?" |

### Performance Analysis

| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `analyze_performance_bottlenecks` | Find slow operations | "Are there any slow endpoints?" |
| `compare_requests` | Compare timing between requests | "Compare the /api and /users endpoints" |
| `generate_optimization_report` | Full performance report | "Generate a performance report" |

### Database Analysis

| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `detect_n_plus_one_queries` | Find N+1 query patterns | "Are there any N+1 queries?" |

### Security Analysis

| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `analyze_security_alerts` | Check for security issues | "Check for security problems" |

## Example Prompts

Here are effective prompts to use with Claude Code:

### General Analysis
```
"Analyze my application's debug toolbar data"
"What's happening in my app?"
"Show me recent requests and any issues"
```

### Performance
```
"What's the slowest endpoint in my application?"
"Find performance bottlenecks"
"Which requests are taking longer than 200ms?"
"Generate an optimization report for my app"
```

### Security
```
"Are there any security issues in my responses?"
"Check for missing security headers"
"Analyze security alerts from the debug toolbar"
```

### Database
```
"Are there N+1 query problems?"
"How many database queries per request?"
"Find inefficient database access patterns"
```

### Comparison
```
"Compare the performance of /api/users vs /api/posts"
"What changed between these two requests?"
```

## MCP Resources

The MCP server also exposes resources for direct data access:

| Resource | URI | Description |
|----------|-----|-------------|
| Request List | `debug://requests` | All tracked requests |
| Request Details | `debug://request/{id}` | Single request details |
| Panel Data | `debug://panel/{request_id}/{panel_id}` | Specific panel data |
| Toolbar Config | `debug://config` | Current configuration |
| Available Panels | `debug://panels` | List of enabled panels |

## Programmatic Usage

You can also use the MCP server programmatically:

```python
from debug_toolbar import DebugToolbar, DebugToolbarConfig
from debug_toolbar.mcp import create_mcp_server, is_available

if is_available():
    config = DebugToolbarConfig(enabled=True)
    toolbar = DebugToolbar(config)

    mcp = create_mcp_server(
        storage=toolbar.storage,
        toolbar=toolbar,
        redact_sensitive=True,  # Redact passwords, tokens, etc.
        server_name="my-app-debug",
    )

    # Run with stdio transport (for Claude Code)
    mcp.run(transport="stdio")

    # Or SSE transport (for web clients)
    # mcp.run(transport="sse")
```

## Security Considerations

### Sensitive Data Redaction

By default, the MCP server redacts sensitive data like:
- Passwords and secrets in headers
- Authorization tokens
- API keys
- Session cookies

Enable/disable with:

```python
mcp = create_mcp_server(
    storage=toolbar.storage,
    toolbar=toolbar,
    redact_sensitive=True,  # Default: True
)
```

### Production Usage

The MCP server is intended for **development use only**. Do not expose it in production environments as it reveals internal application details.

## Troubleshooting

### MCP Server Not Loading

1. Check that `mcp` package is installed: `pip show mcp`
2. Verify settings.json syntax is valid JSON
3. Restart Claude Code after config changes
4. Check Claude Code logs for MCP connection errors

### No Request Data

1. Ensure your application has the debug toolbar enabled
2. Make some requests to your application first
3. Check that `max_request_history` is > 0 in config

### Tools Not Working

1. Verify the MCP server is running: check Claude Code's MCP status
2. Try a simple prompt first: "What requests have been made?"
3. Check that your application is generating debug data

## Running the Example

Try the included MCP example:

```bash
# Terminal 1: Run the web app
make example-mcp

# Terminal 2: The MCP server runs via Claude Code settings

# Then:
# 1. Visit http://localhost:8004 and click around
# 2. Ask Claude Code: "Analyze my debug toolbar data"
```
