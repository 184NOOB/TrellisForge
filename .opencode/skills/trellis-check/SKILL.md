---
name: trellis-check
description: "Quality verification for the current Trellis task under the project's five-level review profile. Uses the trellisforge-trellis-review Skill as the authoritative profile contract; fixes only mechanical, small, and determinate in-scope issues; reports static checks, tests, installer smoke checks, and downstream validation separately. Use when code is written and needs quality verification, before commit preparation, or to catch context drift during long sessions."
---

# Code Quality Check

Project-scoped quality verification for the active Trellis task. The
authoritative review profile (scope, independence, rounds, evidence
invalidation, report fields) is the `trellisforge-trellis-review` Skill at
`.opencode/skills/trellisforge-trellis-review/SKILL.md` — read it first and
follow it. This Skill only defines the common verification procedure.

## Step 1: Identify What Changed

```bash
git diff --name-only HEAD
git status --short
```

The complete change set includes tracked diffs, task-directory untracked files
listed by `git status --short`, and `research/task-change-manifest.md` when
present. `git diff` alone is not a complete change set.

## Step 2: Read Task Artifacts and Applicable Specs

Read the current task artifacts in order:

- `prd.md` — including its `Review level`
- `design.md` if present
- `implement.md` if present
- `check.jsonl` and every file it lists (starting point, not proof that
  unlisted applicable Specs can be skipped)

```bash
python ./.trellis/scripts/get_context.py --mode packages
```

For each changed package/layer, read the spec index and follow its **Quality
Check** section:

```bash
cat .trellis/spec/<package>/<layer>/index.md
```

Index files list the specific guideline docs to read when checking — the index
is a pointer, not the goal.

## Step 3: Select the Review Profile

Read `Review level: <level>` from `prd.md` and the dispatch prompt. Accept only
`light`, `standard`, `reinforced`, `comprehensive`, or `strict`; missing or
invalid values use `standard` and must be reported. Execute exactly one round
of the selected profile per the review Skill's Profile Matrix — do not invent
rounds, do not waive blocking findings by lowering the profile.

## Step 4: Run Project-Defined Checks Only

Run only the affected static checks, tests, and installer smoke checks explicitly
defined by the task PRD, `AGENTS.md`, or validation Specs. This tooling repository
has no generic product build or hardware-validation assumption. Report each
category separately as `pass | fail | not run | not applicable` with reasons.
Keep downstream validation distinct from executable checks and never report an
unrun test, installer check, or downstream validation as passed.

## Step 5: Review Against the Change Set

Check layering, error handling, and boundary conditions. Where affected, check
path safety, backup/rollback behavior, placeholder replacement, UTF-8 handling,
subprocess error propagation, and generated-file compatibility. Trace each
acceptance criterion to implementation or validation evidence.

Also verify the execution plan has no verification downgrade:

```bash
python ./.trellis/scripts/plan.py --task "<task path>" status
```

Renamed, dropped, or trivialized `required_checks` across plan revisions versus
the acceptance criteria in `prd.md` must be reported.

## Step 6: Handle Findings Within the Boundary

Classify each finding before writing:

- Simultaneously local, mechanical, small, determinate, and inside the current
  task scope → fix directly and record the fix plus its verification.
- Design/judgment, implementation-blocking, planning, or out-of-task-scope
  findings → report only, with location, severity, evidence, and routing
  (planning defects return to Phase 1; environment/permission blocks and
  out-of-scope findings are reported for the main session).
- Never dispatch or resume an Implement Agent, and never let fix ownership
  schedule an extra review round — review scheduling follows the selected
  profile and the evidence-invalidation rules in the review Skill.

After a fix, rerun only the affected checks. Report the full field set from the
review Skill's Report Contract and stop.
