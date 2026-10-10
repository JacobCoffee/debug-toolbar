"""Tests for the task factory async profiler backend."""

from __future__ import annotations

import asyncio
import sys

import pytest

from debug_toolbar.core.panels.async_profiler.taskfactory import TaskFactoryBackend


async def _child() -> str:
    return "ok"


@pytest.mark.skipif(sys.version_info < (3, 14), reason="create_task forwards eager_start to task factories on 3.14+")
async def test_create_task_with_eager_start_while_profiling() -> None:
    loop = asyncio.get_running_loop()
    backend = TaskFactoryBackend()
    backend.start(loop)
    try:
        result = await loop.create_task(_child(), eager_start=False)
    finally:
        backend.stop()

    assert result == "ok"
