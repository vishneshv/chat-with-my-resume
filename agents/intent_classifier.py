"""
Fast intent classification (no LLM) for routing hints.

Intents drive critic strictness and optional routing hints to the supervisor.
"""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal["casual", "resume", "github", "web", "mixed"]

_GREETINGS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hii",
        "helo",
        "yo",
        "sup",
        "howdy",
        "hai",
        "good morning",
        "good afternoon",
        "good evening",
    }
)

_GITHUB_PATTERNS = re.compile(
    r"\b(github|repo|repository|repositories|commit|pull request|gist)\b", re.I
)
_RESUME_PATTERNS = re.compile(
    r"\b(resume|cv|project|projects|skill|skills|experience|worked|kore|zendesk|"
    r"intern|developer|background|achievement|technologies|stack)\b",
    re.I,
)
_WEB_PATTERNS = re.compile(
    r"\b(latest|news|today|current|breaking|who won|stock price|weather|"
    r"2025|2026|president|election|market|headlines|what happened)\b",
    re.I,
)


_USER_SELF_PATTERNS = re.compile(
    r"\b(what'?s my name|whats my name|who am i|my name is|call me|^i am |^i'm )\b",
    re.I,
)


def classify_intent(query: str) -> tuple[Intent, str]:
    """
    Returns (intent, short_reason_for_thoughts_log).
    """
    q = query.strip()
    low = q.lower().rstrip("!?. ")

    if len(low) <= 2:
        return "casual", "empty_or_tiny"

    # User asking about themselves, not Vishnesh — short-circuit to casual / direct answer
    if _USER_SELF_PATTERNS.search(q):
        return "casual", "user_self_question"

    if low in _GREETINGS:
        return "casual", "greeting"

    if _GITHUB_PATTERNS.search(q):
        return "github", "github_keywords"

    if _WEB_PATTERNS.search(q):
        return "web", "fresh_or_external_info"

    if _RESUME_PATTERNS.search(q):
        return "resume", "resume_or_projects_keywords"

    return "mixed", "no_strong_signal"
