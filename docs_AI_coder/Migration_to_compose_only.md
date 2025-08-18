# Migration Plan: Testcontainers → Compose-only (Minimal, Incremental, Verifiable)

> Goal: remove Testcontainers with **small, reversible steps**, keeping tests reliable via Compose
> healthchecks, startup ordering, isolation, and diagnostics.

---

## Step 0 — Baseline & Snapshot

* **Action**:

  * Run current tests once (even if some fail) and capture logs.
  * Note which specs rely on Testcontainers vs. Compose.
* **Verify**: A short list of “TC tests” exists; you have a last-known failure/success snapshot.

---

## Step 1 — Add Healthchecks to Every Service

* **Action**: Add `healthcheck` for `weaviate`, `ollama`, and `app`. Example:

  ```yaml
  services:
    weaviate:
      image: semitechnologies/weaviate:1.32.0
      healthcheck:
        test: ["CMD-SHELL", "curl -sf http://localhost:8080/v1/.well-known/ready || exit 1"]
        interval: 5s
        timeout: 3s
        retries: 30
        start_period: 30s
  ```

  Use `depends_on: { <svc>: { condition: service_healthy } }` for any dependent service.
  **Rationale**: Compose can wait on **health** of dependencies; healthchecks define “ready.” ([Docker Documentation](https://docs.docker.com/compose/how-tos/startup-order/?utm_source=chatgpt.com))
* **Verify**: `docker compose up -d --wait --wait-timeout 120` returns success and `docker ps`
  shows services as **healthy**. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/up/?utm_source=chatgpt.com))

---

## Step 2 — Introduce a Test Overlay File

* **Action**: Create `compose.test.yml` for test-specific tweaks (pinned images, ephemeral
  volumes, fewer exposed ports). Merge with:

  ```bash
  docker compose -f compose.yml -f compose.test.yml config
  ```

  Ensure paths are correct (paths are resolved relative to the **first** `-f` file). ([Docker Documentation](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/?utm_source=chatgpt.com))
* **Verify**:

  * `docker compose -f compose.yml -f compose.test.yml config --images` lists the expected
    tags.
  * Optional: generate digests for stricter parity:
    `docker compose -f compose.yml -f compose.test.yml config --resolve-image-digests`. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/config/?utm_source=chatgpt.com))

---

## Step 3 — Add “Up/Down/Logs” Test Harness Scripts

* **Action**: Create tiny scripts (or Make targets):

  * **Up**: `docker compose -f compose.yml -f compose.test.yml -p "$RUN_ID" up -d --wait --wait-timeout 120`
  * **Down**: `docker compose -p "$RUN_ID" down -v`
  * **Logs (on failure)**: `docker compose -p "$RUN_ID" logs -n 200 app weaviate ollama`
    Use a **unique project name** (`-p`) per run to isolate networks/volumes. ([Docker Documentation](https://docs.docker.com/compose/project-name/?utm_source=chatgpt.com))
* **Verify**: Running **Up** returns only after services are healthy; **Down** removes volumes; **Logs**
  show tailed output (-n). ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/down/?utm_source=chatgpt.com))

---

## Step 4 — Convert One TC Test (The Smallest) to Compose

* **Action**:

  * Remove its Testcontainers fixture.
  * Ensure the test targets the **Compose** services (use service DNS names; avoid host ports for
    internal deps).
  * For CLI-style tests, run through the **app container**:
    `docker compose -p "$RUN_ID" exec -T app ./scripts/cli.sh …`
* **Verify**: Only that single test passes with the Compose stack up via Step 3 scripts.

---

## Step 5 — Spread Readiness & Race-proofing

* **Action**: For any test that previously had “sleep” or fragile waits, rely on:

  * `up --wait` + healthchecks (Step 1/3).
  * If a *first call* can still race (e.g., model warmup), add a tiny retry loop in the test helper.
* **Verify**: Flakes from “service not ready” disappear; first runs succeed. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/up/?utm_source=chatgpt.com))

---

## Step 6 — Batch-Convert the Remaining TC Tests

* **Action**: Move the rest of the Testcontainers specs in **small batches** (2–3 at a time):

  * Point them to the Compose services.
  * Remove per-test containers; reuse the single stack from Step 3.
* **Verify**: After each batch, run just that batch; keep failures contained and fix before moving on.

---

## Step 7 — Wire CI for Compose-only (Minimal)

* **Action**:

  * Keep **unit tests** on every PR.
  * Add a **manual/scheduled** job that runs the Compose test lane with unique `-p` names, `up --wait`,
    and `down -v`, dumping tailed logs on failure. ([Docker Documentation](https://docs.docker.com/compose/project-name/?utm_source=chatgpt.com))
* **Verify**:

  * Local `act` run is green.
  * The scheduled job is green and produces useful logs on failure.

---

## Step 8 — Remove Testcontainers Code & Dependency

* **Action**: Delete TC fixtures/helpers and the TC package from `pyproject.toml`/`requirements`.
* **Verify**: A full test run passes; repo search shows **no** TC imports left.

---

## Step 9 — Lock Parity & Document

* **Action**:

  * Pin image **tags** (or output a digest-locked overlay via `config --lock-image-digests`).
  * Add a short **README** note: use `up --wait`, healthchecks, unique `-p`, and `down -v`. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/config/?utm_source=chatgpt.com))
* **Verify**: New developers can clone → run the scripts → get green tests without extra steps.

---

## Step 10 — (Optional) Modularize Compose

* **Action**: If your stack grows, consider Compose **include** (2.20.3+) to split files cleanly, or keep
  the simple `-f` merge flow you already use. ([Docker Documentation](https://docs.docker.com/compose/multiple-compose-files/include/?utm_source=chatgpt.com))
* **Verify**: `docker compose config` shows the expected merged model; relative paths remain correct. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/config/?utm_source=chatgpt.com))

---

### Why these steps work

* **Healthchecks + `depends_on: condition: service_healthy`** express readiness, and
  **`up --wait`** blocks until services are healthy; this removes most race conditions. ([Docker Documentation](https://docs.docker.com/compose/how-tos/startup-order/?utm_source=chatgpt.com))
* **Project names (`-p`)** isolate networks/volumes per run—critical when tests run in parallel or on CI. ([Docker Documentation](https://docs.docker.com/compose/project-name/?utm_source=chatgpt.com))
* **`down -v` + tailed `logs`** give deterministic cleanup and actionable diagnostics. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/down/?utm_source=chatgpt.com))

> Keep each step tiny: convert **one** test, prove it, then proceed. This keeps risk low and momentum high.
