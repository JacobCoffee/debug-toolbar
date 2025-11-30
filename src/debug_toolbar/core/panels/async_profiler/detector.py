"""Detection utilities for blocking calls and event loop lag."""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from debug_toolbar.core.panels.async_profiler.models import BlockingCall, LagSample

if TYPE_CHECKING:
    ExceptionHandler = Callable[[asyncio.AbstractEventLoop, dict[str, Any]], object]

logger = logging.getLogger(__name__)

DEFAULT_BLOCKING_THRESHOLD_MS = 100.0
DEFAULT_LAG_THRESHOLD_MS = 10.0
DEFAULT_SAMPLE_INTERVAL_MS = 10.0
DEFAULT_MAX_STACK_DEPTH = 10
STACK_SKIP_FRAMES = 3
MS_TO_SECONDS = 1000.0


def _get_stack_frames(
    skip: int = STACK_SKIP_FRAMES, limit: int = DEFAULT_MAX_STACK_DEPTH
) -> list[dict[str, str | int]]:
    """Capture the current call stack.

    Args:
        skip: Number of most recent frames to skip.
        limit: Maximum number of frames to return.

    Returns:
        List of dictionaries containing frame information.
    """
    frames = []
    for frame_info in traceback.extract_stack()[:-skip][-limit:]:
        frames.append(
            {
                "file": frame_info.filename,
                "line": frame_info.lineno,
                "function": frame_info.name,
                "code": frame_info.line or "",
            }
        )
    return frames


