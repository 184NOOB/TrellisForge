---
name: PROJECT_PREFIX-trellis-review
description: Applies the task-selected light, standard, reinforced, comprehensive, or strict quality-review profile to this project's Trellis tasks. Use during planning to persist the review level and during Phase 2 or pre-commit review to choose reviewer dispatch, scope, repetition, validation, and reporting.
---

# Project Trellis Review Profiles

Read the active task's `prd.md`. For `light`, use this project Skill by
itself with applicable embedded C project Specs; do not load the bundled generic
`trellis-check` Skill. For `standard`, `reinforced`, `comprehensive`, and
`strict`, use this Skill as the profile contract for the independent
`trellis-check` agent.

```markdown
## Workflow Settings

- Review level: standard
```

Accept only `light`, `standard`, `reinforced`, `comprehensive`, or `strict`.
The latest explicit user choice wins. If missing or invalid, write and use
`standard`. Do not ask a separate question only to choose a missing level;
show the selected level in the final planning summary.

Fixed strength order: `light < standard < reinforced < comprehensive < strict`.
Never rely on numeric comparison; each profile below is defined explicitly.

## Scope Definitions

- `changed-scope`: the actual task diff, listed untracked task files, changed
  files, public headers, immediate call sites, and directly applicable fast
  checks.
- `affected-scope`: the complete task change set, affected modules, public
  headers, direct call sites, one dependency hop, every acceptance criterion,
  and the Specs and tests proven relevant by impact evidence. Do not expand to
  unrelated modules without evidence.
- `full-scope`: the complete task change set, all affected packages or
  embedded C tool layers, applicable Specs, cross-layer contracts, tests,
  installer checks, and the downstream-validation records required for release
  template changes. It still excludes repository areas with no impact
  relationship to the task; full-scope is not an indiscriminate whole-repository
  scan.

## Profile Matrix

| Level | Scope | Independent review after implementation | After a blocking-fix round | Extra commit-ready review |
|---|---|---|---|---|
| `light` | changed-scope | none; main-session review | main session reruns failed or directly affected checks | none |
| `standard` | affected-scope | exactly one | main-session verification; no repeat independent review unless evidence is invalidated | none |
| `reinforced` | affected-scope | yes | dispatch a fresh independent Check Agent; fully re-review until blocking findings are zero | none |
| `comprehensive` | full-scope | yes | dispatch a fresh independent Check Agent; fully re-review until blocking findings are zero | none; reaching zero blocking findings does not add a commit-ready review |
| `strict` | full-scope | yes; also after significant implementation batches | dispatch a fresh independent Check Agent; fully re-review until blocking findings are zero | required: one fresh independent full-scope final review on the stable commit-ready snapshot, repeating until zero blocking |

## Light

- Run one main-session review after implementation and before commit.
- Do not dispatch an independent `trellis-check` agent.
- Do not load the bundled generic `trellis-check` Skill; it contains
  cross-project Web assumptions that are not authoritative for this embedded C project.
- Read `prd.md`, acceptance criteria, `design.md` / `implement.md` when
  present, and the affected package plus shared embedded C project Specs.
- Use changed-scope: tracked diff, listed untracked task files, changed files,
  public headers, immediate call sites, and directly applicable fast checks.
- Trace each acceptance criterion to implementation or validation evidence.
- Check layering, error handling, and boundary conditions. When affected,
  explicitly check ISR boundedness, DMA buffer ownership, shared state,
  scheduler blocking, persistent-state restore order, fixed hardware
  contracts, Flash layout, and protocol compatibility.
- Run only project-defined affected fast tests, static checks, and target builds.
  Report static checks, tests, target builds, and hardware validation separately as
  pass/fail/not run/not applicable with reasons; never invent generic Web checks.
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
- Run relevant module tests, static checks, and available builds. Report checks
  not run and keep build evidence distinct from hardware validation.
- Fix clear in-scope findings directly. After fixes, the main session reruns
  affected checks; do not start another complete independent review unless the
  task scope materially changes.
- Report findings by severity, verification evidence, checks not run, and
  residual risks.

## Reinforced

- Use affected-scope exactly as defined in `Standard`.
- Run an independent review after implementation whenever the platform can
  dispatch a `trellis-check` agent.
- If the latest independent report has blocking findings, batch-fix that
  round's blocking findings first (ownership rules below), then dispatch a
  fresh independent `trellis-check` agent for the next review round. Repeat
  until the newest independent report shows zero blocking findings.
- Each re-review round re-covers the profile's complete affected-scope; it is
  not a spot-check of only the previous round's findings. A materially
  changed task diff must be reviewed as a new full round of this profile.
- Do not review per minor finding: fix one batch of blocking findings, then
  start the next round.
- No extra commit-ready review is required once the blocking-fix loop reaches
  zero.
- Report the review round number and stage as in the Report Contract.

## Comprehensive

- Use full-scope as defined in `Scope Definitions`; full-scope still requires
  impact evidence and is not an indiscriminate whole-repository scan.
- Run an independent full-scope review after implementation whenever the
  platform can dispatch a `trellis-check` agent.
- Use the same blocking-fix and independent re-review loop as `reinforced`:
  batch-fix the round's blocking findings, dispatch a fresh independent
  `trellis-check` agent, and continue until the newest independent report
  shows zero blocking findings. Each round re-covers the complete full-scope.
- After reaching zero blocking findings, entering commit preparation does NOT
  add an extra commit-ready review round. This is the fixed distinction from
  `strict`.
- Report the review round number and stage as in the Report Contract.

## Strict

- Use full-scope for every independent review round.
- Allow reviews after significant implementation batches and run the first
  independent review after implementation.
- Codex inline mode suppresses implement-agent dispatch, not review dispatch;
  use independent `trellis-check` agents whenever the platform supports them.
