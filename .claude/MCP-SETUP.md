# MCP Server Setup

This project uses MCP (Model Context Protocol) servers to enhance Claude Code capabilities.

## Required Servers

### 1. Context7 (Library Documentation)

Provides up-to-date documentation for libraries like Litestar, SQLAlchemy, etc.

**Claude Code CLI:**
```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

**Manual config** (add to `~/.claude/settings.json` or project `.claude/settings.json`):
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

Source: [Context7 GitHub](https://github.com/upstash/context7)

---

### 2. Sequential Thinking (Structured Analysis)

Enables step-by-step reasoning for complex problems.

**Claude Code CLI:**
```bash
claude mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
```

**Manual config:**
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
      }
  }
}
```

Source: [Sequential Thinking on npm](https://www.npmjs.com/package/@modelcontextprotocol/server-sequential-thinking)

---

## Optional Server

### 3. Zen (Advanced AI Tools)

Multi-model collaboration server providing consensus, deep thinking, debugging, and planning tools.

**Requires** API keys for external providers (Gemini, OpenAI, OpenRouter, etc.).

**Option A - Using uvx (recommended):**
```bash
claude mcp add zen -- uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server
```

**Option B - Clone and run setup script:**
```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server
./run-server.sh  # Auto-configures Claude Code
```

**Environment variables needed:**
```bash
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="..."      # optional
export OPENROUTER_API_KEY="..."  # optional
```

Source: [Zen MCP Server GitHub](https://github.com/BeehiveInnovations/zen-mcp-server)

---

## Verification

After installation, restart Claude Code and verify:

```bash
claude mcp list
```

## Usage in This Project

- **Context7**: Fetch Litestar/SQLAlchemy docs when implementing features
- **Sequential Thinking**: Break down complex panel implementations
- **Zen**: Multi-model validation for architectural decisions

See `mcp-strategy.md` for task-based tool selection guidance.
