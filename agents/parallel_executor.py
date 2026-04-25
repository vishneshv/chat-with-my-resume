"""Parallel execution stub."""

from __future__ import annotations


def run_parallel(tasks: list) -> list:
    """Execute tasks sequentially (placeholder)."""
    results = []
    for task in tasks:
        results.append(task())
    return results
