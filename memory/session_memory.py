"""Session context: profile + rolling summary + recent turns for the LLM."""

from __future__ import annotations

from typing import Any

from agents.llm import get_llm
from config.settings import get_settings
from langchain_core.messages import HumanMessage, SystemMessage
from memory.resume_profile import load_resume_profile
from utils.logging import get_logger

logger = get_logger(__name__)


def format_memory_block(
    *,
    conversation_history: list[dict[str, Any]],
    session_summary: str,
) -> str:
    s = get_settings()
    profile = load_resume_profile()
    skills = profile.get("skills") or []
    skill_txt = ", ".join(skills[:25]) if skills else "(see RAG)"
    projects = profile.get("projects") or []
    proj_preview = "; ".join(projects[:8]) if projects else ""

    recent = conversation_history[-(s.memory_max_turns * 2) :]
    conv_lines = []
    for m in recent:
        role = m.get("role", "?")
        content = (m.get("content") or "")[:1200]
        conv_lines.append(f"{role}: {content}")

    summary = session_summary.strip() or "(none yet — long summary builds after longer chats)"

    parts = [
        "=== Candidate profile (structured) ===",
        f"Name: {profile.get('name', 'Vishnesh')}",
        f"Experience: {profile.get('experience', '')}",
        f"Education: {profile.get('education', '')}",
        f"Skills: {skill_txt}",
        f"Project titles: {proj_preview}",
        "=== Conversation summary ===",
        summary,
        "=== Recent dialogue ===",
        "\n".join(conv_lines) if conv_lines else "(first turn)",
    ]
    return "\n".join(parts)


def maybe_refresh_summary(
    user_id: str,
    messages: list[dict[str, Any]],
    current_summary: str,
) -> str:
    """Periodic LLM compression of older context (cheap guard on size)."""
    s = get_settings()
    n = len(messages)
    if n < s.summary_refresh_messages:
        return current_summary

    # Only refresh every time we cross a multiple of summary_refresh_messages
    if n % s.summary_refresh_messages != 0:
        return current_summary

    try:
        llm = get_llm()
        transcript = "\n".join(
            f"{m.get('role')}: {(m.get('content') or '')[:800]}" for m in messages[-40:]
        )
        prompt = f"""Summarize this interview-practice chat in 3 short bullet lines for future context.
Focus on topics discussed and facts the user asked about.

{transcript}

Summary (3 bullets):"""
        out = llm.invoke(
            [
                SystemMessage(content="You compress chat logs for an AI assistant."),
                HumanMessage(content=prompt),
            ]
        )
        text = (out.content or "").strip()
        logger.info("Refreshed session summary for user_id=%s...", user_id[:8])
        return text[:2000]
    except Exception as e:
        logger.warning("summary refresh failed: %s", e)
        return current_summary
