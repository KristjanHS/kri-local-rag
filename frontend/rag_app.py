# run locally: ~/projects/kri-local-rag$ streamlit run frontend/rag_app.py
import sys
import os
import threading
import streamlit as st

# Add backend directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
from qa_loop import answer, set_debug_level
from config import DEBUG_LEVEL, OLLAMA_CONTEXT_TOKENS

st.set_page_config(page_title="RAG Q&A", layout="centered")
st.title("RAG Q&A (Streamlit Frontend)")

debug_level = st.sidebar.selectbox("Debug Level", [0, 1, 2, 3], index=[0, 1, 2, 3].index(DEBUG_LEVEL))
set_debug_level(debug_level)
k = st.sidebar.slider("Number of top chunks (k)", min_value=1, max_value=10, value=3)
context_tokens = st.sidebar.number_input(
    "Ollama context window (tokens)",
    min_value=1024,
    max_value=32768,
    value=OLLAMA_CONTEXT_TOKENS,
    step=512,
)
st.sidebar.markdown(
    """
**VRAM usage:**
To monitor your GPU VRAM usage while running large context windows, open a terminal and run:
```
nvidia-smi -l 1
```
This will update VRAM usage every second.
"""
)

with st.form("question_form"):
    question = st.text_area("Ask a question:", height=100)
    submitted = st.form_submit_button("Get Answer")

# Session state for stop event and debug expander
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

stop_clicked = st.button("Stop", key="stop_button")
if stop_clicked:
    st.session_state.stop_event.set()

if submitted and question.strip():
    st.session_state.stop_event.clear()
    answer_placeholder = st.empty()
    debug_placeholder = st.empty()
    answer_tokens = []
    debug_lines = []

    def on_token(token):
        answer_tokens.append(token)
        answer_placeholder.markdown("**Answer:**\n" + "".join(answer_tokens))

    def on_debug(msg):
        debug_lines.append(msg)
        debug_placeholder.text("\n".join(debug_lines))

    with st.spinner("Thinking..."):
        answer(
            question,
            k=k,
            debug=debug_level > 0,
            on_token=on_token,
            on_debug=on_debug,
            stop_event=st.session_state.stop_event,
            context_tokens=context_tokens,
        )
    # After streaming, keep showing the debug info
    debug_placeholder.text("\n".join(debug_lines))
else:
    # Show a persistent debug info area even when not running
    if "debug_lines" in locals():
        st.expander("Debug info", expanded=False).text("\n".join(debug_lines))
