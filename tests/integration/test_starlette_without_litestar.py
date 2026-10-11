"""The Starlette/FastAPI integration must work when Litestar is not installed."""

from __future__ import annotations

import subprocess
import sys

CHECK = """
import sys
sys.modules["litestar"] = None

from starlette.applications import Starlette
from starlette.testclient import TestClient

from debug_toolbar.core.toolbar import DebugToolbar
from debug_toolbar.starlette import StarletteDebugToolbarConfig, create_debug_toolbar_routes

toolbar = DebugToolbar(StarletteDebugToolbarConfig(enabled=True))
client = TestClient(Starlette(routes=create_debug_toolbar_routes(toolbar.storage)))
for name in ("toolbar.css", "toolbar.js"):
    response = client.get(f"/_debug_toolbar/static/{name}")
    assert response.status_code == 200, name
    assert response.text, name
"""


def test_toolbar_assets_load_without_litestar() -> None:
    result = subprocess.run([sys.executable, "-c", CHECK], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