class BlockingCallDetector:
    """Detects blocking calls in async context.

    Uses asyncio's debug mode and slow callback duration feature
    to detect when synchronous code blocks the event loop.
    """

    __slots__ = (
        "_blocking_calls",
        "_loop",
        "_original_debug",
        "_original_duration",
        "_original_handler",
        "_threshold_ms",
    )

    def __init__(self, threshold_ms: float = DEFAULT_BLOCKING_THRESHOLD_MS) -> None:
        """Initialize the blocking call detector.

        Args:
            threshold_ms: Threshold in milliseconds for detecting blocking calls.
        """
        self._threshold_ms = threshold_ms
        self._blocking_calls: list[BlockingCall] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._original_debug: bool = False
        self._original_duration: float = 0.1
        self._original_handler: ExceptionHandler | None = None

    def install(self, loop: asyncio.AbstractEventLoop) -> None:
        """Install blocking call detection on the event loop.

        Args:
            loop: The asyncio event loop to monitor.
        """
        self._loop = loop
        self._blocking_calls = []

        self._original_debug = loop.get_debug()
        self._original_duration = loop.slow_callback_duration
        self._original_handler = loop.get_exception_handler()

        loop.set_debug(True)
        loop.slow_callback_duration = self._threshold_ms / MS_TO_SECONDS
        loop.set_exception_handler(self._exception_handler)

    def _exception_handler(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        """Custom exception handler that captures slow callback warnings.

        Args:
            loop: The event loop.
            context: Exception context dictionary.
        """
        message = context.get("message", "")
        if "Executing" in message and "took" in message and "seconds" in message:
            import re

            match = re.search(r"took ([\d.]+) seconds", message)
            if match:
                duration_s = float(match.group(1))
                duration_ms = duration_s * MS_TO_SECONDS
                source = context.get("source_traceback", [])
                if source:
                    frame = source[-1] if source else None
                    self.record_blocking_call(
                        duration_ms=duration_ms,
                        function_name=frame.name if frame else "unknown",
                        file=frame.filename if frame else "unknown",
                        line=frame.lineno if frame else 0,
                    )
                else:
                    self.record_blocking_call(duration_ms=duration_ms)

        if self._original_handler:
            self._original_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    def uninstall(self) -> None:
        """Uninstall blocking call detection and restore original settings."""
        if self._loop is None:
            return

        self._loop.set_debug(self._original_debug)
        self._loop.slow_callback_duration = self._original_duration
        self._loop.set_exception_handler(self._original_handler)

    def record_blocking_call(
        self,
        duration_ms: float,
        function_name: str = "unknown",
        file: str = "unknown",
        line: int = 0,
    ) -> None:
        """Record a blocking call detection.

        Args:
            duration_ms: Duration of the blocking call in milliseconds.
            function_name: Name of the blocking function.
            file: File where the blocking call occurred.
            line: Line number of the blocking call.
        """
        if self._loop is None:
            return

        self._blocking_calls.append(
            BlockingCall(
                timestamp=self._loop.time(),
                duration_ms=duration_ms,
                function_name=function_name,
                file=file,
                line=line,
                stack_frames=_get_stack_frames(),
            )
        )

    def get_stats(self) -> dict[str, Any]:
        """Get blocking call statistics.

        Returns:
            Dictionary containing blocking call data.
        """
        calls = []
        for call in self._blocking_calls:
            calls.append(
                {
                    "timestamp": call.timestamp,
                    "duration_ms": call.duration_ms,
                    "function_name": call.function_name,
                    "file": call.file,
                    "line": call.line,
                    "stack_frames": call.stack_frames,
                }
            )

        return {
            "blocking_calls": calls,
            "total_blocking_time_ms": sum(c.duration_ms for c in self._blocking_calls),
        }


class EventLoopLagMonitor:
    """Monitors event loop lag via scheduled callbacks.

    Measures the difference between expected and actual callback execution
    times to detect when the event loop is falling behind.
    """

    __slots__ = (
        "_handle",
        "_lag_threshold_ms",
        "_last_check",
        "_loop",
        "_max_lag_ms",
        "_running",
        "_sample_interval",
        "_samples",
        "_start_time",
    )

    def __init__(
        self,
        sample_interval_ms: float = DEFAULT_SAMPLE_INTERVAL_MS,
        lag_threshold_ms: float = DEFAULT_LAG_THRESHOLD_MS,
    ) -> None:
        """Initialize the event loop lag monitor.

        Args:
            sample_interval_ms: Interval between lag checks in milliseconds.
            lag_threshold_ms: Threshold for recording lag samples.
        """
        self._sample_interval = sample_interval_ms / MS_TO_SECONDS
        self._lag_threshold_ms = lag_threshold_ms
        self._samples: list[LagSample] = []
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_check: float = 0.0
        self._start_time: float = 0.0
        self._max_lag_ms: float = 0.0
        self._handle: asyncio.TimerHandle | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start monitoring event loop lag.

        Args:
            loop: The asyncio event loop to monitor.
        """
        self._loop = loop
        self._running = True
        self._samples = []
        self._max_lag_ms = 0.0
        self._start_time = loop.time()
        self._last_check = time.perf_counter()

        self._schedule_check()

    def _schedule_check(self) -> None:
        """Schedule the next lag check."""
        if not self._running or self._loop is None:
            return

        self._handle = self._loop.call_later(self._sample_interval, self._check_lag)

    def _check_lag(self) -> None:
        """Check for event loop lag."""
        if not self._running or self._loop is None:
            return

        current = time.perf_counter()
        actual_delta = current - self._last_check
        expected_delta = self._sample_interval
        lag_ms = max(0.0, (actual_delta - expected_delta) * MS_TO_SECONDS)

        if lag_ms > self._lag_threshold_ms:
            self._samples.append(
                LagSample(
                    timestamp=self._loop.time() - self._start_time,
                    expected_delta=expected_delta,
                    actual_delta=actual_delta,
                    lag_ms=lag_ms,
                )
            )
            self._max_lag_ms = max(self._max_lag_ms, lag_ms)

        self._last_check = current
        self._schedule_check()

    def stop(self) -> None:
        """Stop monitoring event loop lag."""
        self._running = False
        if self._handle:
            self._handle.cancel()
            self._handle = None

    def get_stats(self) -> dict[str, Any]:
        """Get event loop lag statistics.

        Returns:
            Dictionary containing lag monitoring data.
        """
        samples = []
        for sample in self._samples:
            samples.append(
                {
                    "timestamp": sample.timestamp,
                    "expected_delta": sample.expected_delta,
                    "actual_delta": sample.actual_delta,
                    "lag_ms": sample.lag_ms,
                }
            )

        return {
            "samples": samples,
            "max_lag_ms": self._max_lag_ms,
            "sample_count": len(self._samples),
        }
