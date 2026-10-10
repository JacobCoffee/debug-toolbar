"""Debug toolbar API routes for Starlette."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.routing import Route

    from debug_toolbar.core.storage import ToolbarStorage

HTTP_STATUS_OK_MIN = 200
HTTP_STATUS_OK_MAX = 300


def _render_request_row(request_id: UUID, data: dict[str, Any]) -> str:
    """Render a single request row for the history table."""
    metadata = data.get("metadata", {})
    timing = data.get("timing_data", {})
    method = metadata.get("method", "GET")
    path = metadata.get("path", "/")
    status = metadata.get("status_code", HTTP_STATUS_OK_MIN)
    total_time = timing.get("total_time", 0) * 1000

    status_class = "status-success" if HTTP_STATUS_OK_MIN <= status < HTTP_STATUS_OK_MAX else "status-error"

    return f"""
    <tr class="request-row" data-request-id="{request_id}">
        <td><a href="/_debug_toolbar/{request_id}">{str(request_id)[:8]}...</a></td>
        <td><span class="method-badge method-{method.lower()}">{method}</span></td>
        <td class="path-cell">{path}</td>
        <td><span class="status-badge {status_class}">{status}</span></td>
        <td>{total_time:.2f}ms</td>
    </tr>
    """


def _get_toolbar_css() -> str:
    """Get the toolbar CSS content."""
    from debug_toolbar.litestar.routes.handlers import get_toolbar_css

    return get_toolbar_css()


def _get_toolbar_js() -> str:
    """Get the toolbar JavaScript content."""
    from debug_toolbar.litestar.routes.handlers import get_toolbar_js

    return get_toolbar_js()


def _render_index_html(requests_data: list[tuple[UUID, dict[str, Any]]]) -> str:
    """Render the index HTML page."""
    rows_html = [_render_request_row(rid, data) for rid, data in requests_data]
    empty_row = '<tr><td colspan="5" class="empty">No requests recorded yet</td></tr>'
    tbody_content = "".join(rows_html) if rows_html else empty_row

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug Toolbar - Request History</title>
    <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
</head>
<body>
    <div class="toolbar-page">
        <header class="toolbar-header">
            <h1>Debug Toolbar</h1>
            <p>Request History ({len(requests_data)} requests)</p>
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
                <tbody>{tbody_content}</tbody>
            </table>
        </main>
    </div>
    <script src="/_debug_toolbar/static/toolbar.js"></script>
</body>
</html>"""


def _render_detail_html(request_id: UUID, data: dict[str, Any]) -> str:
    """Render the request detail HTML page."""
    metadata = data.get("metadata", {})
    timing = data.get("timing_data", {})
    panels_data = data.get("panels", {})

    method = metadata.get("method", "GET")
    path = metadata.get("path", "/")
    status = metadata.get("status_code", HTTP_STATUS_OK_MIN)
    total_time = timing.get("total_time", 0) * 1000

    panels_html = []
    for panel_id, panel_data in panels_data.items():
        panel_content = "<pre>" + str(panel_data) + "</pre>"
        panels_html.append(f"""
        <div class="panel-section">
            <h3>{panel_id}</h3>
            {panel_content}
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug Toolbar - Request {str(request_id)[:8]}</title>
    <link rel="stylesheet" href="/_debug_toolbar/static/toolbar.css">
</head>
<body>
    <div class="toolbar-page">
        <header class="toolbar-header">
            <h1>Request Details</h1>
            <p><a href="/_debug_toolbar/">← Back to History</a></p>
        </header>
        <main class="toolbar-main">
            <div class="request-summary">
                <h2>{method} {path}</h2>
                <p>Status: {status} | Time: {total_time:.2f}ms | ID: {request_id}</p>
            </div>
            <div class="panels-container">
                {"".join(panels_html)}
            </div>
        </main>
    </div>
    <script src="/_debug_toolbar/static/toolbar.js"></script>
</body>
</html>"""


def create_debug_toolbar_routes(storage: ToolbarStorage) -> list[Route]:
    """Create the debug toolbar routes.

    Args:
        storage: The toolbar storage instance.

    Returns:
        List of Starlette Route objects for the debug toolbar.
    """
    from starlette.responses import HTMLResponse, JSONResponse, Response
    from starlette.routing import Route

    async def get_toolbar_index(_request: Request) -> Response:
        """Get the debug toolbar history page."""
        requests_data = storage.get_all()
        html = _render_index_html(requests_data)
        return HTMLResponse(html)

    async def get_request_detail(request: Request) -> Response:
        """Get detailed view for a specific request."""
        request_id_str = request.path_params.get("request_id", "")
        try:
            request_id = UUID(request_id_str)
        except ValueError:
            return HTMLResponse("<h1>Invalid request ID</h1>", status_code=400)

        data = storage.get(request_id)
        if data is None:
            return HTMLResponse(f"<h1>Request {request_id} not found</h1>", status_code=404)

        html = _render_detail_html(request_id, data)
        return HTMLResponse(html)

    async def get_requests_json(_request: Request) -> Response:
        """Get all requests as JSON."""
        requests_data = storage.get_all()
        return JSONResponse(
            [
                {
                    "request_id": str(rid),
                    "metadata": d.get("metadata", {}),
                    "timing": d.get("timing_data", {}),
                }
                for rid, d in requests_data
            ]
        )

    async def get_request_json(request: Request) -> Response:
        """Get a specific request as JSON."""
        request_id_str = request.path_params.get("request_id", "")
        try:
            request_id = UUID(request_id_str)
        except ValueError:
            return JSONResponse({"error": "Invalid request ID"}, status_code=400)

        data = storage.get(request_id)
        if data is None:
            return JSONResponse({"error": f"Request {request_id} not found"}, status_code=404)

        return JSONResponse({"request_id": str(request_id), **data})

    async def get_static_css(_request: Request) -> Response:
        """Serve the toolbar CSS."""
        css = _get_toolbar_css()
        return Response(content=css, media_type="text/css")

    async def get_static_js(_request: Request) -> Response:
        """Serve the toolbar JavaScript."""
        js = _get_toolbar_js()
        return Response(content=js, media_type="application/javascript")

    return [
        Route("/_debug_toolbar/", endpoint=get_toolbar_index, name="debug_toolbar_index"),
        Route("/_debug_toolbar/{request_id}", endpoint=get_request_detail, name="debug_toolbar_detail"),
        Route("/_debug_toolbar/api/requests", endpoint=get_requests_json, name="debug_toolbar_api_requests"),
        Route(
            "/_debug_toolbar/api/requests/{request_id}",
            endpoint=get_request_json,
            name="debug_toolbar_api_request_detail",
        ),
        Route("/_debug_toolbar/static/toolbar.css", endpoint=get_static_css, name="debug_toolbar_css"),
        Route("/_debug_toolbar/static/toolbar.js", endpoint=get_static_js, name="debug_toolbar_js"),
    ]
