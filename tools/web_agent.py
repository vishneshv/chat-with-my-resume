"""Lightweight web search (DuckDuckGo) — optional package: duckduckgo-search."""

from __future__ import annotations

from utils.logging import get_logger

logger = get_logger(__name__)


def search_web(query: str, max_results: int = 5) -> dict:
    """
    Returns snippets + source titles/URLs for grounding.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return {
            "success": False,
            "error": "Install duckduckgo-search: pip install duckduckgo-search",
            "snippets": [],
            "sources": [],
        }

    query = (query or "").strip()
    if not query:
        return {"success": False, "error": "empty query", "snippets": [], "sources": []}

    try:
        results = []
        ddgs = DDGS()
        for i, r in enumerate(ddgs.text(query, max_results=max_results)):
            results.append(
                {
                    "title": r.get("title") or "",
                    "url": r.get("href") or "",
                    "body": (r.get("body") or "")[:400],
                }
            )
            if i + 1 >= max_results:
                break
        if not results:
            return {"success": False, "error": "No web results", "snippets": [], "sources": []}

        lines = []
        for r in results:
            lines.append(f"- {r['title']}: {r['body']}")
        blob = "\n".join(lines)
        return {
            "success": True,
            "query": query,
            "snippets": blob,
            "sources": results,
        }
    except Exception as e:
        logger.exception("web search failed")
        return {"success": False, "error": str(e), "snippets": [], "sources": []}
