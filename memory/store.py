"""SQLite-backed chat persistence (survives server restarts)."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings

_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    def __init__(self, db_path: Path | None = None) -> None:
        s = get_settings()
        self._path = db_path or Path(s.session_db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    messages TEXT NOT NULL DEFAULT '[]',
                    summary TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.commit()

    def get_messages(self, user_id: str) -> list[dict[str, Any]]:
        with _lock, self._connect() as conn:
            row = conn.execute(
                "SELECT messages FROM sessions WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return []
            try:
                return json.loads(row["messages"])
            except json.JSONDecodeError:
                return []

    def get_summary(self, user_id: str) -> str:
        with _lock, self._connect() as conn:
            row = conn.execute(
                "SELECT summary FROM sessions WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return ""
            return row["summary"] or ""

    def save_session(
        self,
        user_id: str,
        messages: list[dict[str, Any]],
        summary: str | None = None,
    ) -> None:
        with _lock, self._connect() as conn:
            if summary is None:
                row = conn.execute(
                    "SELECT summary FROM sessions WHERE user_id = ?", (user_id,)
                ).fetchone()
                summary = row["summary"] if row else ""
            conn.execute(
                """
                INSERT INTO sessions (user_id, messages, summary, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    messages = excluded.messages,
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
                """,
                (user_id, json.dumps(messages), summary, _utc_now()),
            )
            conn.commit()

    def set_summary(self, user_id: str, summary: str) -> None:
        messages = self.get_messages(user_id)
        self.save_session(user_id, messages, summary=summary)


_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
