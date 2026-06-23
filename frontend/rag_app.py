# run locally: ~/projects/kri-local-rag$ streamlit run frontend/rag_app.py
import contextlib
import html
import io
import os
import threading

import streamlit as st

from backend.config import OLLAMA_CONTEXT_TOKENS, get_logger

# Set up logging for this module
logger = get_logger(__name__)

# Upload safety limits (defense-in-depth for the ingestion entry point).
# Overridable via env: MAX_UPLOAD_FILES (count), MAX_UPLOAD_MB (per-file size).
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "20"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
PDF_MAGIC = b"%PDF-"


def _render_answer(placeholder, tokens):
    """Render streamed answer tokens inside a stable Playwright locator.

    The wrapper is static, trusted HTML; the model/document-derived content is
    HTML-escaped to prevent script injection (XSS) from ingested documents.
    """
    # quote=False: body-text context (not an attribute), so literal quotes render cleanly
    content = html.escape("".join(tokens), quote=False)
    placeholder.markdown(
        f"<div data-testid='answer'><h3>Answer</h3><div class='answer-content'>{content}</div></div>",
        unsafe_allow_html=True,
    )


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
./scripts/dev/monitor_gpu.sh
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
        elif len(uploaded_files) > MAX_UPLOAD_FILES:
            st.error(f"Too many files ({len(uploaded_files)}); max {MAX_UPLOAD_FILES} per ingest.")
        else:
            save_dir = "data"
            os.makedirs(save_dir, exist_ok=True)
            real_save_dir = os.path.realpath(save_dir)
            saved_paths = []
            rejected = []
            for f in uploaded_files:
                # B2/B9: strip directory components and confirm the resolved path stays in save_dir
                safe_name = os.path.basename(f.name)
                if len(safe_name) <= len(".pdf") or not safe_name.lower().endswith(".pdf"):
                    rejected.append(f"{f.name} (not a .pdf)")
                    continue
                dest = os.path.realpath(os.path.join(real_save_dir, safe_name))
                if os.path.commonpath([real_save_dir, dest]) != real_save_dir:
                    rejected.append(f"{f.name} (unsafe path)")
                    continue
                # B3: enforce per-file size cap and validate PDF magic bytes before writing
                data = f.getbuffer()
                if data.nbytes > MAX_UPLOAD_BYTES:
                    rejected.append(f"{safe_name} (exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
                    continue
                if bytes(data[: len(PDF_MAGIC)]) != PDF_MAGIC:
                    rejected.append(f"{safe_name} (not a valid PDF)")
                    continue
                with open(dest, "wb") as out:
                    out.write(data)
                saved_paths.append(dest)

            if rejected:
                st.warning("Skipped: " + ", ".join(rejected))

            if not saved_paths:
                st.error("No valid PDF files to ingest.")
            else:
                with st.spinner("Ingesting ..."):
                    # Ingest operates on a directory; use the save directory
                    from backend.config import COLLECTION_NAME
                    from backend.ingest import (
                        connect_to_weaviate,
                        ingest,
                    )
                    from backend.models import load_embedder

                    client = connect_to_weaviate()
                    try:
                        model = load_embedder()
                        ingest(
                            directory=save_dir,
                            collection_name=COLLECTION_NAME,
                            weaviate_client=client,
                            embedding_model=model,
                        )
                    finally:
                        client.close()
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
        # Render with a stable locator for Playwright; content is HTML-escaped (XSS-safe)
        _render_answer(answer_placeholder, answer_tokens)

    def on_debug(msg):
        st.session_state["debug_lines"].append(msg)
        debug_placeholder.text("\n".join(st.session_state["debug_lines"]))

    # If tests requested a fake answer, render it immediately to satisfy E2E
    fake_answer = os.getenv("RAG_FAKE_ANSWER")
    if fake_answer:
        for ch in fake_answer:
            on_token(ch)
        # Ensure final full content is rendered for visibility tests
        _render_answer(answer_placeholder, answer_tokens)
        # Explicit marker for fake-mode to help E2E tests verify bypassed backend
        st.markdown("<div data-testid='fake-mode'></div>", unsafe_allow_html=True)
    else:
        with st.spinner("Thinking..."):
            # Lazy import to avoid heavy deps during module import
            from backend.qa_loop import answer
            from backend.models import load_reranker

            try:
                cross_encoder = load_reranker()
            except Exception as e:
                logger.error("Failed to load CrossEncoder: %s", e)
                st.error("CrossEncoder model could not be loaded. Ensure the model is available or try again later.")
                raise

            answer(
                question,
                k=k,
                on_token=on_token,
                on_debug=on_debug,
                stop_event=st.session_state.stop_event,
                context_tokens=context_tokens,
                cross_encoder=cross_encoder,
            )
    # After streaming, keep showing the debug info
    debug_placeholder.text("\n".join(st.session_state["debug_lines"]))
else:
    # Show a persistent debug info area even when not running
    st.sidebar.expander("Debug info", expanded=False).text("\n".join(st.session_state.get("debug_lines", [])))
