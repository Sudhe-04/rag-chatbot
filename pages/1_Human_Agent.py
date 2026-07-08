"""
Human Agent Interface (Streamlit)

Lets a human agent see all conversations, pick one, view history, and reply
directly to the user. Only conversations in 'human' status accept agent replies.
"""

import os
import time

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Human Agent Console", page_icon="🧑‍💼", layout="wide")

st.title("🧑‍💼 Human Agent Console")
st.caption("View active conversations and respond to users after a handoff request.")


def list_conversations():
    try:
        r = requests.get(f"{API_BASE_URL}/conversations", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Could not load conversations: {e}")
        return []


def get_messages(conv_id: str):
    try:
        r = requests.get(f"{API_BASE_URL}/messages/{conv_id}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def send_agent_reply(conv_id: str, message: str):
    r = requests.post(
        f"{API_BASE_URL}/agent/reply",
        json={"conversation_id": conv_id, "message": message},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def set_status(conv_id: str, status: str):
    endpoint = "handoff" if status == "human" else "handoff/resume"
    r = requests.post(f"{API_BASE_URL}/{endpoint}", json={"conversation_id": conv_id}, timeout=10)
    r.raise_for_status()
    return r.json()


col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Conversations")
    if st.button("🔄 Refresh list"):
        st.rerun()

    conversations = list_conversations()

    if not conversations:
        st.info("No conversations yet.")
    else:
        labels = []
        for c in conversations:
            badge = "🧑‍💼 human" if c["status"] == "human" else "🤖 ai"
            labels.append(f"{c['id'][:8]}... [{badge}] (updated {c['updated_at'][:19]})")

        selected_idx = st.radio(
            "Select a conversation",
            options=range(len(conversations)),
            format_func=lambda i: labels[i],
            label_visibility="collapsed",
        )
        selected_conv = conversations[selected_idx]

with col2:
    if conversations:
        conv_id = selected_conv["id"]
        st.subheader(f"Conversation: {conv_id}")

        status = selected_conv["status"]
        badge_col, action_col = st.columns([1, 1])
        with badge_col:
            if status == "human":
                st.warning("Status: Human agent is handling this conversation")
            else:
                st.success("Status: AI is handling this conversation")
        with action_col:
            if status == "ai":
                if st.button("Take over conversation (handoff to me)"):
                    set_status(conv_id, "human")
                    st.rerun()
            else:
                if st.button("Return conversation to AI"):
                    set_status(conv_id, "ai")
                    st.rerun()

        st.divider()

        messages = get_messages(conv_id)
        chat_container = st.container(height=400)
        with chat_container:
            for msg in messages:
                if msg["sender"] == "user":
                    with st.chat_message("user"):
                        st.markdown(msg["content"])
                elif msg["sender"] == "ai":
                    with st.chat_message("assistant"):
                        st.markdown(msg["content"])
                elif msg["sender"] == "agent":
                    with st.chat_message("assistant", avatar="🧑‍💼"):
                        st.markdown(f"**You (agent):** {msg['content']}")

        if status == "human":
            reply = st.chat_input("Reply to user as human agent...")
            if reply:
                send_agent_reply(conv_id, reply)
                st.rerun()
        else:
            st.info("Take over this conversation to send a reply as a human agent.")
    else:
        st.info("Select a conversation from the left panel.")

# Light auto-refresh so the agent sees new user messages arriving
time.sleep(4)
st.rerun()
