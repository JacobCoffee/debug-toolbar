"""Versions panel for displaying Python and package versions."""

from __future__ import annotations

import platform
import sys
from importlib.metadata import distributions
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

if TYPE_CHECKING:
    from debug_toolbar.core.context import RequestContext


class VersionsPanel(Panel):
    """Panel displaying Python and package version information.

    Shows:
    - Python version
    - Platform information
    - Installed packages
    """

    panel_id: ClassVar[str] = "VersionsPanel"
    title: ClassVar[str] = "Versions"
    template: ClassVar[str] = "panels/versions.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Versions"

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate version statistics."""
        packages = []
        for dist in distributions():
            packages.append(
                {
                    "name": dist.metadata["Name"],
                    "version": dist.metadata["Version"],
                }
            )

        packages.sort(key=lambda x: x["name"].lower())

        return {
            "python_version": sys.version,
            "python_version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
                "releaselevel": sys.version_info.releaselevel,
            },
            "platform": platform.platform(),
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_machine": platform.machine(),
            "packages": packages,
            "package_count": len(packages),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing Python version."""
        return f"Python {sys.version_info.major}.{sys.version_info.minor}"
