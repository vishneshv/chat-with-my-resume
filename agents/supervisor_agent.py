"""
Backward-compatible entry points.

The graph lives in `graph/` — import `build_graph` / `run_agent` from there or use this module.
"""

from graph.build import build_graph, run_agent
from graph.state import HireGraphState

# Alias used by older imports (e.g. main.py migration)
AgentState = HireGraphState

__all__ = ["build_graph", "run_agent", "AgentState", "HireGraphState"]
