"""Conditional edge functions."""

from __future__ import annotations

from config.settings import get_settings
from graph.state import HireGraphState


def after_input_guard(state: HireGraphState) -> str:
    if state.get("guardrail_blocked"):
        return "blocked"
    return "continue"


def after_intent(state: HireGraphState) -> str:
    """Skip supervisor for casual — go straight to answer."""
    if state.get("intent") == "casual":
        return "answer_gen"
    return "supervisor"


def should_continue(state: HireGraphState) -> str:
    action = state.get("_next_action", "answer")
    iteration = state.get("iteration_count", 0)
    settings = get_settings()
    chunks = state.get("retrieved_chunks") or []
    rag_calls = int(state.get("rag_call_count") or 0)

    if iteration >= settings.max_supervisor_iterations:
        return "answer_gen"

    # Stop RAG ping-pong: after we have chunks, never search_rag again this turn
    if action == "search_rag" and len(chunks) > 0 and rag_calls >= 1:
        return "answer_gen"

    # At most two RAG attempts per request; then answer with whatever we have
    if action == "search_rag" and rag_calls >= 2:
        return "answer_gen"

    if action not in [
        "search_rag",
        "github_repos",
        "github_details",
        "github_languages",
        "web_search",
    ]:
        return "answer_gen"

    return "tools"


def should_retry(state: HireGraphState) -> str:
    settings = get_settings()
    if state.get("needs_retry") and state.get("iteration_count", 0) < settings.max_supervisor_iterations:
        return "retry"
    return "end"
