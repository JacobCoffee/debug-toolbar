"""Shared fixtures for testing the applications under ``examples/``.

``examples`` is a real (namespace) package, but its submodules build module-level
singletons (toolbars, Litestar/Starlette/FastAPI apps, on-disk storage files) at
import time. Importing the same example twice in a test session would reuse that
stale state, so every test must import examples through the ``import_example``
fixture below, which evicts any cached module (and its submodules) before and
after each import to guarantee a fresh app per test.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType


def _evict(dotted_path: str) -> None:
    """Remove ``dotted_path`` and any of its submodules from ``sys.modules``."""
    for name in [n for n in sys.modules if n == dotted_path or n.startswith(f"{dotted_path}.")]:
        del sys.modules[name]


@pytest.fixture
def import_example() -> Iterator[Callable[[str], ModuleType]]:
    """Import an example module fresh, isolating module-level state between tests.

    Usage::

        def test_something(import_example):
            app_module = import_example("examples.litestar_basic.app")
            client = TestClient(app_module.app)
    """
    imported: list[str] = []

    def _import(dotted_path: str) -> ModuleType:
        _evict(dotted_path)
        module = importlib.import_module(dotted_path)
        imported.append(dotted_path)
        return module

    yield _import

    for dotted_path in imported:
        _evict(dotted_path)
