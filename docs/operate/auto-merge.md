# Auto-Merge for `main`

> PRs targeting `main` merge themselves once required CI checks pass — no manual "Enable auto-merge" click. This guide documents how that works and how to operate it.

## How it works

Two independent pieces combine:

1. **Gate** — branch rulesets block a PR from merging until checks pass.
2. **Arming** — a workflow turns on GitHub's auto-merge for every eligible PR, so it merges automatically the moment the gate clears.

```
PR opened/reopened/ready against main
  └─> .github/workflows/enable-automerge.yml arms auto-merge (merge commit)
        └─> GitHub holds the merge until ALL required gates are green:
              ├─ ruleset "Require CI tests on main": Lint, Pyright, Unit Tests,
              │                                       Deptry dependency health, Sec Scan
              └─ ruleset "protect Main and Dev":      CodeQL + Copilot review
        └─> all green -> GitHub merges via merge commit
```

## The pieces

### Repo setting
- **Allow auto-merge** must stay enabled (Settings → General → Pull Requests).
  Check: `gh api repos/KristjanHS/kri-local-rag --jq '.allow_auto_merge'` → `true`.

### Workflow — `.github/workflows/enable-automerge.yml`
- Trigger: `pull_request_target` on `[opened, reopened, ready_for_review]`, `branches: [main]`.
- Uses `pull_request_target` (not `pull_request`) so the **base-branch** copy of the workflow always runs — covering PRs from branches cut before it existed — and it never checks out PR code, so the write-scoped token is not exposed.
- Skips drafts (`if: !github.event.pull_request.draft`). Mark a draft **Ready for review** to arm it.
- Runs `gh pr merge --auto --merge "$PR_URL"` (merge commit, per the `dev`-is-permanent-integration convention). The PR is named explicitly via `$PR_URL` (`github.event.pull_request.html_url`) because the workflow never checks out PR code, so there is no local git context for `gh` to infer the current PR.

### Rulesets (the gate)
| Ruleset | Applies to | Enforces |
|---------|-----------|----------|
| **Require CI tests on main** | `main` only | required status checks: Lint, Pyright, Unit Tests, Deptry dependency health, Sec Scan |
| **protect Main and Dev** | `main`, `dev` | PR required (0 approvals), CodeQL code-scanning, Copilot review, no deletion / force-push |

Inspect: `gh api repos/KristjanHS/kri-local-rag/rulesets` then `…/rulesets/<id>`.

## Why only those 5 checks are required

A required status check that is **skipped** (path-filtered or excluded) on a given PR stays *pending forever* and freezes the merge. Only checks that run on **every** PR to `main` are safe to require:

- ✅ Required (no path filter): Lint, Pyright, Unit Tests, Deptry, Sec Scan.
- ❌ Not required (path-filtered — would freeze unrelated PRs): Actionlint / Yamlfmt / Hadolint (yml/Dockerfile only), uv audit / Trivy FS (dep/Docker only).
- Integration / E2E / UI tests are **excluded from GitHub CI by design** (they run locally via `act`) — never require them.

CodeQL is already gated by the `code_scanning` rule in "protect Main and Dev", so it is not duplicated in the status-check list.

## Operating notes

- **PR sits green but `BLOCKED`?** Most likely waiting on the Copilot review from "protect Main and Dev". Confirm with `gh pr checks <n>` and the PR's "merge box".
- **Add/remove a required check:** edit the "Require CI tests on main" ruleset. Only add checks that run on every PR (see above).
- **Disable auto-merge temporarily:** disable the ruleset's enforcement, or convert the PR to a draft (the workflow skips drafts) — do not rely on memory; the gate is what guarantees tests pass.
- **Manual one-off arm** (e.g. before the workflow reaches a branch): `gh pr merge <n> --auto --merge`.

## Bootstrapping a brand-new clone of this setup

The arming workflow must already exist on `main` to arm PRs into `main`. The first PR that *introduces* the workflow can't self-arm — arm it manually once (`gh pr merge <n> --auto --merge`); every PR after it self-arms.
