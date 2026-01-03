"""Debug toolbar API route handlers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from litestar.connection import WebSocket as LitestarWebSocket
from litestar.exceptions import NotFoundException
from litestar.response import Response

from debug_toolbar.core.panels.websocket import WebSocketPanel
from litestar import Request, Router, get, post, websocket

if TYPE_CHECKING:
    from debug_toolbar.core.storage import ToolbarStorage

logger = logging.getLogger(__name__)

DEFAULT_DISPLAY_DEPTH = 10
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_STRING = 1000
BYTES_PER_KB = 1024
QUERY_PREVIEW_LENGTH = 200


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _format_value(  # noqa: PLR0911, PLR0912, C901
    value: Any,
    max_depth: int = DEFAULT_DISPLAY_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_string: int = DEFAULT_MAX_STRING,
) -> str:
    """Format a value for HTML display."""
    if value is None:
        return "<span class='null'>null</span>"
    if isinstance(value, bool):
        return f"<span class='bool'>{str(value).lower()}</span>"
    if isinstance(value, int | float):
        if isinstance(value, float):
            return f"<span class='number'>{value:.4f}</span>"
        return f"<span class='number'>{value}</span>"
    if isinstance(value, str):
        if len(value) > max_string:
            return f"<span class='string'>{_escape_html(value[:max_string])}...</span>"
        return f"<span class='string'>{_escape_html(value)}</span>"
    if isinstance(value, list | tuple):
        if max_depth <= 0:
            return f"<span class='array'>[{len(value)} items]</span>"
        shown = value[:max_items]
        items = ", ".join(_format_value(v, max_depth - 1, max_items, max_string) for v in shown)
        if len(value) > max_items:
            return f"<span class='array'>[{items}, ...{len(value) - max_items} more]</span>"
        return f"<span class='array'>[{items}]</span>"
    if isinstance(value, dict):
        if max_depth <= 0:
            return f"<span class='object'>{{{len(value)} keys}}</span>"
        items = []
        dict_items = list(value.items())[:max_items]
        for k, v in dict_items:
            items.append(
                f"<strong>{_escape_html(str(k))}</strong>: {_format_value(v, max_depth - 1, max_items, max_string)}",
            )
        if len(value) > max_items:
            items.append(f"...{len(value) - max_items} more")
        return f"<span class='object'>{{{', '.join(items)}}}</span>"
    return f"<span class='unknown'>{_escape_html(str(value)[:max_string])}</span>"


_PANEL_RENDERERS: dict[str, Any] = {}


def _render_panel_content(stats: dict[str, Any], panel_id: str = "") -> str:
    """Render panel content as HTML with special handling for certain panels."""
    if not stats:
        return "<p class='empty'>No data</p>"

    # Initialize renderers lazily to avoid circular imports
    if not _PANEL_RENDERERS:
        _PANEL_RENDERERS.update(
            {
                "AlertsPanel": _render_alerts_panel,
                "MemoryPanel": _render_memory_panel,
                "ProfilingPanel": _render_profiling_panel,
                "AsyncProfilerPanel": _render_async_profiler_panel,
                "GraphQLPanel": _render_graphql_panel,
            },
        )

    # Use specialized renderer if available
    renderer = _PANEL_RENDERERS.get(panel_id)
    if renderer:
        return renderer(stats)

    # Default table rendering
    rows = []
    for key, value in stats.items():
        escaped_key = _escape_html(str(key))
        formatted_value = _format_value(value)
        rows.append(f"<tr><td class='key'>{escaped_key}</td><td class='value'>{formatted_value}</td></tr>")
    return f"<table class='panel-table'><tbody>{''.join(rows)}</tbody></table>"


def _render_alerts_panel(stats: dict[str, Any]) -> str:
    """Render alerts panel with severity-colored cards."""
    alerts = stats.get("alerts", [])
    if not alerts:
        return "<p class='empty alert-success'>✓ No issues detected</p>"

    severity_colors = {
        "critical": "#dc2626",
        "warning": "#f59e0b",
        "info": "#3b82f6",
    }
    severity_icons = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "(i)",
    }
    category_icons = {
        "security": "🔒",
        "performance": "⚡",
        "database": "🗄️",
        "configuration": "⚙️",
    }

    html = f"<div class='alerts-summary'><strong>{len(alerts)}</strong> issue(s) detected</div>"
    html += "<div class='alerts-container'>"

    for alert in alerts:
        severity = alert.get("severity", "info")
        category = alert.get("category", "")
        title = _escape_html(alert.get("title", "Alert"))
        message = _escape_html(alert.get("message", ""))
        suggestion = alert.get("suggestion", "")

        color = severity_colors.get(severity, "#6b7280")
        icon = severity_icons.get(severity, "•")
        cat_icon = category_icons.get(category, "")

        html += f"""
        <div class='alert-card alert-{severity}' style='border-left-color: {color}'>
            <div class='alert-header'>
                <span class='alert-icon'>{icon}</span>
                <span class='alert-title'>{title}</span>
                <span class='alert-category'>{cat_icon} {_escape_html(category)}</span>
            </div>
            <div class='alert-message'>{message}</div>
        """
        if suggestion:
            html += f"<div class='alert-suggestion'>💡 {_escape_html(suggestion)}</div>"
        html += "</div>"

    html += "</div>"
    return html


def _render_memory_panel(stats: dict[str, Any]) -> str:
    """Render memory panel with allocation details."""
    html = "<div class='memory-panel'>"

    # Summary stats
    peak = stats.get("peak_memory", 0)
    current = stats.get("current_memory", 0)
    alloc_count = stats.get("allocation_count", 0)
    backend = stats.get("backend", "unknown")

    html += f"""
    <div class='memory-summary'>
        <div class='memory-stat'>
            <span class='stat-value'>{_format_bytes(peak)}</span>
            <span class='stat-label'>Peak Memory</span>
        </div>
        <div class='memory-stat'>
            <span class='stat-value'>{_format_bytes(current)}</span>
            <span class='stat-label'>Current</span>
        </div>
        <div class='memory-stat'>
            <span class='stat-value'>{alloc_count}</span>
            <span class='stat-label'>Allocations</span>
        </div>
        <div class='memory-stat'>
            <span class='stat-value'>{_escape_html(backend)}</span>
            <span class='stat-label'>Backend</span>
        </div>
    </div>
    """

    # Top allocations
    top_allocs = stats.get("top_allocations", [])
    if top_allocs:
        html += "<h4>Top Allocations</h4>"
        html += "<div class='allocations-list'>"
        for alloc in top_allocs[:10]:
            size = alloc.get("size", 0)
            file_info = alloc.get("file") or alloc.get("location", "unknown")
            line = alloc.get("line", 0)
            location = f"{file_info}:{line}" if line > 0 else file_info
            location = _escape_html(str(location))
            count = alloc.get("count", 1)
            html += f"""
            <div class='allocation-item'>
                <span class='alloc-size'>{_format_bytes(size)}</span>
                <span class='alloc-location'>{location}</span>
                <span class='alloc-count'>({count} allocs)</span>
            </div>
            """
        html += "</div>"

    html += "</div>"
    return html


def _render_profiling_panel(stats: dict[str, Any]) -> str:
    """Render profiling panel with flame graph button."""
    html = "<div class='profiling-panel'>"

    # Stats
    total_time = stats.get("total_time", 0)
    function_count = stats.get("function_count", 0)
    has_flamegraph = stats.get("flamegraph_data") is not None

    html += f"""
    <div class='profiling-summary'>
        <div class='prof-stat'>
            <span class='stat-value'>{total_time * 1000:.2f}ms</span>
            <span class='stat-label'>Total Time</span>
        </div>
        <div class='prof-stat'>
            <span class='stat-value'>{function_count}</span>
            <span class='stat-label'>Functions</span>
        </div>
    </div>
    """

    if has_flamegraph:
        html += """
        <div class='flamegraph-actions'>
            <button class='flamegraph-btn' onclick='downloadFlamegraph()'>
                🔥 Download Flame Graph
            </button>
            <a class='flamegraph-link' href='https://www.speedscope.app/' target='_blank'>
                Open speedscope.app →
            </a>
        </div>
        <p class='flamegraph-hint'>Download the JSON and upload to speedscope.app to visualize</p>
        """
    else:
        html += "<p class='empty'>Flame graph not available for this request</p>"

    # Top functions
    top_funcs = stats.get("top_functions", [])
    if top_funcs:
        html += "<h4>Top Functions by Time</h4>"
        html += "<table class='panel-table'><tbody>"
        for func in top_funcs[:10]:
            # Handle both 'function' and 'name' keys
            func_name = func.get("function") or func.get("name", "unknown")
            filename = func.get("filename", "")
            lineno = func.get("lineno", 0)
            # Format as filename:lineno:function for better display
            if filename and filename != "unknown":
                short_file = filename.split("/")[-1] if "/" in filename else filename
                display_name = f"{short_file}:{lineno} {func_name}" if lineno else f"{short_file} {func_name}"
            else:
                display_name = func_name
            display_name = _escape_html(display_name)
            time_ms = func.get("cumulative_time", 0) * 1000
            calls = func.get("calls", 0)
            value = f"{time_ms:.2f}ms ({calls} calls)"
            html += f"<tr><td class='key'>{display_name}</td><td class='value'>{value}</td></tr>"
        html += "</tbody></table>"

    html += "</div>"
    return html


def _render_async_profiler_panel(stats: dict[str, Any]) -> str:
    """Render async profiler panel with timeline and task details."""
    html = "<div class='async-profiler-panel'>"

    summary = stats.get("summary", {})
    total_tasks = summary.get("total_tasks", 0)
    completed = summary.get("completed_tasks", 0)
    cancelled = summary.get("cancelled_tasks", 0)
    errors = summary.get("error_tasks", 0)
    blocking_count = summary.get("blocking_calls_count", 0)
    max_lag = summary.get("max_lag_ms", 0.0)
    has_warnings = summary.get("has_warnings", False)
    backend = _escape_html(stats.get("backend", "unknown"))

    html += f"""
    <div class='async-summary'>
        <div class='async-stat'>
            <span class='stat-value'>{total_tasks}</span>
            <span class='stat-label'>Total Tasks</span>
        </div>
        <div class='async-stat'>
            <span class='stat-value'>{completed}</span>
            <span class='stat-label'>Completed</span>
        </div>
        <div class='async-stat {"async-warning" if cancelled > 0 else ""}'>
            <span class='stat-value'>{cancelled}</span>
            <span class='stat-label'>Cancelled</span>
        </div>
        <div class='async-stat {"async-error" if errors > 0 else ""}'>
            <span class='stat-value'>{errors}</span>
            <span class='stat-label'>Errors</span>
        </div>
        <div class='async-stat {"async-error" if blocking_count > 0 else ""}'>
            <span class='stat-value'>{blocking_count}</span>
            <span class='stat-label'>Blocking Calls</span>
        </div>
        <div class='async-stat'>
            <span class='stat-value'>{max_lag:.1f}ms</span>
            <span class='stat-label'>Max Lag</span>
        </div>
        <div class='async-stat'>
            <span class='stat-value'>{backend}</span>
            <span class='stat-label'>Backend</span>
        </div>
    </div>
    """

    if has_warnings:
        html += """
        <div class='async-warning-banner'>
            <span class='warning-icon'>⚠️</span>
            <span>Blocking calls detected! These may impact application performance.</span>
        </div>
        """

    blocking_calls = stats.get("blocking_calls", [])
    if blocking_calls:
        html += "<h4>Blocking Calls</h4>"
        html += "<div class='blocking-calls-list'>"
        for call in blocking_calls[:10]:
            func_name = _escape_html(call.get("function_name", "unknown"))
            duration = call.get("duration_ms", 0.0)
            file_loc = _escape_html(call.get("file", "unknown"))
            line = call.get("line", 0)
            location = f"{file_loc}:{line}" if line > 0 else file_loc
            html += f"""
            <div class='blocking-call-item'>
                <div class='blocking-call-header'>
                    <span class='blocking-func'>{func_name}</span>
                    <span class='blocking-duration'>{duration:.2f}ms</span>
                </div>
                <div class='blocking-location'>{location}</div>
            </div>
            """
        html += "</div>"

    tasks = stats.get("tasks", [])
    created_tasks = [t for t in tasks if t.get("event_type") == "created"]
    if created_tasks:
        html += "<h4>Tasks</h4>"
        html += "<table class='panel-table'><tbody>"
        for task in created_tasks[:15]:
            task_name = _escape_html(task.get("task_name", "unknown"))
            coro_name = _escape_html(task.get("coro_name", ""))
            duration = task.get("duration_ms", 0)
            task_id = task.get("task_id", "")
            end_states = ("completed", "cancelled", "error")
            completion = next(
                (t for t in tasks if t.get("task_id") == task_id and t.get("event_type") in end_states),
                None,
            )
            allowed_statuses = {"completed", "cancelled", "error", "running", "unknown"}
            if completion:
                status = completion.get("event_type", "completed")
                if status not in allowed_statuses:
                    status = "unknown"
            else:
                status = "running"
            status_class = "async-status-" + status
            html += f"""
            <tr>
                <td class='key'>{task_name}<br><small class='coro-name'>{coro_name}</small></td>
                <td class='value'>
                    <span class='task-status {status_class}'>{_escape_html(status)}</span>
                    {f"<span class='task-duration'>{duration:.2f}ms</span>" if duration else ""}
                </td>
            </tr>
            """
        html += "</tbody></table>"

    timeline = stats.get("timeline", {})
    if timeline.get("events"):
        html += f"""
        <h4>Timeline</h4>
        <div class='timeline-info'>
            <span>Duration: {timeline.get("total_duration_ms", 0):.2f}ms</span>
            <span>Max Concurrent: {timeline.get("max_concurrent", 0)}</span>
        </div>
        """

    html += "</div>"
    return html


def _render_graphql_panel(stats: dict[str, Any]) -> str:  # noqa: C901, PLR0912
    """Render GraphQL panel with operations, resolvers, and analysis."""
    html = "<div class='graphql-panel'>"

    # Summary stats
    op_count = stats.get("operation_count", 0)
    total_time = stats.get("total_time_ms", 0.0)
    resolver_count = stats.get("resolver_count", 0)
    n1_count = stats.get("n_plus_one_count", 0)
    dup_count = stats.get("duplicate_count", 0)
    slow_count = stats.get("slow_operation_count", 0)
    has_issues = stats.get("has_issues", False)

    html += f"""
    <div class='graphql-summary'>
        <div class='graphql-stat'>
            <span class='stat-value'>{op_count}</span>
            <span class='stat-label'>Operations</span>
        </div>
        <div class='graphql-stat'>
            <span class='stat-value'>{total_time:.2f}ms</span>
            <span class='stat-label'>Total Time</span>
        </div>
        <div class='graphql-stat'>
            <span class='stat-value'>{resolver_count}</span>
            <span class='stat-label'>Resolvers</span>
        </div>
        <div class='graphql-stat {"graphql-warning" if n1_count > 0 else ""}'>
            <span class='stat-value'>{n1_count}</span>
            <span class='stat-label'>N+1 Issues</span>
        </div>
        <div class='graphql-stat {"graphql-warning" if dup_count > 0 else ""}'>
            <span class='stat-value'>{dup_count}</span>
            <span class='stat-label'>Duplicates</span>
        </div>
        <div class='graphql-stat {"graphql-warning" if slow_count > 0 else ""}'>
            <span class='stat-value'>{slow_count}</span>
            <span class='stat-label'>Slow Ops</span>
        </div>
    </div>
    """

    if has_issues:
        html += """
        <div class='graphql-warning-banner'>
            <span class='warning-icon'>⚠️</span>
            <span>Performance issues detected! Check N+1 patterns and duplicates below.</span>
        </div>
        """

    # N+1 Patterns
    n1_patterns = stats.get("n_plus_one_patterns", [])
    if n1_patterns:
        html += "<h4>N+1 Query Patterns</h4>"
        html += "<div class='n1-patterns-list'>"
        for pattern in n1_patterns:
            field = _escape_html(pattern.get("field_name", "unknown"))
            parent = _escape_html(pattern.get("parent_type", ""))
            count = pattern.get("count", 0)
            duration = pattern.get("total_duration_ms", 0.0)
            suggestion = _escape_html(pattern.get("suggestion", ""))
            html += f"""
            <div class='n1-pattern-item'>
                <div class='n1-header'>
                    <span class='n1-field'>{parent}.{field}</span>
                    <span class='n1-count'>Called {count}x</span>
                    <span class='n1-duration'>{duration:.2f}ms total</span>
                </div>
                <div class='n1-suggestion'>💡 {suggestion}</div>
            </div>
            """
        html += "</div>"

    # Duplicate Operations
    dups = stats.get("duplicate_operations", [])
    if dups:
        unique_count = len(set(dups))
        html += f"<h4>Duplicate Operations ({unique_count} unique, {len(dups)} total)</h4>"
        html += "<p class='dup-hint'>These queries were executed multiple times with the same parameters.</p>"

    # Operations list
    operations = stats.get("operations", [])
    if operations:
        html += "<h4>Operations</h4>"
        html += "<div class='operations-list'>"
        for op in operations:
            if isinstance(op, dict):
                op_data = op
            else:
                op_data = op.to_dict() if hasattr(op, "to_dict") else {}

            op_type = _escape_html(op_data.get("operation_type", "query"))
            op_name = _escape_html(op_data.get("operation_name") or "Anonymous")
            duration = op_data.get("duration_ms", 0.0)
            raw_query = op_data.get("query", "")
            query = _escape_html(raw_query[:QUERY_PREVIEW_LENGTH])
            truncated = "..." if len(raw_query) > QUERY_PREVIEW_LENGTH else ""
            resolvers = op_data.get("resolvers", [])
            errors = op_data.get("errors", [])

            op_class = f"op-{op_type}"
            error_class = " op-error" if errors else ""

            html += f"""
            <div class='operation-item {op_class}{error_class}'>
                <div class='op-header'>
                    <span class='op-type'>{op_type}</span>
                    <span class='op-name'>{op_name}</span>
                    <span class='op-duration'>{duration:.2f}ms</span>
                    <span class='op-resolvers'>{len(resolvers)} resolvers</span>
                </div>
                <pre class='op-query'>{query}{truncated}</pre>
            """

            if errors:
                html += "<div class='op-errors'>"
                for err in errors[:3]:
                    msg = _escape_html(str(err.get("message", "Unknown error")))
                    html += f"<div class='op-error-msg'>❌ {msg}</div>"
                html += "</div>"

            # Show slow resolvers
            slow_resolvers = [r for r in resolvers if isinstance(r, dict) and r.get("is_slow")]
            if slow_resolvers:
                html += "<div class='slow-resolvers'>"
                html += "<span class='slow-label'>Slow resolvers:</span>"
                for r in slow_resolvers[:5]:
                    r_name = _escape_html(r.get("field_path", r.get("field_name", "?")))
                    r_dur = r.get("duration_ms", 0.0)
                    html += f"<span class='slow-resolver'>{r_name} ({r_dur:.2f}ms)</span>"
                html += "</div>"

            html += "</div>"
        html += "</div>"

    if not operations:
        html += "<p class='empty'>No GraphQL operations recorded</p>"

    html += "</div>"
    return html


def _format_bytes(size: float) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size) < BYTES_PER_KB:
            return f"{size:.1f} {unit}"
        size /= BYTES_PER_KB
    return f"{size:.1f} TB"


def _render_request_row(request_id: UUID, data: dict[str, Any]) -> str:
    """Render a request row for the history table."""
    metadata = data.get("metadata", {})
    timing = data.get("timing_data", {})
    total_time = timing.get("total_time", 0) * 1000
    method = _escape_html(str(metadata.get("method", "GET")))
    path = _escape_html(str(metadata.get("path", "/")))
    status = metadata.get("status_code", 200)
    status_class = status // 100
    # Sanitize method for CSS class (only allow alphanumeric)
    method_class = "".join(c for c in method.lower() if c.isalnum())

    return f"""
        <tr class="request-row" data-request-id="{request_id}"
            onclick="window.location='/_debug_toolbar/{request_id}'">
            <td><code>{str(request_id)[:8]}</code></td>
            <td><span class="method method-{method_class}">{method}</span></td>
            <td class="path">{path}</td>
            <td><span class="status status-{status_class}xx">{status}</span></td>
            <td class="time">{total_time:.2f}ms</td>
        </tr>
    """


def create_debug_toolbar_router(storage: ToolbarStorage) -> Router:  # noqa: C901
    """Create the debug toolbar router with routes.

    Args:
        storage: The toolbar storage instance.

    Returns:
        Configured Router for debug toolbar.
    """

    async def get_toolbar_index() -> Response[str]:
        """Get the debug toolbar history page."""
        requests = storage.get_all()
        rows_html = [_render_request_row(rid, data) for rid, data in requests]
        empty_row = '<tr><td colspan="5" class="empty">No requests recorded yet</td></tr>'
        tbody_content = "".join(rows_html) if rows_html else empty_row

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug Toolbar - Request History</title>
    <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
    <script>document.documentElement.dataset.theme=localStorage.getItem('debug-toolbar-theme')||'dark';</script>
</head>
<body>
    <div class="toolbar-page">
        <header class="toolbar-header">
            <div class="header-row">
                <h1>Debug Toolbar</h1>
                <button class="toolbar-theme-btn page-theme-btn" onclick="togglePageTheme(this)" title="Toggle theme">
                    <span class="theme-icon"></span>
                </button>
            </div>
            <p>Request History ({len(requests)} requests)</p>
        </header>

        <main class="toolbar-main">
            <table class="requests-table">
                <thead>
                    <tr>
                        <th>Request ID</th>
                        <th>Method</th>
                        <th>Path</th>
                        <th>Status</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {tbody_content}
                </tbody>
            </table>
        </main>
    </div>
    <script src="/_debug_toolbar/static/toolbar.js"></script>
</body>
</html>"""
        return Response(content=html, media_type="text/html")

    async def get_request_detail(request_id: UUID) -> Response[str]:
        """Get detailed view for a specific request."""
        data = storage.get(request_id)
        if data is None:
            raise NotFoundException(f"Request {request_id} not found")

        metadata = data.get("metadata", {})
        timing = data.get("timing_data", {})
        panel_data = data.get("panel_data", {})
        total_time = timing.get("total_time", 0) * 1000

        method = _escape_html(str(metadata.get("method", "GET")))
        path = _escape_html(str(metadata.get("path", "/")))
        status = metadata.get("status_code", 200)
        status_class = status // 100
        # Sanitize method for CSS class
        method_class = "".join(c for c in method.lower() if c.isalnum())
        # Pre-escape metadata values for display
        query_string = _escape_html(str(metadata.get("query_string", "") or "(none)"))
        content_type = _escape_html(str(metadata.get("response_content_type", "N/A")))
        client_host = _escape_html(str(metadata.get("client_host", "N/A")))
        client_port = _escape_html(str(metadata.get("client_port", "N/A")))

        panels_html = []
        for panel_id, stats in panel_data.items():
            panel_content = _render_panel_content(stats, panel_id)
            # Sanitize panel_id for use in HTML id and JS (alphanumeric + underscore only)
            panel_id_class = "".join(c for c in str(panel_id) if c.isalnum() or c == "_")
            panel_title = _escape_html(str(panel_id).replace("Panel", ""))
            panels_html.append(f"""
                <div class="panel" id="panel-{panel_id_class}">
                    <div class="panel-header" onclick="togglePanel('{panel_id_class}')">
                        <span class="panel-title">{panel_title}</span>
                        <span class="panel-toggle">+</span>
                    </div>
                    <div class="panel-content">
                        {panel_content}
                    </div>
                </div>
            """)

        panels_section = "".join(panels_html) if panels_html else '<p class="empty">No panel data</p>'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug Toolbar - Request {str(request_id)[:8]}</title>
    <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
    <script>document.documentElement.dataset.theme=localStorage.getItem('debug-toolbar-theme')||'dark';</script>
