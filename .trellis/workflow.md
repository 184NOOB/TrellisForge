# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist everything** — research, decisions, and lessons all go to files; conversations get compacted, files don't
4. **Incremental development** — one task at a time
5. **Capture learnings** — after each task, review and write new knowledge back to spec

---

## Trellis System

### Developer Identity

On first use, initialize your identity:

```bash
python ./.trellis/scripts/init_developer.py <your-name>
```

Creates `.trellis/.developer` (gitignored) + `.trellis/workspace/<your-name>/`.

### Spec System

`.trellis/spec/` holds coding guidelines organized by package and layer.

- `.trellis/spec/<package>/<layer>/index.md` — entry point with **Pre-Development Checklist** + **Quality Check**. Actual guidelines live in the `.md` files it points to.
- `.trellis/spec/guides/index.md` — cross-package thinking guides.

```bash
python ./.trellis/scripts/get_context.py --mode packages   # list packages / layers
```

**When to update spec**: new pattern/convention found · bug-fix prevention to codify · new technical decision.

### Task System

Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and context manifests (`implement.jsonl`, `check.jsonl`) for sub-agent-capable platforms.

```bash
# Task lifecycle
python ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
python ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
python ./.trellis/scripts/task.py current --source      # show active task and source
python ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
python ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
python ./.trellis/scripts/task.py list [--mine] [--status <s>]
python ./.trellis/scripts/task.py list-archive

# Code-spec context (injected into implement/check agents via JSONL).
# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
# platforms; the AI curates real spec + research entries during planning when needed.
python ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
python ./.trellis/scripts/task.py list-context <name> [action]
python ./.trellis/scripts/task.py validate <name>

# Task metadata
python ./.trellis/scripts/task.py set-branch <name> <branch>
python ./.trellis/scripts/task.py set-base-branch <name> <branch>    # PR target
python ./.trellis/scripts/task.py set-scope <name> <scope>

# Hierarchy (parent/child)
python ./.trellis/scripts/task.py add-subtask <parent> <child>
python ./.trellis/scripts/task.py remove-subtask <parent> <child>

# PR creation
python ./.trellis/scripts/task.py create-pr [name] [--dry-run]
```

> Run `python ./.trellis/scripts/task.py --help` to see the authoritative, up-to-date list.

**Current-task mechanism**: `task.py create` creates the task directory and (when session identity is available) auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`. State is stored under `.trellis/.runtime/sessions/`. Main sessions require an exact context key from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable; without one, hooks emit `no_task` and CLI resolution reports `ambiguous` when unrelated runtime session files exist. They never borrow the sole old session file. Only a hook path that has already identified an explicit pull-based sub-agent may opt into sole-session fallback. `task.py start` can still enter its upstream degraded mode without a context key, but it cannot persist an active-task pointer for that session. `task.py finish` deletes the exact current session file (status unchanged). `task.py archive <task>` writes `status=completed`, moves the directory to `archive/`, and deletes any runtime session files that still point at the archived task.

### Workspace System

Records every AI session for cross-session tracking under `.trellis/workspace/<developer>/`.

- `journal-N.md` — session log. **Max 2000 lines per file**; a new `journal-(N+1).md` is auto-created when exceeded.
- `index.md` — personal index (total sessions, last active).

```bash
python ./.trellis/scripts/add_session.py --title "Title" --commit "hash" --summary "Summary"
```

### Context Script

```bash
python ./.trellis/scripts/get_context.py                            # full session runtime
python ./.trellis/scripts/get_context.py --mode packages            # available packages + spec layers
python ./.trellis/scripts/get_context.py --mode phase --step <X.Y>  # detailed guide for a workflow step
```

---

<!--
  WORKFLOW-STATE BREADCRUMB CONTRACT (read this before editing the tag blocks below)

  The [workflow-state:STATUS] blocks embedded in the ## Phase Index section
  below are the SINGLE source of truth for the per-turn `<workflow-state>`
  breadcrumb that the supported Claude Code and Codex hooks read.
  The project hook parsers only parse them — there is no
  fallback dict baked into the scripts after v0.5.0-rc.0.

  STATUS charset: [A-Za-z0-9_-]+. When the hook can't find a tag, it
  degrades to a generic "Refer to workflow.md for current step." line —
  intentionally visible so users notice and fix a broken workflow.md.

  INVARIANT (test/regression.test.ts):
    Every workflow-walkthrough step marked `[required · once]` must have a
    matching enforcement line in its phase's [workflow-state:*] block. The
    breadcrumb is the only per-turn channel; if a mandatory step isn't
    mentioned there, the AI silently skips it (Phase 1 planning gate
    skip and Phase 3.4 commit skip both manifested via this gap).

  TAG ↔ PHASE scoping:
    [workflow-state:no_task]      → no active task; before Phase 1
    [workflow-state:planning]     → all of Phase 1 (status='planning')
    [workflow-state:planning-inline] → Codex inline variant of Phase 1
    [workflow-state:in_progress]  → Phase 2 + Phase 3.2-3.4
                                    (status stays 'in_progress' from
                                    task.py start until task.py archive)
    [workflow-state:in_progress-inline] → Codex inline variant of Phase 2/3
    [workflow-state:completed]    → currently DEAD: cmd_archive flips
                                    status and moves the dir in the same
                                    call, so the resolver loses the
                                    pointer (block kept for a future
                                    explicit in_progress→completed
                                    transition)

  Editing checklist:
    - When you change a [workflow-state:STATUS] block, also check the
      matching phase's `[required · once]` walkthrough steps for sync
    - Run `trellis update` after editing to push the new bodies to
      downstream user projects (block-level managed replacement)
    - Full runtime contract:
      .trellis/spec/cli/backend/workflow-state-contract.md
-->

## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, run Grill Me, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify, update spec, commit, and wrap up
```

