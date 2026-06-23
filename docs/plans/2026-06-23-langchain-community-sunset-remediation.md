# Plan: Drop `langchain-community` (sunset) + `pymupdf` (AGPL) + `unstructured[pdf]` from ingestion → pypdf

Status: **PROPOSED** (2026-06-23). Owner: Claude/Kristjan.
Follow-up to `docs/plans/archive/2026-06-23-langchain-1x-migration.md` — that plan's last
"Follow-up" bullet deferred this: *"`langchain-community` 0.4.x emits a sunset
DeprecationWarning … revisit when community is fully sunset."* It is now fully sunset.

## Why (two problems, one migration)

1. **`langchain-community` is archived (read-only) since 2026-05-26** — no maintenance, no security
   fixes. It emits a `DeprecationWarning` from `langchain_community/__init__.py:13` on **any** import,
   so the only way to silence it is to stop importing the package. We import 5 loaders from it, all in
   `backend/ingest.py` (`DirectoryLoader`, `PyPDFLoader`, `TextLoader` at line 29; lazy `PyMuPDFLoader`
   line 79, `UnstructuredPDFLoader` line 85).
2. **`pymupdf` is AGPL-3.0** (dual-licensed; commercial license is paid). AGPL obligations trigger on
   distribution **or** running as a network service users interact with — then the whole app must be
   AGPL-licensed. The user confirmed this system may be distributed/hosted, so AGPL is disqualifying.
3. **`unstructured[pdf]` is dead weight** (`pyproject.toml:23`). It was only ever reachable via the
   `UnstructuredPDFLoader` fallback (removed here) — grep confirms **zero usage** in
   `backend/`/`frontend/`/`scripts/`. It drags a 15+ package ML/OCR stack (`onnx`, `onnxruntime`,
   `opencv-python`, `effdet`, `timm`, `pdf2image`, `pikepdf`, `unstructured.pytesseract`, `numba`,
   `nltk`, `lxml`) + system binaries (tesseract/poppler), and its `unstructured-inference` caps
   `requires-python <3.14` — **it is the blocker** for the parked
   `docs/plans/archive/2026-06-23-python-3.14-upgrade.md`. Removing it slims the Docker image, cuts
   CVE surface (the `pdfminer-six` floor pin exists for it), and unblocks Python 3.14.

## Decision: parse PDFs with `pypdf` directly; wrap text/dir loading in-house

- **PDF** → **`pypdf`** (BSD-licensed, permissive). It is **already a direct dependency**
  (`pyproject.toml:101`, `pypdf>=6.13.3`; installed 6.14.0) — the project's prior `PyPDFLoader`
  fallback already used it. Pure-Python, no compiled C.
- **`.md`** → stdlib `Path.read_text()`.
- **directory** → the `glob.glob(..., recursive=True)` the directory branch already does.
- Loaders return `langchain_core.documents.Document` (kept; `langchain-core` is fully supported).

### Bonus: this also fixes the original `make stack-up` failure durably

The build broke earlier today because `pymupdf` 1.24.x has no cp313 wheel and source-built. The
interim hotfix (bump `pymupdf>=1.25.0`, regenerate lock — currently **uncommitted** working changes)
is **superseded by this migration**: dropping pymupdf for pure-Python pypdf removes the native-wheel
failure mode entirely. When implementing, remove pymupdf rather than keep the bump.

### Behaviour changes accepted

- The `PyMuPDF → Unstructured → PyPDF` "best-available" fallback chain is removed; PDFs are parsed by
  pypdf only. Downstream consumes only `doc.page_content` + `doc.metadata["source"]`
  (`ingest.py:177-223`), so custom loaders only need those two keys.
