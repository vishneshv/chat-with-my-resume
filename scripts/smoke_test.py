#!/usr/bin/env python3
"""Run from repo root: python scripts/smoke_test.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.build import run_agent


def main() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("Set GROQ_API_KEY for live test.")
        sys.exit(1)

    for q in [
        "Hello",
        "What projects has Vishnesh built?",
        "List my GitHub repos",
    ]:
        print("\n=== Query:", q, "===")
        out = run_agent(q, user_id="smoke-user", conversation_history=[], session_summary="")
        print(out)


if __name__ == "__main__":
    main()