### Request Triage

- Simple conversation or small task: ask only whether this turn should create a Trellis task. If the user says no, skip Trellis for this session.
- Complex task: ask whether you may create a Trellis task and enter planning. If the user says no, do not do broad inline implementation; explain, clarify scope, or suggest a smaller split.
- User approval to create a task is not approval to start implementation. Planning still happens first.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — technical design for complex tasks: boundaries, contracts, data flow, tradeoffs, compatibility, rollout / rollback shape.
- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
- `implement.jsonl` / `check.jsonl` — spec and research manifests for sub-agent context. They do not replace `implement.md`.
- Lightweight tasks may be PRD-only. Complex tasks must have `prd.md`, `design.md`, and `implement.md` before `task.py start`.

### Parent / Child Task Trees

Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.

Use child tasks for deliverables that can be planned, implemented, checked, and archived independently. Parent/child structure is not a dependency system: if one child must wait for another, write that ordering in the child `prd.md` / `implement.md` and keep each child's acceptance criteria testable.

Create new children with `task.py create "<title>" --slug <name> --parent <parent-dir>`. Link existing tasks with `task.py add-subtask <parent> <child>`, and unlink mistakes with `task.py remove-subtask <parent> <child>`.

<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->

[workflow-state:no_task]
No active task. First classify the current turn and ask for task-creation consent before creating any Trellis task.
Simple conversation / small task: ask only whether this turn should create a Trellis task. If the user says no, skip Trellis for this session.
Complex task: ask the user if you can create a Trellis task and enter the planning phase. If the user says no, explain, clarify scope, or suggest a smaller split.
[/workflow-state:no_task]

### Phase 1: Plan
- 1.0 Create task `[required · once]` (only after task-creation consent)
- 1.1 Requirement exploration and Grill Me `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
- 1.2 Research `[optional · repeatable]`
- 1.3 Configure context `[required · once]` — Claude Code and Codex sub-agent mode only; Codex inline mode skips curation
- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
- 1.5 Completion criteria

<!-- Per-turn breadcrumb: shown throughout Phase 1 (status='planning') -->

[workflow-state:planning]
Load `trellis-brainstorm`, the upstream `grill-me`, and `trellisforge-trellis-grill-adapter`; stay in planning. First use repository evidence to separate facts, explicit user decisions, engineering decisions, and unresolved user-owned decisions. Ask one Grill question only when a user-owned product/scope/compatibility/risk/acceptance branch remains; never manufacture a question. Resolve engineering alternatives during planning and do not leave "implementation decides" branches. The project-local `task.py start` blocks unless convergence and subsequent approval markers are present.
Persist `## Workflow Settings` with `Review level: light|standard|strict` in `prd.md`; use the latest explicit user choice, otherwise default to `standard` and show it in the final planning summary. Complex tasks still need `design.md` and `implement.md`.
Persist `## Planning Convergence`; it may become `ready` only when blocking user and technical decisions are both zero and the final summary is ready. A final approval request does not count as a Grill clarification question.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; dependencies must be written in child artifacts, not implied by tree position.
Sub-agent mode: curate `implement.jsonl` and `check.jsonl` as spec/research manifests before start.
[/workflow-state:planning]

<!-- Per-turn breadcrumb: shown throughout Phase 1 when codex.dispatch_mode=inline.
     Codex-only opt-in alternate to [workflow-state:planning]. The main agent
     edits code directly in Phase 2, so jsonl curation is skipped —
     the inline workflow loads `trellis-before-dev` instead of injecting JSONL
     into a sub-agent. -->

[workflow-state:planning-inline]
Load `trellis-brainstorm`, the upstream `grill-me`, and `trellisforge-trellis-grill-adapter`; stay in planning. First use repository evidence to separate facts, explicit user decisions, engineering decisions, and unresolved user-owned decisions. Ask one Grill question only when a user-owned product/scope/compatibility/risk/acceptance branch remains; never manufacture a question. Resolve engineering alternatives during planning and do not leave "implementation decides" branches. The project-local `task.py start` blocks unless convergence and subsequent approval markers are present.
Persist `## Workflow Settings` with `Review level: light|standard|strict` in `prd.md`; use the latest explicit user choice, otherwise default to `standard` and show it in the final planning summary. Complex tasks still need `design.md` and `implement.md`.
Persist `## Planning Convergence`; it may become `ready` only when blocking user and technical decisions are both zero and the final summary is ready. A final approval request does not count as a Grill clarification question.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; dependencies must be written in child artifacts, not implied by tree position.
Inline mode: skip jsonl curation; Phase 2 reads artifacts/specs via `trellis-before-dev`. Inline keeps implementation in the main session, but `standard` and `strict` review still dispatch independent check agents when the platform supports them.
[/workflow-state:planning-inline]

### Phase 2: Execute
- 2.1 Implement `[required · repeatable]`
- 2.2 Quality check `[required · repeatable]`
- 2.3 Rollback `[on demand]`

<!-- Per-turn breadcrumb: shown while status='in_progress'.
     Scope: all of Phase 2 + Phase 3.2-3.4 (status stays 'in_progress' from
     task.py start until task.py archive; only archive flips it). The body
     therefore must cover every required step from implementation through
     commit, including Phase 3.3 spec update and Phase 3.4 commit. -->

