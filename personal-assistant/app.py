"""Chat window for the personal assistant. Start it with:  streamlit run app.py"""

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import assistant  # noqa: E402  (needs the keys loaded first)

st.set_page_config(page_title="My Assistant", page_icon="🗂️")
st.title("My Assistant")
st.caption("Remembers things, plans with your calendar, to-dos and email. It never sends or deletes anything.")

if "messages" not in st.session_state:
    st.session_state.messages = []  # everything Claude sees, including tool use
    st.session_state.shown = []  # just the chat bubbles

with st.sidebar:
    st.subheader("Try asking")
    st.markdown(
        "- What's on this week?\n"
        "- Remember that Sarah's birthday is 3 March\n"
        "- What have I got on my Remember list?\n"
        "- Any emails about theatre tickets?\n"
        "- Help me plan Saturday"
    )
    if st.button("Start a new conversation"):
        st.session_state.messages, st.session_state.shown = [], []
        st.rerun()

for role, text in st.session_state.shown:
    st.chat_message(role).markdown(text)

if prompt := st.chat_input("Type here…"):
    st.chat_message("user").markdown(prompt)
    st.session_state.shown.append(("user", prompt))
    before = len(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                reply = assistant.chat(st.session_state.messages)
            except Exception as e:  # show problems in plain words rather than crashing
                del st.session_state.messages[before:]  # forget the failed turn so the next one starts clean
                reply = f"Something went wrong: {e}"
        st.markdown(reply)
    st.session_state.shown.append(("assistant", reply))
