# Start Session

Initialize or re-orient a Trellis-managed development session on OpenCode.

The OpenCode plugins normally do this for you: the first user message of a
session receives the compact SessionStart context, every turn receives the
`<workflow-state>` breadcrumb, and shell commands receive the session's
`TRELLIS_CONTEXT_ID`. Use this command to reload that orientation manually
when hooks were disabled (`TRELLIS_DISABLE_HOOKS=1` / `TRELLIS_HOOKS=0`),
after a context compaction, or when the injected marker is missing.

---

## Step 1: Current state
Identity, git status, current task, active tasks, journal location.

```bash
python ./.trellis/scripts/get_context.py
```

If this output includes a line beginning `Trellis update available:`, copy the
full line verbatim when summarizing session context. Do not shorten
operational command hints.

## Step 2: Workflow overview
Compact Phase Index, request triage rules, planning artifact contract, and the
step-detail command.

```bash
python ./.trellis/scripts/get_context.py --mode phase
```

Full guide in `.trellis/workflow.md` (read on demand). Step detail loads with
`python ./.trellis/scripts/get_context.py --mode phase --step <X.Y> --platform opencode`.

## Step 3: Guideline indexes
Discover packages + spec layers, then read each relevant index file.

```bash
python ./.trellis/scripts/get_context.py --mode packages
cat .trellis/spec/guides/index.md
cat .trellis/spec/<package>/<layer>/index.md   # for each relevant layer
```

Index files list the specific guideline docs to read when you actually start
coding.

## Step 4: Decide next action
From Step 1 you know the current task and status. Check the task directory:

- **Active task status `planning` + no `prd.md`** → Phase 1.1. Load the
  `trellis-brainstorm` skill; user-owned decisions go through `grill-me` /
  `trellisforge-trellis-grill-adapter`.
- **Active task status `planning` + `prd.md` exists** → stay in Phase 1.
  Lightweight tasks can be PRD-only; complex tasks need `design.md` +
  `implement.md`. `prd.md` must carry a `Review level` among `light`,
  `standard`, `reinforced`, `comprehensive`, `strict` and a ready
  `## Planning Convergence` block. Load the relevant Phase 1 step detail
  before `task.py start`; `task.py start` also requires `planning_ready` and
  the user's subsequent explicit approval — never skip those gates.
- **Active task status `in_progress`** → Phase 2 step 2.1. Load the step
  detail:
  ```bash
  python ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform opencode
  ```
- **Active task status `completed`** → Phase 3 finishing steps, then the
  project `trellis-finish-work` Skill.
- **No active task** → classify first. For simple conversation / small task,
  ask only whether this turn should create a Trellis task. For complex work,
  ask whether you may create a Trellis task and enter planning. If the user
  says no, skip Trellis for this session.

---

## Skill routing (quick reference)

| User intent | Skill |
|---|---|
| New feature / unclear requirements | `trellis-brainstorm` (+ `grill-me` / `trellisforge-trellis-grill-adapter`) |
| About to write code | `trellis-before-dev` |
| Done coding / quality check | `trellis-check` under `trellisforge-trellis-review` |
| Stuck / fixed same bug multiple times | `trellis-break-loop` |
| Learned something worth capturing | `trellis-update-spec` |
| Wrap up the session | `trellis-finish-work` |

Full rules, the five review profiles, and the anti-rationalization table live
in `.trellis/workflow.md` and the project Skills — this command is only an
entry point.
