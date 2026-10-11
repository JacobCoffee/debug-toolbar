"""Profiling panel for performance analysis using cProfile, pyinstrument, or Tachyon."""

from __future__ import annotations

import contextlib
import cProfile
import io
import logging
import pstats
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from debug_toolbar.core.panel import Panel

logger = logging.getLogger(__name__)

STDLIB_PATTERNS = frozenset(
    {
        "threading.py",
        "_weakrefset.py",
        "abc.py",
        "functools.py",
        "contextlib.py",
        "typing.py",
        "weakref.py",
        "collections",
        "importlib",
        "asyncio",
        "concurrent",
        "queue.py",
        "selectors.py",
        "socket.py",
        "ssl.py",
        "urllib",
        "http",
        "json",
        "logging",
        "re.py",
        "sre_",
        "codecs.py",
        "posixpath.py",
        "genericpath.py",
        "pathlib.py",
        "_bootstrap",
        "frozen ",
        "<frozen",
    }
)

if TYPE_CHECKING:
    try:
        from pyinstrument import Profiler as PyinstrumentProfiler  # type: ignore[import-untyped]
    except ImportError:
        PyinstrumentProfiler = None

    try:
        from profiling.sampling import CollapsedStackCollector  # type: ignore[import-not-found]
    except ImportError:
        CollapsedStackCollector = None

    from debug_toolbar.core.context import RequestContext
    from debug_toolbar.core.toolbar import DebugToolbar

MAX_RECURSION_DEPTH = 100
CPROFILE_FUNC_TUPLE_LENGTH = 3
ENABLE_FLAMEGRAPH_DEFAULT = True
TACHYON_MIN_PYTHON_VERSION = (3, 15)
TACHYON_SAMPLE_INTERVAL_USEC_DEFAULT = 1000
TACHYON_JOIN_TIMEOUT_SEC = 2.0


class _TachyonPrintPatchState:
    """Tracks the refcounted patch of ``profiling.sampling.sample.print``."""

    __slots__ = ("lock", "original_print", "patch_count")

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.patch_count = 0
        self.original_print: object = None


_tachyon_print_state = _TachyonPrintPatchState()


def _no_op_print(*_args: object, **_kwargs: object) -> None:
    """Replace ``sample.py``'s summary print while Tachyon sampling is silenced."""


@contextlib.contextmanager
def _silence_tachyon_output() -> Any:
    """Silence the stdout summary that ``SampleProfiler.sample`` prints when it finishes.

    Patches ``print`` on the ``profiling.sampling.sample`` module only, instead of
    redirecting process-wide stdout, so other threads are unaffected. Uses a
    reference count so concurrent requests can share the patch safely.
    """
    import profiling.sampling.sample as sample_module  # type: ignore[import-not-found]

    state = _tachyon_print_state
    with state.lock:
        if state.patch_count == 0:
            state.original_print = sample_module.__dict__.get("print")
            sample_module.print = _no_op_print
        state.patch_count += 1
    try:
        yield
    finally:
        with state.lock:
            state.patch_count -= 1
            if state.patch_count == 0:
                if state.original_print is None:
                    del sample_module.print
                else:
                    sample_module.print = state.original_print


def _is_stdlib_or_internal(filename: str) -> bool:
    """Check if a filename belongs to Python stdlib or internal modules."""
    if not filename:
        return True

    for pattern in STDLIB_PATTERNS:
        if pattern in filename:
            return True

    stdlib_prefixes = (sys.prefix, sys.base_prefix)
    for prefix in stdlib_prefixes:
        if prefix and filename.startswith(prefix):
            lib_path = str(Path(prefix) / "lib")
            if filename.startswith(lib_path) and "site-packages" not in filename:
                return True

    return False


def _is_user_code(filename: str) -> bool:
    """Check if a filename is user/application code (not in site-packages)."""
    if not filename or _is_stdlib_or_internal(filename):
        return False
    return "site-packages" not in filename and "dist-packages" not in filename


