from __future__ import annotations

from config.settings import get_settings
from rag.vector_store import load_vector_store


def get_retriever(k=4):
    vector_store = load_vector_store()
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
    print(f"✅ Retriever ready — top {k} chunks per query")
    return retriever


def retrieve(query: str, k: int | None = None) -> list[dict]:
    s = get_settings()
    k = k or s.rag_top_k
    max_dist = s.rag_max_l2_distance

    vector_store = load_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)

    chunks = []
    for doc, score in results:
        dist = float(score)
        if dist > max_dist:
            continue
        chunks.append(
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "score": round(dist, 4),
            }
        )

    return chunks