- pypdf is slower than pymupdf and weaker on complex tables — acceptable for text-RAG chunking.
  ([PyMuPDF vs pdfplumber](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/),
  [Nutrient PDF library comparison](https://www.nutrient.io/blog/best-python-pdf-libraries/))
- **OCR / scanned-PDF support is dropped** with `unstructured[pdf]`. pypdf returns empty text for
  image-only (scanned/photographed) PDFs — it has no OCR. **Accepted on the assumption the corpus is
  born-digital text PDFs.** If scanned PDFs are later needed, add a *targeted* OCR path
  (`ocrmypdf`/`pytesseract` on detected image-only pages, or MIT-licensed Docling) rather than
  re-adding the full unstructured stack. Likewise `pdfplumber` (MIT) for a table-heavy path if needed.

## Files changed

### 1. `backend/ingest.py`
- Remove the line-29 community import and the lazy `PyMuPDFLoader`/`UnstructuredPDFLoader` imports +
  the loader-selection try/except (lines 76-90).
- Add helpers returning `list[Document]`:
  - `_load_pdf(path)` → `pypdf.PdfReader(path)`, one `Document` per page,
    `page_content=page.extract_text()`, `metadata={"source": path, "page": i}`. Keep `_is_valid_pdf`.
  - `_load_text(path)` → `Document(page_content=Path(path).read_text("utf-8"), metadata={"source": path})`.
- Rewrite `load_and_split_documents`: single file dispatches on extension; directory keeps the
  existing glob and calls the helpers (drop `DirectoryLoader`), preserving per-pattern try/except +
  logging so one bad file doesn't abort the batch.
- Update module docstring (lines 6-13): drop "uses LangChain for … document loading".

### 2. `tests/unit/test_ingest_pdf_pymupdf_unit.py` → rename `test_ingest_pdf_unit.py`
- Drop the `meta["format"]` assertion (PyMuPDFLoader-specific). Assert extracted marker text +
  `meta["source"]` endswith `test.pdf` + `meta["page"] == 0` (our loader sets it).
- Reframe the docstring: the original "catch missing cp313 wheel" rationale no longer applies (pypdf
  is pure-Python and can't miss a wheel). The retained value is **functional coverage of ingest's PDF
  path**, which was entirely absent before today. Fixture `tests/test_data/test.pdf` stays — verified
  pypdf extracts the marker from it.

### 3. `tests/unit/test_ingest_logic.py::test_load_and_split_documents`
- `@patch("backend.ingest.DirectoryLoader")` breaks (symbol gone). Rewrite to drive real temp
  `.md`/`.pdf` files (use `tests/test_data/test.pdf`) through `load_and_split_documents`, asserting
  splitting occurred. No internal-loader mock.

### 4. `tests/integration/test_pdf_ingestion_unstructured.py`
- **Delete.** Tests only the now-removed `UnstructuredPDFLoader` fallback via
  `langchain_community.document_loaders._module_lookup`. Obsolete.

### 5. `pyproject.toml`
- Remove from `[project.dependencies]`: `langchain-community>=0.4,<0.5.0` (line 10),
  `pymupdf>=1.25.0,<2.0.0` (line 25), and `unstructured[pdf]>=0.18.18,<0.19.0` (line 23).
  (`pypdf` already present at line 101.)
- `[tool.uv] constraint-dependencies`: the `pdfminer-six>=20251230` pin (line 110, commented
  "unstructured[pdf]/pdfplumber") becomes a **no-op** once unstructured/pdfplumber leave the tree —
  `constraint-dependencies` only bind packages that are actually resolved. Leave it (harmless) or
  drop it; verify pdfplumber/pdfminer-six are gone from `uv.lock` after sync (step 4). Keep the
  other CVE pins (pillow/lxml/nltk are pulled by other deps, e.g. streamlit/langchain).
- `[tool.deptry.package_module_name_map]`: remove the `langchain-community` entry (line 247).
- `[tool.deptry.per_rule_ignores]` DEP002 (line ~255): remove `pdfplumber`, `pymupdf`, `unstructured`
  from the PDF-backends ignore. Keep `pillow` (still transitive, not first-party-imported).
- `make export-reqs` to regenerate `requirements.txt`; `uv sync` to drop langchain-community
  (+ `langchain-classic`), pymupdf (+ `pymupdfb`), and the entire unstructured ML/OCR stack
  (`onnx`/`onnxruntime`/`opencv-python`/`effdet`/`timm`/`pdf2image`/`pikepdf`/`pytesseract`/`numba`/…)
  from `uv.lock`.

## Verification

1. `ruff check backend tests --fix && ruff format` ; `make pyright`.
2. `.venv/bin/python -W error::DeprecationWarning -c "import backend.ingest"` — must NOT raise the
   sunset warning (proves no `langchain_community` import path remains).
3. `.venv/bin/python -m pytest tests/unit/ -q` — all green (esp. the 3 ingest tests touched).
4. In `uv.lock`, `grep -c 'name = "<pkg>"'` → 0 for `langchain-community`, `pymupdf`, `unstructured`,
   `unstructured-inference`, `onnx`, `pdfplumber`. Package count drops substantially.
5. `make stack-up` build succeeds (durable: no native PDF wheel involved) and the app image shrinks.
6. `make audit` (uv audit / OSV) — confirm no *new* advisories and that unstructured-stack ones leave.
7. `make pre-commit` (deptry clean after the ignore-list edits). `make ingest` round-trip is
   Docker-gated; covered by steps 2-3.
8. **3.14 unblock check (optional, confirms the bonus):** `unstructured-inference`'s `<3.14` cap is
   gone from the tree — the parked `docs/plans/archive/2026-06-23-python-3.14-upgrade.md` blocker is
   lifted. Don't action 3.14 here; just note it in that plan when this ships.

## Risks / notes

- **Text-extraction parity**: pypdf's `extract_text()` differs from pymupdf's `get_text()` on layout
  edge cases (column order, ligatures). For chunked text RAG this is low-impact, but spot-check a real
  multi-column PDF if available.
- **Scope**: 3 prod/test files + deps. Per `.claude/rules/plan-hygiene.md` plan-doc-optional (≤1
  session); this doc exists because the user requested it and to record the licence + "no replacement
  package" rationale. **Archive (`git rm`) on ship**.
