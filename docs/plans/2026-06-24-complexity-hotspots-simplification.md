# Complexity Hotspots — Simplification Plan

**Date:** 2026-06-24
**Author:** Brutal-honesty review (Linus mode), full read of all 11 core modules (~2,100 LOC)
**Scope:** `backend/`, `frontend/` — identify and remove unnecessary code complexity

## Premise

A ~2,100-line RAG app carrying the complexity budget of a 10,000-line one. The dominant
smell is **defensive generality against inputs that never occur**: fallback branches for
APIs we don't call, type machinery for one concrete class, caching layered three deep.
None of it is load-bearing; all of it is maintenance tax.

Recurring anti-pattern to internalize: **"handle the case that never happens."**
Write for the inputs we actually have; let the code crash loudly on the ones we don't.
A `KeyError` on an unexpected Ollama frame beats 40 lines of silent fallback that hide
the day Ollama changes its API.

---

## Ranked findings

| # | Hotspot | File:lines | Severity | Verdict |
|---|---------|-----------|----------|---------|
| 1 | `metadata_filter` dict vs v4 `Filter` mismatch | qa_loop / retriever | **CRITICAL** | Broken feature + dead complexity |
| 2 | torchvision fail-fast stub module | models.py:26-170 | **CRITICAL** | 145 lines to dodge one import |
| 3 | `generate_response` token-extraction generality | ollama_client.py:194-232 | **HIGH** | SSE/`[DONE]`/`choices` paths Ollama never sends |
| 4 | `to_float_list` 6-branch converter | vector_utils.py (full) | **HIGH** | Speculative; untested fallbacks |
| 5 | Triple-layered embedding-model caching | models + retriever + qa_loop | **HIGH** | 3 caches for 1 singleton |
| 6 | `ensure_weaviate_ready_and_populated` bootstrap | qa_loop.py:243-323 | **HIGH** | ✅ DONE 2026-06-24 — D6 investigation: warmup NOT load-bearing (embedder lazy-loads+caches on first query; dance only ran on fresh DB). Collapsed to `ensure_collection()` (empty schema only); dropped PDF round-trip + delete_many + version-fallback + `Filter` import |
| 7 | Streamlit per-thread logging plumbing | rag_app.py:51-79,185-226 | **HIGH** | 60 lines of handler gymnastics |
| 8 | `answer()` does 6 jobs | qa_loop.py:118-230 | **HIGH** | Retrieve+rerank+prompt+stream+CLI+test-hook |
| 9 | Duplicated `RAG_FAKE_ANSWER` bypass | qa_loop.py:137 + rag_app.py:27-29,245 | MEDIUM | Two char-streaming fake paths |
| 10 | Debug-log spam per token/line | ollama_client.py:185-234 | MEDIUM | ~20 debug calls, one per token |
| 11 | Three URL-resolution mechanisms | config.py:183-204 + ollama_client.py:16-28 | MEDIUM | `get_service_url` + consts + `_get_ollama_base_url` |
| 12 | `optimize_embedding_model` torch.compile | ingest.py:256-280 | MEDIUM | ✅ DONE 2026-06-24 — proven no-op (`.encode()` bypasses compiled forward); removed fn + call + `torch` import |
| 13 | `connect_to_weaviate` "deprecated" shim | ingest.py:155-158 | MEDIUM | Comment lies; it's the live path |
| 14 | Three logging config entry points | config.py + qa_loop.py:30-46 | MEDIUM | `_setup_logging`/`set_log_level`/`_setup_cli_logging` |
| 15 | `load_and_split_documents` dual path | ingest.py:86-149 | MEDIUM | file-branch & dir-branch duplicate logic |
| 16 | Duplicated PDF magic-byte validation | ingest.py:63-69 + rag_app.py:138 | MEDIUM | Two impls of the same 5-byte check |
| 17 | `SupportsEncode`/`TModel`/`runtime_checkable` | ingest.py:41-44,253 | LOW | Partial: `TModel` removed with #12 (2026-06-24); `SupportsEncode`/`runtime_checkable` still used |
| 18 | Re-sort of already-sorted results | retriever.py:122-124 | LOW | "just in case" sort on dubious key |
| 19 | Over-defensive `getattr`/`cast` on `Document` | ingest.py:179,206 | LOW | `.metadata` always exists |
| 20 | Dead comments describing non-behavior | ingest.py:224-235 | LOW | 3 comment blocks on upsert we don't do |

