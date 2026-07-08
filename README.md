# AI Chatbot with Simple RAG and Human Handoff

A chatbot application that answers user questions using a Retrieval-Augmented
Generation (RAG) pipeline over uploaded PDF documents, with a Human Handoff
feature that lets a human agent take over any conversation.

## Architecture

```
┌─────────────────────┐        ┌──────────────────────┐
│  Streamlit (8501)    │        │   FastAPI (8000)     │
│  ─────────────────   │  HTTP  │  ──────────────────  │
│  • User Chat UI       │───────▶│  /chat               │
│  • Human Agent Console│        │  /handoff             │
│  • Admin (KB upload)  │        │  /agent/reply         │
└─────────────────────┘        │  /ingest, /kb/stats   │
                                 └──────────┬────────────┘
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
             ┌───────────────┐     ┌────────────────┐     ┌────────────────┐
             │ RAG Pipeline  │     │  SQLite DB      │     │  Gemini API     │
             │ (PDF→chunks→  │     │  (conversations,│     │  (embeddings + │
             │  FAISS index) │     │   messages)     │     │   chat model)  │
             └───────────────┘     └────────────────┘     └────────────────┘
```

**Technology stack**
- **Backend / REST API:** FastAPI
- **User & Agent interfaces:** Streamlit (multi-page app)
- **LLM & Embeddings:** Google Gemini (`gemini-2.5-flash` for generation, `gemini-embedding-001` for embeddings)
- **Vector store:** FAISS (file-based, no external service required)
- **PDF text extraction:** `pypdf` (text only — no OCR/tables/images, per spec)
- **Conversation storage:** SQLite
- **Containerization:** Docker / Docker Compose

## How it works

1. **Ingestion (Admin page):** PDFs are uploaded → text is extracted → split into
   overlapping ~800-character chunks → each chunk is embedded via Gemini →
   embeddings + chunk text/source are stored in a FAISS index on disk.
2. **Chat (User page):** A user question is embedded, the top-k most similar
   chunks are retrieved from FAISS, and those chunks are passed as context to
   the chat model, which generates the final answer.
3. **Human Handoff:** Clicking "Talk to a human agent" (or calling `/handoff`)
   flips the conversation's status to `human`. From that point on:
   - The `/chat` endpoint stores the user's message but **does not** call the
     RAG pipeline — it returns `responder: "human_pending"` instead.
   - The Human Agent Console lists all conversations and lets an agent view
     history and reply; replies are stored with sender `agent` and shown to
     the user.
   - An agent (or the system) can call `/handoff/resume` to switch the
     conversation back to AI mode.
4. **Conversation storage:** every message (`user` / `ai` / `agent`) and the
   conversation's current status (`ai` / `human`) are persisted in SQLite, so
   history survives restarts and is available to both the API and the agent
   console.

## Project Structure

```
rag-chatbot/
├── app/
│   ├── api/
│   │   ├── main.py            # FastAPI app & REST endpoints
│   │   └── schemas.py         # Pydantic request/response models
│   ├── core/
│   │   ├── pdf_processor.py   # PDF text extraction + chunking
│   │   ├── vector_store.py    # FAISS index wrapper
│   │   ├── llm.py             # Gemini embeddings + chat completion
│   │   └── rag_pipeline.py    # Ingestion & query orchestration
│   └── db/
│       └── database.py        # SQLite conversation/message storage
├── pages/
│   ├── 1_Human_Agent.py       # Human agent console (Streamlit page)
│   └── 2_Admin_Knowledge_Base.py # PDF upload / KB admin (Streamlit page)
├── streamlit_app.py           # User chat interface (Streamlit home page)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh              # Runs FastAPI + Streamlit in one container
├── .env.example
└── README.md
```

## Setup & Installation (local, without Docker)

