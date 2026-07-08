# AI Chatbot with RAG and Human Handoff

## About the Project

This project is an AI chatbot that answers questions using information from uploaded PDF documents. Instead of giving general AI responses, it searches the uploaded documents for relevant information and uses that to generate accurate answers. This approach is called Retrieval-Augmented Generation (RAG).

If the chatbot is unable to continue the conversation or the user wants personal assistance, the conversation can be handed over to a human agent.


## What the Project Can Do

* Upload PDF documents to build a knowledge base.
* Answer questions using the uploaded documents.
* Generate responses with Google Gemini.
* Transfer conversations to a human agent whenever needed.
* Save all conversations for future reference.
* Manage the knowledge base through a simple admin page.
* Run locally or inside Docker.


## Technologies Used

* **FastAPI** for the backend APIs.
* **Streamlit** for the user interface.
* **Google Gemini** for text generation and embeddings.
* **FAISS** to store and search document embeddings.
* **SQLite** to save conversations.
* **pypdf** to extract text from PDF files.
* **Docker** for containerized deployment.


## How the Chatbot Works

### Uploading Documents

The admin uploads one or more PDF files through the Admin page. The chatbot extracts the text, breaks it into smaller sections, creates embeddings, and stores them in FAISS. These documents become the chatbot's knowledge base.

### Asking Questions

When a user asks a question, the chatbot searches the uploaded documents for the most relevant information. That information is sent to Gemini along with the user's question, and Gemini generates a response based on the document content.

### Human Handoff

If the user clicks **"Talk to Human Agent"**, the chatbot stops responding and transfers the conversation to a human agent. The agent can view the conversation history and reply directly. Whenever needed, the conversation can be switched back to AI mode.


## Project Structure

```text
rag-chatbot/
│
├── app/
│   ├── api/          # FastAPI endpoints
│   ├── core/         # RAG logic and AI functions
│   └── db/           # SQLite database
│
├── pages/            # Streamlit pages
├── streamlit_app.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .env.example
```

---

## Running the Project

### Without Docker

1. Download or clone the project.
2. Create a virtual environment.
3. Install the required packages.

```bash
pip install -r requirements.txt
```

4. Create a `.env` file and add your Gemini API key.

```env
GEMINI_API_KEY=your_api_key
```

5. Start the FastAPI server.

```bash
uvicorn app.api.main:app --reload
```

6. Open another terminal and run the Streamlit application.

```bash
streamlit run streamlit_app.py
```

Open your browser:

* User Chat: `http://localhost:8501`
* Human Agent: `http://localhost:8501/Human_Agent`
* Admin Page: `http://localhost:8501/Admin_Knowledge_Base`
* API Documentation: `http://localhost:8000/docs`

---

## Running with Docker

Build the image:

```bash
docker build -t rag-chatbot .
```

Run the container:

```bash
docker run -d -p 8000:8000 -p 8501:8501 -e GEMINI_API_KEY=your_api_key rag-chatbot
```

Or simply use Docker Compose:

```bash
docker compose up --build
```



## Available API Endpoints

* **GET /health** – Check if the API is running.
* **POST /chat** – Send a message to the chatbot.
* **POST /handoff** – Transfer the conversation to a human agent.
* **POST /handoff/resume** – Switch the conversation back to AI.
* **GET /messages/{conversation_id}** – View conversation history.
* **POST /agent/reply** – Send a reply as a human agent.
* **POST /ingest** – Upload PDF documents.
* **GET /kb/stats** – View knowledge base details.
* **DELETE /kb** – Remove all uploaded documents.


## Limitations

* The chatbot can read only text from PDF files.
* Image-based or scanned PDFs are not supported.
* All uploaded documents are stored in a single shared knowledge base.
* User authentication is not included.
* Human handoff must be started manually.
* A valid Google Gemini API key is required to use the chatbot.

---

## Summary

This project shows how a RAG-based chatbot can provide better answers by using information from uploaded documents instead of relying only on the language model. It also includes a human handoff feature, making it suitable for customer support, document assistance, and knowledge-based applications.
