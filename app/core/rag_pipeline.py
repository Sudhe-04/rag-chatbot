"""
Orchestrates the simple RAG pipeline:
    ingest_pdf(s) -> chunk -> embed -> store in FAISS
    answer_query -> embed query -> retrieve top-k chunks -> generate answer via LLM
"""

import os
from typing import List, Dict

from app.core.pdf_processor import process_pdf
from app.core.vector_store import get_vector_store
from app.core.llm import embed_texts, embed_query, generate_answer

TOP_K = int(os.environ.get("RAG_TOP_K", "4"))


def ingest_pdf(file_path: str, source_name: str) -> int:
    """Process a single PDF file: extract, chunk, embed, and store. Returns #chunks added."""
    chunks = process_pdf(file_path, source_name)
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    store = get_vector_store()
    store.add(embeddings, chunks)
    return len(chunks)


def ingest_pdfs(file_paths: List[str]) -> Dict[str, int]:
    """Ingest multiple PDFs. Returns a dict of {filename: num_chunks}."""
    results = {}
    for path in file_paths:
        name = os.path.basename(path)
        results[name] = ingest_pdf(path, name)
    return results


def answer_query(question: str, top_k: int = TOP_K) -> Dict:
    """
    Run the retrieval + generation steps for a user question.
    Returns {"answer": str, "sources": [source names], "chunks_used": int}
    """
    store = get_vector_store()

    if store.is_empty():
        return {
            "answer": (
                "No documents have been uploaded yet. Please ask an administrator "
                "to upload PDF documents before I can answer questions."
            ),
            "sources": [],
            "chunks_used": 0,
        }

    query_embedding = embed_query(question)
    results = store.search(query_embedding, top_k=top_k)

    context_chunks = [r["text"] for r in results]
    sources = sorted(set(r["source"] for r in results))

    answer = generate_answer(question, context_chunks)

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(context_chunks),
    }


def vector_store_stats() -> Dict:
    store = get_vector_store()
    sources = sorted(set(m["source"] for m in store.metadata)) if store.metadata else []
    return {
        "total_chunks": len(store.metadata),
        "sources": sources,
    }


def clear_knowledge_base():
    store = get_vector_store()
    store.clear()
