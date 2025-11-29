"""Example demonstrating Flame Graph generation with cProfile.

This example shows how to use the FlameGraphGenerator to create
interactive flame graph visualizations from cProfile statistics.

The generated speedscope JSON can be visualized at https://www.speedscope.app/
"""

# ruff: noqa: T201, INP001

from __future__ import annotations

import cProfile
import json
from pathlib import Path


def fibonacci(n: int) -> int:
    """Calculate fibonacci number recursively (slow for demonstration)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def compute_intensive_task() -> dict[str, int]:
    """Simulate a compute-intensive task."""
    results = {}
    for i in range(10):
        results[f"fib_{i}"] = fibonacci(i + 15)
    return results


def data_processing() -> int:
    """Simulate data processing operations."""
    data = [i**2 for i in range(10000)]
    total = sum(data)
    filtered = [x for x in data if x % 2 == 0]
    return sum(filtered) + total


def main() -> None:
    """Demonstrate Flame Graph generation."""
    print("=" * 70)
    print("Flame Graph Generation Example")
    print("=" * 70)
    print()

    print("Step 1: Profile code with cProfile")
    print("-" * 70)
    profiler = cProfile.Profile()
    profiler.enable()

    result1 = compute_intensive_task()
    result2 = data_processing()
    result3 = sum(i**3 for i in range(1000))

    profiler.disable()
    print(f"Profiled {len(result1)} fibonacci calculations")
    print(f"Processed {result2:,} data points")
    print(f"Computed sum: {result3:,}")
    print()

    print("Step 2: Generate flame graph data")
    print("-" * 70)
    from debug_toolbar.core.panels.flamegraph import FlameGraphGenerator

    generator = FlameGraphGenerator(profiler)
    speedscope_json = generator.generate()

    print("Speedscope JSON generated successfully!")
    print(f"  Schema: {speedscope_json['$schema']}")
    print(f"  Frames: {len(speedscope_json['shared']['frames'])}")
    print(f"  Profiles: {len(speedscope_json['profiles'])}")
    print(f"  Exporter: {speedscope_json['exporter']}")
    print()

    profile = speedscope_json["profiles"][0]
    print("Profile details:")
    print(f"  Type: {profile['type']}")
    print(f"  Name: {profile['name']}")
    print(f"  Unit: {profile['unit']}")
    print(f"  Duration: {profile['endValue']:.6f}s")
    print(f"  Samples: {len(profile['samples'])}")
    print()

    print("Step 3: Inspect top frames")
    print("-" * 70)
    frames_with_weights = list(zip(profile["samples"], profile["weights"], strict=False))
    frames_with_weights.sort(key=lambda x: x[1], reverse=True)

    print("Top 10 functions by cumulative time:")
    for i, (sample, weight) in enumerate(frames_with_weights[:10], 1):
        frame_idx = sample[0]
        frame = speedscope_json["shared"]["frames"][frame_idx]
        print(f"  {i}. {frame['name']}")
        print(f"     File: {frame['file']}:{frame['line']}")
        print(f"     Time: {weight:.6f}s")
        print()

    print("Step 4: Save to file")
    print("-" * 70)
    output_path = Path("profile.speedscope.json")
    with output_path.open("w") as f:
        json.dump(speedscope_json, f, indent=2)

    print(f"Saved to: {output_path.absolute()}")
    print()
    print("Step 5: Visualize the flame graph")
    print("-" * 70)
    print("To view the flame graph:")
    print("1. Open https://www.speedscope.app/ in your browser")
    print("2. Drag and drop 'profile.speedscope.json' onto the page")
    print("3. Explore the interactive flame graph visualization")
    print()
    print("Flame graph features:")
    print("  - Time-ordered: Shows execution timeline")
    print("  - Left-heavy: Shows call tree ordered by self-time")
    print("  - Sandwich: Shows callers and callees of selected frame")
    print()

    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