</head>
<body>
    <div class="toolbar-page">
        <header class="toolbar-header">
            <a href="/_debug_toolbar/" class="back-link">&larr; Back to History</a>
            <div class="header-row">
                <h1>Request Details</h1>
                <button class="toolbar-theme-btn page-theme-btn" onclick="togglePageTheme(this)" title="Toggle theme">
                    <span class="theme-icon"></span>
                </button>
            </div>
            <div class="request-summary">
                <span class="method method-{method_class}">{method}</span>
                <span class="path">{path}</span>
                <span class="status status-{status_class}xx">{status}</span>
                <span class="time">{total_time:.2f}ms</span>
            </div>
        </header>

        <main class="toolbar-main">
            <section class="metadata-section">
                <h2>Request Metadata</h2>
                <dl class="metadata-list">
                    <dt>Request ID</dt>
                    <dd><code>{request_id}</code></dd>
                    <dt>Method</dt>
                    <dd>{method}</dd>
                    <dt>Path</dt>
                    <dd>{path}</dd>
                    <dt>Query String</dt>
                    <dd><code>{query_string}</code></dd>
                    <dt>Status Code</dt>
                    <dd>{status}</dd>
                    <dt>Content Type</dt>
                    <dd>{content_type}</dd>
                    <dt>Client</dt>
                    <dd>{client_host}:{client_port}</dd>
                </dl>
            </section>

            <section class="panels-section">
                <h2>Panels</h2>
                <div class="panels-container">
                    {panels_section}
                </div>
            </section>
        </main>
    </div>
    <script src="/_debug_toolbar/static/toolbar.js"></script>
