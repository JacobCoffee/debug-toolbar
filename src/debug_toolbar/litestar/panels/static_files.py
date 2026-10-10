"""Static files panel for displaying configured static file locations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


def _static_directories(handler: Any) -> list[str] | None:
    """Return the configured directories for a static file handler, or None.

    Litestar's ``create_static_files_router`` builds its handlers as closures
    over a ``StaticFiles`` instance, so the only way to recover the configured
    directories is to inspect that closure.
    """
    fn = getattr(handler, "fn", None)
    if fn is None or not getattr(fn, "__closure__", None):
        return None

    for name, cell in zip(fn.__code__.co_freevars, fn.__closure__, strict=True):
        if name != "static_files":
            continue
        directories = getattr(cell.cell_contents, "directories", None)
        if not directories:
            return None
        return [str(directory) for directory in directories]

    return None


def collect_static_files_metadata(app: Any, context: RequestContext) -> None:
    """Collect configured static file mount points from a Litestar app.

    Args:
        app: The Litestar application.
        context: The request context to populate.
    """
    mounts: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for route in getattr(app, "routes", []):
        for handler in getattr(route, "route_handlers", None) or []:
            directories = _static_directories(handler)
            if directories is None:
                continue

            url_path = route.path.split("{")[0].rstrip("/") or "/"
            if url_path in seen_paths:
                break
            seen_paths.add(url_path)
            mounts.append({"url_path": url_path, "directories": directories})
            break

    mounts.sort(key=lambda mount: mount["url_path"])
    context.metadata["static_files"] = mounts


class StaticFilesPanel(Panel):
    """Panel displaying where an app's static files are served from.

    Shows the URL path and folder(s) on disk for every static file mount
    registered on the application (e.g. via ``create_static_files_router``).
    It does not track which static files a specific page actually loaded.
    """

    panel_id: ClassVar[str] = "StaticFilesPanel"
    title: ClassVar[str] = "Static files"
    template: ClassVar[str] = "panels/static_files.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Static files"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate static file mount statistics."""
        mounts = context.metadata.get("static_files", [])

        if not mounts:
            return {"mounts": [], "message": "No static files configured"}

        return {"mounts": mounts, "mount_count": len(mounts)}

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle."""
        return ""
