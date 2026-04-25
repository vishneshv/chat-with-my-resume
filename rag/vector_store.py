from __future__ import annotations

import threading
from pathlib import Path

from langchain_community.vectorstores import FAISS

from rag.document_loader import chunk_documents, load_documents
from rag.embeddings import get_embeddings

VECTOR_STORE_PATH = Path(__file__).parent.parent / "vector_store"

_store_lock = threading.Lock()
_cached_store: FAISS | None = None


def build_vector_store():
    print("\n🔨 Building vector store...")
    documents = load_documents()
    chunks = chunk_documents(documents)
    embeddings = get_embeddings()

    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(str(VECTOR_STORE_PATH))

    global _cached_store
    with _store_lock:
        _cached_store = vector_store

    print(f"✅ Vector store built and saved to {VECTOR_STORE_PATH}")
    return vector_store


def load_vector_store():
    global _cached_store
    with _store_lock:
        if _cached_store is not None:
            return _cached_store

    embeddings = get_embeddings()

    if not VECTOR_STORE_PATH.exists():
        print("⚠️  Vector store not found — building now...")
        return build_vector_store()

    vector_store = FAISS.load_local(
        str(VECTOR_STORE_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    with _store_lock:
        _cached_store = vector_store
    print("✅ Vector store loaded from disk")
    return vector_store


def reload_vector_store():
    """Clear cache and load fresh index from disk (after rebuild)."""
    global _cached_store
    with _store_lock:
        _cached_store = None
    return load_vector_store()
