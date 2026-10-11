"""Tests for the async profiler blocking call detector."""

from __future__ import annotations

import asyncio
import logging
import time

from debug_toolbar.core.panels.async_profiler.detector import BlockingCallDetector


async def _blocking_handler() -> None:
    time.sleep(0.15)  # noqa: ASYNC251 -- intentional blocking call under test


async def test_detects_real_blocking_call() -> None:
    """asyncio reports slow callbacks via the ``asyncio`` logger, not
    ``call_exception_handler``, so the detector must hook the logger to see them.
    """
    loop = asyncio.get_running_loop()
    detector = BlockingCallDetector(threshold_ms=50)
    detector.install(loop)
    try:
        task = loop.create_task(_blocking_handler())
        await asyncio.sleep(0.3)
        await task
    finally:
        detector.uninstall()

    stats = detector.get_stats()
    assert len(stats["blocking_calls"]) == 1
    call = stats["blocking_calls"][0]
    assert call["function_name"] == "_blocking_handler"
    assert call["duration_ms"] >= 100


async def test_no_false_positives_for_fast_code() -> None:
    loop = asyncio.get_running_loop()
    detector = BlockingCallDetector(threshold_ms=100)
    detector.install(loop)
    try:
        await asyncio.sleep(0.01)
    finally:
        detector.uninstall()

    stats = detector.get_stats()
    assert stats["blocking_calls"] == []


async def test_uninstall_restores_logger_and_loop_state() -> None:
    loop = asyncio.get_running_loop()
    asyncio_logger = logging.getLogger("asyncio")
    original_debug = loop.get_debug()
    original_duration = loop.slow_callback_duration
    original_level = asyncio_logger.level
    original_handlers = list(asyncio_logger.handlers)

    detector = BlockingCallDetector(threshold_ms=50)
    detector.install(loop)
    detector.uninstall()

    assert loop.get_debug() == original_debug
    assert loop.slow_callback_duration == original_duration
    assert asyncio_logger.level == original_level
    assert asyncio_logger.handlers == original_handlers
