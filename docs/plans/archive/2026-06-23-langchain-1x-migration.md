# Plan: LangChain 1.x migration (+ tracked upstream-blocked advisories)

Status: **DONE** (2026-06-23, commit `290c6e2` on `dev`). Owner: Claude/Kristjan.

## Outcome / plan-reality deltas (resolved during impl)

The plan's assumed fix versions were partly wrong; resolved empirically via PyPI + `uv lock`:

- **`langchain` has no 1.4.6** — latest is 1.3.11. The advisory (GHSA-gr75, "fixed in 1.3.9/1.4.6")
  is satisfied by 1.3.9. Moot anyway — see next point.
- **`langchain` umbrella dropped as a direct dep entirely.** After re-pointing imports, nothing
  imports the bare `langchain` package; it was pulling the unused `langgraph` agent stack. Removing
  it (deptry DEP002) prunes 6 packages and **moots GHSA-gr75** (package no longer installed).
- **`langchain-community` has NO 1.x** — the 1.x-compatible release is the **0.4.x** line
  (resolved `0.4.2`). It pulls `langchain-classic` + `langchain-core` (where loaders now live).
- **Two test files** also imported the old `langchain.docstore.document` path
  (`test_ingest_logic.py`, `test_supports_encode_protocol_unit.py`) — re-pointed to
  `langchain_core.documents`. (Plan listed only `backend/ingest.py`.)
- **Two lazy loader imports** in `ingest.py` (`PyMuPDFLoader`/`UnstructuredPDFLoader`, lines 79/85)
  beyond the 3 top-level ones — all stay in `langchain_community.document_loaders`.
- `langchain-core` + `langchain-text-splitters` added as **direct deps** (imported directly);
  redundant `langchain-core` constraint-dependencies floor dropped.
- **`uv audit`: 13 → 8 vulns**, all 5 LangChain advisories cleared; remaining 8 are the
  upstream-blocked set (transformers/nltk/torch). 65 unit tests green.
- **Follow-up:** `langchain-community` 0.4.x emits a sunset DeprecationWarning (not escalated —
  fires outside `backend/`). Standalone loader packages are the eventual successor; revisit when
  community is fully sunset.
- **Not run:** live `make ingest` + QA round-trip (needs Docker stack); covered by import
  smoke-test + unit suite.

## Why

`uv audit` (OSV) — now the project's dependency-audit gate (replaced `pip-audit`, see
`security_scans.yml`) — flags 5 advisories across the LangChain stack whose **only fixes
ship in the 1.x line**. These cannot be cleared by a floor bump because `langchain 1.0`
is a breaking API rewrite; they need a deliberate migration. The second-wave/third-wave
floor bumps (committed alongside this plan) already cleared every advisory that had a
non-major fix. This plan covers the remainder that needs real work.

## Advisories this plan clears

| Package | Current | Fixed in | Advisory | Exploitable in our code? |
|---|---|---|---|---|
| langchain | 0.3.30 | 1.3.9 / 1.4.6 | GHSA-gr75-jv2w-4656 (path traversal in file-search middleware + loaders) | **Maybe** — we use `langchain_community` loaders (PyPDFLoader/DirectoryLoader/TextLoader) |
| langchain-core | 0.3.86 | 1.2.11 | GHSA-2g6r-c272-w58r (SSRF via `image_url` in `ChatOpenAI.get_num_tokens_from_messages`) | **No** — we don't use ChatOpenAI |
| langchain-core | 0.3.86 | 1.2.22 | GHSA-qh6h-p6c9-ff54 (path traversal in legacy `load_prompt`) | **No** — we don't call `load_prompt` |
| langchain-text-splitters | 0.3.11 | 1.1.2 | GHSA-fv5p-p927-qmxr (SSRF in `HTMLHeaderTextSplitter.split_text_from_url`) | **No** — we use `RecursiveCharacterTextSplitter` |
| langchain-text-splitters | 0.3.11 | 1.1.2 | PYSEC-2026-77 (no summary) | unknown |

**Risk note:** only the loader path-traversal (GHSA-gr75) plausibly touches our code; the
rest are in APIs we don't import. This is a hardening/hygiene migration, not an active-
exploit emergency — schedule it deliberately, don't rush a major bump.

## Current LangChain footprint (small — the good news)

All usage is in `backend/ingest.py`:
- `from langchain.docstore.document import Document`
- `from langchain.text_splitter import RecursiveCharacterTextSplitter`
- `from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader`

`pyproject.toml` direct deps: `langchain>=0.3.30,<0.4.0`, `langchain-community>=0.3.30,<0.4.0`
(plus the `langchain-core>=0.3.81` / `langsmith>=0.8.18` constraints in `[tool.uv]`).

## Migration steps

1. **Re-point imports to the stable public API** (1.x relocated/deprecated several paths):
   - `Document` → `from langchain_core.documents import Document`.
   - `RecursiveCharacterTextSplitter` → `from langchain_text_splitters import RecursiveCharacterTextSplitter`.
   - Loaders: confirm `langchain_community.document_loaders` still exports
     `DirectoryLoader`/`PyPDFLoader`/`TextLoader` under 1.x; if split out, add the
     successor package (e.g. a dedicated loader package) instead of `langchain-community`.
2. **Bump bounds** in `pyproject.toml`: `langchain>=1.4.6,<2.0.0`, `langchain-community` to its
   1.x-compatible release, and raise the `langchain-core` constraint to `>=1.2.22`. Drop the
   now-redundant lower constraints. `uv lock` and resolve conflicts (langchain-community 1.x
   pulls a matching langchain-core).
3. **Verify functionally** — ingestion is the only affected path: `make ingest` on a sample
   PDF + directory, then a retrieval/QA round-trip (`make cli ARGS='--question "..."'`).
   Unit + integration suites must stay green.
4. **Re-audit**: `make audit` (uv audit) should drop the 5 LangChain advisories
   (→ ~8 remaining, all upstream-blocked; see below).

## Out of scope here — tracked upstream-blocked advisories (no fix available)

Leave flagged; revisit when upstream ships fixes (Renovate/`uv audit` will surface them):
- **transformers 4.56.1** (6 advisories: PYSEC-2025-214..218 + CVE-2026-1839) — only fix is
  `5.0.0rc3` (pre-release), and 5.x breaks `sentence-transformers>=5.1.0`.
- **nltk 3.9.4** (GHSA-p4gq-832x-fm9v, path traversal in `nltk.data.load`) — no fixed release.
- **torch** (GHSA-rrmf-rvhw-rf47, memory corruption via `torch.jit.script`) — no fixed
  release; we don't call `torch.jit.script` directly.

## Done when

`make audit` shows only the upstream-blocked set (transformers/nltk/torch) and ingestion +
QA work end-to-end on the 1.x stack.
