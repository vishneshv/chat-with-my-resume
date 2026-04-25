"""Vector retrieval for the HireGraph KB (FAISS; sources in chunk metadata act as logical namespaces)."""

from __future__ import annotations

from rag.retriever import retrieve


def search_knowledge_base(query: str, k: int | None = None) -> dict:
    try:
        chunks = retrieve(query, k=k)

        if not chunks:
            return {
                "success": False,
                "error": "No chunks above similarity threshold — try rephrasing or use web search for fresh info",
                "chunks": [],
            }

        return {
            "success": True,
            "query": query,
            "chunks": chunks,
            "sources": list({c["source"] for c in chunks}),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "chunks": []}
