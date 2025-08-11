# run locally: ~/projects/kri-local-rag$ streamlit run frontend/rag_app.py
import contextlib
import io
import os
import threading

import streamlit as st

from backend.config import OLLAMA_CONTEXT_TOKENS, get_logger

# Set up logging for this module
logger = get_logger(__name__)

st.set_page_config(page_title="RAG Q&A", layout="centered")
st.title("RAG Q&A (Streamlit Frontend)")

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
**GPU Monitoring:**
To monitor your GPU VRAM usage while running large context windows, open a terminal and run:
```
./monitor_gpu.sh
```
This shows GPU memory, utilization, and container resource usage.

For continuous monitoring:
```
gpustat -i 2
```
"""
)

# ---------------- Ingestion Sidebar ------------------
with st.sidebar.expander("Ingest PDFs"):
    uploaded_files = st.file_uploader("Select PDF files", accept_multiple_files=True, type=["pdf"])
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
                # Ingest operates on a directory; use the save directory
                from backend.ingest import ingest  # lazy import to avoid heavy deps during module import

                ingest(save_dir)
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
            skip_checks = os.getenv("RAG_SKIP_STARTUP_CHECKS", "0").lower() in ("1", "true", "yes")
            fake_answer_present = bool(os.getenv("RAG_FAKE_ANSWER"))
            logger.info(
                "App startup env: RAG_SKIP_STARTUP_CHECKS=%s, RAG_FAKE_ANSWER=%s",
                str(skip_checks),
                str(fake_answer_present),
            )
            if skip_checks:
                logger.info("Startup checks skipped via RAG_SKIP_STARTUP_CHECKS")
            else:
                # Lazy import to avoid heavy deps during module import
                from backend.qa_loop import ensure_weaviate_ready_and_populated

                ensure_weaviate_ready_and_populated()
        except Exception as e:
            logger.error("Backend initialization failed: %s", e)
    st.session_state["init_logs"] = buf.getvalue()
    st.session_state["init_done"] = True

# Show init logs in sidebar
st.sidebar.expander("Backend init logs", expanded=False).text(st.session_state.get("init_logs", "No init logs."))

# Ensure a persistent debug buffer exists
if "debug_lines" not in st.session_state:
    st.session_state["debug_lines"] = []

if submitted and question.strip():
    st.session_state.stop_event.clear()
    answer_placeholder = st.empty()
    debug_placeholder = st.empty()
    answer_tokens = []
    st.session_state["debug_lines"] = []

    def on_token(token):
        answer_tokens.append(token)
        # Render with a stable locator for Playwright and include both label and content
        answer_html = (
            "<div data-testid='answer'>"
            "<h3>Answer</h3>"
            f"<div class='answer-content'>{''.join(answer_tokens)}</div>"
            "</div>"
        )
        answer_placeholder.markdown(answer_html, unsafe_allow_html=True)

    def on_debug(msg):
        st.session_state["debug_lines"].append(msg)
        debug_placeholder.text("\n".join(st.session_state["debug_lines"]))

    # If tests requested a fake answer, render it immediately to satisfy E2E
    fake_answer = os.getenv("RAG_FAKE_ANSWER")
    if fake_answer:
        for ch in fake_answer:
            on_token(ch)
        # Ensure final full content is rendered for visibility tests
        final_html = (
            "<div data-testid='answer'>"
            "<h3>Answer</h3>"
            f"<div class='answer-content'>{''.join(answer_tokens)}</div>"
            "</div>"
        )
        answer_placeholder.markdown(final_html, unsafe_allow_html=True)
        # Explicit marker for fake-mode to help E2E tests verify bypassed backend
        st.markdown("<div data-testid='fake-mode'></div>", unsafe_allow_html=True)
    else:
        with st.spinner("Thinking..."):
            # Lazy import to avoid heavy deps during module import
            from backend.qa_loop import answer

            answer(
                question,
                k=k,
                on_token=on_token,
                on_debug=on_debug,
                stop_event=st.session_state.stop_event,
                context_tokens=context_tokens,
            )
    # After streaming, keep showing the debug info
    debug_placeholder.text("\n".join(st.session_state["debug_lines"]))
else:
    # Show a persistent debug info area even when not running
    st.sidebar.expander("Debug info", expanded=False).text("\n".join(st.session_state.get("debug_lines", [])))
