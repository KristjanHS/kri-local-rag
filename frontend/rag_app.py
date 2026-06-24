# run locally: ~/projects/kri-local-rag$ streamlit run frontend/rag_app.py
import html
import io
import logging
import os
import threading

import streamlit as st

from backend.config import OLLAMA_CONTEXT_TOKENS, PDF_MAGIC, get_logger

# Set up logging for this module
logger = get_logger(__name__)

# Upload safety limits (defense-in-depth for the ingestion entry point).
# Overridable via env: MAX_UPLOAD_FILES (count), MAX_UPLOAD_MB (per-file size).
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "150"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024


# --- Test-only hooks -------------------------------------------------------
# These env vars let CLI/UI e2e tests bypass the real backend. They are read
# only through the helpers below so the test surface stays explicit and in one
# place (Tier 2.6 of complexity-cleanup). The backend's own RAG_FAKE_ANSWER
# bypass lives independently in backend.qa_loop.answer().
def _fake_answer() -> str | None:
    """Return the canned answer for fake-mode, or None when the hook is unset/empty."""
    return os.getenv("RAG_FAKE_ANSWER") or None


def _skip_startup_checks() -> bool:
    """True when startup Weaviate/ingest checks should be bypassed for tests."""
    return os.getenv("RAG_SKIP_STARTUP_CHECKS", "0").lower() in ("1", "true", "yes")


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


class _DebugPanelHandler(logging.Handler):
    """Feed backend ``logger.debug`` records into the Streamlit debug panel.

    Replaces the old hand-maintained ``on_debug`` callback channel: backend code now emits
    diagnostics solely via logging, and the UI captures them by attaching this handler around
    the ``answer()`` call. Restricted to the originating ScriptRunner thread so concurrent
    sessions don't cross-feed each other's debug lines (mirrors ``_ThreadLogFilter`` below).
    """

    def __init__(self, thread_id: int, placeholder) -> None:
        super().__init__(level=logging.DEBUG)
        self._thread_id = thread_id
        self._placeholder = placeholder
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self._thread_id:
            return
        lines = st.session_state.get("debug_lines")
        if lines is None:
            return
        lines.append(self.format(record))
        try:
            self._placeholder.text("\n".join(lines))
        except Exception:
            # Placeholder may be unavailable after a rerun; the sidebar expander still
            # renders the accumulated buffer at the end of the run. handleError writes to
            # stderr (never via a logger), so it can't re-enter emit().
            self.handleError(record)


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
                    from backend.ingest import ingest
                    from backend.models import load_embedder
                    from backend.weaviate_client import get_weaviate_client

                    client = get_weaviate_client()
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
    # Capture log records (not stdout): app logging goes to stderr handlers, so a
    # temporary in-memory handler on the root logger is what surfaces init output here.
    buf = io.StringIO()
    capture_handler = logging.StreamHandler(buf)
    capture_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    # The root logger is shared across all Streamlit session threads. Restrict capture to
    # this thread so a concurrently-initializing session's logs (queries, retrieved context)
    # don't leak into this session's "Backend init logs".
    init_thread_id = threading.get_ident()

    class _ThreadLogFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.thread == init_thread_id

    capture_handler.addFilter(_ThreadLogFilter())
    root_logger = logging.getLogger()
    root_logger.addHandler(capture_handler)
    try:
        skip_checks = _skip_startup_checks()
        logger.info(
            "App startup env: RAG_SKIP_STARTUP_CHECKS=%s, RAG_FAKE_ANSWER=%s",
            str(skip_checks),
            str(_fake_answer() is not None),
        )
        if skip_checks:
            logger.info("Startup checks skipped via RAG_SKIP_STARTUP_CHECKS")
        else:
            # Lazy import to avoid heavy deps during module import
            from backend.qa_loop import ensure_weaviate_ready_and_populated

            ensure_weaviate_ready_and_populated()
    except Exception as e:
        logger.error("Backend initialization failed: %s", e)
    finally:
        root_logger.removeHandler(capture_handler)
    st.session_state["init_logs"] = buf.getvalue() or "No init logs."
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

    # If tests requested a fake answer, render it immediately to satisfy E2E
    fake_answer = _fake_answer()
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

            # Route backend diagnostics into the debug panel via logging (replaces on_debug).
            # Raise the module logger to DEBUG so its records reach the handler. This is done
            # idempotently and NOT restored: the logger is a process-wide singleton shared by
            # every Streamlit session thread, so restoring a prior level in this thread's
            # finally would silence DEBUG for a concurrent thread still inside answer(). DEBUG
            # records are still filtered out at the root handler (INFO) and the per-thread
            # _DebugPanelHandler only feeds this session's panel, so leaving it on is safe.
            ollama_logger = logging.getLogger("backend.ollama_client")
            if ollama_logger.level > logging.DEBUG or ollama_logger.level == logging.NOTSET:
                ollama_logger.setLevel(logging.DEBUG)
            debug_handler = _DebugPanelHandler(threading.get_ident(), debug_placeholder)
            ollama_logger.addHandler(debug_handler)
            try:
                answer(
                    question,
                    k=k,
                    on_token=on_token,
                    stop_event=st.session_state.stop_event,
                    context_tokens=context_tokens,
                    cross_encoder=cross_encoder,
                )
            finally:
                ollama_logger.removeHandler(debug_handler)
    # After streaming, keep showing the debug info
    debug_placeholder.text("\n".join(st.session_state["debug_lines"]))

# Always surface the latest debug lines in the sidebar (reflects the most recent run).
st.sidebar.expander("Debug info", expanded=False).text(
    "\n".join(st.session_state.get("debug_lines", [])) or "No debug info."
)
