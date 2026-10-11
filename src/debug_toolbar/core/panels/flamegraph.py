"""Flame graph generator for cProfile data.

This module converts cProfile statistics into the speedscope JSON format
for interactive flame graph visualization.
"""

from __future__ import annotations

import pstats
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import cProfile


SPEEDSCOPE_SCHEMA_VERSION = "https://www.speedscope.app/file-format-schema.json"
CPROFILE_FUNC_TUPLE_LENGTH = 3


class FlameGraphGenerator:
    """Generate flame graph data from cProfile stats.

    Converts cProfile statistics into the speedscope JSON format,
    which can be visualized using speedscope.app or embedded viewers.

    The speedscope format uses a sampled profile type with frames
    representing function calls and their hierarchical relationships.
    """

    __slots__ = ("_frame_map", "_frames", "_stats")

    def __init__(self, profiler: cProfile.Profile) -> None:
        """Initialize the flame graph generator.

        Args:
            profiler: The cProfile profiler instance to extract data from.
        """
        self._stats = pstats.Stats(profiler)
        self._frames: list[dict[str, Any]] = []
        self._frame_map: dict[tuple[str, int, str], int] = {}

    def generate(self) -> dict[str, Any]:
        """Generate speedscope JSON format from cProfile stats.

        Returns:
            Dictionary representing the speedscope JSON format with:
            - $schema: The speedscope schema URL
            - shared.frames: List of frame definitions
            - profiles: List of profile data with samples and weights
        """
        self._frames = []
        self._frame_map = {}

        samples: list[list[int]] = []
        weights: list[float] = []

        for func, (_cc, _nc, _tt, ct, _callers) in self._stats.stats.items():  # type: ignore[attr-defined]
            if isinstance(func, tuple) and len(func) == CPROFILE_FUNC_TUPLE_LENGTH:
                filename, lineno, func_name = func
            else:
                filename = str(func)
                lineno = 0
                func_name = "unknown"

            frame_idx = self._get_or_create_frame(func_name, filename, lineno)

            if ct > 0:
                samples.append([frame_idx])
                weights.append(ct)

        total_time = self._stats.total_tt  # type: ignore[attr-defined]

        return {
            "$schema": SPEEDSCOPE_SCHEMA_VERSION,
            "shared": {"frames": self._frames},
            "profiles": [
                {
                    "type": "sampled",
                    "name": "Request Profile",
                    "unit": "seconds",
                    "startValue": 0,
                    "endValue": total_time,
                    "samples": samples,
                    "weights": weights,
                }
            ],
            "exporter": "async-python-debug-toolbar",
            "activeProfileIndex": 0,
        }

    def _get_or_create_frame(self, name: str, file: str, line: int) -> int:
        """Get or create a frame index for the given function.

        Args:
            name: Function name
            file: File path
            line: Line number

        Returns:
            Index of the frame in the frames list
        """
        key = (file, line, name)
        if key in self._frame_map:
            return self._frame_map[key]

        frame_idx = len(self._frames)
        self._frames.append({"name": name, "file": file, "line": line})
        self._frame_map[key] = frame_idx
        return frame_idx


def generate_flamegraph_data(profiler: cProfile.Profile | None) -> dict[str, Any] | None:
    """Generate flame graph data from a cProfile profiler.

    Args:
        profiler: The cProfile profiler instance, or None if profiling is disabled.

    Returns:
        Speedscope JSON format dictionary, or None if profiler is None.
    """
    if profiler is None:
        return None

    generator = FlameGraphGenerator(profiler)
    return generator.generate()


def generate_tachyon_flamegraph_data(
    stack_counter: dict[tuple[tuple[tuple[str, int, str], ...], int], int],
    request_thread_id: int | None,
    interval_sec: float,
) -> dict[str, Any] | None:
    """Generate flame graph data from Tachyon sampling profiler stacks.

    Unlike cProfile's flat frame data, Tachyon samples carry full call stacks,
    so each sample becomes a proper nested stack in the speedscope output.

    Args:
        stack_counter: Mapping of (call_tree, thread_id) to sample count, as
            produced by ``profiling.sampling.CollapsedStackCollector``.
        request_thread_id: Native thread id that served the request; samples
            from other threads (including the sampler's own thread) are dropped.
        interval_sec: Sampling interval in seconds, used to weight samples.

    Returns:
        Speedscope JSON format dictionary, or None if there is no sample data.
    """
    if not stack_counter:
        return None

    frames: list[dict[str, Any]] = []
    frame_map: dict[tuple[str, int, str], int] = {}
    samples: list[list[int]] = []
    weights: list[float] = []
    total_samples = 0

    for (call_tree, thread_id), count in stack_counter.items():
        if request_thread_id is not None and thread_id != request_thread_id:
            continue
        if not call_tree:
            continue

        stack_indices = []
        for filename, lineno, func_name in call_tree:
            key = (filename, lineno, func_name)
            frame_idx = frame_map.get(key)
            if frame_idx is None:
                frame_idx = len(frames)
                frames.append({"name": func_name, "file": filename, "line": lineno})
                frame_map[key] = frame_idx
            stack_indices.append(frame_idx)

        samples.append(stack_indices)
        weights.append(count * interval_sec)
        total_samples += count

    if not samples:
        return None

    return {
        "$schema": SPEEDSCOPE_SCHEMA_VERSION,
        "shared": {"frames": frames},
        "profiles": [
            {
                "type": "sampled",
                "name": "Request Profile (Tachyon)",
                "unit": "seconds",
                "startValue": 0,
                "endValue": total_samples * interval_sec,
                "samples": samples,
                "weights": weights,
            }
        ],
        "exporter": "async-python-debug-toolbar",
        "activeProfileIndex": 0,
    }