</body>
</html>"""
        return Response(content=html, media_type="text/html")

    async def get_requests_json() -> list[dict[str, Any]]:
        """Get all requests as JSON."""
        requests = storage.get_all()
        return [
            {
                "request_id": str(rid),
                "metadata": d.get("metadata", {}),
                "timing": d.get("timing_data", {}),
            }
            for rid, d in requests
        ]

    async def get_request_json(request_id: UUID) -> dict[str, Any]:
        """Get a specific request as JSON."""
        data = storage.get(request_id)
        if data is None:
            raise NotFoundException(f"Request {request_id} not found")
        return {"request_id": str(request_id), **data}

    async def post_explain(request: Request, data: dict[str, Any]) -> dict[str, Any]:
        """Execute EXPLAIN for a SQL query.

        Expects JSON body with 'sql' and optional 'parameters'.
        Requires app.state.db_engine to be set.
        """
        from debug_toolbar.extras.advanced_alchemy.panel import ExplainExecutor

        sql = data.get("sql")
        parameters = data.get("parameters")
        if not sql:
            return {"error": "Missing 'sql' in request body"}

        engine = getattr(request.app.state, "db_engine", None)
        if not engine:
            return {"error": "No database engine available for EXPLAIN"}

        return await ExplainExecutor.execute_explain(engine, sql, parameters)

    async def get_static_css() -> Response[str]:
        """Serve the toolbar CSS."""
        css = get_toolbar_css()
        return Response(content=css, media_type="text/css")

    async def get_static_js() -> Response[str]:
        """Serve the toolbar JavaScript."""
        js = get_toolbar_js()
        return Response(content=js, media_type="application/javascript")

    async def get_flamegraph_data(request_id: UUID) -> Response[str]:
        """Get flame graph data for a specific request in speedscope JSON format.

        This endpoint returns speedscope-compatible JSON that can be:
        1. Downloaded and opened in speedscope.app
        2. Opened directly via speedscope.app URL with profileURL parameter
        3. Embedded in a viewer that supports speedscope format
        """
        data = storage.get(request_id)
        if data is None:
            raise NotFoundException(f"Request {request_id} not found")

        panel_data = data.get("panel_data", {})
        profiling_data = panel_data.get("ProfilingPanel", {})
        flamegraph_data = profiling_data.get("flamegraph_data")

        if not flamegraph_data:
            return Response(
                content='{"error": "Flame graph data not available for this request"}',
                media_type="application/json",
                status_code=404,
            )

        return Response(
            content=json.dumps(flamegraph_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="flamegraph-{str(request_id)[:8]}.speedscope.json"'},
        )

    index_handler = get("/")(get_toolbar_index)
    detail_handler = get("/{request_id:uuid}")(get_request_detail)
    api_requests_handler = get("/api/requests")(get_requests_json)
    api_request_handler = get("/api/requests/{request_id:uuid}")(get_request_json)
    api_explain_handler = post("/api/explain")(post_explain)
    api_flamegraph_handler = get("/api/flamegraph/{request_id:uuid}")(get_flamegraph_data)
    css_handler = get("/static/toolbar.css")(get_static_css)
    js_handler = get("/static/toolbar.js")(get_static_js)

    @get("/api/websocket/stats")
    async def get_websocket_stats() -> dict:
        """Get current WebSocket statistics."""
        return WebSocketPanel.get_current_stats()

    @websocket("/ws/live")
    async def websocket_live_handler(socket: LitestarWebSocket) -> None:
        """WebSocket endpoint for live WebSocket panel updates.

        Clients connect here to receive real-time updates about WebSocket
        connections and messages being tracked by the debug toolbar.
        """
        await socket.accept()
        queue = WebSocketPanel.subscribe()
        try:
            initial_stats = WebSocketPanel.get_current_stats()
            logger.debug("Live WS: Sending initial stats: %s", initial_stats)
            await socket.send_json({"type": "init", "data": initial_stats})

            while True:
                message = await queue.get()
                try:
                    await socket.send_text(message)
                except Exception:
                    break
        finally:
            WebSocketPanel.unsubscribe(queue)

    return Router(
        path="/_debug_toolbar",
        route_handlers=[
            index_handler,
            detail_handler,
            api_requests_handler,
            api_request_handler,
            api_explain_handler,
            api_flamegraph_handler,
            get_websocket_stats,
            css_handler,
            js_handler,
            websocket_live_handler,
        ],
        tags=["Debug Toolbar"],
    )


def get_toolbar_css() -> str:
    """Get the toolbar CSS styles.

    The inline toolbar supports 4 positions: right (default), left, top, bottom.
    Position is controlled via data-position attribute on #debug-toolbar element.
    Theme is controlled via data-theme attribute (dark/light).
    """
    return """
:root, [data-theme="dark"] {
    --dt-bg-primary: #1e1e1e;
    --dt-bg-secondary: #2d2d2d;
    --dt-bg-tertiary: #3d3d3d;
    --dt-text-primary: #ffffff;
    --dt-text-secondary: #b0b0b0;
    --dt-text-muted: #9a9a9a;
    --dt-accent: #007acc;
    --dt-accent-hover: #0098ff;
    --dt-success: #4ec9b0;
    --dt-warning: #dcdcaa;
    --dt-error: #f14c4c;
    --dt-border: #404040;
    --dt-font-mono: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    --dt-font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

[data-theme="light"] {
    --dt-bg-primary: #ffffff;
    --dt-bg-secondary: #f5f5f5;
    --dt-bg-tertiary: #e8e8e8;
    --dt-text-primary: #1e1e1e;
    --dt-text-secondary: #555555;
    --dt-text-muted: #6b6b6b;
    --dt-accent: #0066cc;
    --dt-accent-hover: #0052a3;
    --dt-success: #2e7d32;
    --dt-warning: #f57c00;
    --dt-error: #c62828;
    --dt-border: #d0d0d0;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    padding: 0;
    font-family: var(--dt-font-sans);
    background: var(--dt-bg-primary);
    color: var(--dt-text-primary);
    line-height: 1.5;
}

.toolbar-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.toolbar-header {
    background: var(--dt-bg-secondary);
    padding: 20px 24px;
    border-bottom: 2px solid var(--dt-accent);
}

.header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.toolbar-header h1 {
    margin: 0 0 8px 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--dt-accent);
}

.page-theme-btn {
    width: 32px;
    height: 32px;
    font-size: 18px;
}

.theme-icon::before {
    content: '\u2600';
}

[data-theme="light"] .theme-icon::before {
    content: '\u263e';
}

.toolbar-header p {
    margin: 0;
    color: var(--dt-text-secondary);
    font-size: 14px;
}

.back-link {
    display: inline-block;
    margin-bottom: 12px;
    color: var(--dt-accent);
    text-decoration: none;
    font-size: 14px;
}

.back-link:hover {
    color: var(--dt-accent-hover);
    text-decoration: underline;
}

.request-summary {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
    font-family: var(--dt-font-mono);
    font-size: 14px;
}

.toolbar-main {
    flex: 1;
    padding: 24px;
}

.requests-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.requests-table th,
.requests-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--dt-border);
}

.requests-table th {
    background: var(--dt-bg-secondary);
    color: var(--dt-text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}

.requests-table tbody tr {
    cursor: pointer;
    transition: background 0.15s;
}

.requests-table tbody tr:hover {
    background: var(--dt-bg-secondary);
}

.requests-table code {
    font-family: var(--dt-font-mono);
    color: var(--dt-text-secondary);
}

.requests-table .path {
    font-family: var(--dt-font-mono);
    color: var(--dt-text-primary);
}

.requests-table .time {
    font-family: var(--dt-font-mono);
    color: var(--dt-success);
}

.empty {
    text-align: center;
    color: var(--dt-text-muted);
    padding: 40px !important;
}

.method {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--dt-font-mono);
    text-transform: uppercase;
}

.method-get { background: #2d5a2d; color: #98c379; }
.method-post { background: #5a4a2d; color: #e5c07b; }
.method-put { background: #2d4a5a; color: #61afef; }
.method-patch { background: #4a2d5a; color: #c678dd; }
.method-delete { background: #5a2d2d; color: #e06c75; }

.status {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--dt-font-mono);
}

.status-2xx { background: #2d5a2d; color: #98c379; }
.status-3xx { background: #2d4a5a; color: #61afef; }
.status-4xx { background: #5a4a2d; color: #e5c07b; }
.status-5xx { background: #5a2d2d; color: #e06c75; }

.metadata-section,
.panels-section {
    margin-bottom: 32px;
}

.metadata-section h2,
.panels-section h2 {
    font-size: 16px;
    font-weight: 600;
    color: var(--dt-text-secondary);
    margin: 0 0 16px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metadata-list {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 8px 16px;
    background: var(--dt-bg-secondary);
    padding: 16px;
    border-radius: 8px;
}

.metadata-list dt {
    color: var(--dt-text-secondary);
    font-size: 13px;
}

.metadata-list dd {
    margin: 0;
    font-family: var(--dt-font-mono);
    font-size: 13px;
    word-break: break-all;
}

.metadata-list code {
    background: var(--dt-bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
}

.panels-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.panel {
    background: var(--dt-bg-secondary);
    border-radius: 8px;
    overflow: hidden;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    transition: background 0.15s;
}

.panel-header:hover {
    background: var(--dt-bg-tertiary);
}

.panel-title {
    font-weight: 500;
    color: var(--dt-text-primary);
}

.panel-toggle {
    color: var(--dt-text-muted);
    font-family: var(--dt-font-mono);
    font-size: 18px;
    width: 24px;
    text-align: center;
}

.panel-content {
    padding: 16px;
    border-top: 1px solid var(--dt-border);
    background: var(--dt-bg-primary);
    max-height: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-height 0.25s ease-out, opacity 0.2s ease-out, padding 0.25s ease-out;
    padding: 0 16px;
}

.panel-content.expanded {
    max-height: 500px;
    overflow-y: auto;
    opacity: 1;
    padding: 16px;
}

.panel-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.panel-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--dt-border);
    vertical-align: top;
}

.panel-table .key {
    width: 200px;
    color: var(--dt-text-secondary);
    font-family: var(--dt-font-mono);
}

.panel-table .value {
    font-family: var(--dt-font-mono);
    word-break: break-all;
}

.null { color: var(--dt-text-muted); font-style: italic; }
.bool { color: #569cd6; }
.number { color: var(--dt-success); }
.string { color: #ce9178; }
.array { color: var(--dt-warning); }
.object { color: #9cdcfe; }
.unknown { color: var(--dt-text-secondary); }

.array-items, .object-items {
    padding-left: 16px;
    border-left: 2px solid var(--dt-border);
    margin: 4px 0;
}

.array-item, .object-item {
    padding: 2px 0;
    font-size: 12px;
}

.array-more, .object-more {
    color: var(--dt-text-muted);
    font-style: italic;
    padding: 2px 0;
}

#debug-toolbar {
    position: fixed;
    background: var(--dt-bg-primary);
    color: var(--dt-text-primary);
    font-family: var(--dt-font-mono);
    font-size: 12px;
    z-index: 99999;
    box-shadow: 0 0 12px rgba(0, 0, 0, 0.3);
    display: flex;
    overflow: hidden;
}

/* Default position: right */
#debug-toolbar,
#debug-toolbar[data-position="right"] {
    top: 0;
    right: 0;
    bottom: 0;
    width: 400px;
    min-width: 250px;
    max-width: 80vw;
    border-left: 2px solid var(--dt-accent);
    flex-direction: column;
}

#debug-toolbar[data-position="left"] {
    top: 0;
    left: 0;
    bottom: 0;
    right: auto;
    width: 400px;
    min-width: 250px;
    max-width: 80vw;
    border-right: 2px solid var(--dt-accent);
    border-left: none;
    flex-direction: column;
}

#debug-toolbar[data-position="top"] {
    top: 0;
    left: 0;
    right: 0;
    bottom: auto;
    width: 100vw;
    max-width: 100vw;
    height: auto;
    min-height: 40px;
    max-height: 60vh;
    border-bottom: 2px solid var(--dt-accent);
    border-left: none;
    border-right: none;
    flex-direction: column;
}

#debug-toolbar[data-position="bottom"] {
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    width: 100vw;
    max-width: 100vw;
    height: auto;
    min-height: 40px;
    max-height: 60vh;
    border-top: 2px solid var(--dt-accent);
    border-left: none;
    border-right: none;
    flex-direction: column;
}

/* Collapsed state - hide everything except collapse button */
#debug-toolbar.collapsed .toolbar-panels,
#debug-toolbar.collapsed .toolbar-details,
#debug-toolbar.collapsed .toolbar-content,
#debug-toolbar.collapsed .toolbar-brand,
#debug-toolbar.collapsed .toolbar-time,
#debug-toolbar.collapsed .toolbar-request-id,
#debug-toolbar.collapsed .toolbar-history-link,
#debug-toolbar.collapsed .toolbar-theme-btn,
#debug-toolbar.collapsed .toolbar-position-btn,
#debug-toolbar.collapsed .toolbar-position-controls,
#debug-toolbar.collapsed .toolbar-resize-handle {
    display: none !important;
}

/* Collapsed state for side positions - shrink to just the button */
#debug-toolbar.collapsed[data-position="right"],
#debug-toolbar[data-position="right"].collapsed,
#debug-toolbar.collapsed[data-position="left"],
#debug-toolbar[data-position="left"].collapsed {
    width: auto;
    min-width: 0;
    max-width: 50px;
}

#debug-toolbar.collapsed[data-position="top"],
#debug-toolbar[data-position="top"].collapsed,
#debug-toolbar.collapsed[data-position="bottom"],
#debug-toolbar[data-position="bottom"].collapsed {
    height: auto;
    min-height: 0;
    max-height: 50px;
}

/* Collapsed toolbar bar should be minimal */
#debug-toolbar.collapsed .toolbar-bar {
    padding: 6px;
    justify-content: center;
}

/* Resize handle */
.toolbar-resize-handle {
    position: absolute;
    background: transparent;
    z-index: 10;
}

#debug-toolbar[data-position="right"] .toolbar-resize-handle {
    left: 0;
    top: 0;
    bottom: 0;
    width: 6px;
    cursor: ew-resize;
}

#debug-toolbar[data-position="left"] .toolbar-resize-handle {
    right: 0;
    top: 0;
    bottom: 0;
    width: 6px;
    cursor: ew-resize;
}

