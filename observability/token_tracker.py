"""Rough token / character accounting per pipeline stage (for ops visibility)."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"chars_in": 0.0, "chars_out": 0.0, "calls": 0})


def record(stage: str, chars_in: int, chars_out: int) -> None:
    with _lock:
        b = _totals[stage]
        b["chars_in"] += chars_in
        b["chars_out"] += chars_out
        b["calls"] += 1


def estimate_tokens(chars: int) -> int:
    return max(1, chars // 4)


def snapshot() -> dict[str, Any]:
    with _lock:
        return {k: dict(v) for k, v in _totals.items()}


def reset() -> None:
    with _lock:
        _totals.clear()
