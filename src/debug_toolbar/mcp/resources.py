"""MCP resource definitions for debug toolbar data access."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from debug_toolbar.mcp.server import MCPContext

try:
    from mcp.server.fastmcp import Context, FastMCP
except ImportError:
    Context = Any  # type: ignore[assignment, misc]
    FastMCP = Any  # type: ignore[assignment, misc]


def register_resources(mcp: FastMCP) -> None:  # noqa: C901
    """Register all debug toolbar resources with the MCP server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.resource("debug://requests")
    def get_all_requests(ctx: Context) -> str:
        """List all tracked requests with summaries.

        Returns JSON array of request summaries including ID, method, path,
        status code, and duration.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        requests = []
        for request_id, data in storage.get_all():
            metadata = data.get("metadata", {})
            timing = data.get("timing_data", {})

            summary = {
                "request_id": str(request_id),
                "method": metadata.get("method", ""),
                "path": metadata.get("path", ""),
                "status_code": metadata.get("status_code"),
                "duration_ms": timing.get("total_time", 0) * 1000,  # seconds to ms
                "timestamp": metadata.get("timestamp"),
            }

            if mcp_ctx.redact_sensitive:
                summary = redact_dict(summary)

            requests.append(summary)

        return json.dumps(requests, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}")
    def get_request_detail(request_id: str, ctx: Context) -> str:
        """Get full details for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON object with metadata, timing, and available panels.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        result = {
            "request_id": request_id,
            "metadata": data.get("metadata", {}),
            "timing_data": data.get("timing_data", {}),
            "panels_available": list(data.get("panel_data", {}).keys()),
        }

        if mcp_ctx.redact_sensitive:
            result = redact_dict(result)

        return json.dumps(result, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}/panels")
    def get_request_panels(request_id: str, ctx: Context) -> str:
        """Get all panel data for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON object with all panel data.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})

        if mcp_ctx.redact_sensitive:
            panel_data = redact_dict(panel_data)

        return json.dumps(panel_data, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}/panels/{panel_name}")
    def get_panel_data(request_id: str, panel_name: str, ctx: Context) -> str:
        """Get specific panel data for a request.

        Args:
            request_id: UUID of the request.
            panel_name: Name of the panel (e.g., SQLAlchemyPanel, GraphQLPanel).

        Returns JSON object with the panel's data.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        if panel_name not in panel_data:
            available = list(panel_data.keys())
            return json.dumps(
                {
                    "error": f"Panel '{panel_name}' not found",
                    "available_panels": available,
                }
            )

        result = panel_data[panel_name]

        if mcp_ctx.redact_sensitive:
            result = redact_dict(result) if isinstance(result, dict) else result

        return json.dumps(result, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}/sql")
    def get_sql_queries(request_id: str, ctx: Context) -> str:
        """Get SQL queries for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON array of SQL queries with timing and EXPLAIN data.
        """
        from debug_toolbar.mcp.security import redact_dict, redact_sql_parameters

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        sql_panel = panel_data.get("SQLAlchemyPanel", {})
        queries = sql_panel.get("queries", [])

        if mcp_ctx.redact_sensitive:
            queries = [
                {
                    **redact_dict(q),
                    "parameters": redact_sql_parameters(q.get("parameters")),
                }
                for q in queries
            ]

        return json.dumps(
            {
                "query_count": len(queries),
                "total_duration_ms": sql_panel.get("total_duration_ms", 0),
                "n_plus_one_patterns": sql_panel.get("n_plus_one_patterns", []),
                "queries": queries,
            },
            indent=2,
            default=str,
        )

    @mcp.resource("debug://requests/{request_id}/graphql")
    def get_graphql_data(request_id: str, ctx: Context) -> str:
        """Get GraphQL operations for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON object with GraphQL operations and resolver timings.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        graphql_panel = panel_data.get("GraphQLPanel", {})

        if not graphql_panel:
            return json.dumps({"message": "No GraphQL data for this request"})

        if mcp_ctx.redact_sensitive:
            graphql_panel = redact_dict(graphql_panel)

        return json.dumps(graphql_panel, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}/alerts")
    def get_security_alerts(request_id: str, ctx: Context) -> str:
        """Get security alerts for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON array of security alerts and warnings.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        alerts_panel = panel_data.get("AlertsPanel", {})

        return json.dumps(
            {
                "alerts": alerts_panel.get("alerts", []),
                "alert_count": len(alerts_panel.get("alerts", [])),
            },
            indent=2,
            default=str,
        )

    @mcp.resource("debug://requests/{request_id}/memory")
    def get_memory_profile(request_id: str, ctx: Context) -> str:
        """Get memory profiling data for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON object with memory usage and allocation data.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        memory_panel = panel_data.get("MemoryPanel", {})

        if not memory_panel:
            return json.dumps({"message": "No memory profiling data for this request"})

        return json.dumps(memory_panel, indent=2, default=str)

    @mcp.resource("debug://requests/{request_id}/async")
    def get_async_profile(request_id: str, ctx: Context) -> str:
        """Get async task profiling data for a specific request.

        Args:
            request_id: UUID of the request.

        Returns JSON object with async task timeline and blocking call data.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return json.dumps({"error": f"Request {request_id} not found"})

        panel_data = data.get("panel_data", {})
        async_panel = panel_data.get("AsyncProfilerPanel", {})

        if not async_panel:
            return json.dumps({"message": "No async profiling data for this request"})

        return json.dumps(async_panel, indent=2, default=str)

    @mcp.resource("debug://config")
    def get_config(ctx: Context) -> str:
        """Get current debug toolbar configuration.

        Returns JSON object with toolbar configuration settings.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        toolbar = mcp_ctx.toolbar

        if not toolbar:
            return json.dumps({"message": "Toolbar instance not available"})

        config = toolbar.config
        config_dict = {
            "enabled": config.enabled,
            "panels": config.panels,
            "max_request_history": config.max_request_history,
            "slow_request_threshold_ms": config.slow_request_threshold_ms,
        }

        if hasattr(config, "intercept_redirects"):
            config_dict["intercept_redirects"] = config.intercept_redirects

        if mcp_ctx.redact_sensitive:
            config_dict = redact_dict(config_dict)

        return json.dumps(config_dict, indent=2, default=str)
