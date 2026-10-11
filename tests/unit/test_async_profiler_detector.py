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


async def test_overlapping_detectors_share_loop_state_safely() -> None:
    """Two detectors installed on the same loop at once must not clobber each
    other's loop debug state: uninstalling one must not disturb the other, and
    the loop's original settings are restored only once both have uninstalled.
    """
    loop = asyncio.get_running_loop()
    asyncio_logger = logging.getLogger("asyncio")
    original_debug = loop.get_debug()
    original_duration = loop.slow_callback_duration
    original_level = asyncio_logger.level

    detector_a = BlockingCallDetector(threshold_ms=50)
    detector_b = BlockingCallDetector(threshold_ms=80)
    detector_a.install(loop)
    detector_b.install(loop)
    try:
        task = loop.create_task(_blocking_handler())
        await asyncio.sleep(0.3)
        await task
    finally:
        detector_a.uninstall()
        assert loop.get_debug() is True
        detector_b.uninstall()

    assert loop.get_debug() == original_debug
    assert loop.slow_callback_duration == original_duration
    assert asyncio_logger.level == original_level

    assert len(detector_a.get_stats()["blocking_calls"]) == 1
    assert len(detector_b.get_stats()["blocking_calls"]) == 1


async def test_install_only_raises_logger_level_when_more_restrictive() -> None:
    """A user's asyncio logger level more verbose than WARNING must survive
    install/uninstall unchanged, while a level that would hide WARNING
    records (e.g. ERROR) must be raised to WARNING while installed.
    """
    loop = asyncio.get_running_loop()
    asyncio_logger = logging.getLogger("asyncio")

    original_level = asyncio_logger.level
    try:
        asyncio_logger.setLevel(logging.DEBUG)
        detector = BlockingCallDetector(threshold_ms=50)
        detector.install(loop)
        assert asyncio_logger.level == logging.DEBUG
        detector.uninstall()
        assert asyncio_logger.level == logging.DEBUG

        asyncio_logger.setLevel(logging.ERROR)
        detector = BlockingCallDetector(threshold_ms=50)
        detector.install(loop)
        assert asyncio_logger.level == logging.WARNING
        detector.uninstall()
        assert asyncio_logger.level == logging.ERROR
    finally:
        asyncio_logger.setLevel(original_level)
