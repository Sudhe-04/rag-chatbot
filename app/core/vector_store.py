"""
Simple FAISS-backed vector store for storing and retrieving text chunk embeddings.

Persists to disk as:
    - <path>.index   (FAISS index)
    - <path>.meta.json (chunk texts + source metadata, in the same order as the index)
"""

import os
import json
import threading
from typing import List, Dict, Optional

import numpy as np
import faiss

VECTORSTORE_DIR = os.environ.get("VECTORSTORE_DIR", "/app/data/vectorstore")
INDEX_PATH = os.path.join(VECTORSTORE_DIR, "index.faiss")
META_PATH = os.path.join(VECTORSTORE_DIR, "meta.json")

_lock = threading.Lock()


class VectorStore:
    def __init__(self, dim: int = 768):
        self.dim = dim
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict] = []
        os.makedirs(VECTORSTORE_DIR, exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            with open(META_PATH, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(self.dim)  # cosine sim via normalized vectors
            self.metadata = []

    def _save(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        return vectors / norms

    def add(self, embeddings: List[List[float]], chunks: List[Dict]):
        """Add embeddings + associated chunk metadata ({'text', 'source'}) to the index."""
        with _lock:
            vecs = np.array(embeddings, dtype="float32")
            vecs = self._normalize(vecs)
            self.index.add(vecs)
            self.metadata.extend(chunks)
            self._save()

    def search(self, query_embedding: List[float], top_k: int = 4) -> List[Dict]:
        """Return top_k chunks most similar to the query embedding."""
        if self.index.ntotal == 0:
            return []
        with _lock:
            vec = np.array([query_embedding], dtype="float32")
            vec = self._normalize(vec)
            scores, indices = self.index.search(vec, min(top_k, self.index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            item = dict(self.metadata[idx])
            item["score"] = float(score)
            results.append(item)
        return results

    def is_empty(self) -> bool:
        return self.index is None or self.index.ntotal == 0

    def clear(self):
        with _lock:
            self.index = faiss.IndexFlatIP(self.dim)
            self.metadata = []
            self._save()


_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