**Weighted total:** 2 CRITICAL (6) + 6 HIGH (12) + 8 MEDIUM (8) + 4 LOW (2) = **28**.

---

## Deep dives

### #1 — `metadata_filter` is probably broken, not just complex  (CRITICAL)
- **Broken:** `qa_loop.py:378-388` builds a Weaviate **v3 GraphQL** dict
  (`{"path": ["source"], "operator": "Equal", "valueText": ...}`). It flows to
  `retriever.py:64` → `query.filter(metadata_filter)`. The Weaviate **v4** client's
  `.filter()` expects a `_Filters` object (`Filter.by_property(...).equal(...)`),
  not a dict. Passing a dict raises or silently no-ops.
- **Untested:** the only test on this path (`test_qa_pipeline.py:45`) passes
  `metadata_filter=None`. The entire non-None branch — the feature — has zero coverage.
- **Fix:** build real `Filter` objects in the CLI and delete the dict-shape +
  And/operands nesting, OR delete the `--source`/`--language` flags. Add one test that
  actually exercises a filter. Do not ship a third state.

### #2 — torchvision stub: 145 lines to avoid an import  (CRITICAL)
- **models.py:26-170** — hand-rolled fake `torchvision` with fake `InterpolationMode`,
  fake `ImageReadMode`, fail-fast `__getattr__`, fabricated `ModuleSpec`s, introspection
  cosmetics — all to stop `transformers` pulling in `torchvision` at import time.
- **Wrong:** fighting the dependency tree from inside Python instead of at the boundary.
  7% of the codebase exists to dodge an import, and it already broke once on the
  transformers 5.x upgrade (admitted in the comment). Every transformers bump is a landmine.
- **Fix:** solve at the env boundary (we control Docker / `uv` / `--extra cpu`): pin
  `transformers` to a clean text-only version, or install a CPU-matched `torchvision`
  wheel so the import just works, or set `TRANSFORMERS_NO_TORCHVISION` and stop —
  without the 145-line fake module. The single biggest deletion available in the repo.

### #3 — `generate_response` parses an API Ollama doesn't speak  (HIGH)
- **ollama_client.py:197-215** handles `data:` SSE prefixes, `[DONE]` sentinels, and
  OpenAI-style `choices[0].text`. Ollama `/api/generate` returns newline-delimited
  `{"response": "...", "done": bool}` — none of those. The `choices`/`[DONE]` branches
  have no real callers; the unit fixture (`test_ollama_client_unit.py:52`) emits `data:`
  because it was written to match the speculative code, not real Ollama.
- **Fix:** `token = json.loads(line).get("response", "")`; check `done`. Delete the
  SSE/`[DONE]`/`choices` handling. Fix the fixture to emit real Ollama frames.

### #5 — Embedding model cached in three places  (HIGH)
- `models.py:173` global + `load_embedder()` (the real, idempotent cache);
  `retriever.py:28` its own global + `_get_embedding_model()` that re-caches the
  already-cached result and swallows errors to `None` — which only exists to feed the
  downstream `if embedding_model is not None` fallback in `get_top_k`;
  `qa_loop.answer()` threads a fourth path via params.
- **Fix:** delete `retriever._get_embedding_model` + its module global; call
  `load_embedder()` directly. One cache, one owner. Removing the `None` path also lets
  the `get_top_k` fallback branch go.

### #6 — First-run bootstrap living in the readiness check  (HIGH)
- **qa_loop.py:243-323** — `ensure_weaviate_ready_and_populated` connects, and on a
  missing collection: creates it → loads embedder → ingests `example_data/test.pdf` →
  checks objects via `next(collection.iterator())` → **deletes the data it just
  ingested**, plus a `collections.use`/`collections.get` version-fallback.
