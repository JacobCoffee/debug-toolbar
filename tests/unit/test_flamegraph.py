"""Tests for flame graph generation."""

from __future__ import annotations

import cProfile

from debug_toolbar.core.panels.flamegraph import FlameGraphGenerator, generate_flamegraph_data


def create_sample_profile() -> cProfile.Profile:
    """Create a sample cProfile profiler with some data."""
    profiler = cProfile.Profile()
    profiler.enable()

    def sample_function_a() -> int:
        total = 0
        for i in range(1000):
            total += i
        return total

    def sample_function_b() -> int:
        total = 0
        for i in range(500):
            total += i * 2
        return total

    def sample_function_c() -> None:
        sample_function_a()
        sample_function_b()

    sample_function_c()
    profiler.disable()
    return profiler


class TestFlameGraphGenerator:
    """Tests for FlameGraphGenerator class."""

    def test_initialization(self) -> None:
        """Test FlameGraphGenerator initialization."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        assert generator._stats is not None
        assert generator._frames == []
        assert generator._frame_map == {}

    def test_generate_returns_speedscope_format(self) -> None:
        """Test generate returns speedscope-compatible format."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        assert "$schema" in result
        assert result["$schema"] == "https://www.speedscope.app/file-format-schema.json"
        assert "shared" in result
        assert "frames" in result["shared"]
        assert "profiles" in result
        assert "exporter" in result
        assert result["exporter"] == "async-python-debug-toolbar"

    def test_generate_creates_frames(self) -> None:
        """Test generate creates frame definitions."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        frames = result["shared"]["frames"]
        assert isinstance(frames, list)
        assert len(frames) > 0

        for frame in frames:
            assert "name" in frame
            assert "file" in frame
            assert "line" in frame
            assert isinstance(frame["name"], str)
            assert isinstance(frame["file"], str)
            assert isinstance(frame["line"], int)

    def test_generate_creates_profile(self) -> None:
        """Test generate creates profile data."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        profiles = result["profiles"]
        assert isinstance(profiles, list)
        assert len(profiles) == 1

        profile = profiles[0]
        assert profile["type"] == "sampled"
        assert profile["name"] == "Request Profile"
        assert profile["unit"] == "seconds"
        assert "startValue" in profile
        assert "endValue" in profile
        assert "samples" in profile
        assert "weights" in profile
        assert isinstance(profile["samples"], list)
        assert isinstance(profile["weights"], list)
        assert len(profile["samples"]) == len(profile["weights"])

    def test_generate_has_active_profile_index(self) -> None:
        """Test generate includes activeProfileIndex."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        assert "activeProfileIndex" in result
        assert result["activeProfileIndex"] == 0

    def test_frame_deduplication(self) -> None:
        """Test that frames are deduplicated correctly."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        frames = result["shared"]["frames"]
        frame_keys = [(f["file"], f["line"], f["name"]) for f in frames]

        assert len(frame_keys) == len(set(frame_keys))

    def test_samples_reference_valid_frames(self) -> None:
        """Test that sample frame indices reference valid frames."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        frames = result["shared"]["frames"]
        samples = result["profiles"][0]["samples"]

        for sample in samples:
            assert isinstance(sample, list)
            for frame_idx in sample:
                assert isinstance(frame_idx, int)
                assert 0 <= frame_idx < len(frames)

    def test_weights_are_positive(self) -> None:
        """Test that all weights are positive numbers."""
        profiler = create_sample_profile()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        weights = result["profiles"][0]["weights"]
        for weight in weights:
            assert isinstance(weight, (int, float))
            assert weight >= 0


class TestGenerateFlamegraphData:
    """Tests for generate_flamegraph_data helper function."""

    def test_returns_none_for_none_profiler(self) -> None:
        """Test returns None when profiler is None."""
        result = generate_flamegraph_data(None)
        assert result is None

    def test_returns_speedscope_format(self) -> None:
        """Test returns valid speedscope format for valid profiler."""
        profiler = create_sample_profile()
        result = generate_flamegraph_data(profiler)

        assert result is not None
        assert isinstance(result, dict)
        assert "$schema" in result
        assert "shared" in result
        assert "profiles" in result

    def test_generates_consistent_data(self) -> None:
        """Test that multiple calls generate consistent structure."""
        profiler = create_sample_profile()

        result1 = generate_flamegraph_data(profiler)
        result2 = generate_flamegraph_data(profiler)

        assert result1 is not None
        assert result2 is not None
        assert len(result1["shared"]["frames"]) == len(result2["shared"]["frames"])
        assert len(result1["profiles"]) == len(result2["profiles"])


class TestFlameGraphIntegration:
    """Integration tests for flame graph generation."""

    def test_minimal_profile(self) -> None:
        """Test handling of minimal profile with no user code."""
        profiler = cProfile.Profile()
        profiler.enable()
        profiler.disable()
        generator = FlameGraphGenerator(profiler)
        result = generator.generate()

        assert isinstance(result["shared"]["frames"], list)
        assert isinstance(result["profiles"][0]["samples"], list)
        assert isinstance(result["profiles"][0]["weights"], list)
        assert len(result["profiles"][0]["samples"]) == len(result["profiles"][0]["weights"])

    def test_realistic_profile_structure(self) -> None:
        """Test with a more realistic profile."""
        profiler = cProfile.Profile()
        profiler.enable()

        def inner_function() -> int:
            return sum(range(100))

        def middle_function() -> int:
            result = 0
            for _ in range(10):
                result += inner_function()
            return result

        def outer_function() -> int:
            result = 0
            for _ in range(5):
                result += middle_function()
            return result

        outer_function()
        profiler.disable()

        result = generate_flamegraph_data(profiler)
        assert result is not None

        frames = result["shared"]["frames"]
        assert len(frames) > 0

        frame_names = [f["name"] for f in frames]
        expected_names = ("inner_function", "middle_function", "outer_function")
        assert any(expected in name for expected in expected_names for name in frame_names)

        profile = result["profiles"][0]
        assert profile["endValue"] > 0
        assert len(profile["samples"]) > 0
        assert len(profile["weights"]) > 0
