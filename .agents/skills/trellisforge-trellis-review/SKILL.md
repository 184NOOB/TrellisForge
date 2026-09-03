---
name: trellisforge-trellis-review
description: Applies the task-selected light, standard, or strict quality-review profile to this project's Trellis tasks. Use during planning to persist the review level and during Phase 2 or pre-commit review to choose reviewer dispatch, scope, repetition, validation, and reporting.
---

# Project Trellis Review Profiles

Read the active task's `prd.md`. For `light`, use this project Skill by
itself with applicable TrellisForge project Specs; do not load the bundled generic
`trellis-check` Skill. For `standard` and `strict`, use this Skill as the
profile contract for the independent `trellis-check` agent.

```markdown
## Workflow Settings

- Review level: standard
```

Accept only `light`, `standard`, or `strict`. The latest explicit user choice
wins. If missing or invalid, write and use `standard`. Do not ask a separate
question only to choose a missing level; show the selected level in the final
planning summary.

## Light

- Run one main-session review after implementation and before commit.
- Do not dispatch an independent `trellis-check` agent.
- Do not load the bundled generic `trellis-check` Skill; it contains
  cross-project assumptions that are not authoritative for this tooling repository.
- Read `prd.md`, acceptance criteria, `design.md` / `implement.md` when
  present, and the affected package plus shared TrellisForge Specs.
- Use changed-scope: tracked diff, listed untracked task files, changed files,
  public headers, immediate call sites, and directly applicable fast checks.
- Trace each acceptance criterion to implementation or validation evidence.
- Check layering, error handling, and boundary conditions. When affected,
  explicitly check path safety, backup/rollback behavior, placeholder replacement,
  UTF-8 handling, subprocess error propagation, and generated-file compatibility.
- Run only project-defined affected tests, static checks, and installer smoke checks.
  Report each category separately as pass/fail/not run/not applicable with reasons;
  never invent commands for unavailable product or hardware targets.
- After a fix, rerun only failed or directly affected checks; do not repeat a
  complete light review unless the task scope materially changes.
- Report the selected level, changed-scope, findings by severity, acceptance
  evidence, checks not run, and residual risks.

## Standard

- Run exactly one independent review after implementation whenever the
  platform can dispatch a `trellis-check` agent. Codex inline mode keeps
  implementation in the main session but does not suppress this review.
- Read `prd.md`, every acceptance criterion, `design.md` / `implement.md` when
  present, and the Specs listed in `check.jsonl` first. Then use the diff,
  call graph, acceptance criteria, and applicable project rules to identify
  and read every other relevant Spec. The manifest is a starting point, not
  proof that unlisted applicable Specs can be skipped.
- Use affected-scope: inspect the complete task diff, affected modules, public
  headers, direct call sites, and one dependency hop. Do not scan the entire
  repository or unrelated Spec tree without evidence that broader scope is
  affected.
- Include untracked task files from `research/task-change-manifest.md` and
  `git status --short`; `git diff` alone is not a complete change set for a
  newly initialized project. Inspect listed untracked files directly. Missing
  task ownership/baseline is blocking, and unrelated dirty files are excluded.
- Trace every acceptance criterion to implementation or validation evidence.
  Check layering, error handling, boundary conditions, and test coverage.
- Run relevant module tests, static checks, and installer smoke checks. Report checks
  not run and keep repository evidence distinct from downstream validation.
- Fix clear in-scope findings directly. After fixes, the main session reruns
  affected checks; do not start another complete independent review unless the
  task scope materially changes.
- Report findings by severity, verification evidence, checks not run, and
  residual risks.

## Strict

- Allow reviews after significant implementation batches and require a final
  review before commit.
- Codex inline mode suppresses implement-agent dispatch, not review dispatch;
  use independent `trellis-check` agents whenever the platform supports them.
- Use full-scope for the final review: complete task diff, affected packages or
  tooling layers, applicable Specs, cross-layer contracts, tests, installer checks,
  and downstream validation records when published templates change.
- Repeat the relevant review after fixes until all blocking findings are
  resolved. A blocking correctness, safety, or acceptance failure cannot be
  waived by lowering the profile or accepting it as residual risk.

## Common Baseline

- Inspect the real tracked Git diff, listed untracked task files, and task artifacts.
- Never report an unrun test, installer check, or downstream validation as passed.
- Preserve unrelated user changes and stay inside task scope.
- Treat blocking correctness, safety, or acceptance failures as blocking under
  every profile.
- Report review level, scope, checks run, checks not run, findings, fixes, and
  residual risks.
