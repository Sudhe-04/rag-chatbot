"""
User Chat Interface (Streamlit)

Talks to the FastAPI backend over HTTP. Users chat here; if a human agent takes
over the conversation, AI responses stop and the human's replies appear instead.
"""

import os
import uuid
import time

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Chatbot", page_icon="💬", layout="centered")

# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages_cache" not in st.session_state:
    st.session_state.messages_cache = []


def get_status(conv_id: str) -> str:
    try:
        r = requests.get(f"{API_BASE_URL}/status/{conv_id}", timeout=10)
        r.raise_for_status()
        return r.json()["status"]
    except Exception:
        return "ai"


def get_messages(conv_id: str):
    try:
        r = requests.get(f"{API_BASE_URL}/messages/{conv_id}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def send_chat(conv_id: str, message: str):
    r = requests.post(
        f"{API_BASE_URL}/chat",
        json={"conversation_id": conv_id, "message": message},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def request_handoff(conv_id: str):
    r = requests.post(f"{API_BASE_URL}/handoff", json={"conversation_id": conv_id}, timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("💬 Chat Session")
    st.text_input("Conversation ID", value=st.session_state.conversation_id, disabled=True)

    status = get_status(st.session_state.conversation_id)
    if status == "human":
        st.warning("🧑‍💼 A human agent is handling this conversation.")
    else:
        st.success("🤖 AI is responding to your messages.")

    st.divider()
    if st.button("🙋 Talk to a human agent", use_container_width=True, disabled=(status == "human")):
        request_handoff(st.session_state.conversation_id)
        st.rerun()

    st.divider()
    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

    st.caption("This conversation is stored so a human agent can view and reply to it.")

# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
st.title("🤖 AI Chatbot (RAG over your PDFs)")
st.caption("Ask questions about the uploaded documents. Request a human anytime from the sidebar.")

history = get_messages(st.session_state.conversation_id)

for msg in history:
    if msg["sender"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["sender"] == "ai":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])
    elif msg["sender"] == "agent":
        with st.chat_message("assistant", avatar="🧑‍💼"):
            st.markdown(f"**Human agent:** {msg['content']}")

user_input = st.chat_input("Type your message...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Thinking..."):
        try:
            result = send_chat(st.session_state.conversation_id, user_input)
        except Exception as e:
            st.error(f"Error contacting the chatbot service: {e}")
            result = None

    if result:
        if result["responder"] == "ai":
            with st.chat_message("assistant"):
                st.markdown(result["answer"])
                if result.get("sources"):
                    st.caption("Sources: " + ", ".join(result["sources"]))
        else:
            st.info("Your message has been sent to a human agent. Please wait for a reply.")
    st.rerun()

# Auto-refresh while in human mode so incoming agent replies appear without manual reload
if status == "human":
    time.sleep(3)
    st.rerun()