class ProfilingPanel(Panel):
    """Panel for profiling request performance.

    Supports three profiling backends:
    - cProfile: Standard library profiler (default)
    - pyinstrument: Optional third-party profiler (more readable output)
    - tachyon: Standard library statistical sampling profiler (Python 3.15+ only,
      via PEP 799's `profiling.sampling`). Low overhead, good for profiling
      requests without the deterministic-tracing cost of cProfile.

    The profiler tracks function calls, execution time, and generates
    detailed statistics about performance hotspots.

    Configure via toolbar config:
        profiler_backend: "cprofile" | "pyinstrument" | "tachyon" (default: "cprofile")
        profiler_top_functions: int (default: 50)
        profiler_sort_by: str (default: "cumulative")
        profiler_tachyon_interval_usec: int (default: 1000)
        enable_flamegraph: bool (default: True)
    """

    panel_id: ClassVar[str] = "ProfilingPanel"
    title: ClassVar[str] = "Profiling"
    template: ClassVar[str] = "panels/profiling.html"
    has_content: ClassVar[bool] = True
    nav_title: ClassVar[str] = "Profile"

    __slots__ = (
        "_backend",
        "_enable_flamegraph",
        "_profiler",
        "_profiling_overhead",
        "_sort_by",
        "_tachyon_request_native_id",
        "_tachyon_thread",
        "_top_functions",
    )

    def __init__(self, toolbar: DebugToolbar) -> None:
        super().__init__(toolbar)
        self._profiler: cProfile.Profile | PyinstrumentProfiler | CollapsedStackCollector | None = None
        self._backend = self._get_backend()
        self._top_functions = self._get_config("profiler_top_functions", 50)
        self._sort_by = self._get_config("profiler_sort_by", "cumulative")
        self._enable_flamegraph = self._get_config("enable_flamegraph", ENABLE_FLAMEGRAPH_DEFAULT)
        self._profiling_overhead: float = 0.0
        self._tachyon_thread: threading.Thread | None = None
        self._tachyon_request_native_id: int | None = None

    def _get_backend(self) -> str:
        """Determine which profiling backend to use."""
        backend = self._get_config("profiler_backend", "cprofile")
        if backend == "pyinstrument":
            try:
                import pyinstrument  # noqa: F401  # type: ignore[import-untyped]

                return "pyinstrument"
            except ImportError:
                return "cprofile"
        if backend == "tachyon":
            if sys.version_info < TACHYON_MIN_PYTHON_VERSION:
                logger.debug("Tachyon profiler requires Python 3.15+, falling back to cProfile")
                return "cprofile"
            try:
                from profiling.sampling.sample import SampleProfiler  # noqa: F401  # type: ignore[import-not-found]
            except ImportError:
                logger.debug("Tachyon profiler (profiling.sampling) is unavailable, falling back to cProfile")
                return "cprofile"
            return "tachyon"
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
        elif self._backend == "tachyon":
            try:
                self._start_tachyon()
            except (ImportError, OSError, RuntimeError, SystemExit):
                logger.debug("Failed to start Tachyon profiler, falling back to cProfile", exc_info=True)
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

    def _start_tachyon(self) -> None:
        """Start a Tachyon sampling profiler thread for the current request."""
        import os

        from profiling.sampling import CollapsedStackCollector  # type: ignore[import-not-found]
        from profiling.sampling.sample import SampleProfiler  # type: ignore[import-not-found]

        interval_usec = self._get_config("profiler_tachyon_interval_usec", TACHYON_SAMPLE_INTERVAL_USEC_DEFAULT)
        collector = CollapsedStackCollector(interval_usec)
        collector.running = True
        sampler = SampleProfiler(os.getpid(), interval_usec, all_threads=True)

        def run() -> None:
            with _silence_tachyon_output():
                sampler.sample(collector, duration_sec=None, async_aware=None)

        thread = threading.Thread(target=run, name="tachyon-profiler-sample", daemon=True)
        self._tachyon_request_native_id = threading.get_native_id()
        thread.start()
        self._tachyon_thread = thread
        self._profiler = collector

    def _stop_tachyon(self) -> float:
        """Signal the sampler thread to stop and join it.

        The toolbar calls ``generate_stats`` before ``process_response`` (see
        ``DebugToolbar.process_response``), so stopping must happen the first time
        either one runs; calling this more than once for the same request is a no-op.

        Returns:
            Elapsed time spent stopping and joining the sampler thread.
        """
        import time

        start = time.perf_counter()
        if self._profiler is not None:
            self._profiler.running = False  # type: ignore[union-attr]
        if self._tachyon_thread is not None:
            self._tachyon_thread.join(timeout=TACHYON_JOIN_TIMEOUT_SEC)
            self._tachyon_thread = None
        return time.perf_counter() - start

    async def process_response(self, context: RequestContext) -> None:
        """Stop profiling at response completion."""
        import time

        if self._profiler is None:
            return

        start = time.perf_counter()

        if self._backend == "pyinstrument" and hasattr(self._profiler, "stop"):
            self._profiler.stop()  # type: ignore[attr-defined]
        elif self._backend == "tachyon":
            self._stop_tachyon()
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
        if self._backend == "tachyon":
            return self._generate_tachyon_stats()
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

        user_funcs: list[dict[str, Any]] = []
        lib_funcs: list[dict[str, Any]] = []

        for func, (cc, nc, tt, ct, _) in stats.stats.items():  # type: ignore[attr-defined]
            if isinstance(func, tuple) and len(func) == CPROFILE_FUNC_TUPLE_LENGTH:
                filename, lineno, func_name = func
            else:
                filename = str(func)
                lineno = 0
                func_name = "unknown"

            if _is_stdlib_or_internal(filename):
                continue

            per_call = ct / nc if nc > 0 else 0.0

            func_data = {
                "function": func_name,
                "filename": filename,
                "lineno": lineno,
                "calls": nc,
                "primitive_calls": cc,
                "total_time": tt,
                "cumulative_time": ct,
                "per_call": per_call,
            }

            if _is_user_code(filename):
                user_funcs.append(func_data)
            else:
                lib_funcs.append(func_data)

        user_funcs.sort(key=lambda x: x["cumulative_time"], reverse=True)
        lib_funcs.sort(key=lambda x: x["cumulative_time"], reverse=True)

        top_functions = user_funcs[: self._top_functions]
        remaining = self._top_functions - len(top_functions)
        if remaining > 0:
            top_functions.extend(lib_funcs[:remaining])

        call_tree = self._generate_cprofile_tree(stats)

        result = {
            "backend": "cprofile",
            "total_time": total_time,
            "function_calls": total_calls,
            "primitive_calls": prim_calls,
            "top_functions": top_functions,
            "call_tree": call_tree,
            "profiling_overhead": self._profiling_overhead,
            "user_function_count": len(user_funcs),
            "library_function_count": len(lib_funcs),
        }

        if self._enable_flamegraph:
            from debug_toolbar.core.panels.flamegraph import generate_flamegraph_data

            flamegraph_data = generate_flamegraph_data(self._profiler)
            result["flamegraph_available"] = flamegraph_data is not None
            if flamegraph_data:
                result["flamegraph_data"] = flamegraph_data

        return result

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

    def _generate_tachyon_stats(self) -> dict[str, Any]:
        """Extract statistics from the Tachyon sampling profiler."""
        if self._profiler is None:
            return self._empty_stats()

        self._profiling_overhead += self._stop_tachyon()

        stack_counter = getattr(self._profiler, "stack_counter", None)
        if not stack_counter:
            return self._empty_stats()

        interval_usec = self._get_config("profiler_tachyon_interval_usec", TACHYON_SAMPLE_INTERVAL_USEC_DEFAULT)
        interval_sec = interval_usec / 1_000_000
        request_tid = self._tachyon_request_native_id

        function_samples, total_samples = self._aggregate_tachyon_samples(stack_counter, request_tid)
        user_funcs, lib_funcs = self._tachyon_function_lists(function_samples, interval_sec)

        top_functions = user_funcs[: self._top_functions]
        remaining = self._top_functions - len(top_functions)
        if remaining > 0:
            top_functions.extend(lib_funcs[:remaining])

        result = {
            "backend": "tachyon",
            "total_time": total_samples * interval_sec,
            "function_calls": total_samples,
            "primitive_calls": total_samples,
            "top_functions": top_functions,
            "call_tree": self._generate_tachyon_tree(stack_counter, request_tid),
            "profiling_overhead": self._profiling_overhead,
            "user_function_count": len(user_funcs),
            "library_function_count": len(lib_funcs),
            "sample_count": total_samples,
            "sample_interval_usec": interval_usec,
        }

        if self._enable_flamegraph:
            from debug_toolbar.core.panels.flamegraph import generate_tachyon_flamegraph_data

            flamegraph_data = generate_tachyon_flamegraph_data(stack_counter, request_tid, interval_sec)
            result["flamegraph_available"] = flamegraph_data is not None
            if flamegraph_data:
                result["flamegraph_data"] = flamegraph_data

        return result

    @staticmethod
    def _aggregate_tachyon_samples(
        stack_counter: Any, request_tid: int | None
    ) -> tuple[dict[tuple[str, int, str], dict[str, int]], int]:
        """Aggregate per-function cumulative and self sample counts for the request thread."""
        function_samples: dict[tuple[str, int, str], dict[str, int]] = {}
        total_samples = 0

        for (call_tree, thread_id), count in stack_counter.items():
            if request_tid is not None and thread_id != request_tid:
                continue
            if not call_tree:
                continue

            total_samples += count

            seen_in_stack: set[tuple[str, int, str]] = set()
            for filename, lineno, func_name in call_tree:
                if _is_stdlib_or_internal(filename):
                    continue
                key = (filename, lineno, func_name)
                if key in seen_in_stack:
                    continue
                seen_in_stack.add(key)
                function_samples.setdefault(key, {"cumulative": 0, "self": 0})["cumulative"] += count

            leaf_filename, leaf_lineno, leaf_func = call_tree[-1]
            if not _is_stdlib_or_internal(leaf_filename):
                leaf_key = (leaf_filename, leaf_lineno, leaf_func)
                function_samples.setdefault(leaf_key, {"cumulative": 0, "self": 0})["self"] += count

        return function_samples, total_samples

    @staticmethod
    def _tachyon_function_lists(
        function_samples: dict[tuple[str, int, str], dict[str, int]], interval_sec: float
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Build sorted user/library function stat lists from aggregated sample counts."""
        user_funcs: list[dict[str, Any]] = []
        lib_funcs: list[dict[str, Any]] = []

        for (filename, lineno, func_name), counts in function_samples.items():
            cumulative_samples = counts["cumulative"]
            self_samples = counts["self"]
            cumulative_time = cumulative_samples * interval_sec
            func_data = {
                "function": func_name,
                "filename": filename,
                "lineno": lineno,
                "calls": cumulative_samples,
                "primitive_calls": self_samples,
                "total_time": self_samples * interval_sec,
                "cumulative_time": cumulative_time,
                "per_call": cumulative_time / cumulative_samples if cumulative_samples else 0.0,
            }

            if _is_user_code(filename):
                user_funcs.append(func_data)
            else:
                lib_funcs.append(func_data)

        user_funcs.sort(key=lambda x: x["cumulative_time"], reverse=True)
        lib_funcs.sort(key=lambda x: x["cumulative_time"], reverse=True)
        return user_funcs, lib_funcs

    def _generate_tachyon_tree(self, stack_counter: Any, request_tid: int | None) -> str:
        """Generate a folded-stack call tree from Tachyon sample data."""
        lines: list[tuple[str, int]] = []
        for (call_tree, thread_id), count in stack_counter.items():
            if request_tid is not None and thread_id != request_tid:
                continue
            if not call_tree:
                continue
            parts = []
            for filename, lineno, func_name in call_tree:
                if filename == "~" and lineno == 0:
                    parts.append(func_name)
                else:
                    short_file = filename.rsplit("/", 1)[-1]
                    parts.append(f"{short_file}:{func_name}:{lineno}")
            lines.append((";".join(parts), count))

        lines.sort(key=lambda item: item[1], reverse=True)
        return "\n".join(f"{stack} {count}" for stack, count in lines[: self._top_functions])

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
