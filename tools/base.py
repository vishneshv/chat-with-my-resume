"""Base tool protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Tool protocol."""

    name: str

    def run(self, input_str: str) -> str:
        """Execute tool."""
        ...