- **Wrong:** a function named `ensure_*_ready` silently doing a full ingest-and-rollback
  to "warm modules." Ingest-then-delete is a convoluted "create an empty schema."
- **Fix:** split into `ensure_ready()` (connectivity) and explicit
  `bootstrap_empty_collection()` (schema only). If warmup is genuinely needed, warm the
  model directly — don't round-trip a PDF through the vector DB to throw it away.

### #7 — Streamlit logging plumbing to show a debug panel  (HIGH)
- **rag_app.py:51-79** (`_DebugPanelHandler`), **185-226** (`_ThreadLogFilter` + StringIO
  root-handler swap), **266-284** (flip `"backend.ollama_client"` to DEBUG, attach/detach
  handler around `answer()`). ~60 lines of logging gymnastics to put text in a sidebar
  expander — and the frontend reaches into a backend logger by name (layering violation).
- **Fix:** give `answer()` an optional `on_debug: Callable[[str], None]` (or return
  structured diagnostics); the UI appends to its buffer. No handlers, filters, or
  level-flipping. Deletes the most intricate non-ML code in the app.

### #8 — `answer()` does six jobs  (HIGH)
- **qa_loop.py:118-230** — retrieval + rerank + prompt build + LLM stream + CLI console
  printing + `RAG_FAKE_ANSWER` test hook + a nested `cli_on_token` closure with
  `first_token_processed` lstrip logic. Leading-whitespace trimming appears in 3 places.
- **Fix:** extract CLI presentation (console printing, `cli_on_token`) out of the core
  pipeline; collapse the triple lstrip to one spot; move the fake-answer hook to a single
  layer (see #9).

---

## Quick, high-confidence deletions (do first — low risk)

- **#13** Delete the "Deprecated" lie on `connect_to_weaviate` (live callers:
  `rag_app.py:160`, `ingest.py:328`). Inline to `get_weaviate_client` or drop the comment.
- **#16** Two PDF magic-byte checks (`ingest._is_valid_pdf` + `rag_app` inline `PDF_MAGIC`).
  Export one, call it twice.
- **#11 / #14** Collapse URL resolution (`get_service_url` + module constants +
  `ollama_client._get_ollama_base_url`) to one resolver; collapse the three logging-config
  entry points to `get_logger` + `set_log_level`.
- **#18** Delete `retriever.py:122-124`. Hybrid results are already ranked; re-sorting on a
  maybe-present `distance` (not even the hybrid score) can only make ordering worse.
- **#19 / #20** Drop `getattr(doc, "metadata", {})`/`cast` defensiveness (LangChain
  `Document.metadata` always exists) and the three comment blocks at ingest.py:224-235
  narrating the upsert we deliberately don't implement.
- **#4** Replace `to_float_list`'s six branches with
  `np.asarray(x, dtype=float).reshape(-1).tolist()`. `SentenceTransformer.encode` returns
  ndarray by default; torch/scalar/`tolist`/iterate fallbacks are untested speculative
  generality (grep found no test references).

---

## Recommended execution order

> **SUPERSEDED — see "## Decisions & revised sequencing (2026-06-24)" at the end of this
> doc.** The order below was pass 1's; it predates the A1-kill, A2-first, and #1
> delete-not-fix decisions. Kept for provenance.

1. **#1 — fix the broken filter** (correctness; user-facing flag). Add a test.
2. **#2 — remove torchvision stub** by fixing the env boundary (biggest deletion).
3. **Cheap-deletions batch** (#13, #16, #18, #19, #20) as one low-risk cleanup commit.
4. **#3, #5, #11, #14** — delete speculative generality / collapse duplicated mechanisms.
5. **#6, #7, #8** — structural refactors (split bootstrap, simplify UI logging, decompose `answer()`).
6. **#9, #10, #12, #15, #17** — remaining mediums/lows as capacity allows.

---

## Second pass — tool-driven (python-simplifier, 2026-06-24)

Ran `python-simplifier`'s analyzers (complexity / smells / dead-code / duplicates /
coupling / over-engineering) over `backend/` + `frontend/` as a different lens than pass 1's
manual brutal-honesty read. The tool **confirmed** #2 (models.py stub: the highest internal
duplication + dead-code cluster), #3/#4/#8 (`generate_response`, `to_float_list`, `answer`).
It surfaced **4 findings absent from pass 1**, plus useful precision on existing ones.