Sub-agent dispatch protocol in this project applies only to Claude Code and Codex:
every dispatch prompt starts with `Active task: <task path from task.py current>`
before role-specific instructions. Claude uses project `.claude/agents/` and
hooks. Codex uses `.codex/agents/` and native `SubagentStart` context injection
with child-side pull fallback. Upstream examples for other platforms are outside
this template's supported scope and must not trigger extra files or dispatch work.

[workflow-state:in_progress]
Tools: `trellis-implement` / `trellis-research` are sub-agent types only (Task/Agent tool, NOT Skill; there is no skill by these names). `trellis-update-spec` and `trellisforge-trellis-review` are skills. `trellis-check` exists as both; prefer the Agent form according to the selected review level.
Flow: `trellis-implement` -> `trellisforge-trellis-review` -> light main-session review OR standard/strict `trellis-check` Agent -> `trellis-update-spec` -> commit (Phase 3.4) -> `/trellis:finish-work`.
Main-session default: dispatch the implement sub-agent. Review dispatch follows the persisted profile: light stays in the main session and does not load the bundled generic `trellis-check` Skill; standard/strict dispatch the independent `trellis-check` Agent when supported. Sub-agent self-exemption: if already running as `trellis-implement`, do NOT spawn another `trellis-implement` or `trellis-check`; if already running as `trellis-check`, do NOT spawn another `trellis-check` or `trellis-implement`. Dispatch is main session only.
Dispatch prompt starts with `Active task: <task path from task.py current>`. Read context: jsonl entries -> `prd.md` -> `design.md if present` -> `implement.md if present`.
Execution plan: the implement sub-agent creates/approves `<task>/execution-plan.json` via `plan.py` before any source edit and advances only through `plan.py start/record/done/block/revise` (two-level verification: minimal records required_checks, one terminal report phase writes final-report.md); between rounds run `python .trellis/scripts/plan.py --task "<task-path>" status` to decide re-dispatch vs 2.2. The `<execution-plan>` breadcrumb is display-only.

### Sub-agent dispatch efficiency contract

The main session must describe acceptance evidence without prescribing one tool
call per item. “逐项验收” and “每项附证据” mean that the final report lists
each result; they do not mean one `grep`, read, edit, or build per symbol,
field, or file. For equivalent checks, require one batch command or script that
prints named per-item results. Do not dispatch instructions such as “每个符号
单独 grep” or “每个字段单独执行命令”.

An implement sub-agent must batch independent reads and searches, group related
edits, validate at phase boundaries, and rerun only checks affected by a real
code fix. A comment or documentation match for a historical name is not a code
residual and must not trigger a rebuild. Once scope, acceptance evidence,
required verification, and the report are complete, the sub-agent stops; it
does not repeat an unaffected scan or build merely to confirm it again.
[/workflow-state:in_progress]

<!-- Per-turn breadcrumb: shown while status='in_progress' when
     codex.dispatch_mode=inline. Codex-only opt-in alternate to
     [workflow-state:in_progress]. The main session edits code directly
     instead of dispatching sub-agents. -->

[workflow-state:in_progress-inline]
Flow: `trellis-before-dev` -> edit -> `trellisforge-trellis-review` + profiled review -> validation -> `trellis-update-spec` -> commit (Phase 3.4) -> `/trellis:finish-work`.
Inline mode keeps implementation in the main session. For review, `light` is a main-session changed-scope review; `standard` dispatches one independent affected-scope `trellis-check` agent when supported; `strict` dispatches independent full-scope reviews when supported and repeats until blocking findings are resolved.
Read context: `prd.md` -> `design.md if present` -> `implement.md if present`, plus relevant spec/research loaded by skills.
Execution plan (same gate, main session as executor): write `<task>/execution-plan.json` first, `plan.py validate` before touching business source, then advance exclusively via `plan.py start/record/done/block/revise` per phase.
[/workflow-state:in_progress-inline]

### Phase 3: Finish
- 3.2 Debug retrospective `[on demand]`
- 3.3 Spec update `[required · once]`
- 3.4 Commit changes `[required · once]`
- 3.5 Wrap-up reminder

> Note: step 3.1 was folded into 2.2 (last-iteration full-scope check) and 3.4 (commit preamble). Numbering kept stable to avoid breaking external references.

<!-- Per-turn breadcrumb: shown while status='completed'.
     Currently DEAD in normal flow: cmd_archive writes status='completed' in
     the same call that moves the task dir to archive/, so the active-task
     resolver loses the pointer and the hook never fires on archived tasks.
     Block preserved for a future status-transition redesign (e.g. an
     explicit in_progress→completed command). Edit through the same spec
     channel as the live blocks. -->

[workflow-state:completed]
Code committed. Run `/trellis:finish-work`; if dirty, return to Phase 3.4 first.
[/workflow-state:completed]

### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run steps in order inside each Phase; `[required]` steps can't be skipped
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing `design.md` / `implement.md` is valid for lightweight tasks and incomplete planning for complex tasks.

### Active Task Routing

When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.

[Claude Code]

- Planning -> `trellis-brainstorm` + mandatory upstream `grill-me` + `trellisforge-trellis-grill-adapter`.
- `in_progress` implementation -> dispatch `trellis-implement`; review ->
  load `trellisforge-trellis-review`, keep `light` in the main session, and
  dispatch `trellis-check` only for `standard` / `strict`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Claude Code]

[Codex]

