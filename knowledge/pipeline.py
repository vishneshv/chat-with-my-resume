"""Single entry point: profile JSON + FAISS + knowledge_meta.json."""

from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

from config.settings import get_settings
from memory.resume_profile import build_resume_profile_file
from utils.logging import get_logger

logger = get_logger(__name__)

_build_lock = threading.Lock()
META_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_meta.json"


def read_knowledge_meta() -> dict:
    if not META_PATH.exists():
        return {}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_knowledge_meta() -> dict:
    meta = read_knowledge_meta()
    return {
        "last_built_at": meta.get("last_built_at"),
        "status": meta.get("status", "unknown"),
        "error": meta.get("error"),
    }


def _write_meta(ok: bool, error: str | None = None) -> None:
    payload = {
        "last_built_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if ok else "error",
        "error": error,
    }
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_knowledge_base() -> dict:
    """
    Build resume_profile.json, FAISS index, and update knowledge_meta.json.
    Thread-safe; reload vector store in-process after success.
    """
    with _build_lock:
        try:
            settings = get_settings()
            if settings.crawl_site_on_build:
                from memory.crawl_site import run_crawl_and_write

                logger.info("Crawling personal site (Playwright)...")
                crawl_result = run_crawl_and_write()
                if crawl_result["success"]:
                    logger.info(
                        "Site crawl OK (%s page(s)); data/crawled_site.md updated.",
                        crawl_result["pages"],
                    )
                else:
                    logger.warning(
                        "Site crawl skipped or failed (continuing with existing data): %s",
                        crawl_result.get("error"),
                    )
            logger.info("Building resume profile JSON...")
            profile = build_resume_profile_file()
            logger.info("Building vector store...")
            from rag.vector_store import build_vector_store, reload_vector_store

            build_vector_store()
            reload_vector_store()
            _write_meta(True, None)
            return {"success": True, "profile_keys": list(profile.keys())}
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}"
            logger.error("build_knowledge_base failed: %s", err)
            _write_meta(False, str(e))
            return {"success": False, "error": str(e)}