#debug-toolbar[data-position="top"] .toolbar-resize-handle {
    left: 0;
    right: 0;
    bottom: 0;
    height: 6px;
    cursor: ns-resize;
}

#debug-toolbar[data-position="bottom"] .toolbar-resize-handle {
    left: 0;
    right: 0;
    top: 0;
    height: 6px;
    cursor: ns-resize;
}

.toolbar-resize-handle:hover {
    background: var(--dt-accent);
    opacity: 0.5;
}

/* Toolbar content area */
.toolbar-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
}

.toolbar-bar {
    display: flex;
    align-items: center;
    padding: 8px 16px;
    gap: 12px;
    flex-wrap: wrap;
}

/* Horizontal layout for top/bottom positions */
#debug-toolbar[data-position="top"] .toolbar-bar,
#debug-toolbar[data-position="bottom"] .toolbar-bar {
    flex-direction: row;
    flex-wrap: nowrap;
    width: 100%;
}

#debug-toolbar[data-position="top"] .toolbar-panels,
#debug-toolbar[data-position="bottom"] .toolbar-panels {
    flex: 1;
    flex-wrap: wrap;
    justify-content: flex-start;
}

/* Vertical layout for side positions */
#debug-toolbar[data-position="right"] .toolbar-bar,
#debug-toolbar[data-position="left"] .toolbar-bar {
    flex-direction: column;
    align-items: flex-start;
}

#debug-toolbar[data-position="right"] .toolbar-panels,
#debug-toolbar[data-position="left"] .toolbar-panels {
    flex-direction: column;
    width: 100%;
}

#debug-toolbar[data-position="right"] .toolbar-panel-btn,
#debug-toolbar[data-position="left"] .toolbar-panel-btn {
    width: 100%;
    text-align: left;
}

.toolbar-controls {
    display: flex;
    gap: 8px;
    align-items: center;
}

.toolbar-position-controls {
    display: flex;
    gap: 4px;
}

.toolbar-position-btn,
.toolbar-theme-btn {
    background: var(--dt-bg-tertiary);
    border: none;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    color: var(--dt-text-secondary);
    cursor: pointer;
    font-size: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, color 0.15s;
}

.toolbar-position-btn:hover,
.toolbar-theme-btn:hover {
    background: var(--dt-accent);
    color: white;
}

.toolbar-position-btn.active {
    background: var(--dt-accent);
    color: white;
}

.toolbar-theme-btn {
    font-size: 14px;
}

.toolbar-collapse-btn {
    background: var(--dt-bg-tertiary);
    border: none;
    width: 28px;
    height: 28px;
    border-radius: 4px;
    color: var(--dt-text-secondary);
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, color 0.15s, transform 0.2s;
    flex-shrink: 0;
}

.toolbar-collapse-btn:hover {
    background: var(--dt-accent);
    color: white;
}

/* Right position (default): expanded » (points right to collapse), collapsed « (points left to expand) */
#debug-toolbar[data-position="right"] .toolbar-collapse-btn .collapse-icon,
#debug-toolbar:not([data-position]) .toolbar-collapse-btn .collapse-icon {
    transform: rotate(180deg);
}

#debug-toolbar[data-position="right"].collapsed .toolbar-collapse-btn .collapse-icon,
#debug-toolbar:not([data-position]).collapsed .toolbar-collapse-btn .collapse-icon {
    transform: rotate(0deg);
}

/* Left position: expanded « (points left to collapse), collapsed » (points right to expand) */
#debug-toolbar[data-position="left"] .toolbar-collapse-btn .collapse-icon {
    transform: rotate(0deg);
}

#debug-toolbar[data-position="left"].collapsed .toolbar-collapse-btn .collapse-icon {
    transform: rotate(180deg);
}

#debug-toolbar[data-position="top"] .toolbar-collapse-btn .collapse-icon {
    transform: rotate(90deg);
}

#debug-toolbar[data-position="top"].collapsed .toolbar-collapse-btn .collapse-icon {
    transform: rotate(-90deg);
}

#debug-toolbar[data-position="bottom"] .toolbar-collapse-btn .collapse-icon {
    transform: rotate(-90deg);
}

#debug-toolbar[data-position="bottom"].collapsed .toolbar-collapse-btn .collapse-icon {
    transform: rotate(90deg);
}

.toolbar-brand {
    font-weight: bold;
    color: var(--dt-accent);
    cursor: pointer;
}

.toolbar-brand:hover {
    color: var(--dt-accent-hover);
}

.toolbar-time {
    color: var(--dt-success);
}

.toolbar-panels {
    display: flex;
    gap: 8px;
    flex: 1;
}

.toolbar-panel-btn {
    background: var(--dt-bg-secondary);
    border: none;
    padding: 4px 12px;
    border-radius: 4px;
    color: var(--dt-text-secondary);
    cursor: pointer;
    font-family: var(--dt-font-mono);
    font-size: 12px;
    transition: all 0.15s;
}

.toolbar-panel-btn:hover {
    background: var(--dt-bg-tertiary);
    color: var(--dt-text-primary);
}

.toolbar-panel-btn.active {
    background: var(--dt-accent);
    color: white;
}

.toolbar-request-id {
    color: var(--dt-text-muted);
}

.toolbar-history-link {
    color: var(--dt-accent);
    text-decoration: none;
}

.toolbar-history-link:hover {
    text-decoration: underline;
}

.toolbar-details {
    max-height: 0;
    overflow: hidden;
    border-top: 1px solid var(--dt-border);
    padding: 0 16px;
    background: var(--dt-bg-secondary);
    opacity: 0;
    transition: max-height 0.3s ease-out, opacity 0.2s ease-out, padding 0.3s ease-out;
}

.toolbar-details.expanded {
    max-height: 60vh;
    overflow-y: auto;
    padding: 16px;
    opacity: 1;
}

.sql-query-container {
    margin-bottom: 16px;
    background: var(--dt-bg-tertiary);
    border-radius: 6px;
    padding: 12px;
}

.sql-query-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.sql-query-title {
    font-weight: 600;
    color: var(--dt-text-primary);
}

.sql-query-code {
    background: var(--dt-bg-primary);
    padding: 10px;
    border-radius: 4px;
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-warning);
    overflow-x: auto;
    margin-bottom: 8px;
    white-space: pre-wrap;
    word-break: break-all;
}

.sql-query-params {
    font-size: 11px;
    color: var(--dt-text-secondary);
    margin-bottom: 8px;
}

.sql-explain-btn {
    background: var(--dt-accent);
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 11px;
    font-family: var(--dt-font-mono);
    cursor: pointer;
    transition: background 0.15s;
}

.sql-explain-btn:hover {
    background: var(--dt-accent-hover);
}

.sql-explain-btn:disabled {
    background: var(--dt-bg-tertiary);
    color: var(--dt-text-muted);
    cursor: not-allowed;
}

/* N+1 Detection Styles */
.sql-summary {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--dt-border);
}

.sql-summary h3 {
    margin: 0;
    color: var(--dt-text-primary);
}

.sql-total-time {
    color: var(--dt-text-secondary);
    font-size: 13px;
}

.n-plus-one-warning {
    background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(234, 179, 8, 0.05));
    border: 1px solid rgba(234, 179, 8, 0.4);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;
}

.n-plus-one-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    color: var(--dt-warning);
    font-size: 14px;
}

.warning-icon {
    font-size: 18px;
}

.n-plus-one-count {
    margin-left: auto;
    background: rgba(234, 179, 8, 0.2);
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
}

.n-plus-one-groups {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.n-plus-one-group {
    background: var(--dt-bg-secondary);
    border-radius: 6px;
    padding: 12px;
    border-left: 3px solid var(--dt-warning);
}

.n-plus-one-group-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    font-size: 12px;
}

.group-count {
    background: var(--dt-error);
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 11px;
}

.group-origin {
    color: var(--dt-text-primary);
    font-family: var(--dt-font-mono);
}

.group-time {
    margin-left: auto;
    color: var(--dt-text-secondary);
}

.n-plus-one-sql {
    background: var(--dt-bg-primary);
    padding: 8px 10px;
    border-radius: 4px;
    font-family: var(--dt-font-mono);
    font-size: 11px;
    color: var(--dt-warning);
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    margin-bottom: 8px;
}

.n-plus-one-suggestion {
    font-size: 12px;
    color: var(--dt-text-secondary);
    background: rgba(34, 197, 94, 0.1);
    padding: 8px 10px;
    border-radius: 4px;
    margin-bottom: 8px;
}

.n-plus-one-stack {
    font-size: 11px;
    color: var(--dt-text-secondary);
}

.n-plus-one-stack summary {
    cursor: pointer;
    padding: 4px 0;
}

.stack-frames {
    padding: 8px;
    background: var(--dt-bg-primary);
    border-radius: 4px;
    margin-top: 4px;
}

.stack-frame {
    padding: 4px 0;
    border-bottom: 1px solid var(--dt-border);
}

.stack-frame:last-child {
    border-bottom: none;
}

.frame-location {
    color: var(--dt-accent);
    font-family: var(--dt-font-mono);
}

.frame-function {
    color: var(--dt-success);
    font-family: var(--dt-font-mono);
}

.frame-code {
    color: var(--dt-text-muted);
    font-family: var(--dt-font-mono);
    padding-left: 12px;
    margin-top: 2px;
}

/* Query badges */
.query-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    margin-left: 8px;
    text-transform: uppercase;
}

.badge-n-plus-one {
    background: rgba(234, 179, 8, 0.2);
    color: var(--dt-warning);
    border: 1px solid rgba(234, 179, 8, 0.4);
}

.badge-slow {
    background: rgba(239, 68, 68, 0.2);
    color: var(--dt-error);
    border: 1px solid rgba(239, 68, 68, 0.4);
}

.badge-duplicate {
    background: rgba(99, 102, 241, 0.2);
    color: var(--dt-accent);
    border: 1px solid rgba(99, 102, 241, 0.4);
}

/* Highlight flagged queries */
.sql-query-container.is-n-plus-one {
    border-left: 3px solid var(--dt-warning);
}

.sql-query-container.is-slow {
    border-left: 3px solid var(--dt-error);
}

.sql-query-container.is-duplicate {
    border-left: 3px solid var(--dt-accent);
}

.explain-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    z-index: 100000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.explain-modal-content {
    background: var(--dt-bg-primary);
    border: 2px solid var(--dt-accent);
    border-radius: 8px;
    max-width: 900px;
    max-height: 80vh;
    width: 100%;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.explain-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--dt-border);
}

.explain-modal-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--dt-accent);
    margin: 0;
}

.explain-modal-close {
    background: transparent;
    border: none;
    color: var(--dt-text-secondary);
    font-size: 24px;
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background 0.15s, color 0.15s;
}

.explain-modal-close:hover {
    background: var(--dt-bg-tertiary);
    color: var(--dt-text-primary);
}

.explain-modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
}

.explain-result {
    font-family: var(--dt-font-mono);
    font-size: 12px;
}

.explain-result pre {
    background: var(--dt-bg-secondary);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 0;
}

.explain-error {
    color: var(--dt-error);
    padding: 12px;
    background: rgba(241, 76, 76, 0.1);
    border-radius: 4px;
    border-left: 3px solid var(--dt-error);
}

.toolbar-controls-separator {
    color: var(--dt-text-muted);
    margin: 0 4px;
    font-size: 14px;
}

.toolbar-request-info {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--dt-text-secondary);
}

/* Alerts Panel Styles */
.alerts-summary {
    padding: 12px 16px;
    background: var(--dt-bg-tertiary);
    border-radius: 6px;
    margin-bottom: 16px;
    color: var(--dt-warning);
}

.alert-success {
    color: var(--dt-success) !important;
    background: rgba(78, 201, 176, 0.1);
    padding: 16px;
    border-radius: 6px;
    text-align: center;
}

.alerts-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.alert-card {
    background: var(--dt-bg-secondary);
    border-radius: 6px;
    border-left: 4px solid;
    padding: 12px 16px;
}

