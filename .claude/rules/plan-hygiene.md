---
paths:
  - "docs/**/*.md"
  - "**/CLAUDE.md"
  - "docs/plans/**/*.md"
  - ".claude/rules/**/*.md"
last_verified: 2026-05-18
---
# Plan / Doc Hygiene

## When to write a plan doc
- No plan doc for features ≤ 2 files changed AND ≤ 1 session of work. Commit message + code diff is the record.
- Single plan doc (not multi-stage split) for features ≥ 2 sessions or ≥ 3 files.
- Multi-stage split (one file per stage) only after ≥ 2 stages have already shipped and a handoff is actually needed. Do not split speculatively at design time.

## Plan archival
- Plans representing a single shipped session (≤ 1 day end-to-end, all commits reference the plan path or feature name): `git rm`, don't `git mv`. Git log is the audit trail; the archived md is a second copy. Archive only plans whose design rationale isn't fully captured in commit messages.

Shipped plans left in `docs/plans/` auto-load into future sessions and masquerade as active work. When a plan-survey step finds a plan fully shipped, `git mv` it into an `archive/` sibling the same session — don't just note shipped status and move on.

Before `git mv`: grep the plan path across the codebase, docs, and `CLAUDE.md` and update references to the archived location. If a sibling plan references the archived one with conditional/status language (`"Doc A pending"`, `"if X ships first"`, `"either can ship first"`), the condition has resolved — resolve sibling status notes and post-archive diff-list section headers to state the realized order concretely, not as a hypothetical.

Before `git mv`ing a design doc to `archive/`, grep §Design content against the living reference docs. Any load-bearing fact not present is merge-debt — migrate first. Walk each §section — vocabulary grep hits upstream §s but misses downstream rendering rationale. Do NOT archive plans marked "approved but not implemented" — those are still active even if dormant.

If the plan has working-tree amendments (e.g. a §0 resolution note added in the archiving session), `git add <plan>` the amendment BEFORE `git mv` — `git mv` stages the rename against HEAD content, silently dropping uncommitted working-tree edits. The archive commit then ships without the amendment and the audit-trail content is lost.

When a multi-stage split IS warranted: one file per stage under `docs/plans/`, each sized to fit a 200k-token session context. Write `<date>-<feature>-stage-A.md`, `-stage-B.md`, … plus a short `<date>-<feature>-overview.md` index if useful; cross-reference between files. Single-stage plans stay in one file (Design + Plan + Corrections sections in place). Archive rule (`git mv` to `archive/` after ship) applies per-stage file. No `-v2-` / `-enhancements-` version siblings — amend in place with a changelog entry inside the same stage file.

## Doc hygiene
Session-generated audits, analyses, and reports go in an `archived/` or `analysis/` subfolder (and should be `.claudeignore`'d) — not in the reference-doc root. The `docs/` root is for trigger-indexed reference docs listed in `CLAUDE.md`. Don't drop one-off session outputs into the reference tier.

Migration tasks (moving content out of a module/subsystem): before committing, grep the old identifier across `docs/`, `CLAUDE.md`, and `.claude/rules/`. Additive migrations leave stale prose in downstream docs the migrator never opened.

vN → vN+1 design migrations: grep both the identifier AND the *human-readable feature names* that the old design used. Identifier-level sweeps come up clean while stale wording survives in comments, docstrings, and architecture notes.

## Re-work audit scope isn't gated by "phased plan"

Any design doc that lands a long ordered step list (≥10 steps, even a single-PR rollout) has the same cross-step re-write risk as a multi-phase plan. Walk each step's concrete edits and tag which file/function each touches. If the same file appears in two sequential steps where the first's change depends on state the second removes, merge them into one per-file pass. **Trigger is "same target, two steps," not "≥3 phases."**

Test deletes go where the prod-code removal lands, not where the topic finishes — late-stage test deletes leave earlier stages pytest-broken.

## Feature-removal grep

Before finalizing a removal design, sweep `raise.*Error.*"`, `"""` docstrings, and `\.value\s*=\s*"` literals — see `~/.claude/references/pre-ship-sweeps.md` § "Grep user-facing prose when designing a feature removal".