| # | Hotspot | File:lines | Severity | Verdict |
|---|---------|-----------|----------|---------|
| 21 | `_download_model_with_progress` complexity | ollama_client.py:41-94 | **HIGH** | Cognitive complexity **42**, nesting depth **6** — the single most complex function in the repo, missed by pass 1 |
| 22 | Duplicated "ensure backend ready" block | qa_loop.py:338-345 + 414-420 | MEDIUM | `ensure_weaviate_ready_and_populated()` + `pull_if_missing` + error + `sys.exit(1)` copy-pasted verbatim in two callers |
| 23 | `answer()` 9-parameter signature | qa_loop.py:118 | MEDIUM | Distinct from #8's job-count: the *signature* is a config-object candidate (`AnswerRequest` dataclass) |
| 24 | `_setup_logging` length | config.py:19-79 | LOW | 61 lines, reinforces #14 (three logging entry points) |

**Revised weighted total:** pass-1 28 + (1 HIGH ×2) + (2 MEDIUM ×2) + (1 LOW ×1) = **35**.

### #21 — `_download_model_with_progress`: progress-bar generality  (HIGH)
- **ollama_client.py:41-94** — percent-throttle bookkeeping (`last_logged_percent`, "every 5%"),
  a 5-clause `isinstance(total/completed, (int,float))` type guard, and three fallback status
  branches (`verifying`/`writing`/`complete`). Cognitive complexity 42 / nesting 6 for a CLI
  download log. Same "handle the case that never happens" smell as #3 — Ollama's `/api/pull`
  frames are well-defined; the float-vs-int guard and percent throttle are speculative.
- **Fix:** trust the frame shape — `pct = int(data["completed"] / data["total"] * 100)` guarded
  only by `if data.get("total")`. Drop the type-isinstance ladder and the throttle (or keep a
  one-line `% 10 == 0` if log volume matters). Collapses 50 lines to ~15.

### #22 — Duplicated backend-readiness block  (MEDIUM)
- Both `_answer_once`/CLI paths (qa_loop.py:338-345, 414-420) inline the identical
  `ensure_weaviate_ready_and_populated()` → `if not pull_if_missing(OLLAMA_MODEL): logger.error(...) ; sys.exit(1)`.
- **Fix:** extract `ensure_backend_ready()` (the spinner-wrapped readiness + model-pull + exit).
  Pairs naturally with #6's `ensure_ready()`/`bootstrap_*` split.

### Tool false-positives to NOT action (recorded to prevent a bad deletion)
- `find_dead_code` flags `from __future__ import annotations` as "unused" in 5 files — it is a
  compiler directive, not a normal import. **Keep all of them.**
- The 60%-confidence "unused function" list (`generate_response`, `get_top_k`, `pull_if_missing`,
  `get_weaviate_client`, `to_float_list`, `set_log_level`, `preload_models`, `get_logger`) is
  cross-module — the analyzer only sees single-file scope. All are imported elsewhere **except**
  verify `set_log_level` / `preload_models` / `console.get_logger` against #14 (logging-entry
  collapse) before deleting. `retriever.py:23 SentenceTransformerType` unused import **is** real
  and dies with #5.

---

## Third pass — architectural (senior-architect, 2026-06-24)

Ran `senior-architect`'s project-architect + dependency-analyzer and hand-traced the internal
import graph. Goal: find *structural* complexity (layering, coupling, god-modules) that
in-module deletion can't reach.

### Headline verdict: there is NO re-architecture that buys 2x — and that's the finding
- **Coupling score 10/100 (low), 0 circular dependencies.** The internal import graph is a
  clean DAG: `config` is a leaf shared-kernel; `console`/`vector_utils`/`weaviate_client`/
  `models`/`ollama_client` each depend only on `config`; `retriever` and `ingest` sit a layer
  up; `qa_loop` is the single orchestrator; `frontend/rag_app` calls into it.