.alert-critical { border-left-color: #dc2626; background: rgba(220, 38, 38, 0.1); }
.alert-warning { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
.alert-info { border-left-color: #3b82f6; background: rgba(59, 130, 246, 0.1); }

.alert-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.alert-icon { font-size: 16px; }
.alert-title { font-weight: 600; color: var(--dt-text-primary); flex: 1; }
.alert-category { font-size: 11px; color: var(--dt-text-muted); text-transform: uppercase; }
.alert-message { color: var(--dt-text-secondary); font-size: 13px; line-height: 1.5; }
.alert-suggestion {
    margin-top: 8px;
    padding: 8px 12px;
    background: rgba(34, 197, 94, 0.1);
    border-radius: 4px;
    font-size: 12px;
    color: var(--dt-success);
}

/* Memory Panel Styles */
.memory-panel h4 { margin: 16px 0 12px; color: var(--dt-text-secondary); font-size: 13px; }

.memory-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}

.memory-stat {
    background: var(--dt-bg-secondary);
    padding: 12px 16px;
    border-radius: 6px;
    text-align: center;
}

.stat-value {
    display: block;
    font-size: 18px;
    font-weight: 600;
    color: var(--dt-accent);
    font-family: var(--dt-font-mono);
}

.stat-label {
    display: block;
    font-size: 11px;
    color: var(--dt-text-muted);
    text-transform: uppercase;
    margin-top: 4px;
}

.allocations-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.allocation-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: var(--dt-bg-secondary);
    border-radius: 4px;
    font-size: 12px;
    font-family: var(--dt-font-mono);
}

.alloc-size {
    min-width: 80px;
    color: var(--dt-warning);
    font-weight: 600;
}

.alloc-location {
    flex: 1;
    color: var(--dt-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
}

.alloc-count {
    color: var(--dt-text-muted);
}

/* Profiling Panel Styles */
.profiling-panel h4 { margin: 16px 0 12px; color: var(--dt-text-secondary); font-size: 13px; }

.profiling-summary {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
}

.prof-stat {
    background: var(--dt-bg-secondary);
    padding: 12px 20px;
    border-radius: 6px;
    text-align: center;
}

.flamegraph-actions {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 16px 0;
}

.flamegraph-btn {
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
}

.flamegraph-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4);
}

.flamegraph-link {
    color: var(--dt-accent);
    text-decoration: none;
    font-size: 13px;
}

.flamegraph-link:hover { text-decoration: underline; }

.flamegraph-hint {
    font-size: 12px;
    color: var(--dt-text-muted);
    margin: 8px 0 16px;
}

/* Async Profiler Panel Styles */
.async-profiler-panel h4 { margin: 16px 0 12px; color: var(--dt-text-secondary); font-size: 13px; }

.async-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
}

.async-stat {
    background: var(--dt-bg-secondary);
    padding: 10px 14px;
    border-radius: 6px;
    text-align: center;
}

.async-stat.async-warning .stat-value { color: var(--dt-warning); }
.async-stat.async-error .stat-value { color: var(--dt-error); }

.async-warning-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(234, 179, 8, 0.05));
    border: 1px solid rgba(234, 179, 8, 0.4);
    border-radius: 6px;
    margin-bottom: 16px;
    color: var(--dt-warning);
    font-size: 13px;
}

.blocking-calls-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
}

.blocking-call-item {
    background: var(--dt-bg-secondary);
    border-left: 3px solid var(--dt-error);
    padding: 10px 12px;
    border-radius: 0 4px 4px 0;
}

.blocking-call-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.blocking-func {
    font-family: var(--dt-font-mono);
    font-weight: 600;
    color: var(--dt-text-primary);
}

.blocking-duration {
    font-family: var(--dt-font-mono);
    color: var(--dt-error);
    font-weight: 600;
}

.blocking-location {
    font-family: var(--dt-font-mono);
    font-size: 11px;
    color: var(--dt-text-muted);
}

.coro-name {
    font-family: var(--dt-font-mono);
    color: var(--dt-text-muted);
    font-size: 11px;
}

.task-status {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    margin-right: 8px;
}

.async-status-completed { background: rgba(78, 201, 176, 0.2); color: var(--dt-success); }
.async-status-cancelled { background: rgba(220, 220, 170, 0.2); color: var(--dt-warning); }
.async-status-error { background: rgba(241, 76, 76, 0.2); color: var(--dt-error); }
.async-status-running { background: rgba(0, 122, 204, 0.2); color: var(--dt-accent); }

.task-duration {
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-text-secondary);
}

.timeline-info {
    display: flex;
    gap: 20px;
    padding: 10px 14px;
    background: var(--dt-bg-secondary);
    border-radius: 6px;
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-text-secondary);
}

/* WebSocket Panel Styles */
.websocket-panel h4 { margin: 16px 0 12px; color: var(--dt-text-secondary); font-size: 13px; }

.ws-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
}

.ws-stat {
    background: var(--dt-bg-secondary);
    padding: 10px 14px;
    border-radius: 6px;
    text-align: center;
}

.ws-no-connections { color: var(--dt-text-muted); }
.ws-hint { color: var(--dt-text-muted); font-size: 12px; margin-top: 8px; }

.ws-connections { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }

.ws-connection {
    background: var(--dt-bg-secondary);
    border-radius: 6px;
    padding: 12px;
    border-left: 3px solid var(--dt-accent);
}

.ws-connection-active { border-left-color: var(--dt-success); }
.ws-connection-closed { border-left-color: var(--dt-text-muted); opacity: 0.8; }

.ws-conn-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}

.ws-conn-id {
    font-family: var(--dt-font-mono);
    background: var(--dt-bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    color: var(--dt-text-secondary);
}

.ws-conn-path {
    font-family: var(--dt-font-mono);
    font-weight: 600;
    color: var(--dt-text-primary);
}

.ws-conn-state {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    margin-left: auto;
}

.ws-state-connected, .ws-state-connecting { background: rgba(78, 201, 176, 0.2); color: var(--dt-success); }
.ws-state-closing { background: rgba(220, 220, 170, 0.2); color: var(--dt-warning); }
.ws-state-closed { background: rgba(128, 128, 128, 0.2); color: var(--dt-text-muted); }

.ws-conn-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-text-secondary);
}

.ws-conn-close { color: var(--dt-text-muted); }

.ws-messages { margin-top: 10px; }
.ws-messages summary { cursor: pointer; color: var(--dt-text-secondary); font-size: 12px; }
.ws-messages summary:hover { color: var(--dt-text-primary); }

.ws-message-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 8px;
    padding-left: 10px;
    border-left: 2px solid var(--dt-border);
}

.ws-message {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--dt-font-mono);
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 4px;
    background: var(--dt-bg-tertiary);
}

.ws-msg-sent { border-left: 2px solid var(--dt-accent); }
.ws-msg-received { border-left: 2px solid var(--dt-success); }

.ws-msg-dir { color: var(--dt-text-muted); font-size: 10px; }
.ws-msg-type { color: var(--dt-text-muted); }
.ws-msg-preview {
    flex: 1; color: var(--dt-text-primary); overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
}
.ws-msg-size { color: var(--dt-text-muted); font-size: 10px; }

.ws-msg-content-details { flex: 1; min-width: 0; }
.ws-msg-content-details summary { cursor: pointer; }
.ws-msg-content-details summary::-webkit-details-marker { display: none; }
.ws-msg-content-details summary::before {
    content: '\u25b6 ';
    font-size: 8px;
    color: var(--dt-text-muted);
}
.ws-msg-content-details[open] summary::before { content: '\u25bc '; }
.ws-msg-full-content {
    margin: 8px 0 0 16px;
    padding: 8px;
    background: var(--dt-bg-primary);
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
    color: var(--dt-text-primary);
}

.ws-live-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--dt-border);
}

.ws-live-btn {
    padding: 6px 12px;
    border: 1px solid var(--dt-border);
    border-radius: 4px;
    background: var(--dt-bg-secondary);
    color: var(--dt-text-secondary);
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
}

.ws-live-btn:hover {
    background: var(--dt-bg-tertiary);
    color: var(--dt-text-primary);
}

.ws-live-btn.ws-live-active {
    background: rgba(34, 197, 94, 0.2);
    border-color: rgba(34, 197, 94, 0.5);
    color: #22c55e;
}

.ws-live-status {
    font-size: 11px;
    color: #22c55e;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* GraphQL Panel Styles */
.graphql-panel h4 { margin: 16px 0 12px; color: var(--dt-text-secondary); font-size: 13px; }

.graphql-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
}

.graphql-stat {
    background: var(--dt-bg-secondary);
    padding: 10px 14px;
    border-radius: 6px;
    text-align: center;
}

.graphql-stat.graphql-warning .stat-value { color: var(--dt-warning); }

.graphql-warning-banner {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(234, 179, 8, 0.05));
    border: 1px solid rgba(234, 179, 8, 0.4);
    border-radius: 6px;
    margin-bottom: 16px;
    color: var(--dt-warning);
    font-size: 13px;
}

.n1-patterns-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
}

.n1-pattern-item {
    background: var(--dt-bg-secondary);
    border-left: 3px solid var(--dt-warning);
    padding: 10px 12px;
    border-radius: 0 4px 4px 0;
}

.n1-header {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 6px;
}

.n1-field {
    font-family: var(--dt-font-mono);
    font-weight: 600;
    color: var(--dt-text-primary);
}

.n1-count {
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-warning);
    font-weight: 600;
}

.n1-duration {
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-text-muted);
}

.n1-suggestion {
    font-size: 12px;
    color: var(--dt-text-secondary);
}

.dup-hint {
    font-size: 12px;
    color: var(--dt-text-muted);
    margin-bottom: 12px;
}

.operations-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.operation-item {
    background: var(--dt-bg-secondary);
    border-radius: 6px;
    padding: 12px;
    border-left: 3px solid var(--dt-accent);
}

.operation-item.op-mutation { border-left-color: var(--dt-warning); }
.operation-item.op-subscription { border-left-color: #c678dd; }
.operation-item.op-error { border-left-color: var(--dt-error); }

.op-header {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    margin-bottom: 8px;
}

.op-type {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    background: rgba(0, 122, 204, 0.2);
    color: var(--dt-accent);
}

.op-mutation .op-type { background: rgba(220, 220, 170, 0.2); color: var(--dt-warning); }
.op-subscription .op-type { background: rgba(198, 120, 221, 0.2); color: #c678dd; }

.op-name {
    font-family: var(--dt-font-mono);
    font-weight: 600;
    color: var(--dt-text-primary);
}

.op-duration {
    font-family: var(--dt-font-mono);
    font-size: 12px;
    color: var(--dt-success);
}

.op-resolvers {
    font-size: 12px;
    color: var(--dt-text-muted);
}

.op-query {
    font-family: var(--dt-font-mono);
    font-size: 11px;
    background: var(--dt-bg-primary);
    padding: 8px;
    border-radius: 4px;
    margin: 0;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--dt-text-secondary);
}

.op-errors {
    margin-top: 8px;
}

.op-error-msg {
    font-size: 12px;
    color: var(--dt-error);
    padding: 4px 0;
}

.slow-resolvers {
    margin-top: 8px;
    font-size: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
}

.slow-label {
    color: var(--dt-text-muted);
}

.slow-resolver {
    font-family: var(--dt-font-mono);
    background: rgba(241, 76, 76, 0.15);
    color: var(--dt-error);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    /* Automatically position toolbar at bottom on mobile for better UX */
    #debug-toolbar,
    #debug-toolbar[data-position="right"],
    #debug-toolbar[data-position="left"],
    #debug-toolbar[data-position="top"] {
        top: auto !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100vw !important;
        height: auto;
        max-width: 100vw !important;
        min-height: 40px;
        max-height: 70vh;
        border-left: none !important;
        border-right: none !important;
        border-bottom: none !important;
        border-top: 2px solid var(--dt-accent);
        flex-direction: column;
    }

    /* Adjust toolbar bar for mobile */
    .toolbar-bar {
        flex-wrap: wrap;
        padding: 8px 12px;
        gap: 8px;
        font-size: 12px;
    }

    /* Make brand smaller on mobile */
    .toolbar-brand {
        font-size: 13px;
    }

    /* Adjust time display */
    .toolbar-time {
        font-size: 11px;
    }

    /* Stack panels vertically or wrap */
    .toolbar-panels {
        flex-wrap: wrap;
        width: 100%;
        gap: 6px;
    }

    .toolbar-panel-btn {
        padding: 6px 10px;
        font-size: 11px;
        min-height: 32px;
        flex: 1 1 auto;
    }

    /* Touch-friendly buttons - minimum 44px */
    .toolbar-collapse-btn,
    .toolbar-theme-btn,
    .toolbar-position-btn {
        min-width: 32px;
        min-height: 32px;
        width: 32px;
        height: 32px;
    }

    /* Adjust details panel for mobile */
    .toolbar-details {
        max-height: 50vh;
        overflow-y: auto;
        font-size: 12px;
    }

    /* Make content scrollable */
    .toolbar-content {
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }

    /* Optimize panel tables for mobile */
    .panel-table {
        font-size: 11px;
    }

    .panel-table td {
        padding: 6px 8px;
    }

    /* Adjust metadata list for mobile */
    .metadata-list {
        grid-template-columns: 100px 1fr;
        gap: 6px 12px;
        font-size: 12px;
    }

    /* Better spacing for alerts on mobile */
    .alert-card {
        padding: 10px;
        margin-bottom: 8px;
    }

    /* Memory stats grid adjustment */
    .memory-summary,
    .async-summary,
    .graphql-summary,
    .ws-summary {
        grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
        gap: 6px;
        font-size: 11px;
    }

    /* Collapsed state on mobile - just show collapse button */
    #debug-toolbar.collapsed {
        max-height: 50px;
        min-height: 40px;
        max-width: 60px;
        width: auto;
        left: auto !important;
        right: 10px !important;
        bottom: 10px !important;
        border-radius: 8px;
    }

    /* Ensure resize handle is hidden on mobile */
    .toolbar-resize-handle {
        display: none;
    }

    /* Position controls - make them more touch-friendly */
    .toolbar-position-controls {
        gap: 6px;
    }
}

