"""
PDF text extraction and chunking.

Only plain text is extracted (no OCR, no image/table extraction), per spec.
"""

from typing import List, Dict
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from all pages of a PDF file."""
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


def chunk_text(
    text: str, chunk_size: int = 800, chunk_overlap: int = 150
) -> List[str]:
    """
    Split text into overlapping chunks by character count.

    A simple sliding-window splitter is used to keep the pipeline dependency-light
    while still preserving context across chunk boundaries via the overlap.
    """
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        if end == text_len:
            break
        start = end - chunk_overlap
    return chunks


def process_pdf(file_path: str, source_name: str) -> List[Dict]:
    """
    Extract text from a PDF and return a list of chunk dicts:
        {"text": chunk_text, "source": source_name}
    """
    raw_text = extract_text_from_pdf(file_path)
    chunks = chunk_text(raw_text)
    return [{"text": c, "source": source_name} for c in chunks]
