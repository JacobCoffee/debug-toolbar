"""MCP tool definitions for debug toolbar analysis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

if TYPE_CHECKING:
    from debug_toolbar.mcp.server import MCPContext

try:
    from mcp.server.fastmcp import Context, FastMCP
except ImportError:
    Context = Any  # type: ignore[assignment, misc]
    FastMCP = Any  # type: ignore[assignment, misc]

SLOW_QUERY_THRESHOLD_MS = 100
SLOW_RESOLVER_THRESHOLD_MS = 50
HIGH_MEMORY_THRESHOLD_MB = 10
MAX_GRAPHQL_REQUESTS = 5
REGRESSION_THRESHOLD_PCT = 20
IMPROVEMENT_THRESHOLD_PCT = -20
HIGH_QUERY_COUNT_THRESHOLD = 10
SLOW_REQUEST_THRESHOLD_MS = 500


def register_tools(mcp: FastMCP) -> None:  # noqa: C901
    """Register all debug toolbar tools with the MCP server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool()
    def get_request_history(
        ctx: Context,
        limit: int = 20,
        method: str | None = None,
        path_contains: str | None = None,
        min_duration_ms: float | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent request history from the debug toolbar.

        Args:
            ctx: MCP context.
            limit: Maximum number of requests to return (default 20).
            method: Filter by HTTP method (GET, POST, etc.).
            path_contains: Filter by path substring.
            min_duration_ms: Filter by minimum duration in milliseconds.

        Returns:
            List of request summaries with metadata.
        """
        from debug_toolbar.mcp.security import redact_dict

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        requests = []
        for request_id, data in storage.get_all():
            metadata = data.get("metadata", {})

            if method and metadata.get("method") != method:
                continue
            if path_contains and path_contains not in metadata.get("path", ""):
                continue

            timing = data.get("timing_data", {})
            duration = timing.get("total_time", 0) * 1000  # Convert seconds to ms
            if min_duration_ms and duration < min_duration_ms:
                continue

            summary = {
                "request_id": str(request_id),
                "method": metadata.get("method", ""),
                "path": metadata.get("path", ""),
                "status_code": metadata.get("status_code"),
                "duration_ms": duration,
                "timestamp": metadata.get("timestamp"),
                "panels_available": list(data.get("panel_data", {}).keys()),
            }

            if mcp_ctx.redact_sensitive:
                summary = redact_dict(summary)

            requests.append(summary)

            if len(requests) >= limit:
                break

        return requests

    @mcp.tool()
    def analyze_performance_bottlenecks(  # noqa: C901, PLR0912
        ctx: Context,
        request_id: str | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        """Analyze performance bottlenecks in request(s).

        Identifies slow queries, expensive operations, and optimization opportunities.

        Args:
            ctx: MCP context.
            request_id: Specific request ID to analyze (or latest if None).
            top_n: Number of top bottlenecks to return per category.

        Returns:
            Performance analysis with bottlenecks and recommendations.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        if request_id:
            data = storage.get(UUID(request_id))
            if not data:
                return {"error": f"Request {request_id} not found"}
            requests_data = [(UUID(request_id), data)]
        else:
            requests_data = list(storage.get_all())[:10]

        analysis = {
            "total_requests_analyzed": len(requests_data),
            "slow_queries": [],
            "slow_resolvers": [],
            "memory_heavy_requests": [],
            "blocking_calls": [],
            "recommendations": [],
        }

        for rid, data in requests_data:
            panel_data = data.get("panel_data", {})

            sql_panel = panel_data.get("SQLAlchemyPanel", {})
            queries = sql_panel.get("queries", [])
            for q in queries:
                if q.get("duration_ms", 0) > SLOW_QUERY_THRESHOLD_MS:
                    analysis["slow_queries"].append(
                        {
                            "request_id": str(rid),
                            "query": q.get("sql", "")[:200],
                            "duration_ms": q.get("duration_ms"),
                            "is_n_plus_one": q.get("is_n_plus_one", False),
                        }
                    )

            graphql_panel = panel_data.get("GraphQLPanel", {})
            operations = graphql_panel.get("operations", [])
            for op in operations:
                for resolver in op.get("resolvers", []):
                    if resolver.get("duration_ms", 0) > SLOW_RESOLVER_THRESHOLD_MS:
                        analysis["slow_resolvers"].append(
                            {
                                "request_id": str(rid),
                                "resolver": resolver.get("resolver_function", ""),
                                "duration_ms": resolver.get("duration_ms"),
                            }
                        )

            async_panel = panel_data.get("AsyncProfilerPanel", {})
            blocking = async_panel.get("blocking_calls", [])
            for call in blocking:
                analysis["blocking_calls"].append(
                    {
                        "request_id": str(rid),
                        "location": call.get("location", ""),
                        "duration_ms": call.get("duration_ms"),
                    }
                )

            memory_panel = panel_data.get("MemoryPanel", {})
            delta = memory_panel.get("delta_mb", 0)
            if delta > HIGH_MEMORY_THRESHOLD_MB:
                analysis["memory_heavy_requests"].append(
                    {
                        "request_id": str(rid),
                        "memory_delta_mb": delta,
                        "peak_mb": memory_panel.get("peak_mb"),
                    }
                )

        analysis["slow_queries"] = sorted(
            cast("list[dict[str, Any]]", analysis["slow_queries"]),
            key=lambda x: x["duration_ms"],
            reverse=True,
        )[:top_n]

        analysis["slow_resolvers"] = sorted(
            cast("list[dict[str, Any]]", analysis["slow_resolvers"]),
            key=lambda x: x["duration_ms"],
            reverse=True,
        )[:top_n]

        if analysis["slow_queries"]:
            analysis["recommendations"].append("Consider adding database indexes or optimizing slow queries")
        if any(q["is_n_plus_one"] for q in analysis["slow_queries"]):
            analysis["recommendations"].append("N+1 queries detected - use eager loading or batch queries")
        if analysis["blocking_calls"]:
            analysis["recommendations"].append("Blocking calls detected in async context - use async alternatives")
        if analysis["memory_heavy_requests"]:
            analysis["recommendations"].append("High memory usage detected - consider streaming or pagination")

        return analysis

    @mcp.tool()
    def detect_n_plus_one_queries(
        ctx: Context,
        request_id: str | None = None,
        threshold: int = 3,
    ) -> dict[str, Any]:
        """Detect N+1 query patterns in SQL queries.

        Args:
            ctx: MCP context.
            request_id: Specific request ID to analyze (or scan recent if None).
            threshold: Minimum similar queries to flag as N+1 (default 3).

        Returns:
            N+1 detection results with query patterns and suggestions.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        if request_id:
            data = storage.get(UUID(request_id))
            if not data:
                return {"error": f"Request {request_id} not found"}
            requests_data = [(UUID(request_id), data)]
        else:
            requests_data = list(storage.get_all())[:20]

        patterns: dict[str, list[dict[str, Any]]] = {}

        for rid, data in requests_data:
            panel_data = data.get("panel_data", {})
            sql_panel = panel_data.get("SQLAlchemyPanel", {})

            n_plus_one = sql_panel.get("n_plus_one_patterns", [])
            for pattern in n_plus_one:
                sig = pattern.get("query_signature", "")
                if sig not in patterns:
                    patterns[sig] = []
                patterns[sig].append(
                    {
                        "request_id": str(rid),
                        "count": pattern.get("count", 0),
                        "total_duration_ms": pattern.get("total_duration_ms", 0),
                        "example_query": pattern.get("example_query", "")[:200],
                    }
                )

            graphql_panel = panel_data.get("GraphQLPanel", {})
            stats = graphql_panel.get("stats", {})
            graphql_n1 = stats.get("n_plus_one_patterns", [])
            for pattern in graphql_n1:
                sig = f"GraphQL:{pattern.get('resolver_signature', '')}"
                if sig not in patterns:
                    patterns[sig] = []
                patterns[sig].append(
                    {
                        "request_id": str(rid),
                        "count": pattern.get("count", 0),
                        "total_duration_ms": pattern.get("total_duration_ms", 0),
                        "suggestion": pattern.get("suggestion", ""),
                    }
                )

        flagged_patterns = []
        for sig, occurrences in patterns.items():
            total_count = sum(o["count"] for o in occurrences)
            if total_count >= threshold:
                flagged_patterns.append(
                    {
                        "signature": sig,
                        "total_occurrences": total_count,
                        "affected_requests": len(occurrences),
                        "total_duration_ms": sum(o["total_duration_ms"] for o in occurrences),
                        "details": occurrences[:3],
                    }
                )

        return {
            "n_plus_one_detected": len(flagged_patterns) > 0,
            "patterns_found": len(flagged_patterns),
            "threshold_used": threshold,
            "patterns": sorted(
                flagged_patterns,
                key=lambda x: x["total_occurrences"],
                reverse=True,
            ),
            "recommendations": [
                "Use selectinload() or joinedload() for SQLAlchemy relationships",
                "Implement DataLoader for GraphQL resolvers",
                "Consider batch queries instead of individual lookups",
            ]
            if flagged_patterns
            else [],
        }

    @mcp.tool()
    def get_query_explain_plan(
        ctx: Context,
        request_id: str,
        query_index: int = 0,
    ) -> dict[str, Any]:
        """Get EXPLAIN plan for a specific SQL query.

        Args:
            ctx: MCP context.
            request_id: Request ID containing the query.
            query_index: Index of the query in the request (default 0).

        Returns:
            Query EXPLAIN plan if available.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data = storage.get(UUID(request_id))
        if not data:
            return {"error": f"Request {request_id} not found"}

        panel_data = data.get("panel_data", {})
        sql_panel = panel_data.get("SQLAlchemyPanel", {})
        queries = sql_panel.get("queries", [])

        if query_index >= len(queries):
            return {"error": f"Query index {query_index} out of range (max {len(queries) - 1})"}

        query = queries[query_index]
        return {
            "query": query.get("sql", ""),
            "duration_ms": query.get("duration_ms"),
            "explain_plan": query.get("explain_plan"),
            "explain_available": query.get("explain_plan") is not None,
            "parameters": query.get("parameters") if not mcp_ctx.redact_sensitive else "[REDACTED]",
        }

    @mcp.tool()
    def analyze_security_alerts(
        ctx: Context,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Analyze security alerts and configuration issues.

        Args:
            ctx: MCP context.
            request_id: Specific request ID (or scan all if None).

        Returns:
            Security analysis with alerts and recommendations.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        if request_id:
            data = storage.get(UUID(request_id))
            if not data:
                return {"error": f"Request {request_id} not found"}
            requests_data = [(UUID(request_id), data)]
        else:
            requests_data = list(storage.get_all())[:50]

        all_alerts: dict[str, list[dict[str, Any]]] = {}

        for rid, data in requests_data:
            panel_data = data.get("panel_data", {})
            alerts_panel = panel_data.get("AlertsPanel", {})
            alerts = alerts_panel.get("alerts", [])

            for alert in alerts:
                alert_type = alert.get("type", "unknown")
                if alert_type not in all_alerts:
                    all_alerts[alert_type] = []
                all_alerts[alert_type].append(
                    {
                        "request_id": str(rid),
                        "severity": alert.get("severity", "info"),
                        "message": alert.get("message", ""),
                        "details": alert.get("details"),
                    }
                )

        summary = {
            "total_alerts": sum(len(v) for v in all_alerts.values()),
            "alert_types": len(all_alerts),
            "alerts_by_type": {k: len(v) for k, v in all_alerts.items()},
            "critical_alerts": [],
            "high_alerts": [],
            "all_alerts": all_alerts,
        }

        for alerts in all_alerts.values():
            for alert in alerts:
                if alert["severity"] == "critical":
                    summary["critical_alerts"].append(alert)
                elif alert["severity"] == "high":
                    summary["high_alerts"].append(alert)

        return summary

    @mcp.tool()
    def compare_requests(
        ctx: Context,
        request_id_a: str,
        request_id_b: str,
    ) -> dict[str, Any]:
        """Compare two requests for performance regression analysis.

        Args:
            ctx: MCP context.
            request_id_a: First request ID (baseline).
            request_id_b: Second request ID (comparison).

        Returns:
            Comparison of timing, queries, and resource usage.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        data_a = storage.get(UUID(request_id_a))
        data_b = storage.get(UUID(request_id_b))

        if not data_a:
            return {"error": f"Request {request_id_a} not found"}
        if not data_b:
            return {"error": f"Request {request_id_b} not found"}

        timing_a = data_a.get("timing_data", {})
        timing_b = data_b.get("timing_data", {})
        panels_a = data_a.get("panel_data", {})
        panels_b = data_b.get("panel_data", {})

        sql_a = panels_a.get("SQLAlchemyPanel", {})
        sql_b = panels_b.get("SQLAlchemyPanel", {})

        duration_a = timing_a.get("total_time", 0) * 1000  # seconds to ms
        duration_b = timing_b.get("total_time", 0) * 1000  # seconds to ms
        duration_diff = duration_b - duration_a
        if duration_a > 0:
            duration_pct: float | None = duration_diff / duration_a * 100
        elif duration_a == 0 and duration_b > 0:
            duration_pct = None  # Undefined/infinite increase from zero baseline
        else:
            duration_pct = 0.0

        queries_a = len(sql_a.get("queries", []))
        queries_b = len(sql_b.get("queries", []))

        memory_a = panels_a.get("MemoryPanel", {}).get("delta_mb", 0)
        memory_b = panels_b.get("MemoryPanel", {}).get("delta_mb", 0)

        regression_detected = (
            (duration_pct is not None and duration_pct > REGRESSION_THRESHOLD_PCT)
            or queries_b > queries_a * 1.5
            or (duration_a == 0 and duration_b > 0)  # Any increase from zero is notable
        )
        improvements_detected = (
            duration_pct is not None and duration_pct < IMPROVEMENT_THRESHOLD_PCT
        ) or queries_b < queries_a * 0.7

        return {
            "baseline": {
                "request_id": request_id_a,
                "path": data_a.get("metadata", {}).get("path"),
                "duration_ms": duration_a,
                "query_count": queries_a,
                "memory_delta_mb": memory_a,
            },
            "comparison": {
                "request_id": request_id_b,
                "path": data_b.get("metadata", {}).get("path"),
                "duration_ms": duration_b,
                "query_count": queries_b,
                "memory_delta_mb": memory_b,
            },
            "differences": {
                "duration_ms": duration_diff,
                "duration_pct_change": round(duration_pct, 2) if duration_pct is not None else None,
                "query_count_diff": queries_b - queries_a,
                "memory_diff_mb": memory_b - memory_a,
            },
            "regression_detected": regression_detected,
            "improvements_detected": improvements_detected,
        }

    @mcp.tool()
    def get_graphql_operations(
        ctx: Context,
        request_id: str | None = None,
        *,
        include_resolvers: bool = True,
    ) -> dict[str, Any]:
        """Get GraphQL operation details and resolver timings.

        Args:
            ctx: MCP context.
            request_id: Specific request ID (or latest with GraphQL if None).
            include_resolvers: Include individual resolver timings.

        Returns:
            GraphQL operations with timing breakdown.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        if request_id:
            data = storage.get(UUID(request_id))
            if not data:
                return {"error": f"Request {request_id} not found"}
            requests_data = [(UUID(request_id), data)]
        else:
            requests_data = []
            for rid, data in storage.get_all():
                panel_data = data.get("panel_data", {})
                if "GraphQLPanel" in panel_data:
                    requests_data.append((rid, data))
                if len(requests_data) >= MAX_GRAPHQL_REQUESTS:
                    break

        all_operations = []
        for rid, data in requests_data:
            panel_data = data.get("panel_data", {})
            graphql = panel_data.get("GraphQLPanel", {})
            operations = graphql.get("operations", [])

            for op in operations:
                op_summary = {
                    "request_id": str(rid),
                    "operation_id": op.get("operation_id"),
                    "operation_name": op.get("operation_name"),
                    "operation_type": op.get("operation_type"),
                    "duration_ms": op.get("duration_ms"),
                    "resolver_count": len(op.get("resolvers", [])),
                    "has_errors": bool(op.get("errors")),
                    "errors": op.get("errors", []),
                }

                if include_resolvers:
                    resolvers = op.get("resolvers", [])
                    op_summary["resolvers"] = [
                        {
                            "field_path": r.get("field_path"),
                            "duration_ms": r.get("duration_ms"),
                            "is_slow": r.get("is_slow", False),
                        }
                        for r in sorted(resolvers, key=lambda x: x.get("duration_ms", 0), reverse=True)[:10]
                    ]

                all_operations.append(op_summary)

        stats = {}
        if requests_data:
            latest_panel = requests_data[0][1].get("panel_data", {}).get("GraphQLPanel", {})
            stats = latest_panel.get("stats", {})

        return {
            "operations": all_operations,
            "total_operations": len(all_operations),
            "n_plus_one_patterns": stats.get("n_plus_one_patterns", []),
            "duplicate_operations": stats.get("duplicate_operations", []),
        }

    @mcp.tool()
    def get_async_task_profile(
        ctx: Context,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Get async task profiling data and event loop metrics.

        Args:
            ctx: MCP context.
            request_id: Specific request ID (or latest if None).

        Returns:
            Async profiling data with task timeline and blocking calls.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        if request_id:
            data = storage.get(UUID(request_id))
            if not data:
                return {"error": f"Request {request_id} not found"}
        else:
            all_requests = list(storage.get_all())
            if not all_requests:
                return {"error": "No requests in storage"}
            _, data = all_requests[0]

        panel_data = data.get("panel_data", {})
        async_panel = panel_data.get("AsyncProfilerPanel", {})

        if not async_panel:
            return {"message": "No async profiling data available for this request"}

        return {
            "summary": async_panel.get("summary", {}),
            "tasks": async_panel.get("tasks", [])[:20],
            "blocking_calls": async_panel.get("blocking_calls", []),
            "event_loop_lag": async_panel.get("event_loop_lag", {}),
            "warnings": async_panel.get("warnings", []),
        }

    @mcp.tool()
    def generate_optimization_report(
        ctx: Context,
        *,
        include_sql: bool = True,
        include_graphql: bool = True,
        include_async: bool = True,
    ) -> dict[str, Any]:
        """Generate a comprehensive optimization report across all requests.

        Args:
            ctx: MCP context.
            include_sql: Include SQL optimization suggestions.
            include_graphql: Include GraphQL optimization suggestions.
            include_async: Include async optimization suggestions.

        Returns:
            Comprehensive optimization report with prioritized recommendations.
        """
        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        requests_data = list(storage.get_all())[:100]

        report = {
            "requests_analyzed": len(requests_data),
            "sql_optimizations": [],
            "graphql_optimizations": [],
            "async_optimizations": [],
            "general_recommendations": [],
            "priority_actions": [],
        }

        total_duration = 0
        total_queries = 0
        n_plus_one_count = 0
        blocking_calls_count = 0
        graphql_n1_count = 0

        for _rid, data in requests_data:
            timing = data.get("timing_data", {})
            total_duration += timing.get("total_time", 0) * 1000  # seconds to ms

            panels = data.get("panel_data", {})

            if include_sql:
                sql = panels.get("SQLAlchemyPanel", {})
                queries = sql.get("queries", [])
                total_queries += len(queries)
                n_plus_one = sql.get("n_plus_one_patterns", [])
                n_plus_one_count += len(n_plus_one)

            if include_graphql:
                graphql = panels.get("GraphQLPanel", {})
                stats = graphql.get("stats", {})
                graphql_n1 = stats.get("n_plus_one_patterns", [])
                graphql_n1_count += len(graphql_n1)

            if include_async:
                async_p = panels.get("AsyncProfilerPanel", {})
                blocking = async_p.get("blocking_calls", [])
                blocking_calls_count += len(blocking)

        avg_duration = total_duration / len(requests_data) if requests_data else 0
        avg_queries = total_queries / len(requests_data) if requests_data else 0

        report["summary"] = {
            "avg_request_duration_ms": round(avg_duration, 2),
            "avg_queries_per_request": round(avg_queries, 2),
            "n_plus_one_patterns_found": n_plus_one_count,
            "graphql_n_plus_one_found": graphql_n1_count,
            "blocking_calls_found": blocking_calls_count,
        }

        if n_plus_one_count > 0:
            report["priority_actions"].append(
                {
                    "priority": "HIGH",
                    "category": "SQL",
                    "action": f"Fix {n_plus_one_count} N+1 query patterns using eager loading",
                }
            )

        if graphql_n1_count > 0:
            report["priority_actions"].append(
                {
                    "priority": "HIGH",
                    "category": "GraphQL",
                    "action": f"Fix {graphql_n1_count} GraphQL N+1 patterns using DataLoader",
                }
            )

        if blocking_calls_count > 0:
            report["priority_actions"].append(
                {
                    "priority": "HIGH",
                    "category": "Async",
                    "action": f"Replace {blocking_calls_count} blocking calls with async alternatives",
                }
            )

        if avg_queries > HIGH_QUERY_COUNT_THRESHOLD:
            report["priority_actions"].append(
                {
                    "priority": "MEDIUM",
                    "category": "SQL",
                    "action": f"Reduce query count (avg {avg_queries:.1f}/request) through batching",
                }
            )

        if avg_duration > SLOW_REQUEST_THRESHOLD_MS:
            report["general_recommendations"].append("Consider implementing caching for frequently accessed data")

        return report

    @mcp.tool()
    def clear_request_history(
        ctx: Context,
        *,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Clear all stored request history.

        Args:
            ctx: MCP context.
            confirm: Must be True to actually clear (safety check).

        Returns:
            Confirmation of cleared data.
        """
        if not confirm:
            return {
                "warning": "This will delete all request history. Set confirm=True to proceed.",
                "cleared": False,
            }

        mcp_ctx: MCPContext = ctx.request_context.lifespan_context
        storage = mcp_ctx.storage

        count = len(list(storage.get_all()))
        storage.clear()

        return {
            "cleared": True,
            "requests_deleted": count,
        }
