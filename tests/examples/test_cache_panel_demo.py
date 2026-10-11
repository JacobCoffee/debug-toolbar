"""Tests for the cache panel demo script."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType


def test_demo_context_manager_tracking_reports_real_operations(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real demo should report four tracked operations with hit/miss status."""
    module = import_example("examples.cache_panel_demo")

    module.demo_context_manager_tracking()

    output = capsys.readouterr().out
    assert "Total operations tracked: 4" in output
    assert "GET" in output
    assert "HIT" in output
    assert "MISS" in output
    assert "SET" in output
    assert "memcached" in output


def test_demo_multi_key_operation_reports_real_keys(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real multi-key demo should report the tracked key list and hit status."""
    module = import_example("examples.cache_panel_demo")

    module.demo_multi_key_operation()

    output = capsys.readouterr().out
    assert "Operation: MGET" in output
    assert "Keys: ['key1', 'key2', 'key3']" in output
    assert "Hit: True" in output


def test_demo_statistics_reports_real_hit_rate(
    import_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running the real statistics demo should compute a 60% hit rate from its five operations."""
    module = import_example("examples.cache_panel_demo")

    module.demo_statistics()

    output = capsys.readouterr().out
    assert "Total operations: 5" in output
    assert "Cache hits: 3" in output
    assert "Cache misses: 1" in output
    assert "Hit rate: 75.0%" in output
