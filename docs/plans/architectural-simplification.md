# Architectural Simplification — Critique & Steps

**Status:** Proposed · **Branch:** `dev` · **Scope:** `backend/`, `frontend/`, `cli.py`, `docker/`, `scripts/`
**Lens:** Ousterhout (deep vs. shallow modules, information leakage) + Linus (YAGNI, no speculative generality) + brutal-honesty review.
**Method:** Four parallel subagent reviews (pipeline / clients-config / frontend-ops / test-architecture), every load-bearing claim grep-verified against the tree before inclusion. Reviewer overreaches are called out in [§Rejected](#rejected-recommendations-reviewer-overreach).

> Companion to [`complexity-cleanup.md`](complexity-cleanup.md), which is the **tactical** tier (dead code + line-level smells). Tier 1 of that doc already shipped (commit `c234e99`). This doc is the **architectural** tier: it asks not "what's dead?" but "what shape is wrong?" Where the two overlap, this doc points back rather than restating.

---

## Brutal-honesty verdict (read this first)

The backend is **1,913 LOC across 11 files** — average ~174 LOC/file, with several files under 100 (`console.py` 14, `vector_utils.py` 76, `weaviate_client.py` 100). **This codebase is not too monolithic. It is too granular.**

The dominant complexity smell is **death by a thousand small indirections**, plus **production code bent into the shape of its tests** — not under-abstraction. Concretely:

- Rename-only modules and one-line wrapper functions fragment logic that would read more clearly inline (`console.py`, `_get_ollama_base_url`, the weaviate collection wrappers).
- Test-only env vars and a `PYTEST_CURRENT_TEST` check branch the *production* hot path across three entry points.
- A second, redundant model cache and a test-only override branch live in the retriever.

**Therefore the fix direction is consolidate-and-delete, never add-a-pattern.** The instinct (visible in some of the reviewer suggestions) to introduce a `RAGPipeline` class or a `RAGContext` dataclass or split `config.py` into three modules is *the wrong direction for a codebase this size* — it trades a few small indirections for a few new ones. Ousterhout's rule is *deeper* modules, not *more* modules. Every step below removes a file, a parameter, a branch, or an env check. None adds an abstraction.

Weighted findings: **2 HIGH, 4 MEDIUM, 2 LOW** (well above the 3-finding floor).

---

## Findings (ranked by payoff × confidence)

### A — Production code shaped by tests  ·  HIGH

#### A1. Test-only env hooks branch the production hot path across 3 entry points
**Evidence (verified):**
- `RAG_FAKE_ANSWER` → `backend/qa_loop.py:138`, `frontend/rag_app.py:204`, `cli.py:50`
- `RAG_SKIP_STARTUP_CHECKS` → `frontend/rag_app.py:159,167`, `cli.py:56`
- `RAG_VERBOSE_TEST` → `cli.py:49`; **`PYTEST_CURRENT_TEST` → `cli.py:57`**

**What's broken:** A developer reading `answer()` or `cli.py:main()` cannot tell which branches are real. The worst offender is `cli.py:57` — production branching on whether pytest is running. That is a test framework leaking into shipped code.

**Why it's wrong:** Information leakage from the test layer into production. The "is this prod or test mode?" question is now load-bearing in three files for one logical feature.

**What correct looks like / how to fix — resolve *per hook*, not as a blanket delete:**
- `cli.py:57` `PYTEST_CURRENT_TEST` and `RAG_VERBOSE_TEST` (`cli.py:49`) — **remove outright.** Tests should `unittest.mock.patch` the startup/answer functions at the boundary, not signal their own presence to prod.
- `RAG_SKIP_STARTUP_CHECKS` — replace with patching `ensure_weaviate_ready_and_populated` in the relevant tests; the check exists only to make tests fast.
- `RAG_FAKE_ANSWER` in the **Streamlit** path (`rag_app.py:204`) — **decision required, do not blind-delete.** Per `complexity-cleanup.md` §2.6, the e2e harness may depend on the in-DOM `fake-mode` marker being injectable without a real backend. Confirm the e2e approach before touching the Streamlit branch; the `qa_loop.py:138` and `cli.py:50` copies are safer to drop.

**Payoff:** Removes ~20 lines of conditional noise from entry points; makes the real flow single-track. **Risk:** low for cli/qa_loop hooks, medium for the Streamlit fake-answer (e2e coupling).

#### A2. Retriever carries a second model cache + a test-only override branch
**Evidence:** `backend/retriever.py:36` (`_embedding_model` cache) and `:46-67` (`_get_embedding_model(model_name=None)`), where `:57-61` is a `SentenceTransformer(model_name)` bypass used only by tests. `backend/models.py` already owns the canonical `load_embedder()` cache.

**What's broken:** Two module-level caches for the same model, and an override parameter whose only caller is a test.

**Why it's wrong:** Shallow module exposing a wider interface (lazy-load + fallback + override) than its single production use (`retriever.py:115` calls it argument-less) justifies. Redundant state risks two divergent instances.

**Fix:** Drop the `model_name` branch and the retriever-local cache; delegate straight to `load_embedder()`. Tests that need a specific model patch `backend.retriever.load_embedder`. *(This is `complexity-cleanup.md` §2.5 — fold it in here.)*

**Payoff:** Removes one cache, one branch, one test-only code path. **Risk:** low.

---

### B — Micro-module / micro-wrapper fragmentation  ·  MEDIUM

#### B1. `console.py` is a 14-line rename-only re-export
**Evidence:** `backend/console.py` (whole file) — constructs `rich.Console()` and re-exports `config.get_logger` under a new name. Zero logic.

**What's broken:** Logging setup is split across two modules for no benefit; `from backend.console import get_logger` hides that the implementation is in `config.py`, so grepping `config.get_logger` misses callers.

**Fix:** Delete the file. Its handful of callers `from rich.console import Console` and `from backend.config import get_logger` directly. **Payoff:** one fewer module, clearer layering (Rich is presentation, not a "console concern"). **Risk:** trivial — mechanical import update.

#### B2. `_get_ollama_base_url()` duplicates `config.get_service_url` resolution
**Evidence:** `backend/ollama_client.py:16-26` re-derives the Ollama URL (including the `http://localhost:11434` fallback) although `backend/config.py:183-203` already resolved it into the `OLLAMA_URL` constant the client imports at line 10.

**What's broken:** URL/fallback policy lives in two places; a change to the default or env-var name needs edits in both.

**Fix:** Delete `_get_ollama_base_url()`; use the already-imported `OLLAMA_URL` directly. **Payoff:** removes a duplicated fallback and a confusing re-resolution layer. **Risk:** low.

#### B3. Thin Weaviate collection wrappers — flag, don't over-cut
**Evidence:** `backend/weaviate_client.py:72,81,91` — `delete_collection_if_exists` / `reset_collection` / `ensure_collection` are passthroughs-plus-logging.

**Honest take:** Borderline. `reset_collection` does sequence two operations and the logging is genuine. **Low payoff** — inlining trades a named step for a comment. Do this *only* if you're already editing the file; not worth a dedicated pass. Listed for completeness, not as a priority.

---

### C — Ad-hoc model loading, threaded by hand  ·  MEDIUM

**Evidence (verified):** embedder + reranker are loaded at three independent sites — `qa_loop.py:409-410` (CLI), `qa_loop.py:297` (one-shot inside `ensure_weaviate_ready_and_populated`), `ingest.py` — and threaded as `answer(..., embedding_model=, cross_encoder=)` params (`qa_loop.py:120-121`, passed at `:302,:416-417,:450-451`). `models.preload_models()` exists but is never called.

**What's broken:** Each entry point independently knows which models to load and how to pass them. Add a third model and every entry point breaks.

> **Correction to one reviewer:** the test-architecture pass claimed these `answer()` params are test-only injection and "production never passes them." **That is false** — production threads loaded models through them (lines above). They are legitimate dependency-passing, *not* a test shim. **Do not delete the params.**

**What correct looks like / fix — the *light* version:** introduce one small helper, e.g. `models.load_pipeline_models() -> (embedder, reranker)`, called once per entry point; keep threading the results as params. That removes the duplicated load-site knowledge without inventing a class.

**Explicitly do NOT** build a `RAGPipeline` class or a `RAGContext` dataclass (as two reviewers suggested) — that is added architecture for a 1,900-LOC core, the opposite of the verdict above. **Payoff:** medium; one source of truth for "what models the pipeline needs." **Risk:** low-medium (touches three entry points).

---

### D — Ops / deployment duplication  ·  MEDIUM (D1) / LOW (D2)

#### D1. Ollama model name is hardcoded in shell *and* in Python config
**Evidence:** `scripts/docker/docker-setup.sh` hardcodes the Ollama model (~line 69) and then carries sync-check logic against `backend/config.py`'s `OLLAMA_MODEL`.

**What's broken:** Two sources of truth for one value, plus bespoke code to detect drift between them.

**Fix:** Single source — define the model once (env/`.env`) and have both the shell script and Python read it. Delete the drift-check. **Payoff:** removes a whole class of "they diverged" bugs. **Risk:** low.

#### D2. `app-test` and `ingester` compose services duplicate `app`
**Evidence:** `docker/docker-compose.yml:104` (`app-test`, `profiles:[test]`, `command:["tail","-f","/dev/null"]`) and `:118` (`ingester`, `profiles:[ingest]`, one-shot `command`) clone `app`'s env/volumes, differing only in command/profile.

**Honest take:** Real duplication, but **partly justified** — profiles are already in use and the test container needs to stay alive. Collapsing `ingester` into `docker compose run --rm app python -m backend.ingest` is reasonable; collapsing `app-test` is more marginal. **Low priority**; bundle with any other compose edit. *(Reviewer's "shrink compose 25%" is fair; their "nine entry points" framing is not — see Rejected.)*

---

### E — `config.py` mixes five concerns  ·  LOW (flag only)

**Evidence:** `backend/config.py` holds logging setup (`:14-155`), model names, search/chunk tuning, service-URL resolution (`:183-203`), and Weaviate batch tuning in one module.

**Honest take:** It is a grab-bag, but **splitting it into `logging_config.py` + `constants.py` + core is not worth it at this size** — it trades one import everyone already knows for three, i.e. more fragmentation, which is exactly what the verdict warns against. **Flag only.** Revisit only if `config.py` crosses ~400 LOC or the logging setup genuinely needs to load without the rest. No action proposed now.

---

## Rejected recommendations (reviewer overreach)

Brutal honesty cuts both ways — these surfaced in the reviews and are **wrong or net-negative**; recording them so they don't get re-proposed:

| Rejected suggestion | Source | Why rejected (verified) |
|---|---|---|
| Delete `answer()`'s `embedding_model` / `cross_encoder` params as "test-only injection" | test-arch pass | **False premise.** Production threads loaded models through them (`qa_loop.py:302,416,450`). Deleting forces per-call reloads or hidden global state. |
| Inline `vector_utils.to_float_list` into call sites | clients pass | Contradicts the deliberate **keep** in `complexity-cleanup.md` (Out of scope): the defensive conversion is cheap and narrowing risks breaking if `encode()` returns a list. |
| Introduce `RAGPipeline` class / `RAGContext` dataclass | pipeline pass | Adds architecture to a small codebase — opposite of the verdict. Use a one-function loader (§C) instead. |
| "Nine entry points; delete `cli.py`" | frontend pass | Inflated count — Make targets are *aliases*, not entry points. `cli.py` is 168 real lines with its own arg-parsing UX. Worth noting overlap with `qa_loop` main; **not** worth deleting. |
| Split `config.py` into 3 modules | clients pass | More fragmentation, the core smell. See §E. |
| "Collapse 1,589 lines of shell to ~300" | frontend pass | Overstated. Shell total is ~2,194 lines and much is legitimate CI/release tooling (`promote_dev_to_main.sh` 409, installers). Real target is the model-name duplication (§D1), not a mass rewrite. |

---

## Sequenced steps

Each step is behavior-preserving (except the deliberate hook removals) and verified by existing tests. **After every step:** `make pre-commit` + `.venv/bin/python -m pytest tests/unit` (add `tests/integration` for C/D). Surface failures, don't paper over them. Conventional Commits on `dev`, one commit per step.

1. **B1 + B2** (pure deletes, lowest risk): remove `console.py`; remove `_get_ollama_base_url()`. → `refactor(backend): drop rename-only console module and duplicate ollama url resolver`
2. **A2** (retriever cache + override): delegate to `load_embedder()`, repoint tests to patching. → `refactor(retriever): remove redundant embed cache and test-only model override`
3. **A1** (env hooks): remove `PYTEST_CURRENT_TEST` + `RAG_VERBOSE_TEST` (`cli.py`); migrate `RAG_SKIP_STARTUP_CHECKS` and the `qa_loop`/`cli` `RAG_FAKE_ANSWER` copies to test-boundary patching. **Leave the Streamlit `RAG_FAKE_ANSWER` branch pending the e2e decision (§2.6 of the tactical doc).** → `refactor: remove test-only env hooks from cli/qa_loop hot paths`
4. **C** (model loading): add `models.load_pipeline_models()`, call from the three entry points. → `refactor(models): single loader for pipeline models`
5. **D1** (Ollama model single source) → `refactor(ops): single source of truth for ollama model name`
6. **D2 / B3 / E**: opportunistic only — fold into unrelated edits to those files; not standalone work.

## Out of scope

- Everything in `complexity-cleanup.md` §"Out of scope" (the `threading.Event` stop signal, `_ThreadLogFilter`, `vector_utils` narrowing) — those rejections still hold.
- The e2e Docker-compose fixture (`tests/e2e/conftest.py`, ~438 lines): high infra-to-test ratio but **load-bearing** for full-stack tests. Leave it; the ratio is inherent to e2e, not accidental complexity.
- New abstractions of any kind. If a step needs one to proceed, stop and reopen the design.

## Rollout

1. Steps 1–2 (lowest risk) → verify → ready to merge.
2. Step 3 only after the Streamlit `RAG_FAKE_ANSWER` e2e decision is recorded.
3. Steps 4–5 as capacity allows.
4. Archive this doc to `docs/plans/archive/` once Steps 1–4 land; reconcile with `complexity-cleanup.md` (the two should retire together).
