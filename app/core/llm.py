"""
Thin wrapper around the Google Gemini API for embeddings and chat completion.
"""

import os
from typing import List
from google import genai
from google.genai import types

EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

# Gemini embeddings default to 3072 dims; we truncate via MRL to keep the
# FAISS index smaller and faster while still getting strong retrieval quality.
EMBEDDING_DIM = int(os.environ.get("GEMINI_EMBEDDING_DIM", "768"))

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Please set it as an environment variable."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a list of texts (batched in groups of 100)."""
    client = get_client()
    all_embeddings: List[List[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        all_embeddings.extend([e.values for e in response.embeddings])
    return all_embeddings


def embed_query(text: str) -> List[float]:
    client = get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return response.embeddings[0].values


SYSTEM_PROMPT = (
    "You are a helpful assistant that answers user questions using ONLY the "
    "provided context extracted from uploaded PDF documents. "
    "If the answer cannot be found in the context, say you don't have enough "
    "information from the documents to answer, rather than making something up. "
    "Be concise and accurate."
)


def generate_answer(question: str, context_chunks: List[str]) -> str:
    """Generate an answer using retrieved context chunks via the Gemini chat model."""
    client = get_client()
    context_text = (
        "\n\n---\n\n".join(context_chunks) if context_chunks else "(no relevant context found)"
    )

    user_content = (
        f"Context from documents:\n{context_text}\n\n"
        f"User question: {question}\n\n"
        "Answer using only the context above."
    )

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=600,
        ),
    )
    return response.text.strip()
