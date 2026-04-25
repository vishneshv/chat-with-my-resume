"""Central settings (env-driven)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """HireGraph runtime configuration."""

    groq_api_key: Optional[str]
    groq_model: str
    github_token: Optional[str]
    github_username: str
    rag_namespace: str
    max_supervisor_iterations: int
    log_level: str
    # RAG
    rag_top_k: int
    rag_max_l2_distance: float  # FAISS L2; higher = looser (keep chunks with distance <= this)
    # Sessions
    session_db_path: str
    memory_max_turns: int  # recent messages injected into prompt
    summary_refresh_messages: int  # summarize thread when message count reaches this
    # Admin
    rebuild_secret: Optional[str]
    # Knowledge: optional Playwright crawl of personal site before FAISS build
    crawl_site_on_build: bool

    def __init__(self) -> None: 
        root = Path(__file__).resolve().parent.parent
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_username = os.getenv("GITHUB_USERNAME", "vishneshv")
        self.rag_namespace = os.getenv("RAG_NAMESPACE", "hiregraph_kb")
        self.max_supervisor_iterations = int(os.getenv("MAX_SUPERVISOR_ITERATIONS", "5"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.rag_top_k = int(os.getenv("RAG_TOP_K", "6"))
        self.rag_max_l2_distance = float(os.getenv("RAG_MAX_L2_DISTANCE", "2.2"))
        default_db = root / "data" / "sessions.sqlite3"
        self.session_db_path = os.getenv("SESSION_DB_PATH", str(default_db))
        self.memory_max_turns = int(os.getenv("MEMORY_MAX_TURNS", "8"))
        self.summary_refresh_messages = int(os.getenv("SUMMARY_REFRESH_MESSAGES", "24"))
        self.rebuild_secret = os.getenv("REBUILD_SECRET") or None
        self.crawl_site_on_build = os.getenv("CRAWL_SITE_ON_BUILD", "true").lower() in (
            "1",
            "true",
            "yes",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