### Prerequisites
- Python 3.11+
- A Google Gemini API key (free tier available at https://aistudio.google.com/apikey)

### Steps

```bash
# 1. Clone/extract the project and enter it
cd rag-chatbot

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env and set your GEMINI_API_KEY

# 5. Export the env vars (or use `python-dotenv` / your shell's env loader)
export GEMINI_API_KEY=your-gemini-key-here

# 6. Run the REST API (terminal 1)
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# 7. Run the Streamlit app (terminal 2)
export API_BASE_URL=http://localhost:8000
streamlit run streamlit_app.py
```

Then open:
- **User Chat:** http://localhost:8501
- **Human Agent Console:** http://localhost:8501/Human_Agent
- **Admin / Upload PDFs:** http://localhost:8501/Admin_Knowledge_Base
- **REST API docs (Swagger):** http://localhost:8000/docs

> ⚠️ Upload at least one PDF via the Admin page before asking questions —
> otherwise the bot will tell you no documents are available.

## Running with Docker

### Build the image

```bash
docker build -t rag-chatbot:latest .
```

### Run the container

```bash
docker run -d \
  --name rag-chatbot \
  -p 8000:8000 \
  -p 8501:8501 \
  -e GEMINI_API_KEY=your-gemini-key-here \
  -v chatbot_data:/app/data \
  rag-chatbot:latest
```

### Or use Docker Compose (recommended)

```bash
# Set your key once
export GEMINI_API_KEY=your-gemini-key-here

# Build & start
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Then open the same URLs as above (http://localhost:8501 and http://localhost:8000/docs).

The `chatbot_data` Docker volume persists the SQLite database and the FAISS
vector store across container restarts.

## Docker Hub

The image is published to Docker Hub as:

```
docker pull <dockerhub-username>/rag-chatbot:latest
```

> Replace `<dockerhub-username>` with the actual Docker Hub account used to
> publish the image. To publish it yourself:
>
> ```bash
> docker build -t <dockerhub-username>/rag-chatbot:latest .
> docker login
> docker push <dockerhub-username>/rag-chatbot:latest
> ```

### Pulling and running the published image

```bash
docker pull <dockerhub-username>/rag-chatbot:latest

docker run -d \
  --name rag-chatbot \
  -p 8000:8000 \
  -p 8501:8501 \
  -e GEMINI_API_KEY=your-gemini-key-here \
  -v chatbot_data:/app/data \
  <dockerhub-username>/rag-chatbot:latest
```

## REST API Reference

| Method | Endpoint                    | Description                                              |
|--------|------------------------------|-----------------------------------------------------------|
| GET    | `/health`                    | Health check                                              |
| POST   | `/chat`                      | Send a user message; returns AI answer or human-pending status |
| POST   | `/handoff`                   | Transfer a conversation to a human agent                  |
| POST   | `/handoff/resume`             | Switch a conversation back to AI mode                     |
| GET    | `/status/{conversation_id}`  | Get current status (`ai` / `human`) of a conversation      |
| GET    | `/messages/{conversation_id}`| Get full message history for a conversation                |
| GET    | `/conversations`             | List all conversations (used by the agent console)         |
| POST   | `/agent/reply`               | Human agent sends a reply directly to the user              |
| POST   | `/ingest`                    | Upload one or more PDF files to add to the knowledge base   |
| GET    | `/kb/stats`                  | Knowledge base stats (chunk count, indexed source files)   |
| DELETE | `/kb`                        | Clear the entire knowledge base                             |

Full interactive documentation is available at `/docs` (Swagger UI) once the
API is running.

## Assumptions & Limitations

- **Text-only PDF extraction:** No OCR, image extraction, or table-structure
  parsing is performed, per the task scope. Scanned/image-only PDFs will
  yield little or no extractable text.
- **Chunking strategy:** A simple fixed-size sliding-window splitter
  (800 characters, 150-character overlap) is used rather than
  semantic/sentence-aware chunking, to keep the pipeline dependency-light.
- **Single shared knowledge base:** All ingested PDFs are combined into one
  FAISS index; there is no per-user or per-conversation document scoping.
- **One human agent role:** The Human Agent Console does not implement
  authentication, multiple agent accounts, or assignment/routing logic —
  any user of that page can take over and reply to any conversation. This is
  suitable for the current scope but would need access control before use
  with real users.
- **No automatic handoff triggers:** Handoff is manually initiated (by the
  user clicking "Talk to a human agent" or an agent taking over); there is
  no automatic escalation (e.g., based on AI confidence or sentiment).
- **Polling-based updates:** The Streamlit UIs use a lightweight polling
  refresh (every few seconds) rather than websockets, so there can be a
  short delay before new messages appear.
- **Single-process container:** For simplicity, both the FastAPI backend and
  the Streamlit frontend run in the same container (managed by
  `entrypoint.sh`). This is convenient for the deliverable but is not the
  ideal production topology — running them as separate services (as hinted
  in `docker-compose.yml`, which could be split further) would offer better
  scalability and fault isolation.
- **Vector store persistence:** FAISS index and metadata are stored as flat
  files under `/app/data/vectorstore`; this is fine for small-to-medium
  document sets but does not scale to very large corpora the way a managed
  vector database would.
- **API key required:** A Google Gemini API key must be supplied via the
  `GEMINI_API_KEY` environment variable; the app will raise a clear error if
  it's missing when a chat/ingest request is made.