- Planning -> `trellis-brainstorm` + mandatory upstream `grill-me` + `trellisforge-trellis-grill-adapter`.
- Before editing -> `trellis-before-dev`; after editing -> load
  `trellisforge-trellis-review`. For `light`, review in the main session without
  the bundled `trellis-check` Skill; for `standard` / `strict`, dispatch
  the independent `trellis-check` agent when supported.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Codex]

### Guardrails

- Task creation approval is not implementation approval; implementation waits for `task.py start` after artifact review.
- PRD-only is valid for lightweight tasks; complex tasks need `design.md` + `implement.md`.
- Planning must be persisted to task artifacts; checks must run before reporting completion.
- Every Trellis task in `planning` or `planning-inline` must complete the upstream `grill-me` protocol with `trellisforge-trellis-grill-adapter`; task size and risk do not create an exemption.
- Every task `prd.md` must include `## Workflow Settings` with `Review level: light|standard|strict`; missing or invalid values default to `standard`.
- Phase 2 source edits require an approved `<task>/execution-plan.json`; task state advances only through `plan.py` with its audit log intact — hand-edited statuses, verification result maps, revisions, or guarded plan content are rejected against the audit replay, and no hook is load-bearing for that enforcement.

### Loading Step Detail

At each step, run this to fetch detailed guidance:

```bash
python ./.trellis/scripts/get_context.py --mode phase --step <step>
# e.g. python ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---

## Phase 1: Plan

Goal: classify the request, get task-creation consent when a task is needed, and produce the planning artifacts required before implementation.

#### 1.0 Create task `[required · once]`

Create the task directory only after task-creation consent. The command sets status to `planning`, writes `task.json`, creates a default `prd.md`, and auto-targets the new task when session identity is available:

```bash
python ./.trellis/scripts/task.py create "<task title>" --slug <name>
```

`--slug` is the human-readable name only. Do **not** include the `MM-DD-` date prefix; `task.py create` adds that prefix automatically.

For task trees, create the parent task first and then create each child with `--parent <parent-dir>`. Do not start the parent just because children exist; start the child that owns the next independently verifiable deliverable.

Every new development session must bind exactly one planning task to its own
session before continuing planning. Run `task.py current --source` and accept
only an exact `session:<current-context>` source; a main session must treat
`session-fallback:*` as foreign state and must not preserve, inspect, or plan
against that task as its own.

For a multi-task tree, create the parent and deferred siblings with
`--no-start`, but create the one next-actionable child without `--no-start` so
`task.py create` writes this session's planning pointer. Afterwards, verify
that `task.py current --source` names that child with a `session:*` source.
Never put `--no-start` on every task in the new session, and never use
`task.py start` merely to select a planning task because `start` changes its
status to `in_progress` before planning approval.

After this command succeeds, the per-turn breadcrumb auto-switches to `[workflow-state:planning]`, telling the AI to stay in planning.

Run only `create` here — do not also run `start`. `start` flips status to `in_progress`, which switches the breadcrumb to the implementation phase before planning artifacts are reviewed. Save `start` for step 1.4.

Skip when `python ./.trellis/scripts/task.py current --source` already points to a task.

#### 1.1 Requirement exploration and Grill Me `[required · repeatable]`

Load `trellis-brainstorm`, the upstream `grill-me`, and `trellisforge-trellis-grill-adapter`. `trellis-brainstorm` owns evidence inspection, decision ownership, artifact convergence, and the rule against manufactured questions. `grill-me` supplies the one-question-at-a-time interview format for unresolved user-owned branches. The adapter persists convergence and approval markers. The project-local `task.py start` verifies those markers before changing task state.

The brainstorm skill will guide you to:
- Ask one question at a time
- Prefer researching over asking the user
- Prefer offering options over open-ended questions
- Update `prd.md` immediately after each user answer
- Split large scopes into a parent task plus child tasks when the deliverables can be verified independently
- Keep `prd.md` focused on requirements and acceptance criteria
- For complex tasks, produce `design.md` and `implement.md` before implementation starts

The combined protocol applies to every Trellis task, including lightweight and inline tasks. Recompute this inventory before each question and before final review:

- repository-confirmed facts
- explicit user decisions already present in the request or later answers
- engineering decisions resolved from evidence, project constraints, and safe reversible defaults
- unresolved user-owned product, scope, compatibility, risk-tolerance, or acceptance decisions

Ask exactly one highest-value Grill question only when the last group is non-empty. Do not ask the user to reconfirm facts or explicit decisions, and do not force a question when the inventory is already resolved. Conversely, do not carry an engineering alternative into implementation as "A or B", "recommended", or "decide during implementation"; research and select it during planning, or reclassify it as user-owned and ask.

Before the final summary, persist this exact convergence block in `prd.md`:

```markdown
## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
```

Use `pending` / non-zero values until the plan actually converges. Then set `planning_ready=true` in task metadata, present the latest summary, and stop. A subsequent explicit user approval is still required before setting `plan_approved=true` and running `task.py start`.

Persist review settings in every `prd.md`:

```markdown
## Workflow Settings