- **Implication for the 2x goal:** do NOT spend effort on layer extraction, hexagonal
  ports/adapters, or module reorg — there's no structural rot to fix. The 2x reduction is
  *entirely* in-module deletion of defensive generality, exactly what passes 1 & 2 catalogued.
  This pass's contribution is to **rule out the expensive re-architecture trap** and point at
  the two genuine structural moves below.

### A1 — Highest-impact move in the repo: route embeddings to a service boundary  (consider)
- 156 dependencies; the **entire** torch / transformers / sentence-transformers / torchvision
  chain exists for exactly two functions — `models.load_embedder()` and `models.load_reranker()`.
  Findings #2 (145-line torchvision stub), #5 (triple cache), #12 (torch.compile), #4
  (`to_float_list` ndarray-vs-torch branches), and the entire `--extra cpu`/GPU wheel split in
  `pyproject.toml`/Docker are all **tax on hosting a heavy ML dependency in-process**.
- **Architectural option:** Ollama (already a hard dependency) exposes `/api/embeddings`. Routing
  embeddings through it would delete `models.py`'s torch surface, the stub, `to_float_list`'s
  torch branch, the compile hack, and the CPU/GPU dependency bifurcation in one move — a far
  bigger complexity cut than any single code-smell. Reranking is the one piece that may still
  need a local cross-encoder; scope that separately. **Out of current scope, but this is the
  single biggest "2x" decision available — record it as an explicit ADR before doing #2/#5/#12
  piecemeal, since solving the boundary obsoletes all three.**

