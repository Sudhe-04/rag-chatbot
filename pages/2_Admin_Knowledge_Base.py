"""
Admin page: upload PDF documents into the RAG knowledge base.
"""

import os
import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Knowledge Base Admin", page_icon="📄", layout="centered")

st.title("📄 Knowledge Base Admin")
st.caption("Upload PDF documents to power the RAG chatbot's answers.")

st.subheader("Upload PDFs")
uploaded_files = st.file_uploader(
    "Choose one or more PDF files", type=["pdf"], accept_multiple_files=True
)

if st.button("Ingest documents", disabled=not uploaded_files):
    files_payload = [
        ("files", (f.name, f.getvalue(), "application/pdf")) for f in uploaded_files
    ]
    with st.spinner("Extracting text, generating embeddings, and indexing..."):
        try:
            r = requests.post(f"{API_BASE_URL}/ingest", files=files_payload, timeout=300)
            r.raise_for_status()
            result = r.json()
            st.success("Ingestion complete!")
            st.json(result["files_processed"])
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

st.divider()
st.subheader("Knowledge Base Stats")

try:
    r = requests.get(f"{API_BASE_URL}/kb/stats", timeout=10)
    r.raise_for_status()
    stats = r.json()
    col1, col2 = st.columns(2)
    col1.metric("Total chunks indexed", stats["total_chunks"])
    col2.metric("Documents", len(stats["sources"]))
    if stats["sources"]:
        st.write("**Indexed documents:**")
        for s in stats["sources"]:
            st.write(f"- {s}")
except Exception as e:
    st.error(f"Could not load KB stats: {e}")

st.divider()
if st.button("⚠️ Clear entire knowledge base", type="secondary"):
    try:
        r = requests.delete(f"{API_BASE_URL}/kb", timeout=10)
        r.raise_for_status()
        st.success("Knowledge base cleared.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to clear KB: {e}")