- Review level: standard
```

If the user explicitly specifies `light`, `standard`, or `strict`, write that exact latest choice. If missing or invalid, use `standard` without asking a separate question only for review level selection; show the selected level in the final planning summary.

When considering a parent/child split:
- Use a parent task when one request contains several independently verifiable deliverables.
- Parent tasks own source requirements, child-task mapping, cross-child acceptance criteria, and final integration review.
- Child tasks own actual deliverables that can be planned, implemented, checked, and archived independently.
- Parent/child structure is not a dependency system. If child B depends on child A, write that ordering in child B's `prd.md` / `implement.md`.
- Start the child task that owns the next deliverable. Do not start the parent unless the parent itself has direct implementation work.

Return to this step whenever requirements change and revise the relevant artifact.

#### 1.2 Research `[optional · repeatable]`

Research can happen at any time during requirement exploration. It isn't limited to local code — you can use any available tool (MCP servers, skills, web search, etc.) to look up external information, including third-party library docs, industry practices, API references, etc.

[Claude Code, codex-sub-agent]

Spawn the research sub-agent:

- **Agent type**: `trellis-research`
- **Task description**: Research <specific question>
- **Key requirement**: Research output MUST be persisted to `{TASK_DIR}/research/`

[/Claude Code, codex-sub-agent]

[codex-inline]

Do the research in the main session directly and write findings into `{TASK_DIR}/research/`. `codex-inline` is the explicit mode that keeps work in the main session.

[/codex-inline]

**Research artifact conventions**:
- One file per research topic (e.g. `research/auth-library-comparison.md`)
- Record third-party library usage examples, API references, version constraints in files
- Note relevant spec file paths you discovered for later reference

Brainstorm and research can interleave freely — pause to research a technical question, then return to talk with the user.

**Key principle**: Research output must be written to files, not left only in the chat. Conversations get compacted; files don't.

#### 1.3 Configure context `[required · once]`

[Claude Code, codex-sub-agent]

Curate `implement.jsonl` and `check.jsonl` so the Phase 2 sub-agents get the right spec/research context. These files were seeded on `task create` with a single self-describing `_example` line; your job here is to fill in real entries.

**Location**: `{TASK_DIR}/implement.jsonl` and `{TASK_DIR}/check.jsonl` (already exist).

**Format**: one JSON object per line — `{"file": "<path>", "reason": "<why>"}`. Paths are repo-root relative.

**What to put in**:
- **Spec files** — `.trellis/spec/<package>/<layer>/index.md` and any specific guideline files (`error-handling.md`, `conventions.md`, etc.) relevant to this task
- **Research files** — `{TASK_DIR}/research/*.md` that the sub-agent will need to consult

**What NOT to put in**:
- Code files (`src/**`, `packages/**/*.ts`, etc.) — those are read by the sub-agent during implementation, not pre-registered here
- Files you're about to modify — same reason

**Split between the two files**:
- `implement.jsonl` → specs + research the implement sub-agent needs to write code correctly
- `check.jsonl` → specs for the check sub-agent (quality guidelines, check conventions, same research if needed)

These manifests do not replace `implement.md`. `implement.md` is the human-readable execution plan for a complex task; jsonl files only list context files to inject or load.

**How to discover relevant specs**:

```bash
python ./.trellis/scripts/get_context.py --mode packages
```

Lists every package + its spec layers with paths. Pick the entries that match this task's domain.

**How to append entries**:

Either edit the jsonl file directly in your editor, or use:

```bash
python ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