### A2 — `qa_loop.py` is an application-layer god-module  (structural, pairs with #6/#7/#8)
- It is simultaneously: the **orchestration** layer (`answer()` pipeline), the **CLI
  presentation** layer (console printing, `cli_on_token`, spinners, `sys.exit`), and the
  **bootstrap/readiness** layer (`ensure_weaviate_ready_and_populated`, the duplicated
  ensure-ready block #22). Three responsibilities, one module — the root cause behind #6, #8,
  #22 individually.
- **Fix (one structural move, not three patches):** split into `qa_loop` (pure orchestration:
  retrieve→rerank→prompt→stream, returns data) and a thin `cli.py` entrypoint (presentation +
  readiness + bootstrap + `sys.exit`). Doing this split *first* makes #6, #8, #9, #22 fall out
  naturally instead of being patched in place.

### A3 — `config.py` shared-kernel overload  (minor, pairs with #11/#14)
- Imported by all 9 modules; holds logging setup (3 entry points, #14), URL resolution (3
  mechanisms, #11), and all env/constant parsing. Collapsing #11+#14 also shrinks what every
  module transitively imports. Low priority — the DAG is acyclic, this is just hub weight.

### How the three passes compose
- Pass 1 (brutal-honesty): line-level "case that never happens" deletions — the bulk of the LOC.
- Pass 2 (python-simplifier): confirmed pass 1 + found the `_download_model_with_progress`
  hotspot (#21) and the dup readiness block (#22).
- Pass 3 (architecture): **sequence the work** — do the `qa_loop` split (A2) before #6/#8/#22,
  and decide the embedding-service ADR (A1) before #2/#5/#12. The rest is independent deletion.

### Per-change discipline (project rules)
- Run pre-commit + tests after each change; stop and surface logs on a persisting failure
  (max 3 attempts), stating expected vs. actual before touching test or code.
- `ruff check . --fix` + `ruff format .` + `make pyright` before commit.
- Conventional Commits on `dev`. Keep commits scoped (pathspec the index).
- Each "remove a fallback" change: `grep -rn` the symbol across `tests/**` first, and run
  `.venv/bin/python -m pytest tests/ -q` before committing (removing a `None` default
  relocates the fallback, it doesn't erase it).

---

## Decisions & revised sequencing (2026-06-24)

Resolved via a `mybrain` decision session. This section is authoritative and supersedes the
"Recommended execution order" above. An `Explore` pass verified the load-bearing facts (cited).

### D1 — A1 (route embeddings to Ollama) is KILLED
**Rationale (decisive, not preference):** A1's entire value was deleting the torch surface
(torchvision stub #2, CPU/GPU wheel split, `torch`/`torchvision`/`transformers`/
`sentence-transformers`). But the reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` is a
`CrossEncoder` (a sentence-transformers class needing local torch) and **cannot** move to
Ollama — Ollama has no cross-encoder reranking endpoint (`models.py:197-205`, used in
`qa_loop.py:172`, absent from ingest). The reranker is a hard requirement, so the **entire**
torch chain stays in-process regardless of where embeddings come from. A1 would therefore
delete *none* of its headline items while *adding*: a new Ollama embeddings code path, a second
embedding model to host, a forced full re-index (vectors are `Configure.Vectors.self_provided()`,
384-dim MiniLM, computed client-side — `weaviate_client.py:84-96`, `ingest.py:208`,
`retriever.py:102`), and retrieval-quality risk. All cost, no benefit.
**Consequence:** A1 was the upstream gate on #2/#5/#12/#4. With A1 dead, the gate is gone —
those four are ordinary in-place deletions, exactly as pass 1 planned. Do **not** write an
embedding-service ADR; do **not** defer #2/#5/#12 waiting on it.

### D2 — A2 (qa_loop god-module split) is ADOPTED, and goes FIRST among structural work
Pure internal refactor: no behavioral change, no re-index, no dependency shift. Doing the
`qa_loop` → (pure orchestration) + thin `cli.py` (presentation + readiness + bootstrap +
`sys.exit`) split **before** #6/#8/#9/#22 makes those fall out of the split instead of being
patched in place and then relocated.

### D3 — #1 (metadata filter): DELETE the flags, do not fix
Remove `--source`/`--language` from the CLI and the dict/And-operands filter plumbing
(`qa_loop.py:378-388` → `retriever.py:64`). The feature never worked (v3 dict passed to a v4
client expecting `Filter` objects) and has zero coverage. Bonus: this *removes* filter-building
code from `qa_loop`, so it does not collide with the A2 split.

### Authoritative order
1. **#1 — delete `--source`/`--language`** (resolves the only CRITICAL; pure removal).
2. **#2 — remove the torchvision stub at the env boundary** (biggest single deletion; must be
   solved in place per D1 — the reranker keeps the chain).
3. **Cheap-deletions batch** (#13, #16, #18, #19, #20, #4) — one low-risk commit.
   *Explore-confirmed #4:* `SentenceTransformer.encode` returns ndarray, so
   `np.asarray(x, dtype=float).reshape(-1).tolist()` is the correct one-liner.
4. **Speculative-generality / dup-mechanism batch** (#3, #5, #11, #14, #21).
   *Explore-confirmed #5:* the `get_top_k` None-fallback (`retriever.py:109-112`) would fail
   anyway (no Weaviate vectorizer configured), so deleting it is strictly safe.
5. **A2 split first**, then **#6, #8, #9, #22 fall out** of it. **#7** (Streamlit logging) is
   independent structural work — slot alongside.
6. **Remainder as capacity allows:** #10, #15, #17, #23, #24, A3. (**#12 shipped 2026-06-24** —
   see table; surfaced while investigating the `torch.jit.script_method` 3.14 deprecation warning,
   whose sole trigger was this dead `torch.compile` call.)

### Re-work note
Only **#5** (touches `answer()` params) edits `qa_loop` before A2 relocates that code; it is
small, so a minor relocation in A2 is accepted deliberately rather than blocking it. #1 no
longer touches `qa_loop` adversely (D3 makes it a removal).

### D4 — #2 is likely DEAD CODE, not an env-boundary fix; verify then delete outright
New finding (supersedes the three-option env-boundary plan in the deep dive): `torchvision` is
a **hard dependency in both** the default and `--extra cpu` paths (`pyproject.toml:21-22,
38-39`, deliberately ABI-matched). But the 145-line stub only activates
`if not _torchvision_available` (`models.py:32-42`) — i.e. *only when torchvision is absent*.
The in-code comment already warns the stub would "clobber a working torchvision... breaking
CrossEncoder loading." If torchvision is always installed now, the stub never executes and is
pure dead weight (vestige of a pre-direct-dep era; it "broke once on the transformers 5.x
upgrade").
**Action:** one empirical check first — confirm `import torchvision` succeeds in the CPU/Docker
app image (`--extra cpu`). If it does, **delete the entire stub block + the
`TRANSFORMERS_NO_TORCHVISION` setdefault** as dead code (no pin, no wheel surgery). If it does
*not* import cleanly in some env, fall back to the env-boundary fix for that env only.

### D5 — Scope: FULL campaign (all 24 findings + A2 + A3), multi-session
Commit to the whole catalogue, not a severity-bounded subset. Keep this as a single plan doc
(plan-hygiene: no speculative multi-stage split until ≥2 stages have shipped and a handoff is
actually needed). Drive by the authoritative order above; A3 (config shared-kernel) lands last
as it pairs with #11/#14.

### D6 — #6 warmup: INVESTIGATE before collapsing
Do not assume the ingest-then-delete "warm modules" dance is pure dead weight. Before
collapsing `ensure_weaviate_ready_and_populated` to a plain `bootstrap_empty_collection()`,
trace whether anything depends on the warmup side-effect (first-query cold-start latency). If
warmup proves load-bearing, replace the PDF round-trip with a direct model-warm call (no
vector-DB round-trip); if not, drop it entirely. Decision deferred to that investigation.

**RESOLVED 2026-06-24 (`/impag` batch-7): warmup NOT load-bearing → dropped entirely.**
Trace: (1) the ingest-then-delete block runs ONLY when the collection is missing (a fresh
DB); every subsequent run hits `exists()==True` and no-ops, yet queries work fine. (2)
`models.load_embedder()` is an idempotent in-process cache — the first real query lazy-loads
it regardless, so the one-time cold-start cost is paid during the first query whether or not
bootstrap pre-warmed it; moving it out adds ZERO steady-state latency. (3) The dance's only
durable effect was an empty schema, which `weaviate_client.ensure_collection()` already
creates directly. Fix: replaced the whole block with `ensure_collection(client, name)`;
removed the `example_data/test.pdf` resolution, `load_embedder()` warmup, iterator check,
`delete_many`, the `collections.use`/`get` version-fallback, and the now-unused `Filter`
import. The e2e test (`test_weaviate_bootstrap_missing_collection_e2e`) assertions
(collection exists + empty) are unchanged; only its docstring/comment were updated.

---

## A2 resolution — two-CLI consolidation (2026-06-24, `mybrain` deep session)

**Discovery that the A2 deep-dive missed:** A2 was written assuming `cli.py` did not exist and
would be *created* as the thin presentation layer. In reality there are **two divergent,
both-live CLI entrypoints** doing the same job:

| | root `cli.py` (`main()`) | `backend/qa_loop.py` `__main__` |
|---|---|---|
| Invoked by | `[project.scripts] kri-local-rag = "cli:main"`, `python cli.py`, `docker-compose.yml:87` mount, `tests/integration/test_cli_script_integration.py`, `tests/e2e/test_qa_real_end_to_end_container_e2e.py`, two unit tests (`test_cli_error_handling_unit`, `test_startup_model_check_unit`) | `scripts/cli.sh`, `make cli` (Makefile:141), e2e `run_cli_in_container` (`python -m backend.qa_loop`) |
| Flags | `--debug`, `--version`, `-q/--question` | `-q/-v` (repeatable), `--log-level`, `--k`, `--question` |
| UX | `Question:` prompt, `===` separators | Rich rules, spinner, `→ ` prompt |
| Test hooks | `RAG_VERBOSE_TEST` (`PHASE:` prints), `RAG_SKIP_STARTUP_CHECKS`, `PYTEST_CURRENT_TEST` auto-skip | none |

Presentation/readiness logic is **triplicated**: root `cli.py` + `qa_loop.__main__` + embedded
in `answer()`.

### Decisions (user-confirmed)
- **The user's real path is `make cli`/`scripts/cli.sh` → `python -m backend.qa_loop`.** That
  makes `qa_loop.__main__`'s surface **canonical**; root `cli.py` is vestigial (kept alive only
  by tests + packaging).
- **One door.** Collapse to a single invocation path. Survivor = **root `cli.py`** (the
  packaging-idiomatic `cli:main` console-script, already declared + docker-mounted + test-targeted).
- **`backend/qa_loop.py` → orchestration + shared readiness.** Keeps `answer()`, `build_prompt`,
  `_rerank`, `_score_chunks`, `_get_cross_encoder`, `ScoredChunk`, and
  **`ensure_weaviate_ready_and_populated`**. (CORRECTION at implementation: the log-level resolver
  did NOT stay here — it moved to `backend.config` as the public `resolve_cli_log_level()` so
  `cli.py` can resolve log level without importing heavy `qa_loop`/torch. config is already a
  module-level import in cli.py, so this is free; `test_cli_output` repoints its import.) The last
  one is **shared with the Streamlit frontend** (`frontend/rag_app.py:212`) + e2e/unit tests — so
  it is NOT CLI-only and must NOT move to `cli.py` (the A2 deep-dive's "readiness → cli.py" was
  wrong on this point). **Deletes:** the `__main__` block, the `qa_loop()` driver, argparse.
- **Root `cli.py` → single CLI entrypoint** (stays at repo root — do not create `backend/cli.py`;
  the docker-compose mount + in-container e2e test depend on the repo-root path). Absorbs the
  canonical surface (`-v/-q/--log-level` + `set_log_level(_resolve_cli_log_level(...))`,
  spinner-wrapped readiness, Rich-rules interactive banner, model preload). Keeps its
  test-pinned scaffolding (`RAG_*` hooks, `PHASE:` banners, inline fake-answer print, `Error:`
  stderr + exit-1 wrapper, `pull_if_missing`→`Required Ollama model`+exit-1). Adds
  `ensure_backend_ready()` (spinner + readiness + `pull_if_missing` + `sys.exit` — **dedup of
  #22**). **Drops** `--debug`/`--version` (untested vestigial) and the `-q`→`--question` alias.
- **Wiring → one door:** repoint `make cli`, `scripts/cli.sh`, e2e `run_cli_in_container` from
  `python -m backend.qa_loop` → `python cli.py`. `[project.scripts]` + docker mount already target
  `cli.py`.

### Conflicts resolved
- **`-q` alias collision (caught in pre-mortem):** root `cli.py` binds `-q`→`--question`;
  `qa_loop` binds `-q`→`--quiet`. Resolution: `-q/-v` become quiet/verbose (canonical);
  `--question` keeps only its long form (the `-q` alias was untested).
- **Interactive banner:** keep `qa_loop`'s **Rich rules** (the user's real UX); **update** the
  integration test's `"RAG System CLI - Interactive Mode"` assertion to match (it was
  test-scaffolding, not a contract).

### Scope boundary
This A2 work is a **behavior-preserving relocation + one-door consolidation + #22 dedup**, in
one commit. **#8** (purify `answer()`'s embedded console printing) and **#9** (collapse the
fake-answer paths — note `answer()`'s fake path streams chars with no prefix, while `cli.py`'s
inline fake prints `Answer: {fake}`, which the integration test pins) are **deferred to an
immediate follow-up** — they are behavioral surgery on the most-tested function and force test
rewrites that would muddy the structural diff. They "fall out" of A2 more safely as the next step.

### Pre-mortem mitigations baked in
- Sweep all 4 invocation surfaces (Makefile, `scripts/cli.sh`, e2e conftest, docker-compose) in
  the **same commit** as the `__main__` deletion; verify zero remaining `backend.qa_loop`
  *invocation* refs (imports of `answer`/`ensure_*` are fine).
- Confirm nothing external imports the `qa_loop()` driver before deleting it (grep showed only
  `__main__` calls it).
- Keep `cli.py` at repo root; no new top-level module → docker mount + in-container e2e unchanged.
