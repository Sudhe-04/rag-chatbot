FROM python:3.11-slim

WORKDIR /app

# System deps (kept minimal; pypdf is pure Python, faiss-cpu ships wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/pdfs /app/data/vectorstore

ENV PYTHONUNBUFFERED=1 \
    API_BASE_URL=http://localhost:8000 \
    CHATBOT_DB_PATH=/app/data/conversations.db \
    VECTORSTORE_DIR=/app/data/vectorstore \
    GEMINI_EMBEDDING_DIM=768

EXPOSE 8000 8501

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
