"""Shared LLM client."""

import os

from langchain_groq import ChatGroq

from config.settings import get_settings


def get_llm() -> ChatGroq:
    s = get_settings()
    return ChatGroq(
        model=s.groq_model,
        temperature=0.3,
        max_tokens=500,
        api_key=s.groq_api_key,
        timeout=30,
        max_retries=2,
    )
