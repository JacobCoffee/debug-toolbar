"""Profiling panel for performance analysis using cProfile or pyinstrument."""

from __future__ import annotations

import cProfile
import io
import logging
import pstats
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    try:
        from pyinstrument import Profiler as PyinstrumentProfiler  # type: ignore[import-untyped]
    except ImportError:
        PyinstrumentProfiler = None

    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

MAX_RECURSION_DEPTH = 100
CPROFILE_FUNC_TUPLE_LENGTH = 3


class ProfilingPanel(Panel):
    """Panel for profiling request performance.

    Supports two profiling backends:
    - cProfile: Standard library profiler (default)
    - pyinstrument: Optional third-party profiler (more readable output)

    The profiler tracks function calls, execution time, and generates
    detailed statistics about performance hotspots.

    Configure via toolbar config:
        profiler_backend: "cprofile" | "pyinstrument" (default: "cprofile")
        profiler_top_functions: int (default: 50)
        profiler_sort_by: str (default: "cumulative")
    """

    panel_id: ClassVar[str] = "ProfilingPanel"
    title: ClassVar[str] = "Profiling"
    template: ClassVar[str] = "panels/profiling.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Profile"

    __slots__ = ("_backend", "_profiler", "_profiling_overhead", "_sort_by", "_top_functions")

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._profiler: cProfile.Profile | PyinstrumentProfiler | None = None
        self._backend = self._get_backend()
        self._top_functions = self._get_config("profiler_top_functions", 50)
        self._sort_by = self._get_config("profiler_sort_by", "cumulative")
        self._profiling_overhead: float = 0.0

    def _get_backend(self) -> str:
        """Determine which profiling backend to use."""
        backend = self._get_config("profiler_backend", "cprofile")
        if backend == "pyinstrument":
            try:
                import pyinstrument  # noqa: F401  # type: ignore[import-untyped]

                return "pyinstrument"
            except ImportError:
                return "cprofile"
        return "cprofile"

    def _get_config(self, key: str, default: Any) -> Any:
        """Get configuration value from toolbar config."""
        config = getattr(self._toolbar, "config", None)
        if config is None:
            return default
        return getattr(config, key, default)

    async def process_request(self, context: RequestContext) -> None:
        """Start profiling at request start."""
        import time

        start = time.perf_counter()

        if self._backend == "pyinstrument":
            try:
                from pyinstrument import Profiler  # type: ignore[import-untyped]

                self._profiler = Profiler()
                self._profiler.start()  # type: ignore[attr-defined]
            except ImportError:
                self._backend = "cprofile"
                self._profiler = cProfile.Profile()
                try:
                    self._profiler.enable()
                except ValueError:
                    logger.warning("Failed to enable cProfile profiler - another profiler may be active")
                    self._profiler = None
        else:
            self._profiler = cProfile.Profile()
            try:
                self._profiler.enable()
            except ValueError:
                logger.warning("Failed to enable cProfile profiler - another profiler may be active")
                self._profiler = None

        self._profiling_overhead = time.perf_counter() - start

    async def process_response(self, context: RequestContext) -> None:
        """Stop profiling at response completion."""
        import time

        if self._profiler is None:
            return

        start = time.perf_counter()

        if self._backend == "pyinstrument" and hasattr(self._profiler, "stop"):
            self._profiler.stop()  # type: ignore[attr-defined]
        elif hasattr(self._profiler, "disable"):
            self._profiler.disable()

        self._profiling_overhead += time.perf_counter() - start

    async def generate_stats(self, context: RequestContext) -> dict[str, Any]:
        """Generate profiling statistics."""
        if self._profiler is None:
            return {
                "backend": self._backend,
                "total_time": 0.0,
                "function_calls": 0,
                "primitive_calls": 0,
                "top_functions": [],
                "call_tree": None,
                "profiling_overhead": self._profiling_overhead,
            }

        if self._backend == "pyinstrument":
            return self._generate_pyinstrument_stats()
        return self._generate_cprofile_stats()

    def _generate_cprofile_stats(self) -> dict[str, Any]:
        """Extract statistics from cProfile."""
        if self._profiler is None:
            return self._empty_stats()

        stats = pstats.Stats(self._profiler)

        total_calls = stats.total_calls  # type: ignore[attr-defined]
        prim_calls = stats.prim_calls  # type: ignore[attr-defined]
        total_time = stats.total_tt  # type: ignore[attr-defined]

        stats.sort_stats(self._sort_by)

        top_functions = []
        for func, (cc, nc, tt, ct, _) in list(stats.stats.items())[: self._top_functions]:  # type: ignore[attr-defined]
            if isinstance(func, tuple) and len(func) == CPROFILE_FUNC_TUPLE_LENGTH:
                filename, lineno, func_name = func
            else:
                filename = str(func)
                lineno = 0
                func_name = "unknown"

            per_call = ct / nc if nc > 0 else 0.0

            top_functions.append(
                {
                    "function": func_name,
                    "filename": filename,
                    "lineno": lineno,
                    "calls": nc,
                    "primitive_calls": cc,
                    "total_time": tt,
                    "cumulative_time": ct,
                    "per_call": per_call,
                }
            )

        call_tree = self._generate_cprofile_tree(stats)

        return {
            "backend": "cprofile",
            "total_time": total_time,
            "function_calls": total_calls,
            "primitive_calls": prim_calls,
            "top_functions": top_functions,
            "call_tree": call_tree,
            "profiling_overhead": self._profiling_overhead,
        }

    def _generate_cprofile_tree(self, stats: pstats.Stats) -> str:
        """Generate a formatted call tree from cProfile stats."""
        output = io.StringIO()
        stats.stream = output  # type: ignore[attr-defined]
        stats.print_stats(self._top_functions)
        return output.getvalue()

    def _generate_pyinstrument_stats(self) -> dict[str, Any]:
        """Extract statistics from pyinstrument."""
        if self._profiler is None:
            return self._empty_stats()

        try:
            session = self._profiler.last_session  # type: ignore[attr-defined]
            if session is None:
                return self._empty_stats()

            root_frame = session.root_frame()
            if root_frame is None:
                return self._empty_stats()

            total_time = root_frame.time()
            function_calls = self._count_pyinstrument_calls(root_frame)

            top_functions = self._extract_pyinstrument_functions(root_frame)

            call_tree = self._profiler.output_text(unicode=True, show_all=True)  # type: ignore[attr-defined]

            return {
                "backend": "pyinstrument",
                "total_time": total_time,
                "function_calls": function_calls,
                "primitive_calls": function_calls,
                "top_functions": top_functions,
                "call_tree": call_tree,
                "profiling_overhead": self._profiling_overhead,
            }
        except (AttributeError, ImportError):
            return self._empty_stats()

    def _count_pyinstrument_calls(self, frame: Any) -> int:
        """Recursively count function calls in pyinstrument frame tree."""
        count = 1
        for child in getattr(frame, "children", []):
            count += self._count_pyinstrument_calls(child)
        return count

    def _extract_pyinstrument_functions(self, root_frame: Any) -> list[dict[str, Any]]:
        """Extract top functions from pyinstrument frame tree."""
        functions: list[dict[str, Any]] = []

        def collect_frames(frame: Any, depth: int = 0) -> None:
            if depth > MAX_RECURSION_DEPTH:
                return

            time_val = frame.time() if hasattr(frame, "time") else 0.0
            function = getattr(frame, "function", "unknown")
            file_path = getattr(frame, "file_path_short", "unknown")
            line_no = getattr(frame, "line_no", 0)

            functions.append(
                {
                    "function": function,
                    "filename": file_path,
                    "lineno": line_no,
                    "calls": 1,
                    "primitive_calls": 1,
                    "total_time": time_val,
                    "cumulative_time": time_val,
                    "per_call": time_val,
                }
            )

            for child in getattr(frame, "children", []):
                collect_frames(child, depth + 1)

        collect_frames(root_frame)

        functions.sort(key=lambda x: x["cumulative_time"], reverse=True)
        return functions[: self._top_functions]

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure."""
        return {
            "backend": self._backend,
            "total_time": 0.0,
            "function_calls": 0,
            "primitive_calls": 0,
            "top_functions": [],
            "call_tree": None,
            "profiling_overhead": self._profiling_overhead,
        }

    def generate_server_timing(self, context: RequestContext) -> dict[str, float]:
        """Generate Server-Timing data for profiling overhead."""
        stats = self.get_stats(context)
        if not stats:
            return {}

        return {
            "profiling": stats.get("profiling_overhead", 0.0),
            "profiled_time": stats.get("total_time", 0.0),
        }

    def get_nav_subtitle(self) -> str:
        """Get the navigation subtitle showing backend."""
        return self._backend
