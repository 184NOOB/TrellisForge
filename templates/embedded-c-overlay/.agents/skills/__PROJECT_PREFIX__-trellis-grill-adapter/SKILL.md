---
name: PROJECT_PREFIX-trellis-grill-adapter
description: Connects Trellis brainstorm decision ownership and the upstream grill-me interview format to this project's planning artifacts and the project-local start gate. Use together with trellis-brainstorm and grill-me for every task in planning or planning-inline, after task creation and before implementation approval.
---

# PROJECT_NAME Trellis Grill Adapter

Keep responsibilities separate: `trellis-brainstorm` owns evidence inspection,
decision ownership, whether a clarification is needed, convergence, and
planning-artifact structure. `grill-me` supplies the one-question-at-a-time
shape and branch traversal only for unresolved user-owned decisions. This
adapter persists resolved decisions and states the Trellis phase-boundary
protocol.

This adapter combines the upstream interview format with
`trellis-brainstorm`'s evidence and decision-ownership rules. The project also
uses a local `task.py start` readiness gate, but that gate only verifies the
persisted convergence and approval markers. It cannot prove that an AI
classified every decision correctly, so the artifact rules remain mandatory.

## Decision Ownership

Before asking a question, recompute a decision inventory with four groups:

1. Repository-confirmed facts: resolve these by reading code, tests, configs,
   Specs, task history, or external documentation.
2. Explicit user decisions: preserve them as requirements; do not ask the user
   to reconfirm them merely because the AI prefers another design.
3. Engineering decisions: resolve these from project patterns, constraints,
   and safe reversible defaults, then record the rationale in `design.md`.
4. Unresolved user-owned decisions: product behavior, scope, compatibility,
   risk tolerance, or acceptance behavior that evidence cannot decide.

Ask exactly one highest-value question only when group 4 is non-empty. Use the
upstream `grill-me` question shape. Do not manufacture a question when groups
1-3 already resolve the plan; proceed to the final planning summary instead.
Implementation approval is a phase-transition gate, not a Grill question.

## Planning Integration

1. Resolve the active task with `task.py current --source`. A main session may
   continue only when the source is its exact `session:*` pointer. Treat
   `session-fallback:*` as another session's state; do not read, preserve, or
   plan against it as the current task. For task trees, bind exactly one
   next-actionable planning child and keep parent/deferred children unselected.
   Then read that task's existing `prd.md`, `design.md`, `implement.md`,
   relevant Specs, and repository evidence.
2. Run `trellis-brainstorm`'s evidence pass and decision inventory, then apply
   the unmodified `grill-me` question format to every unresolved user-owned
   branch. Do not bypass this merely because a task is labeled lightweight.
3. After each user answer, summarize the resolved decision and immediately
   persist it in `prd.md`; update `design.md` and `implement.md` when the
   decision changes design or execution.
4. Keep facts, explicit user decisions, engineering decisions, assumptions,
   and unresolved user-owned decisions distinguishable in the artifacts.
5. Resolve every engineering branch before final review. Do not leave wording
   such as "choose during implementation", "A or B", or an unselected
   recommendation in `prd.md`, `design.md`, or `implement.md`. Research and
   select a safe design when it is an engineering decision; ask the user only
   when the remaining choice is user-owned.
6. Treat the review profile separately: use the user's latest explicit
   `light|standard|strict` choice; otherwise persist `standard`. Do not upgrade
   it based on the AI's risk opinion and do not ask a question solely to select
   the default.
7. Before final review, persist this exact section in `prd.md`:

   ```markdown
   ## Planning Convergence

   - Status: ready
   - Blocking user decisions: 0
   - Blocking technical decisions: 0
   - Final summary ready: yes
   ```

   Use `pending` / non-zero values while the plan is not converged. Never mark
   the section ready merely to satisfy the start gate.
8. After convergence, set task metadata `planning_ready=true`, present the
   latest planning summary with scope, acceptance criteria, key decisions,
   risks/deferred items, and selected review level, then stop.
9. Only after a subsequent user message explicitly approves that exact summary,
   set `plan_approved=true` and run `task.py start`. Approval given before the
   latest summary does not activate the task.

## Phase Boundary

Stay in `planning` or `planning-inline` throughout the interview. Do not edit
product code, dispatch implementation, or run `task.py start` until the user
explicitly approves the latest converged plan. If implementation reveals a
material requirement or design change, return to planning, rerun the affected
`grill-me` branches, update the artifacts, and obtain approval again.

Do not add minimum question counts. A zero-question plan is valid when the
initial request and evidence resolve every decision, but it still requires the
convergence pass, final summary, and a subsequent explicit approval.
