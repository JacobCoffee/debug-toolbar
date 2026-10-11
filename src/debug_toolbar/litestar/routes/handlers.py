"""Debug toolbar API route handlers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from litestar.connection import WebSocket as LitestarWebSocket
from litestar.exceptions import NotFoundException
from litestar.response import Response

from debug_toolbar.core.assets import get_toolbar_css, get_toolbar_js
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
    call_count = stats.get("function_calls", 0)
    has_flamegraph = stats.get("flamegraph_data") is not None

    html += f"""
    <div class='profiling-summary'>
        <div class='prof-stat'>
            <span class='stat-value'>{total_time * 1000:.2f}ms</span>
            <span class='stat-label'>Total Time</span>
        </div>
        <div class='prof-stat'>
            <span class='stat-value'>{call_count}</span>
            <span class='stat-label'>Calls</span>
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