Delete the seed `_example` line once real entries exist (optional — it's skipped automatically by consumers).

Ready gate: both `implement.jsonl` and `check.jsonl` must contain at least one real `{"file": "...", "reason": "..."}` entry before `task.py start`. The seed `_example` row alone is not ready.

Skip this step only when both files already have real curated entries.

[/Claude Code, codex-sub-agent]

[codex-inline]

Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.

[/codex-inline]

#### 1.4 Activate task `[required · once]`

After artifact convergence, mark the task ready before presenting the final planning summary:

```bash
python ./.trellis/scripts/task.py set-meta <task-dir> planning_ready true
```

After the user subsequently approves that exact summary, record approval and flip the task status to `in_progress`:

```bash
python ./.trellis/scripts/task.py set-meta <task-dir> plan_approved true
python ./.trellis/scripts/task.py start <task-dir>
```

For lightweight tasks, `prd.md` can be enough. For complex tasks, `prd.md`, `design.md`, and `implement.md` must exist and be reviewed before start. On sub-agent-dispatch platforms, `implement.jsonl` and `check.jsonl` must both have real curated entries before start. Runtime consumers tolerate missing or seed-only manifests for compatibility, but that tolerance is not a planning-ready state.

`task.py start` rejects planning tasks unless `prd.md` contains a valid review level and a ready `## Planning Convergence` block, and task metadata contains both `planning_ready=true` and `plan_approved=true`. Rejection happens before active-task or status mutation. After the command succeeds, the breadcrumb auto-switches to `[workflow-state:in_progress]`, and the rest of Phase 2 / 3 follows.

If `task.py start` errors with a session-identity message (no context key from hook input, `TRELLIS_CONTEXT_ID`, or platform-native session env), follow the hint in the error to set up session identity, then retry.

#### 1.5 Completion criteria

| Condition | Required |
|------|:---:|
| `prd.md` exists | ✅ |
| Evidence/decision inventory converged; Grill questions asked only where user-owned decisions remained | ✅ |
| `prd.md` contains `## Workflow Settings` and `Review level` | ✅ |
| `prd.md` contains a ready `## Planning Convergence` block | ✅ |
| Task metadata contains `planning_ready=true` | ✅ |
| User confirms task should enter implementation | ✅ |
| Task metadata contains `plan_approved=true` after that confirmation | ✅ |
| `task.py start` has been run (status = in_progress) | ✅ |
| `research/` has artifacts (complex tasks) | recommended |
| `design.md` exists (complex tasks) | ✅ |
| `implement.md` exists (complex tasks) | ✅ |

[Claude Code, codex-sub-agent]

| `implement.jsonl` and `check.jsonl` each contain at least one real curated entry (seed row does not count) | ✅ |

[/Claude Code, codex-sub-agent]

---

## Phase 2: Execute

Goal: turn reviewed planning artifacts into code that passes quality checks.

**Execution plan gate (applies to every Phase 2 mode: sub-agent dispatch and inline)**

Implementation progress is driven by the execution plan in the active task directory, advanced through `.trellis/scripts/plan.py`:

- `<task-path>/execution-plan.json` (schema 3) holds the model-authored plan and current state; `<task-path>/execution-events.jsonl` is the append-only audit log. Both files live inside the task directory. `<task-path>/final-report.md` is written only by the single `report` phase.
- Round 1: the implementer reads PRD/Spec/code and writes the plan first (`python .trellis/scripts/plan.py --task "<task-path>" template` prints the skeleton; ≤ 8 phase-level tasks with `depends_on`, `scope.read`/`scope.write`, and `verification` `{level, required_checks[, report_path]}`). Business source code stays untouched until `plan.py validate` approves the plan.
- Verification is two-level only: `minimal` (normal phases) records each declared `required_checks` result with exit code and a short summary — no phase Markdown, no mandatory raw logs; `report` (at most one, terminal, and transitively depending on every other phase) additionally writes `final-report.md` and registers it via `record --artifact final-report.md` before `done`. There is no `risk` field, no `raw` level, and no `required_evidence`.
- `required_checks` cannot be bypassed by an empty list: only a pure read-only/analysis phase (empty `scope.write`) may declare none, and then it must state a non-empty `no_check_reason`. Any file-modifying/build/test phase needs ≥ 1 declared check, and `done` refuses missing or non-pass records. A recorded `fail` is permanent for the revision. Check ids are declarative, so `plan.py` can only verify presence/pass — the 2.2 review must additionally re-check the declared check list itself against `prd.md` acceptance criteria: renaming, dropping, or trivializing a declared check between revisions is a verification downgrade that only the independent review catches.
- State advances only through `plan.py` (`start` / `record` / `done` / `block` / `revise`). Hand-edited task statuses, revisions, verification result maps, guarded task content, and completed-task history are rejected — statuses and managed maps are cross-checked against the audit replay. Consistent forgery of the plan JSON and the audit log together is outside this mechanism's defense envelope; the independent 2.2 review remains the real verification.
- `plan.py record <id> --check <declared-check-id> --result pass|fail --command <command-id> --exit-code <number> --summary "<short text>" [--artifact <task-relative-path>]` is the implementer's attestation of a check it actually ran (plan.py never executes builds or tests); `--artifact` is an optional task-directory-local reference, never required for `minimal`. Independent verification belongs to the 2.2 quality-check review, which must rerun or otherwise confirm the declared checks. A failed phase is audited through `plan.py block <id> --reason "..."` — there is no separate `task_failed` event; `blocked` + reason + `plan_revised` history carry failure semantics.
- The phase loop is batch-shaped: `start` → batch read / batch edit / batch check → `record` every declared check → `done`. Hooks are display-only aids: the UserPromptSubmit hook shows an `<execution-plan>` breadcrumb, the sub-agent injection hooks carry the protocol + current state, and the PreToolUse edit counter only warns (it never feeds `done`). The CLI flow must work completely with every hook disabled or unavailable (Codex `SubagentStart` has no PreToolUse equivalent).
- Between implement rounds the main session runs `plan.py --task "<task-path>" status`: runnable tasks → re-dispatch (or continue inline); all completed → 2.2 quality check; `blocked` or `plan_revised` history → review the reason before proceeding.
- Crash recovery depends on task-directory files only: re-read `execution-plan.json`, resume the `in_progress` phase (its recorded checks are already in the plan) or the first dependency-ready `pending` phase. Session ids, hooks, and sidechain/bg state must never be load-bearing.
- When a damaged `execution-events.jsonl` is reported, fix the audit log before any further state change; never bypass `plan.py`.

#### 2.1 Implement `[required · repeatable]`

[Claude Code, codex-sub-agent]

Spawn the implement sub-agent:

- **Agent type**: `trellis-implement`
- **Task description**: Implement the reviewed task artifacts, consulting materials under `{TASK_DIR}/research/`; finish by running applicable project checks/builds; report unavailable or inapplicable checks in the final message (plan.py record only accepts pass|fail — a declared check that cannot run goes through block/revise, never a false pass). The task-content portion should contain only the objective, affected scope, explicit non-goals, acceptance conditions already in task artifacts, and validation commands already defined by the task or project; do not paste full PRD, Spec, research, checklist, or diff bodies.
- **Dispatch prompt guard**: The prompt MUST start with `Active task: <task path>`, then tell the spawned agent it is already the `trellis-implement` sub-agent and must implement directly, not spawn another `trellis-implement` / `trellis-check`. Preserve these role and lifecycle instructions in addition to the task-content boundary.

The platform hook/plugin auto-handles:
- Reads `implement.jsonl` and injects referenced spec/research files into the agent prompt
- Injects `prd.md`, `design.md` if present, and `implement.md` if present
- For Codex, `SubagentStart` supplies native context injection; the agent profile keeps child-side loading as the fallback
- Injects the execution-plan protocol block and the current plan state (round-1 plan creation or the live task loop from the plan gate above)

[/Claude Code, codex-sub-agent]

[codex-inline]

1. Load the `trellis-before-dev` skill to read project guidelines
2. Read `{TASK_DIR}/prd.md`, then `design.md` if present, then `implement.md` if present
3. Consult materials under `{TASK_DIR}/research/`
4. Implement the code per reviewed artifacts
5. Run only project-defined affected static checks, tests, and installer smoke checks; report unavailable or inapplicable categories in the final message instead of inventing commands or recording false passes

[/codex-inline]

#### 2.2 Quality check `[required · repeatable]`

Load `trellisforge-trellis-review` before choosing the review route. Read `prd.md`
and accept only `light`, `standard`, or `strict`; if missing or invalid, write
and use `standard`.

[Claude Code, codex-sub-agent]

Apply the selected profile:

- `light`: do not dispatch an independent `trellis-check` agent. Run one
  main-session changed-scope review over the actual diff, changed files,
  immediate call sites, acceptance criteria, and directly applicable fast
  checks. Use only `trellisforge-trellis-review` plus applicable task artifacts
  and TrellisForge Specs; do not load the bundled generic `trellis-check` Skill.
- `standard`: dispatch exactly one independent affected-scope `trellis-check`
  agent when the platform supports it. The task-content portion of the
  dispatch prompt must contain only: task path and role, task-specific
  objective, affected scope and explicit non-goals, acceptance criteria
  already present in task artifacts, and validation commands already defined
  by the task or project.
  Do not paste PRD, spec, research, checklist, or diff contents into the
  prompt. Do not add requirements that cannot be traced to user instructions
  or task artifacts; the Trellis hook supplies available context, and the
  agent may supplement it when content is missing or needs precise checking.
  The prompt must include a stop condition: after the declared scope,
  acceptance evidence, verification, and report are complete, stop unless new
  evidence expands the scope. For untracked initialization work, name
  `research/task-change-manifest.md` and require direct inspection of its
  listed files; do not paste their contents into the prompt.
- `strict`: dispatch independent full-scope `trellis-check` agents after
  significant implementation batches when useful and always before commit.
  Repeat relevant review after fixes until blocking correctness, safety, and
  acceptance findings are resolved.

When dispatching the check sub-agent:

- **Agent type**: `trellis-check`
- **Task description**: Review code changes against specs, task artifacts, and the selected `trellisforge-trellis-review` profile; fix clear in-scope findings directly; ensure applicable validation is run or explicitly reported as unavailable
- **Dispatch prompt guard**: The prompt MUST start with `Active task: <task path>`, then tell the spawned agent it is already the `trellis-check` sub-agent and must review/fix directly, not spawn another `trellis-check` / `trellis-implement`.

The check agent's job:
- Review code changes against specs
- Review code changes against `prd.md`, `design.md` if present, and `implement.md` if present
- Auto-fix issues it finds
- Run applicable configured checks and builds; report static checks, tests,
  installer smoke checks and downstream validation separately as pass/fail/not run/not applicable
  with reasons, and never invent generic checks for the project type

[/Claude Code, codex-sub-agent]

[codex-inline]

Apply the selected profile:

- `light`: run one main-session changed-scope review using
  `trellisforge-trellis-review`, task artifacts, and applicable TrellisForge project
  Specs. Do not load the bundled generic `trellis-check` Skill.
- `standard`: Codex inline keeps implementation in the main session but still dispatches one independent affected-scope `trellis-check` agent when supported. Platforms that cannot dispatch a reviewer must explicitly record a main-session equivalent review.
- `strict`: dispatch independent full-scope check agents when supported and repeat relevant review after fixes until blocking findings are resolved. Platforms that cannot dispatch a reviewer must explicitly record a main-session equivalent review.

All profiles check spec compliance, acceptance evidence, validation, and cross-layer consistency when changes span layers.

If issues are found → fix → re-check, until green.

[/codex-inline]

**Final pass (before Phase 3.4 commit)**: use the selected profile from `trellisforge-trellis-review`: `light` = changed-scope main-session review, `standard` = one independent affected-scope review when supported, `strict` = full-scope review with repeats until blocking findings are resolved. Derive affected packages from the actual diff, task manifest, and direct call graph; load only package/spec indexes supported by that evidence. Do not enumerate unrelated packages without evidence of impact.

#### 2.3 Rollback `[on demand]`

- `check` reveals a prd defect → return to Phase 1, fix `prd.md`, then redo 2.1
- Implementation went wrong → revert code, redo 2.1
- Need more research → research (same as Phase 1.2), write findings into `research/`

---

## Phase 3: Finish

Goal: ensure code quality, capture lessons, record the work.

#### 3.2 Debug retrospective `[on demand]`

If this task involved repeated debugging (the same issue was fixed multiple times), load the `trellis-break-loop` skill to:
- Classify the root cause
- Explain why earlier fixes failed
- Propose prevention

The goal is to capture debugging lessons so the same class of issue doesn't recur.

#### 3.3 Spec update `[required · once]`

Load the `trellis-update-spec` skill and review whether this task produced new knowledge worth recording:
- Newly discovered patterns or conventions
- Pitfalls you hit
- New technical decisions

Update the docs under `.trellis/spec/` accordingly. Even if the conclusion is "nothing to update", walk through the judgment.

#### 3.4 Commit changes `[required · once]`

**Spec-sync preamble**: before drafting commits, ask: did this task fix a bug or surface non-obvious knowledge that should land in `.trellis/spec/` so future-you (or future-AI) doesn't repeat the mistake? If yes, return to Phase 3.3 first — spec writes belong in the same task's commit batch, not as a forgotten follow-up.

**Review-profile preamble**: before drafting commits, confirm the selected `trellisforge-trellis-review` profile from `prd.md` has completed: `light` changed-scope main-session review, `standard` one independent affected-scope review when supported, or `strict` final full-scope review with repeats until blocking findings are resolved. Do not commit while the required profile is incomplete.

The AI may drive a batched commit of this task's code changes only after the user explicitly approves the proposed commit plan. This project keeps `session_auto_commit: false`: `/finish-work`, `task.py archive`, and `add_session.py` update bookkeeping files but do not create Git commits. Work commits happen first; after finish-work, any archive/journal changes require a separate commit plan and fresh user approval.

**Step-by-step**:

1. **Inspect dirty state**:
   ```bash
   git status --porcelain
   ```
   Snapshot every dirty path. If the working tree is clean, skip to 3.5.

2. **Learn commit style** from recent history (so drafted messages blend in):
   ```bash
   git log --oneline -5
   ```
   Note the prefix convention (`feat:` / `fix:` / `chore:` / `docs:` ...), language (中文/English), and length style.

3. **Classify dirty files into two groups**:
   - **AI-edited this session** — files you wrote/edited via Edit/Write/Bash tool calls in this session. You know what changed and why.
   - **Unrecognized** — dirty files you did NOT touch this session (could be the user's manual edits, leftover WIP from a previous session, or unrelated work). Do NOT silently include these.

4. **Draft a commit plan**. Group AI-edited files into logical commits (1 commit per coherent change unit, not 1 commit per file). Each entry: `<commit message>` + file list. List unrecognized files separately at the bottom.

5. **Present the plan once, ask for one-shot confirmation**. Format:
   ```
   Proposed commits (in order):
     1. <message>
        - <file>
        - <file>
     2. <message>
        - <file>

   Unrecognized dirty files (NOT in any commit — confirm include/exclude):
     - <file>
     - <file>

   Reply 'ok' / '行' to execute. Reply with edits, or '我自己来' / 'manual' to abort.
   ```

6. **On confirmation**: run `git add <files>` + `git commit -m "<msg>"` for each batch in order. Do not amend. Do not push.

7. **On rejection** (user replies "不行" / "我自己来" / "manual" / any pushback on the plan): stop. Do not attempt a second plan. The user will commit by hand; you skip ahead to 3.5 once they confirm.

**Rules**:
- No `git commit --amend` anywhere. With `session_auto_commit: false`, neither archive nor journal work is an implicit commit; propose their dirty files separately after finish-work and wait for explicit user approval.
- Never push to remote in this step.
- If the user wants different message wording but accepts the file grouping, edit the message and re-confirm once — but if they reject the grouping, exit to manual mode.
- The batched plan is one prompt; do not prompt per commit.

#### 3.5 Wrap-up reminder

After the above, remind the user they can run `/finish-work` to archive the task and record the session. Then inspect the resulting bookkeeping diff and, if the user wants it committed, present a separate commit plan; do not treat finish-work itself as commit authorization.

---

## Customizing Trellis (for forks)

This section is for developers who want to modify the Trellis workflow itself. All customization is done by editing this file; the scripts are parsers only.

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase 1 / 2 / 3 sections above. Critical invariants:
- No active task must triage first and ask for task-creation consent before creating a Trellis task.
- Planning must distinguish lightweight PRD-only tasks from complex tasks that require `prd.md`, `design.md`, and `implement.md` before start.
- Every required execution path must keep the Phase 3.4 commit reminder reachable before `/trellis:finish-work`.

All tag blocks live in the `## Phase Index` section above, immediately after each phase summary:

| Scope | Corresponding tag |
|---|---|
| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |
| All of Phase 1 (task created → ready for implementation) | `[workflow-state:planning]` (after Phase 1 summary) |
| Codex inline Phase 1 | `[workflow-state:planning-inline]` |
| Phase 2 + Phase 3.2–3.4 (implementation + check + wrap-up) | `[workflow-state:in_progress]` (after Phase 2 summary) |
| Codex inline Phase 2 + Phase 3.2–3.4 | `[workflow-state:in_progress-inline]` |
| After Phase 3.5 (archived) | `[workflow-state:completed]` (after Phase 3 summary; **currently DEAD**) |

### Changing the per-turn prompt text

Directly edit the body of the corresponding `[workflow-state:STATUS]` block. After editing, run `trellis update` (if you're a template maintainer) or restart your AI session (if you're customizing your own project) — no script changes required.

### Adding a custom status

Add a new block:

```
[workflow-state:my-status]
your per-turn prompt text
[/workflow-state:my-status]
```

Constraints:
- STATUS charset: `[A-Za-z0-9_-]+` (underscores and hyphens allowed, e.g. `in-review`, `blocked-by-team`)
- A lifecycle hook must write `task.json.status` to your custom value, otherwise the tag is never read
- Lifecycle hooks live in `task.json.hooks.after_*` and bind to one of `after_create / after_start / after_finish / after_archive`

### Adding a lifecycle hook

Add a `hooks` field to your `task.json`:

```json
{
  "hooks": {
    "after_finish": [
      "your-script-or-command-here"
    ]
  }
}
```

Supported events: `after_create / after_start / after_finish / after_archive`. Note that `after_finish` ≠ a status change (it only clears the active-task pointer); use `after_archive` for "task is done" notifications.

### Full contract

For the workflow state machine's runtime contract, the locations of all status writers, pseudo-statuses (`no_task` / `stale_<source_type>`), the hook reachability matrix, and other deep details, see:

- `.trellis/spec/cli/backend/workflow-state-contract.md` — runtime contract + writer table + test invariants
- `.trellis/scripts/inject-workflow-state.py` — actual parser (reads workflow.md only, no embedded text)
