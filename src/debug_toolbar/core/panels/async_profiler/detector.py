"""Detection utilities for blocking calls and event loop lag."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
import traceback
from typing import Any
from weakref import WeakKeyDictionary

from debug_toolbar.core.panels.async_profiler.models import BlockingCall, LagSample

logger = logging.getLogger(__name__)

DEFAULT_BLOCKING_THRESHOLD_MS = 100.0
DEFAULT_LAG_THRESHOLD_MS = 10.0
DEFAULT_SAMPLE_INTERVAL_MS = 10.0
DEFAULT_MAX_STACK_DEPTH = 10
STACK_SKIP_FRAMES = 3
MS_TO_SECONDS = 1000.0
ASYNCIO_LOGGER_NAME = "asyncio"
SLOW_CALLBACK_LOG_ARGS = 2

_SLOW_CALLBACK_LOCATION_RE = re.compile(
    r"(?P<func>[\w.]+)\(\).*?(?:running at|created at|defined at) (?P<file>.+?):(?P<line>\d+)"
)


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


class _LoopDebugPatchState:
    """Tracks the refcounted patch of a loop's debug mode, slow callback
    duration, and the ``asyncio`` logger level while one or more
    ``BlockingCallDetector`` instances are installed on it.
    """

    __slots__ = (
        "logger_level_changed",
        "original_debug",
        "original_duration",
        "original_logger_level",
        "thresholds_ms",
    )

    def __init__(self) -> None:
        self.original_debug: bool = False
        self.original_duration: float = 0.1
        self.original_logger_level: int = logging.NOTSET
        self.logger_level_changed: bool = False
        self.thresholds_ms: dict[int, float] = {}


_loop_patch_lock = threading.Lock()
_loop_patch_states: WeakKeyDictionary[asyncio.AbstractEventLoop, _LoopDebugPatchState] = WeakKeyDictionary()


def _acquire_loop_patch(loop: asyncio.AbstractEventLoop, detector_key: int, threshold_ms: float) -> None:
    """Enable debug mode and slow-callback logging on a loop, shared across detectors.

    Overlapping ``BlockingCallDetector.install()`` calls on the same loop share
    one patch of the loop's debug state so the first detector to uninstall does
    not disturb detectors still running, and the loop's original settings are
    only restored once every detector has uninstalled.

    Args:
        loop: The event loop to patch.
        detector_key: A key unique to the calling detector (its ``id()``).
        threshold_ms: The calling detector's blocking-call threshold.
    """
    with _loop_patch_lock:
        state = _loop_patch_states.get(loop)
        if state is None:
            state = _LoopDebugPatchState()
            state.original_debug = loop.get_debug()
            state.original_duration = loop.slow_callback_duration
            asyncio_logger = logging.getLogger(ASYNCIO_LOGGER_NAME)
            if asyncio_logger.getEffectiveLevel() > logging.WARNING:
                state.original_logger_level = asyncio_logger.level
                state.logger_level_changed = True
                asyncio_logger.setLevel(logging.WARNING)
            _loop_patch_states[loop] = state

        state.thresholds_ms[detector_key] = threshold_ms
        loop.set_debug(True)
        loop.slow_callback_duration = min(state.thresholds_ms.values()) / MS_TO_SECONDS


def _release_loop_patch(loop: asyncio.AbstractEventLoop, detector_key: int) -> None:
    """Release one detector's share of a loop's debug patch.

    Restores the loop's original debug mode, slow callback duration, and
    (if it was changed) the ``asyncio`` logger level once no detector remains
    installed on the loop.

    Args:
        loop: The event loop to release.
        detector_key: The key passed to the matching ``_acquire_loop_patch`` call.
    """
    with _loop_patch_lock:
        state = _loop_patch_states.get(loop)
        if state is None:
            return

        state.thresholds_ms.pop(detector_key, None)
        if state.thresholds_ms:
            loop.slow_callback_duration = min(state.thresholds_ms.values()) / MS_TO_SECONDS
            return

        loop.set_debug(state.original_debug)
        loop.slow_callback_duration = state.original_duration
        if state.logger_level_changed:
            logging.getLogger(ASYNCIO_LOGGER_NAME).setLevel(state.original_logger_level)
        del _loop_patch_states[loop]


class BlockingCallDetector:
    """Detects blocking calls in async context.

    Uses asyncio's debug mode and slow callback duration feature
    to detect when synchronous code blocks the event loop.
    """

    __slots__ = (
        "_blocking_calls",
        "_log_handler",
        "_loop",
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
        self._log_handler: _SlowCallbackLogHandler | None = None

    def install(self, loop: asyncio.AbstractEventLoop) -> None:
        """Install blocking call detection on the event loop.

        Shares the loop's debug mode, slow callback duration, and ``asyncio``
        logger level with any other detector already installed on the same
        loop, so overlapping requests can detect blocking calls concurrently
        without one request's cleanup disturbing another's.

        Args:
            loop: The asyncio event loop to monitor.
        """
        self._loop = loop
        self._blocking_calls = []

        _acquire_loop_patch(loop, id(self), self._threshold_ms)

        self._log_handler = _SlowCallbackLogHandler(self, self._threshold_ms)
        logging.getLogger(ASYNCIO_LOGGER_NAME).addHandler(self._log_handler)

    def uninstall(self) -> None:
        """Uninstall blocking call detection.

        Only restores the loop's debug mode, slow callback duration, and
        logger level once every detector sharing the loop has uninstalled.
        """
        if self._loop is None:
            return

        if self._log_handler is not None:
            logging.getLogger(ASYNCIO_LOGGER_NAME).removeHandler(self._log_handler)
            self._log_handler = None

        _release_loop_patch(self._loop, id(self))

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


class _SlowCallbackLogHandler(logging.Handler):
    """Logging handler that turns asyncio's slow-callback warnings into blocking call records.

    CPython's event loop reports slow callbacks (when running in debug mode past
    ``slow_callback_duration``) by calling ``logging.getLogger("asyncio").warning(...)``
    directly from ``BaseEventLoop._run_once``, not via ``call_exception_handler``. This
    handler is attached directly to the ``asyncio`` logger to observe those records.
    """

    __slots__ = ("_detector", "_threshold_ms")

    def __init__(self, detector: BlockingCallDetector, threshold_ms: float) -> None:
        super().__init__(level=logging.WARNING)
        self._detector = detector
        self._threshold_ms = threshold_ms

    def emit(self, record: logging.LogRecord) -> None:
        """Parse a slow-callback warning record and record it as a blocking call.

        Args:
            record: The log record emitted by the asyncio logger.
        """
        if record.name != ASYNCIO_LOGGER_NAME or not isinstance(record.msg, str):
            return
        if not record.msg.startswith("Executing") or "took" not in record.msg:
            return

        args = record.args
        if not isinstance(args, tuple) or len(args) < SLOW_CALLBACK_LOG_ARGS:
            return

        duration_arg = args[1]
        if not isinstance(duration_arg, (int, float)):
            return
        duration_ms = float(duration_arg) * MS_TO_SECONDS
        if duration_ms < self._threshold_ms:
            return

        handle_repr = str(args[0])
        match = _SLOW_CALLBACK_LOCATION_RE.search(handle_repr)
        if match:
            function_name = match.group("func")
            file = match.group("file")
            line = int(match.group("line"))
        else:
            function_name, file, line = "unknown", "unknown", 0

        self._detector.record_blocking_call(
            duration_ms=duration_ms,
            function_name=function_name,
            file=file,
            line=line,
        )


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
