# Plan: Replace per-run `RUN_ID` with a fixed test project name

**Date:** 2026-06-24
**Status:** Proposed
**Scope:** `scripts/dev/test-env.sh`, `scripts/dev/test.sh`, `Makefile` (comments), `.gitignore`, `.dockerignore`

## Problem

The docker test environment namespaces every run with a timestamp `RUN_ID`
(used as `COMPOSE_PROJECT_NAME`), persisted in `.run_id`. The original intent
was to let multiple isolated test stacks coexist on one host (parallel CI,
concurrent dev runs with separate DBs).

That intent is no longer served, and the machinery now costs more than it
returns:

1. **It already behaves like a single reused stack.** `test-down` preserves
   both the named volume *and* `.run_id`; `test-up` reuses the preserved id
   ("Reusing preserved RUN_ID"). The id only changes on `test-clean`. Across
   normal up/down cycles it is already a single, named, reused stack — the
   live-stack model.

2. **Fixed host ports make concurrent stacks impossible anyway.** Since
   `84d8344`, every test stack binds the same host ports (18080 / 50052 /
   21434 / 18501). Two test stacks at once collide on those ports regardless of
   project name. The one capability the unique id exists for is already blocked
   by the port scheme — the two features work against each other.

3. **CI doesn't need it.** The `integration`/`e2e` jobs each run on their own
   fresh `ubuntu-latest` VM (and are `nektos/act`-gated), so they are isolated
   by VM, not by project name.

### Cost of the current design

- A varying project name orphans the previous project (containers +
  `<id>_weaviate_db` volume) on every `clean` cycle. This is the sole reason
  `30e0abf` had to add the orphan-pruning loop in `cmd_clean`
  (`grep -E '^[0-9]+_weaviate_db$'`).
- `.run_id`, `resolve_run_id`, `write_run_id`, and the reuse branch in
  `cmd_up` all exist only to manage the mutable id.

## Proposal

Use a single fixed project name, mirroring how the live stack reuses
`kri-local-rag`:

```sh
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-kri-local-rag-test}
```

The test stack lifecycle then matches the live stack exactly (the mental model
already in use).

### Trade-off explicitly accepted

We lose the ability to run N isolated test stacks concurrently on one host.
That is already blocked by the fixed host ports, so it is not a real loss
today. If it is ever wanted back, the per-run id **and** per-run ports must
return together — note this in the script header so the coupling isn't lost.

## Changes

### 1. `scripts/dev/test-env.sh`

- Replace the `RUN_ID` resolution machinery with a single constant
  `PROJECT_NAME` (overridable via env for escape hatch).
- Delete: `RUN_ID_FILE`, `write_run_id`, `resolve_run_id`, and the
  `.run_id`-reading branches in `cmd_up` / `cmd_down` / `cmd_logs` /
  `cmd_run_integration` / `cmd_run_e2e` / `cmd_build_if_needed` / `cmd_clean`.
- `dc()` calls `PROJECT_NAME` directly (drop the per-call proj arg).
- `cmd_up`: simplify to "is it running? → message; else build-if-needed + up".
  No id minting/persisting.
- `cmd_clean`: collapses to `dc down -v` on the one known project +
  remove `.test-build.hash`. **Delete the entire orphan-pruning loop** — with a
  fixed name there is nothing to orphan.
  - One-time migration note: existing timestamp-named projects/volumes on
    developer machines won't be caught by the new `clean`. Provide a one-liner
    in the PR description (or a transitional `clean --legacy` pass) to sweep any
    leftover `^[0-9]+_weaviate_db$` projects once. Do **not** keep that logic
    permanently.
- Update the header comment to record the port↔concurrency coupling above.

### 2. `scripts/dev/test.sh`

`test.sh integration` is **already stale/broken** independent of this change:
it references `docker/compose.test.yml` (does not exist) and execs `app`
(not `app-test`) with `-p "$RUN_ID"`. The Makefile routes `test-integration`
through `test-env.sh run-integration`, not this path.

- Minimum: replace its `.run_id` read with the fixed `PROJECT_NAME`.
- Better (recommended, but confirm scope first): delete the dead
  `integration` branch and the unused `COMPOSE_TEST_FILE` var, or fix it to use
  `--profile test` + `app-test` to match `test-env.sh`. Flagged as a follow-up,
  not bundled blindly.

### 3. `Makefile`

- Update comments on `test-integration` / `test-e2e` that say "using existing
  `.run_id`". No target logic changes (they already delegate to `test-env.sh`).

### 4. `.gitignore` / `.dockerignore`

- Remove `.run_id` entries (line 96 in `.gitignore`, line 65 in
  `.dockerignore`). Keep `.test-build*` — the build-hash gating is unrelated and
  stays.

## Out of scope

- The app-test healthcheck fix (already shipped in `061c0af`).
- The build-hash gating (`.test-build.hash`) — orthogonal, keep as-is.
- Fixing vs deleting `test.sh`'s broken `integration`/`e2e` paths beyond the
  minimal `.run_id` swap — flagged as a follow-up decision.

## Verification

1. `make test-clean` (with old logic still present) to clear any timestamp
   projects, then check `docker volume ls | grep weaviate_db` and
   `docker ps -a` are clear of `^[0-9]+` projects.
2. Apply changes.
3. `make test-up` → containers come up as `kri-local-rag-test-*`; time it
   (expect ~10s, matching post-`061c0af` steady state).
4. `make test-down` → containers removed, `kri-local-rag-test_weaviate_db`
   volume preserved.
5. `make test-up` again → reuses the same project + volume (no orphan).
6. `make test-integration` → runs inside `app-test`, passes.
7. `make test-clean` → single project + volume removed; nothing orphaned.
8. Confirm the live stack (`kri-local-rag`) is untouched throughout
   (`docker compose -f docker/docker-compose.yml ps`).
9. Fresh `code-reviewer` agent over the diff before commit.

## Estimated impact

Net deletion: removes `.run_id` lifecycle (~30 lines) and the orphan-pruning
loop (~12 lines) from `test-env.sh`; the test stack becomes a fixed-name stack
identical in model to the live stack. No change to test-up wall-clock.
