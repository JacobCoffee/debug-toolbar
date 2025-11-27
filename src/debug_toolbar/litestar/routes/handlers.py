"""Debug toolbar API route handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from litestar.exceptions import NotFoundException
from litestar.response import Response

from litestar import Request, Router, get, post

if TYPE_CHECKING:
    from debug_toolbar.core.storage import ToolbarStorage


DEFAULT_DISPLAY_DEPTH = 10
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_STRING = 1000


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
                f"<strong>{_escape_html(str(k))}</strong>: {_format_value(v, max_depth - 1, max_items, max_string)}"
            )
        if len(value) > max_items:
            items.append(f"...{len(value) - max_items} more")
        return f"<span class='object'>{{{', '.join(items)}}}</span>"
    return f"<span class='unknown'>{_escape_html(str(value)[:max_string])}</span>"


def _render_panel_content(stats: dict[str, Any]) -> str:
    """Render panel content as HTML."""
    if not stats:
        return "<p class='empty'>No data</p>"
    rows = []
    for key, value in stats.items():
        escaped_key = _escape_html(str(key))
        formatted_value = _format_value(value)
        rows.append(f"<tr><td class='key'>{escaped_key}</td><td class='value'>{formatted_value}</td></tr>")
    return f"<table class='panel-table'><tbody>{''.join(rows)}</tbody></table>"


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
            panel_content = _render_panel_content(stats)
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

    index_handler = get("/")(get_toolbar_index)
    detail_handler = get("/{request_id:uuid}")(get_request_detail)
    api_requests_handler = get("/api/requests")(get_requests_json)
    api_request_handler = get("/api/requests/{request_id:uuid}")(get_request_json)
    api_explain_handler = post("/api/explain")(post_explain)
    css_handler = get("/static/toolbar.css")(get_static_css)
    js_handler = get("/static/toolbar.js")(get_static_js)

    return Router(
        path="/_debug_toolbar",
        route_handlers=[
            index_handler,
            detail_handler,
            api_requests_handler,
            api_request_handler,
            api_explain_handler,
            css_handler,
            js_handler,
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
    --dt-text-muted: #707070;
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
    --dt-text-muted: #888888;
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

#debug-toolbar.collapsed .toolbar-panels,
#debug-toolbar.collapsed .toolbar-details,
#debug-toolbar.collapsed .toolbar-content {
    display: none;
}

/* Collapsed state for side positions */
#debug-toolbar.collapsed[data-position="right"],
#debug-toolbar[data-position="right"].collapsed,
#debug-toolbar.collapsed[data-position="left"],
#debug-toolbar[data-position="left"].collapsed {
    width: auto;
    min-width: 0;
}

#debug-toolbar.collapsed[data-position="top"],
#debug-toolbar[data-position="top"].collapsed,
#debug-toolbar.collapsed[data-position="bottom"],
#debug-toolbar[data-position="bottom"].collapsed {
    height: auto;
    min-height: 0;
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
        this.isCollapsed = false;
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
                        if (this.isSqlPanel(panelData)) {
                            details.innerHTML = this.renderSqlPanel(panelData);
                        } else {
                            details.innerHTML = this.renderPanelData(panelData);
                        }
                        details.classList.add('expanded');
                    }
                })
                .catch(err => console.error('Failed to load panel data:', err));
        }
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

    isSqlPanel(data) {
        return data && (data.queries !== undefined || data.total_queries !== undefined);
    }

    renderSqlPanel(data) {
        if (!data || !data.queries || data.queries.length === 0) {
            return '<p class="empty">No SQL queries</p>';
        }

        let html = '<div class="sql-panel">';
        html += '<h3>Total Queries: ' + (data.total_queries || data.queries.length) + '</h3>';

        data.queries.forEach((query, index) => {
            const supportsExplain = query.supports_explain !== false;
            const sql = query.sql || query.query || '';
            const params = query.raw_parameters || query.parameters || {};
            const hasParams = params && Object.keys(params).length > 0;
            const sqlEncoded = btoa(unescape(encodeURIComponent(sql)));
            const paramsEncoded = btoa(unescape(encodeURIComponent(JSON.stringify(params))));

            html += '<div class="sql-query-container">';
            html += '<div class="sql-query-header">';
            html += '<span class="sql-query-title">Query #' + (index + 1) + '</span>';
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
            if (query.duration !== undefined) {
                html += '<div class="sql-query-params"><strong>Duration:</strong> ' +
                        query.duration.toFixed(2) + 'ms</div>';
            }
            html += '</div>';
        });

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
