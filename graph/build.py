"""Compile the HireGraph LangGraph pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from graph.nodes import (
    answer_node,
    classify_intent_node,
    critic_node,
    input_guard_node,
    memory_inject_node,
    supervisor_node,
    tool_executor_node,
)
from graph.routing import after_input_guard, after_intent, should_continue, should_retry
from graph.state import HireGraphState


def build_graph():
    graph = StateGraph(HireGraphState)

    graph.add_node("input_guard", input_guard_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("memory_inject", memory_inject_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tools", tool_executor_node)
    graph.add_node("answer_gen", answer_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("input_guard")

    graph.add_conditional_edges(
        "input_guard",
        after_input_guard,
        {"blocked": END, "continue": "classify_intent"},
    )

    graph.add_edge("classify_intent", "memory_inject")

    graph.add_conditional_edges(
        "memory_inject",
        after_intent,
        {"answer_gen": "answer_gen", "supervisor": "supervisor"},
    )

    graph.add_conditional_edges(
        "supervisor",
        should_continue,
        {"tools": "tools", "answer_gen": "answer_gen"},
    )

    graph.add_edge("tools", "supervisor")

    graph.add_edge("answer_gen", "critic")

    graph.add_conditional_edges(
        "critic",
        should_retry,
        {"retry": "supervisor", "end": END},
    )

    return graph.compile()


def run_agent(
    query: str,
    user_id: str = "default",
    conversation_history: list | None = None,
    session_summary: str = "",
) -> dict:
    graph = build_graph()
    history = conversation_history or []
    initial: HireGraphState = {
        "query": query,
        "user_id": user_id,
        "conversation_history": history,
        "thoughts": [],
        "tool_observations": [],
        "iteration_count": 0,
        "answer": "",
        "confidence": 0.0,
        "sources": [],
        "critic_passed": False,
        "needs_retry": False,
        "final_response": {},
        "guardrail_blocked": False,
        "retrieved_chunks": [],
        "_next_action": "",
        "_action_input": "none",
        "intent": "",
        "intent_reason": "",
        "relaxed_critic": False,
        "memory_context": "",
        "session_summary": session_summary,
        "web_sources": [],
        "rag_call_count": 0,
    }
    result = graph.invoke(initial)
    return result.get("final_response", {})