/* Extra small screens - hide non-essential elements */
@media (max-width: 480px) {
    .toolbar-request-id {
        display: none;
    }

    .panel-subtitle {
        display: none;
    }
}

/* Landscape mobile / small tablets */
@media (max-width: 1024px) and (max-height: 600px) {
    #debug-toolbar {
        max-height: 50vh;
    }

    .toolbar-details {
        max-height: 35vh;
    }
}
"""


def get_toolbar_js() -> str:
    """Get the toolbar JavaScript."""
    return """
function togglePageTheme(btn) {
    const current = document.documentElement.dataset.theme || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('debug-toolbar-theme', next);
}

function downloadFlamegraph() {
    // Get request ID from URL or page
    const pathParts = window.location.pathname.split('/');
    const requestId = pathParts[pathParts.length - 1];
    if (!requestId || requestId === '_debug_toolbar') {
        alert('Could not determine request ID');
        return;
    }

    // Trigger download
    const downloadUrl = '/_debug_toolbar/api/flamegraph/' + requestId;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = 'flamegraph-' + requestId.substring(0, 8) + '.speedscope.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function togglePanel(panelId) {
    const panel = document.getElementById('panel-' + panelId);
    if (!panel) return;
    const content = panel.querySelector('.panel-content');
    const toggle = panel.querySelector('.panel-toggle');
    const isExpanded = content.classList.contains('expanded');
    if (isExpanded) {
        content.classList.remove('expanded');
        toggle.textContent = '+';
    } else {
        content.classList.add('expanded');
        toggle.textContent = '-';
    }
}

class DebugToolbar {
    constructor(element) {
        this.element = element;
        this.isCollapsed = localStorage.getItem('debug-toolbar-collapsed') === 'true';
        this.activePanel = null;
        this.position = localStorage.getItem('debug-toolbar-position') || 'right';
        this.theme = localStorage.getItem('debug-toolbar-theme') || 'dark';
        this.size = parseInt(localStorage.getItem('debug-toolbar-size') || '400', 10);
        this.isResizing = false;
        this.init();
    }

