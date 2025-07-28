# run locally: ~/projects/kri-local-rag$ streamlit run frontend/rag_app.py
import sys
import os
import threading
import streamlit as st
import io, contextlib

# Add backend directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
from qa_loop import answer, set_debug_level, ensure_weaviate_ready_and_populated
from config import DEBUG_LEVEL, OLLAMA_CONTEXT_TOKENS
from ingest_pdf import ingest

st.set_page_config(page_title="RAG Q&A", layout="centered")
st.title("RAG Q&A (Streamlit Frontend)")

debug_level = st.sidebar.selectbox(
    "Debug Level", [0, 1, 2, 3], index=[0, 1, 2, 3].index(DEBUG_LEVEL)
)
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

# ---------------- Ingestion Sidebar ------------------
with st.sidebar.expander("Ingest PDFs"):
    uploaded_files = st.file_uploader(
        "Select PDF files", accept_multiple_files=True, type=["pdf"]
    )
    if st.button("Ingest", key="ingest_btn"):
        if not uploaded_files:
            st.warning("No files selected.")
        else:
            save_dir = "data"
            os.makedirs(save_dir, exist_ok=True)
            saved_paths = []
            for f in uploaded_files:
                path = os.path.join(save_dir, f.name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
                saved_paths.append(path)

            with st.spinner("Ingesting ..."):
                ingest(saved_paths)
            st.success(f"Ingested {len(saved_paths)} file(s).")

with st.form("question_form"):
    question = st.text_area("Ask a question:", height=100)
    submitted = st.form_submit_button("Get Answer")

# Session state for stop event and debug expander
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

stop_clicked = st.button("Stop", key="stop_button")
if stop_clicked:
    st.session_state.stop_event.set()

# ---------------- One-time backend initialization ------------------
if "init_done" not in st.session_state:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            ensure_weaviate_ready_and_populated()
        except Exception as e:
            print(f"[Error] Backend initialization failed: {e}")
    st.session_state["init_logs"] = buf.getvalue()
    st.session_state["init_done"] = True

# Show init logs in sidebar
st.sidebar.expander("Backend init logs", expanded=False).text(
    st.session_state.get("init_logs", "No init logs.")
)

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
