"""Graph state shared across all nodes."""

from typing import Annotated, TypedDict

import operator


class HireGraphState(TypedDict):
    query: str
    user_id: str
    conversation_history: Annotated[list, operator.add]
    thoughts: Annotated[list, operator.add]
    tool_observations: Annotated[list, operator.add]
    iteration_count: int
    answer: str
    confidence: float
    sources: list
    critic_passed: bool
    needs_retry: bool
    final_response: dict
    guardrail_blocked: bool
    retrieved_chunks: Annotated[list, operator.add]
    _next_action: str
    _action_input: str
    # Intent + critic
    intent: str
    intent_reason: str
    relaxed_critic: bool
    # Memory (injected after classify_intent)
    memory_context: str
    session_summary: str
    # Web search labels for final sources line
    web_sources: list
    # Cap repeated RAG calls per request
    rag_call_count: int