    init() {
        window.debugToolbar = this;
        this.setPosition(this.position);
        this.setTheme(this.theme);
        this.applySize();
        this.addThemeToggle();
        this.addPositionControls();
        this.addResizeHandle();
        this.addCollapseButton();

        // Apply saved collapsed state
        if (this.isCollapsed) {
            this.element.classList.add('collapsed');
        }

        const brand = this.element.querySelector('.toolbar-brand');
        if (brand) {
            brand.addEventListener('click', () => this.toggle());
        }
        const panelBtns = this.element.querySelectorAll('.toolbar-panel-btn');
        panelBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.showPanel(btn.dataset.panelId);
            });
        });
    }

    addCollapseButton() {
        const collapseBtn = this.element.querySelector('.toolbar-collapse-btn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggle();
            });
        }
    }

    addThemeToggle() {
        this.themeBtn = document.createElement('button');
        this.themeBtn.className = 'toolbar-theme-btn';
        this.themeBtn.title = 'Toggle theme';
        this.themeBtn.innerHTML = this.theme === 'dark' ? '\u2600' : '\u263e';
        this.themeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
            this.themeBtn.innerHTML = this.theme === 'dark' ? '\u2600' : '\u263e';
        });
    }

    setTheme(theme) {
        this.theme = theme;
        this.element.dataset.theme = theme;
        document.documentElement.dataset.theme = theme;
        localStorage.setItem('debug-toolbar-theme', theme);
    }

    addResizeHandle() {
        const handle = document.createElement('div');
        handle.className = 'toolbar-resize-handle';
        this.element.appendChild(handle);

        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.isResizing = true;
            document.body.style.cursor = this.isHorizontal() ? 'ew-resize' : 'ns-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!this.isResizing) return;
            this.handleResize(e);
        });

        document.addEventListener('mouseup', () => {
            if (this.isResizing) {
                this.isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                localStorage.setItem('debug-toolbar-size', String(this.size));
            }
        });
    }

    isHorizontal() {
        return this.position === 'left' || this.position === 'right';
    }

    handleResize(e) {
        const minSize = this.isHorizontal() ? 250 : 100;
        const maxSize = this.isHorizontal() ? window.innerWidth * 0.8 : window.innerHeight * 0.6;
        let newSize;

        if (this.position === 'right') {
            newSize = window.innerWidth - e.clientX;
        } else if (this.position === 'left') {
            newSize = e.clientX;
        } else if (this.position === 'bottom') {
            newSize = window.innerHeight - e.clientY;
        } else {
            newSize = e.clientY;
        }

        this.size = Math.max(minSize, Math.min(maxSize, newSize));
        this.applySize();
    }

    applySize() {
        if (this.isHorizontal()) {
            this.element.style.width = this.size + 'px';
            this.element.style.height = '';
        } else {
            this.element.style.height = this.size + 'px';
            this.element.style.width = '';
        }
    }

    addPositionControls() {
        const bar = this.element.querySelector('.toolbar-bar');
        if (!bar) return;

        const controlsWrapper = document.createElement('div');
        controlsWrapper.className = 'toolbar-controls';

        const positionControls = document.createElement('div');
        positionControls.className = 'toolbar-position-controls';

        const positions = [
            { pos: 'left', label: '\u25c0' },
            { pos: 'top', label: '\u25b2' },
            { pos: 'bottom', label: '\u25bc' },
            { pos: 'right', label: '\u25b6' }
        ];

        positions.forEach(p => {
            const btn = document.createElement('button');
            btn.className = 'toolbar-position-btn' + (p.pos === this.position ? ' active' : '');
            btn.dataset.position = p.pos;
            btn.title = 'Move to ' + p.pos;
            btn.textContent = p.label;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.setPosition(p.pos);
            });
            positionControls.appendChild(btn);
        });

        const separator = document.createElement('span');
        separator.className = 'toolbar-controls-separator';
        separator.textContent = '|';

        controlsWrapper.appendChild(positionControls);
        controlsWrapper.appendChild(separator);
        if (this.themeBtn) {
            controlsWrapper.appendChild(this.themeBtn);
        }
        bar.appendChild(controlsWrapper);
    }

    setPosition(position) {
        const wasHorizontal = this.isHorizontal();
        this.position = position;
        this.element.dataset.position = position;
        localStorage.setItem('debug-toolbar-position', position);

        this.element.querySelectorAll('.toolbar-position-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.position === position);
        });

        if (wasHorizontal !== this.isHorizontal()) {
            this.size = this.isHorizontal() ? 400 : 300;
        }
        this.applySize();
    }

    toggle() {
        this.isCollapsed = !this.isCollapsed;
        this.element.classList.toggle('collapsed', this.isCollapsed);
        localStorage.setItem('debug-toolbar-collapsed', String(this.isCollapsed));
    }

    showPanel(panelId) {
        const details = this.element.querySelector('.toolbar-details');
        const btns = this.element.querySelectorAll('.toolbar-panel-btn');

        btns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.panelId === panelId);
        });

        if (this.activePanel === panelId) {
            this.activePanel = null;
            if (details) details.classList.remove('expanded');
            return;
        }

        this.activePanel = panelId;
        const requestId = this.element.dataset.requestId;
        if (requestId && details) {
            fetch('/_debug_toolbar/api/requests/' + requestId)
                .then(res => res.json())
                .then(data => {
                    const panelData = data.panel_data && data.panel_data[panelId];
                    if (panelData) {
                        details.innerHTML = this.renderPanelById(panelId, panelData, data.request_id);
                        details.classList.add('expanded');
                    }
                })
                .catch(err => console.error('Failed to load panel data:', err));
        }
    }

    renderPanelById(panelId, data, requestId) {
        switch (panelId) {
            case 'AlertsPanel':
                return this.renderAlertsPanel(data);
            case 'MemoryPanel':
                return this.renderMemoryPanel(data);
            case 'ProfilingPanel':
                return this.renderProfilingPanel(data, requestId);
            case 'AsyncProfilerPanel':
                return this.renderAsyncProfilerPanel(data);
            case 'SQLAlchemyPanel':
                return this.renderSqlPanel(data);
            case 'WebSocketPanel':
                return this.renderWebSocketPanel(data);
            default:
                return this.renderPanelData(data);
        }
    }

    renderAlertsPanel(data) {
        const alerts = data.alerts || [];
        if (alerts.length === 0) {
            return '<p class="empty alert-success">No issues detected</p>';
        }
        const severityColors = {critical: '#dc2626', warning: '#f59e0b', info: '#3b82f6'};
        const severityIcons = {critical: '!', warning: '!', info: 'i'};
        const categoryIcons = {security: 'lock', performance: 'zap', database: 'db', configuration: 'cog'};

        let html = '<div class="alerts-summary"><strong>' + alerts.length + '</strong> issue(s) detected</div>';
        html += '<div class="alerts-container">';

        for (const alert of alerts) {
            const severity = alert.severity || 'info';
            const category = alert.category || '';
            const title = this.escapeHtml(alert.title || 'Alert');
            const message = this.escapeHtml(alert.message || '');
            const suggestion = alert.suggestion || '';
            const color = severityColors[severity] || '#6b7280';
            const icon = severityIcons[severity] || '*';
            const catIcon = categoryIcons[category] || '';

            html += '<div class="alert-card alert-' + severity + '" style="border-left-color:' + color + '">';
            html += '<div class="alert-header">';
            html += '<span class="alert-icon">[' + icon + ']</span>';
            html += '<span class="alert-title">' + title + '</span>';
            html += '<span class="alert-category">[' + catIcon + '] ' + this.escapeHtml(category) + '</span>';
            html += '</div>';
            html += '<div class="alert-message">' + message + '</div>';
            if (suggestion) {
                html += '<div class="alert-suggestion">Tip: ' + this.escapeHtml(suggestion) + '</div>';
            }
            html += '</div>';
        }
        html += '</div>';
        return html;
    }

    renderMemoryPanel(data) {
        const peak = data.peak_memory || 0;
        const current = data.current_memory || 0;
        const allocCount = data.allocation_count || 0;
        const backend = data.backend || 'unknown';

        let html = '<div class="memory-panel">';
        html += '<div class="memory-summary">';
        html += '<div class="memory-stat"><span class="stat-value">' + this.formatBytes(peak) + '</span>';
        html += '<span class="stat-label">Peak Memory</span></div>';
        html += '<div class="memory-stat"><span class="stat-value">' + this.formatBytes(current) + '</span>';
        html += '<span class="stat-label">Current</span></div>';
        html += '<div class="memory-stat"><span class="stat-value">' + allocCount + '</span>';
        html += '<span class="stat-label">Allocations</span></div>';
        html += '<div class="memory-stat"><span class="stat-value">' + backend + '</span>';
        html += '<span class="stat-label">Backend</span></div>';
        html += '</div>';

        const topAllocs = data.top_allocations || [];
        if (topAllocs.length > 0) {
            html += '<h4>Top Allocations</h4>';
            html += '<table class="panel-table"><tbody>';
            for (const alloc of topAllocs.slice(0, 10)) {
                const file = alloc.file || alloc.location || 'unknown';
                const line = alloc.line || 0;
                const size = alloc.size || 0;
                const count = alloc.count || 0;
                let loc = file;
                if (line > 0) loc += ':' + line;
                html += '<tr><td class="key">' + this.escapeHtml(loc) + '</td>';
                html += '<td class="value">' + this.formatBytes(size) + ' (' + count + ' allocs)</td></tr>';
            }
            html += '</tbody></table>';
        }
        html += '</div>';
        return html;
    }

    renderProfilingPanel(data, requestId) {
        let html = '<div class="profiling-panel">';

        const totalTime = (data.total_time || 0) * 1000;
        const funcCount = data.function_count || 0;
        const callCount = data.total_calls || 0;
        const profilerType = data.profiler_type || 'cProfile';

        html += '<div class="profiling-summary">';
        html += '<div class="profiling-stat"><span class="stat-value">' + totalTime.toFixed(2) + 'ms</span>';
        html += '<span class="stat-label">Total Time</span></div>';
        html += '<div class="profiling-stat"><span class="stat-value">' + funcCount + '</span>';
        html += '<span class="stat-label">Functions</span></div>';
        html += '<div class="profiling-stat"><span class="stat-value">' + callCount + '</span>';
        html += '<span class="stat-label">Calls</span></div>';
        html += '<div class="profiling-stat"><span class="stat-value">' + profilerType + '</span>';
        html += '<span class="stat-label">Profiler</span></div>';
        html += '</div>';

        if (data.has_flamegraph && requestId) {
            html += '<div class="flamegraph-action">';
            html += '<button onclick="downloadFlamegraph(\\''+requestId+'\\')" class="flamegraph-btn">';
            html += 'Download Flame Graph (Speedscope)</button></div>';
        }

        const topFuncs = data.top_functions || [];
        if (topFuncs.length > 0) {
            html += '<h4>Top Functions by Time</h4>';
            html += '<table class="panel-table"><tbody>';
            for (const func of topFuncs.slice(0, 15)) {
                const funcName = func.function || func.name || 'unknown';
                const filename = func.filename || '';
                const lineno = func.lineno || 0;
                let displayName = funcName;
                if (filename && filename !== 'unknown') {
                    const shortFile = filename.split('/').pop() || filename;
                    displayName = lineno ? shortFile + ':' + lineno + ' ' + funcName : shortFile + ' ' + funcName;
                }
                const timeMs = (func.cumulative_time || 0) * 1000;
                const calls = func.calls || 0;
                html += '<tr><td class="key">' + this.escapeHtml(displayName) + '</td>';
                html += '<td class="value">' + timeMs.toFixed(2) + 'ms (' + calls + ' calls)</td></tr>';
            }
            html += '</tbody></table>';
        }
        html += '</div>';
        return html;
    }

    renderAsyncProfilerPanel(data) {
        let html = '<div class="async-profiler-panel">';

        const summary = data.summary || {};
        const totalTasks = summary.total_tasks || 0;
        const completed = summary.completed_tasks || 0;
        const cancelled = summary.cancelled_tasks || 0;
        const errors = summary.error_tasks || 0;
        const blockingCount = summary.blocking_calls_count || 0;
        const maxLag = summary.max_lag_ms || 0;
        const hasWarnings = summary.has_warnings || false;
        const backend = data.backend || 'unknown';

        html += '<div class="async-summary">';
        html += '<div class="async-stat"><span class="stat-value">' + totalTasks + '</span>';
        html += '<span class="stat-label">Total Tasks</span></div>';
        html += '<div class="async-stat"><span class="stat-value">' + completed + '</span>';
        html += '<span class="stat-label">Completed</span></div>';
        html += '<div class="async-stat' + (cancelled > 0 ? ' async-warning' : '') + '">';
        html += '<span class="stat-value">' + cancelled + '</span>';
        html += '<span class="stat-label">Cancelled</span></div>';
        html += '<div class="async-stat' + (errors > 0 ? ' async-error' : '') + '">';
        html += '<span class="stat-value">' + errors + '</span>';
        html += '<span class="stat-label">Errors</span></div>';
        html += '<div class="async-stat' + (blockingCount > 0 ? ' async-error' : '') + '">';
        html += '<span class="stat-value">' + blockingCount + '</span>';
        html += '<span class="stat-label">Blocking</span></div>';
        html += '<div class="async-stat"><span class="stat-value">' + maxLag.toFixed(1) + 'ms</span>';
        html += '<span class="stat-label">Max Lag</span></div>';
        html += '<div class="async-stat"><span class="stat-value">' + this.escapeHtml(backend) + '</span>';
        html += '<span class="stat-label">Backend</span></div>';
        html += '</div>';

        if (hasWarnings) {
            html += '<div class="async-warning-banner">';
            html += '<span class="warning-icon">⚠️</span>';
            html += '<span>Blocking calls detected! These may impact performance.</span>';
            html += '</div>';
        }

        const blockingCalls = data.blocking_calls || [];
        if (blockingCalls.length > 0) {
            html += '<h4>Blocking Calls</h4>';
            html += '<div class="blocking-calls-list">';
            for (const call of blockingCalls.slice(0, 10)) {
                const funcName = this.escapeHtml(call.function_name || 'unknown');
                const duration = call.duration_ms || 0;
                const file = this.escapeHtml(call.file || 'unknown');
                const line = call.line || 0;
                const location = line > 0 ? file + ':' + line : file;
                html += '<div class="blocking-call-item">';
                html += '<div class="blocking-call-header">';
                html += '<span class="blocking-func">' + funcName + '</span>';
                html += '<span class="blocking-duration">' + duration.toFixed(2) + 'ms</span>';
                html += '</div>';
                html += '<div class="blocking-location">' + location + '</div>';
                html += '</div>';
            }
            html += '</div>';
        }

        const tasks = data.tasks || [];
        const createdTasks = tasks.filter(t => t.event_type === 'created');
        if (createdTasks.length > 0) {
            html += '<h4>Tasks</h4>';
            html += '<table class="panel-table"><tbody>';
            for (const task of createdTasks.slice(0, 15)) {
                const taskName = this.escapeHtml(task.task_name || 'unknown');
                const coroName = this.escapeHtml(task.coro_name || '');
                const taskId = task.task_id || '';
                const completion = tasks.find(t => t.task_id === taskId &&
                    ['completed', 'cancelled', 'error'].includes(t.event_type));
                const allowedStatuses = ['completed', 'cancelled', 'error', 'running', 'unknown'];
                let status = 'running';
                let duration = 0;
                if (completion) {
                    status = completion.event_type;
                    if (!allowedStatuses.includes(status)) {
                        status = 'unknown';
                    }
                    duration = completion.duration_ms || 0;
                }
                const statusClass = 'async-status-' + status;
                const safeClass = this.escapeHtml(statusClass);
                const safeStatus = this.escapeHtml(status);
                html += '<tr>';
                html += '<td class="key">' + taskName + '<br><small class="coro-name">' + coroName + '</small></td>';
                html += '<td class="value">';
                html += '<span class="task-status ' + safeClass + '">' + safeStatus + '</span>';
                if (duration > 0) {
                    html += '<span class="task-duration">' + duration.toFixed(2) + 'ms</span>';
                }
                html += '</td></tr>';
            }
            html += '</tbody></table>';
        }

        const timeline = data.timeline || {};
        if (timeline.events && timeline.events.length > 0) {
            html += '<h4>Timeline</h4>';
            html += '<div class="timeline-info">';
            html += '<span>Duration: ' + (timeline.total_duration_ms || 0).toFixed(2) + 'ms</span>';
            html += '<span>Max Concurrent: ' + (timeline.max_concurrent || 0) + '</span>';
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    renderWebSocketPanel(data) {
        let html = '<div class="websocket-panel" id="ws-panel-content">';

        const isLive = this.wsLiveConnection &&
            this.wsLiveConnection.readyState === WebSocket.OPEN;
        html += '<div class="ws-live-controls">';
        const liveClass = isLive ? 'ws-live-active' : '';
        html += '<button class="ws-live-btn ' + liveClass + '" ';
        html += 'onclick="window.debugToolbar.toggleWsLive()">';
        html += isLive ? '\u25cf Live' : '\u25cb Go Live';
        html += '</button>';
        if (isLive) {
            html += '<span class="ws-live-status">Streaming updates...</span>';
        }
        html += '</div>';

        const totalActive = data.total_active || 0;
        const totalClosed = data.total_closed || 0;
        const msgsSent = data.total_messages_sent || 0;
        const msgsReceived = data.total_messages_received || 0;
        const bytesSent = data.total_bytes_sent || 0;
        const bytesReceived = data.total_bytes_received || 0;

        html += '<div class="ws-summary">';
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-active">' + totalActive + '</span>';
        html += '<span class="stat-label">Active</span></div>';
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-closed">' + totalClosed + '</span>';
        html += '<span class="stat-label">Closed</span></div>';
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-sent">' + msgsSent + '</span>';
        html += '<span class="stat-label">Sent</span></div>';
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-received">' + msgsReceived + '</span>';
        html += '<span class="stat-label">Received</span></div>';
        const fmtBytesSent = this.formatBytes(bytesSent);
        const fmtBytesRecv = this.formatBytes(bytesReceived);
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-bytes-sent">';
        html += fmtBytesSent + '</span><span class="stat-label">Bytes Sent</span></div>';
        html += '<div class="ws-stat"><span class="stat-value" id="ws-stat-bytes-recv">';
        html += fmtBytesRecv + '</span><span class="stat-label">Bytes Recv</span></div>';
        html += '</div>';

        if (totalActive === 0 && totalClosed === 0) {
            html += '<p class="empty ws-no-connections">No WebSocket connections tracked yet.</p>';
            html += '<p class="ws-hint">Connect to a WebSocket endpoint. Click "Go Live" for real-time updates.</p>';
            html += '</div>';
            return html;
        }

        const activeConns = data.active_connections || [];
        html += '<div id="ws-active-section">';
        if (activeConns.length > 0) {
            html += '<h4>Active Connections</h4>';
            html += '<div class="ws-connections">';
            for (const conn of activeConns) {
                html += this.renderWebSocketConnection(conn, 'active');
            }
            html += '</div>';
        }
        html += '</div>';

        const closedConns = data.closed_connections || [];
        html += '<div id="ws-closed-section">';
        if (closedConns.length > 0) {
            html += '<h4>Recent Closed Connections</h4>';
            html += '<div class="ws-connections">';
            for (const conn of closedConns.slice(0, 5)) {
                html += this.renderWebSocketConnection(conn, 'closed');
            }
            html += '</div>';
        }
        html += '</div>';

        html += '</div>';
        return html;
    }

    toggleWsLive() {
        if (this.wsLiveConnection && this.wsLiveConnection.readyState === WebSocket.OPEN) {
            this.wsLiveConnection.close();
            this.wsLiveConnection = null;
            this.refreshWsPanel();
        } else {
            this.connectWsLive();
        }
    }

    connectWsLive() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + '/_debug_toolbar/ws/live';
        this.wsLiveConnection = new WebSocket(wsUrl);

        this.wsLiveConnection.onopen = () => {
            const panel = document.getElementById('ws-panel-content');
            if (panel) {
                const liveBtn = panel.querySelector('.ws-live-btn');
                if (liveBtn) {
                    liveBtn.className = 'ws-live-btn ws-live-active';
                    liveBtn.textContent = '\u25cf Live';
                }
                const controls = panel.querySelector('.ws-live-controls');
                if (controls && !controls.querySelector('.ws-live-status')) {
                    const statusEl = document.createElement('span');
                    statusEl.className = 'ws-live-status';
                    statusEl.textContent = 'Streaming updates...';
                    controls.appendChild(statusEl);
                }
            }
        };

        this.wsLiveConnection.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'init') {
                    this.updateWsPanelContent(msg.data);
                } else {
                    this.handleWsLiveEvent(msg);
                }
            } catch (e) {
                console.error('Debug Toolbar: Error parsing live message', e);
            }
        };

        this.wsLiveConnection.onclose = () => {
            this.wsLiveConnection = null;
            this.refreshWsPanel();
        };

        this.wsLiveConnection.onerror = (err) => {
            console.error('Debug Toolbar: Live WebSocket error', err);
        };
    }

    handleWsLiveEvent(msg) {
        const details = this.element.querySelector('.toolbar-details');
        if (!details || this.activePanel !== 'WebSocketPanel') return;

        if (msg.type === 'message' || msg.type === 'connection' || msg.type === 'state_change') {
            fetch('/_debug_toolbar/api/websocket/stats')
                .then(res => res.json())
                .then(data => {
                    this.updateWsPanelContent(data);
                })
                .catch(() => {});
        }
    }

    updateWsPanelContent(data) {
        const panel = document.getElementById('ws-panel-content');
        if (!panel) return;

        const isLive = this.wsLiveConnection &&
            this.wsLiveConnection.readyState === WebSocket.OPEN;
        const liveBtn = panel.querySelector('.ws-live-btn');
        if (liveBtn) {
            liveBtn.className = 'ws-live-btn' + (isLive ? ' ws-live-active' : '');
            liveBtn.textContent = isLive ? '\u25cf Live' : '\u25cb Go Live';
        }
        let statusEl = panel.querySelector('.ws-live-status');
        if (isLive && !statusEl) {
            const controls = panel.querySelector('.ws-live-controls');
            if (controls && liveBtn) {
                statusEl = document.createElement('span');
                statusEl.className = 'ws-live-status';
                statusEl.textContent = 'Streaming updates...';
                controls.appendChild(statusEl);
            }
        } else if (!isLive && statusEl) {
            statusEl.remove();
        }

        const activeEl = document.getElementById('ws-stat-active');
        const closedEl = document.getElementById('ws-stat-closed');
        const sentEl = document.getElementById('ws-stat-sent');
        const receivedEl = document.getElementById('ws-stat-received');
        const bytesSentEl = document.getElementById('ws-stat-bytes-sent');
        const bytesRecvEl = document.getElementById('ws-stat-bytes-recv');

        if (activeEl) activeEl.textContent = data.total_active || 0;
        if (closedEl) closedEl.textContent = data.total_closed || 0;
        if (sentEl) sentEl.textContent = data.total_messages_sent || 0;
        if (receivedEl) receivedEl.textContent = data.total_messages_received || 0;
        if (bytesSentEl) bytesSentEl.textContent = this.formatBytes(data.total_bytes_sent || 0);
        if (bytesRecvEl) bytesRecvEl.textContent = this.formatBytes(data.total_bytes_received || 0);

        const activeSection = document.getElementById('ws-active-section');
        if (activeSection) {
            const activeConns = data.active_connections || [];
            if (activeConns.length > 0) {
                let html = '<h4>Active Connections</h4><div class="ws-connections">';
                for (const conn of activeConns) {
                    html += this.renderWebSocketConnection(conn, 'active');
                }
                html += '</div>';
                activeSection.innerHTML = html;
            } else {
                activeSection.innerHTML = '';
            }
        }

        const closedSection = document.getElementById('ws-closed-section');
        if (closedSection) {
            const closedConns = data.closed_connections || [];
            if (closedConns.length > 0) {
                let html = '<h4>Recent Closed Connections</h4><div class="ws-connections">';
                for (const conn of closedConns.slice(0, 5)) {
                    html += this.renderWebSocketConnection(conn, 'closed');
                }
                html += '</div>';
                closedSection.innerHTML = html;
            } else {
                closedSection.innerHTML = '';
            }
        }
    }

    refreshWsPanel() {
        if (this.activePanel !== 'WebSocketPanel') {
            return;
        }
        const details = this.element.querySelector('.toolbar-details');
        const requestId = this.element.dataset.requestId;
        if (requestId && details) {
            fetch('/_debug_toolbar/api/requests/' + requestId)
                .then(res => res.json())
                .then(data => {
                    const panelData = data.panel_data && data.panel_data['WebSocketPanel'];
                    if (panelData) {
                        details.innerHTML = this.renderWebSocketPanel(panelData);
                    }
                })
                .catch(err => console.error('Failed to refresh WebSocket panel:', err));
        }
    }

    renderWebSocketConnection(conn, status) {
        const shortId = conn.short_id || conn.connection_id.substring(0, 8);
        const path = this.escapeHtml(conn.path || '/');
        const state = conn.state || 'unknown';
        const duration = (conn.duration || 0).toFixed(2);
        const sent = conn.total_sent || 0;
        const received = conn.total_received || 0;
        const closeCode = conn.close_code;
        const closeReason = conn.close_reason;

        let html = '<div class="ws-connection ws-connection-' + status + '">';
        html += '<div class="ws-conn-header">';
        html += '<span class="ws-conn-id" title="' + this.escapeHtml(conn.connection_id) + '">' + shortId + '</span>';
        html += '<span class="ws-conn-path">' + path + '</span>';
        html += '<span class="ws-conn-state ws-state-' + state + '">' + state + '</span>';
        html += '</div>';

        html += '<div class="ws-conn-stats">';
        html += '<span class="ws-conn-duration">' + duration + 's</span>';
        html += '<span class="ws-conn-msgs">' + sent + ' sent / ' + received + ' received</span>';
        if (closeCode) {
            html += '<span class="ws-conn-close">Close: ' + closeCode;
            if (closeReason) html += ' (' + this.escapeHtml(closeReason) + ')';
            html += '</span>';
        }
        html += '</div>';

        const messages = conn.messages || [];
        if (messages.length > 0) {
            html += '<div class="ws-messages">';
            html += '<details><summary>' + messages.length + ' message(s)</summary>';
            html += '<div class="ws-message-list">';
            for (const msg of messages.slice(-10)) {
                const dir = msg.direction || 'unknown';
                const preview = this.escapeHtml(msg.preview || '<empty>');
                const content = msg.content ? this.escapeHtml(msg.content) : null;
                const size = msg.size || 0;
                const msgType = msg.type || 'text';
                const hasFullContent = content && content.length > preview.length;

                html += '<div class="ws-message ws-msg-' + dir + '">';
                html += '<span class="ws-msg-dir">' + (dir === 'sent' ? '\u2192' : '\u2190') + '</span>';
                html += '<span class="ws-msg-type">[' + msgType + ']</span>';

                if (hasFullContent) {
                    html += '<details class="ws-msg-content-details">';
                    html += '<summary class="ws-msg-preview">' + preview + '</summary>';
                    html += '<pre class="ws-msg-full-content">' + content + '</pre>';
                    html += '</details>';
                } else {
                    html += '<span class="ws-msg-preview">' + preview + '</span>';
                }

                html += '<span class="ws-msg-size">' + this.formatBytes(size) + '</span>';
                html += '</div>';
            }
            html += '</div></details>';
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    renderPanelData(data) {
        if (!data || Object.keys(data).length === 0) {
            return '<p class="empty">No data</p>';
        }
        let html = '<table class="panel-table"><tbody>';
        for (const [key, value] of Object.entries(data)) {
            const escapedKey = this.escapeHtml(key);
            const formattedValue = this.formatValue(value, 0);
            html += '<tr><td class="key">' + escapedKey + '</td>';
            html += '<td class="value">' + formattedValue + '</td></tr>';
        }
        html += '</tbody></table>';
        return html;
    }

    formatValue(value, depth) {
        depth = depth || 0;
        const maxDepth = 10;
        const maxItems = 100;
        const maxStringLen = 1000;

        if (value === null || value === undefined) {
            return '<span class="null">null</span>';
        }
        if (typeof value === 'boolean') {
            return '<span class="bool">' + value + '</span>';
        }
        if (typeof value === 'number') {
            return '<span class="number">' + value + '</span>';
        }
        if (typeof value === 'string') {
            const truncated = value.length > maxStringLen ? value.substring(0, maxStringLen) + '...' : value;
            return '<span class="string">' + this.escapeHtml(truncated) + '</span>';
        }
        if (Array.isArray(value)) {
            if (value.length === 0) {
                return '<span class="array">[]</span>';
            }
            if (depth >= maxDepth) {
                return '<span class="array">[' + value.length + ' items]</span>';
            }
            const items = value.slice(0, maxItems).map(v => this.formatValue(v, depth + 1));
            let html = '<div class="array-items">';
            items.forEach((item, i) => {
                html += '<div class="array-item">' + item + '</div>';
            });
            if (value.length > maxItems) {
                html += '<div class="array-more">... and ' + (value.length - maxItems) + ' more</div>';
            }
            html += '</div>';
            return html;
        }
        if (typeof value === 'object') {
            const keys = Object.keys(value);
            if (keys.length === 0) {
                return '<span class="object">{}</span>';
            }
            if (depth >= maxDepth) {
                return '<span class="object">{' + keys.length + ' keys}</span>';
            }
            let html = '<div class="object-items">';
            keys.slice(0, maxItems).forEach(k => {
                html += '<div class="object-item"><strong>' + this.escapeHtml(k) + ':</strong> ';
                html += this.formatValue(value[k], depth + 1) + '</div>';
            });
            if (keys.length > maxItems) {
                html += '<div class="object-more">... and ' + (keys.length - maxItems) + ' more</div>';
            }
            html += '</div>';
            return html;
        }
        return '<span class="unknown">' + this.escapeHtml(String(value)) + '</span>';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderSqlPanel(data) {
        if (!data || !data.queries || data.queries.length === 0) {
            return '<p class="empty">No SQL queries</p>';
        }

        let html = '<div class="sql-panel">';

        // Summary stats
        html += '<div class="sql-summary">';
        html += '<h3>Total Queries: ' + (data.total_queries || data.queries.length) + '</h3>';
        if (data.total_time_ms !== undefined) {
            html += '<span class="sql-total-time">Total Time: ' + data.total_time_ms.toFixed(2) + 'ms</span>';
        }
        html += '</div>';

        // N+1 Warning Section
        if (data.n_plus_one_groups && data.n_plus_one_groups.length > 0) {
            html += '<div class="n-plus-one-warning">';
            html += '<div class="n-plus-one-header">';
            html += '<span class="warning-icon">⚠️</span>';
            html += '<strong>N+1 Query Problem Detected!</strong>';
            html += '<span class="n-plus-one-count">' + data.n_plus_one_groups.length + ' pattern(s)</span>';
            html += '</div>';
            html += '<div class="n-plus-one-groups">';

            data.n_plus_one_groups.forEach((group, idx) => {
                html += '<div class="n-plus-one-group">';
                html += '<div class="n-plus-one-group-header">';
                html += '<span class="group-count">' + group.count + 'x</span>';
                html += '<span class="group-origin">' + this.escapeHtml(group.origin_display || 'Unknown') + '</span>';
                html += '<span class="group-time">' + (group.total_duration_ms || 0).toFixed(2) + 'ms total</span>';
                html += '</div>';
                html += '<div class="n-plus-one-sql">' + this.escapeHtml(group.normalized_sql || '') + '</div>';
                if (group.suggestion) {
                    html += '<div class="n-plus-one-suggestion">';
                    html += '<strong>💡 Suggestion:</strong> ' + this.escapeHtml(group.suggestion);
                    html += '</div>';
                }
                if (group.stack && group.stack.length > 0) {
                    html += '<details class="n-plus-one-stack">';
                    html += '<summary>Call Stack</summary>';
                    html += '<div class="stack-frames">';
                    group.stack.forEach(frame => {
                        const shortFile = (frame.file || '').split(/[\\/]/).pop();
                        const loc = this.escapeHtml(shortFile) + ':' + frame.line;
                        const fn = this.escapeHtml(frame.function || '');
                        html += '<div class="stack-frame">';
                        html += '<span class="frame-location">' + loc + '</span>';
                        html += ' in <span class="frame-function">' + fn + '</span>';
                        if (frame.code) {
                            html += '<div class="frame-code">' + this.escapeHtml(frame.code) + '</div>';
                        }
                        html += '</div>';
                    });
                    html += '</div></details>';
                }
                html += '</div>';
            });

            html += '</div></div>';
        }

        // Individual queries
        html += '<div class="sql-queries">';
        data.queries.forEach((query, index) => {
            const supportsExplain = query.supports_explain !== false;
            const sql = query.sql || query.query || '';
            const params = query.raw_parameters || query.parameters || {};
            const hasParams = params && Object.keys(params).length > 0;
            const sqlEncoded = btoa(unescape(encodeURIComponent(sql)));
            const paramsEncoded = btoa(unescape(encodeURIComponent(JSON.stringify(params))));

            const classes = ['sql-query-container'];
            if (query.is_slow) classes.push('is-slow');
            if (query.is_duplicate) classes.push('is-duplicate');
            if (query.is_n_plus_one) classes.push('is-n-plus-one');

            html += '<div class="' + classes.join(' ') + '">';
            html += '<div class="sql-query-header">';
            html += '<span class="sql-query-title">Query #' + (index + 1) + '</span>';

            // Badges
            if (query.is_n_plus_one) {
                html += '<span class="query-badge badge-n-plus-one" title="Part of N+1 pattern">N+1</span>';
            }
            if (query.is_slow) {
                html += '<span class="query-badge badge-slow" title="Slow query">SLOW</span>';
            }
            if (query.is_duplicate) {
                html += '<span class="query-badge badge-duplicate" title="Duplicate query">DUP</span>';
            }

            if (supportsExplain) {
                html += '<button class="sql-explain-btn" data-sql="' + sqlEncoded +
                        '" data-params="' + paramsEncoded + '">EXPLAIN</button>';
            } else {
                html += '<button class="sql-explain-btn" disabled>EXPLAIN (not supported)</button>';
            }
            html += '</div>';
            html += '<div class="sql-query-code">' + this.escapeHtml(sql) + '</div>';
            if (hasParams) {
                html += '<div class="sql-query-params"><strong>Parameters:</strong> ' +
                        this.escapeHtml(JSON.stringify(params)) + '</div>';
            }
            if (query.duration_ms !== undefined) {
                html += '<div class="sql-query-params"><strong>Duration:</strong> ' +
                        query.duration_ms.toFixed(2) + 'ms</div>';
            }
            html += '</div>';
        });
        html += '</div>';

        html += '</div>';

        setTimeout(() => {
            document.querySelectorAll('.sql-explain-btn[data-sql]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const sql = decodeURIComponent(escape(atob(btn.dataset.sql)));
                    const params = JSON.parse(decodeURIComponent(escape(atob(btn.dataset.params))));
                    this.runExplain(sql, params);
                });
            });
        }, 0);

        return html;
    }

    async runExplain(sql, parameters) {
        const modal = document.createElement('div');
        modal.className = 'explain-modal';
        modal.innerHTML = `
            <div class="explain-modal-content">
                <div class="explain-modal-header">
                    <h3 class="explain-modal-title">Query Execution Plan</h3>
                    <button class="explain-modal-close"
                            onclick="this.closest('.explain-modal').remove()">&times;</button>
                </div>
                <div class="explain-modal-body">
                    <div class="explain-result">Loading...</div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        try {
            const response = await fetch('/_debug_toolbar/api/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql: sql, parameters: parameters })
            });

            const result = await response.json();
            const resultDiv = modal.querySelector('.explain-result');

            if (result.error) {
                resultDiv.innerHTML = '<div class="explain-error">' + this.escapeHtml(result.error) + '</div>';
            } else if (result.plan) {
                resultDiv.innerHTML = '<pre>' + this.escapeHtml(JSON.stringify(result.plan, null, 2)) + '</pre>';
            } else {
                resultDiv.innerHTML = '<pre>' + this.escapeHtml(JSON.stringify(result, null, 2)) + '</pre>';
            }
        } catch (err) {
            const resultDiv = modal.querySelector('.explain-result');
            resultDiv.innerHTML = '<div class="explain-error">Failed to execute EXPLAIN: ' +
                                this.escapeHtml(err.message) + '</div>';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const toolbar = document.getElementById('debug-toolbar');
    if (toolbar) {
        new DebugToolbar(toolbar);
    }
});
"""