- Run the same blocking-fix and independent full-scope re-review loop as
  `comprehensive` until the newest independent report shows zero blocking
  findings.
- In addition to that loop, before committing dispatch one fresh independent
  full-scope final review against the stable commit-ready snapshot — code,
  tests, Specs, and task artifacts all settled. This final review is
  unconditional: it is required even when no material change happened after
  the implementation-loop review reached zero blocking findings.
- If the commit-ready final review finds blocking issues, fix them, rebuild a
  stable snapshot, and run another fresh full-scope final review until the
  final report shows zero blocking findings.
- A blocking correctness, safety, or acceptance failure cannot be waived by
  lowering the profile or accepting it as residual risk.

## Blocking-Finding Ownership

Fix ownership only answers *who fixes a finding*; it never schedules a review
round. Whether and how to re-review is decided solely by the selected profile
and the Evidence Invalidation rules below.

Route each round's findings in batches before the next review round:

1. **Verify before routing** — the main session first confirms the finding is
   real against the current snapshot and belongs to the current task. This
   ownership check is a routing judgment, not a new independent review round.
2. **Mechanical, small, and determinate issues** — an issue the current Check
   Agent may fix directly must be simultaneously local, mechanical, small,
   and determinate, inside the current task scope. The Check Agent fixes it
   in place and records both the fix and its verification in the report.
   Examples include lint nits, missing types, wrong imports, and clearly dead
   branches; examples never widen the set, and issue count or severity never
   widens it either.
3. **PRD, design, or acceptance defects** — return to Phase 1 planning and
   obtain the required approval again; they are not an Implement-Agent fix.
4. **Out-of-task-scope or environment/permission blocks** — report only; the
   main session decides whether to open a follow-up task.
5. **Other implementation blocking defects** — record location, severity,
   evidence, and why the Check Agent did not fix them, then return the finding
   to the main session. The Check Agent never dispatches or resumes an
   Implement Agent.

The main session routes non-mechanical implementation blocking defects — all
of which are report-only categories: design/judgment issues, implementation
blocking defects, planning defects, and out-of-task-scope findings — in this
order:

- **Codex inline mode**: the main session is itself the implementer and fixes
  the defect directly; it does not invent or force-dispatch an Implement Agent
  that does not exist.
- **Reliably resume the original Implement Agent first** when the host
  supports it: the current main session holds a host-confirmed handle, session
  id, or thread id for that same task and workspace, the host accepts the
  resume call, the task execution plan and audit events are still valid, and
  resuming does not break task scope, permissions, or isolation. Do not scan
  or guess foreign session identifiers, and never treat a handle as a
  crash-recovery source of truth — the task directory remains the recovery
  state.
- **Main session fixes directly** when the original Implement Agent cannot be
  reliably resumed and the fix is small with a clear boundary. Such a fix may
  need a little implementation judgment but does not require rebuilding the
  implementation context.
- **Dispatch a new Implement Agent** when the original Implement Agent cannot
  be reliably resumed and the fix is a complex implementation repair: one or
  more mutually coupled blocking problems touching cross-module, public
  interface, data-flow, or contract surfaces with a larger blast radius or
  regression risk, or a repair that needs a fuller implementation context and
  batched verification.

Finding count and severity are signals only and never decide routing by
themselves. A single high-risk finding can be complex enough to warrant a new
Implement Agent, while multiple same-root local findings may still suit a
main-session fix. When a host cannot resume, degradation to a main-session fix
or a new Implement Agent is the normal path, not a failure, and this policy
never requires new resume infrastructure.

Non-blocking findings may remain recorded as fixed items or residual risks in
the report; they never by themselves trigger another complete independent
review round, and fix ownership itself never schedules a review round.
Blocking correctness, safety, or acceptance findings are never waivable under
any profile.

## Evidence Invalidation

After a profile's review completes, if the task change set, public contracts,
acceptance criteria, or applicable Specs materially change, all existing
review evidence for those areas is invalid and the current profile's review
must run again. For `comprehensive`, such an evidence-invalidation re-review
is not the extra commit-ready gate; only `strict` additionally requires a
fresh commit-ready final review even when nothing materially changed.

## Independence And Degradation

- Every independent review round uses a freshly dispatched `trellis-check`
  agent on Claude Code and Codex paths that support sub-agent dispatch; do not
  resume a previous reviewer's session.
- When the platform cannot dispatch an independent reviewer, follow the
  existing degradation rule: run the equivalent main-session review and
  explicitly record that independence was missing.

## Report Contract

Channel, Claude, and Codex Check Agents use semantically consistent report
fields so the main session can decide whether to continue the review loop or
enter commit preparation:

- `Review level`: one of the five profiles.
- `Review scope`: `changed-scope`, `affected-scope`, or `full-scope`.
- `Review round`: round number starting at 1 within the same stage.
- `Review stage`: `implementation-loop` or `commit-ready-final`.
- `Blocking findings count`: blocking findings still open in this round.
- Findings: split fixed vs not fixed, with severity, location, and reason.
- Fixes/ownership: what was fixed and where unfixed items return (implement,
  plan, or follow-up task).
- Acceptance evidence, verification, checks not run, and residual risks.

The main session treats only the latest round's report as current evidence;
a previous round's "fixed" note is not zero-blocking evidence for now.

## Common Baseline

- Inspect the real tracked Git diff, listed untracked task files, and task artifacts.
- Never report an unrun build, test, or hardware validation as passed.
- Preserve unrelated user changes and stay inside task scope.
- Treat blocking correctness, safety, or acceptance failures as blocking under
  every profile.
- Report review level, scope, round, stage, blocking findings count, checks
  run, checks not run, findings, fixes, and residual risks.
