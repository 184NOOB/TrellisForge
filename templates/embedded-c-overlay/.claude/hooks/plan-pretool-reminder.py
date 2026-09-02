#!/usr/bin/env python3
"""Trellis execution-plan PreToolUse reminder (Claude Code, non-blocking).

Optional convenience per the execution-plan design: warns the session when an
Edit/Write/MultiEdit looks off-plan (state-file tampering, writes outside the
in_progress task's scope.write, discovery-phase writes, edit-count overrun) and
maintains the per-file edit counters that ``plan.py done`` cross-checks.

Hard rules NEVER live here: every rejection is enforced by plan.py so the flow
stays correct when hooks are off or unavailable (Codex, inline, hooks disabled).
This hook exits 0 in every path and never blocks a tool call.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    for _name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _name, None)
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def find_trellis_root(start: Path):
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def emit(message: str) -> None:
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(data, dict) or data.get("tool_name") not in EDIT_TOOLS:
        return 0

    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    raw_target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(raw_target, str) or not raw_target.strip():
        return 0

    cwd = Path(data.get("cwd") or os.getcwd())
    root = find_trellis_root(cwd)
    if root is None:
        return 0
    scripts_dir = root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common import execution_plan as ep
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
    except Exception:
        return 0

    active = resolve_active_task(root, data, allow_single_session_fallback=True)
    if not active.task_path or active.stale:
        return 0
    task_dir = Path(active.task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    if not ep.plan_exists(task_dir):
        return 0
    try:
        plan = ep.load_plan(task_dir)
    except ep.PlanError:
        emit("Trellis plan: execution-plan.json is unreadable — run plan.py status before editing.")
        return 0

    try:
        target = Path(raw_target).resolve()
        target_rel = target.relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        target_rel = ""

    warnings: list[str] = []

    plan_file = task_dir / ep.PLAN_FILE
    events_file = task_dir / ep.EVENTS_FILE
    if target == events_file.resolve():
        warnings.append(
            "execution-events.jsonl is append-only through plan.py; direct writes "
            "break the audit chain and pause all state-changing commands."
        )
    if target == plan_file.resolve() and plan.get("status") == "approved":
        warnings.append(
            "The plan is approved. To change guarded content run "
            "plan.py revise --reason \"...\" first, then validate again."
        )

    status = ep.compute_status(plan)
    in_progress = status["in_progress"]
    constraints = plan.get("constraints") or {}
    max_edits = constraints.get("max_edits_per_file", ep.DEFAULT_MAX_EDITS_PER_FILE)

    # Directory-boundary comparison: a bare startswith(".trellis/tasks/demo")
    # would wrongly count edits under ".trellis/tasks/demo2/" as this task's.
    task_rel = ep.task_rel_path(root, task_dir)
    under_task = bool(target_rel) and (
        target_rel == task_rel or target_rel.startswith(task_rel + "/")
    )
    if not under_task and plan.get("status") == "approved":
        if not in_progress:
            if status["runnable"]:
                warnings.append(
                    f"No plan task is in_progress; this edit likely belongs to "
                    f"'{status['runnable'][0]}' — run plan.py start first."
                )
        else:
            task = next(
                (t for t in plan.get("tasks", []) if t.get("id") == in_progress[0]),
                {},
            )
            write_scope = (task.get("scope") or {}).get("write") or []
            if not write_scope:
                warnings.append(
                    f"'{in_progress[0]}' is a discovery-phase task (scope.write empty); "
                    "this edit writes source code."
                )
            elif target_rel and not any(
                ep.scope_match(p, target_rel) for p in write_scope
            ):
                warnings.append(
                    f"'{target_rel}' is outside '{in_progress[0]}' scope.write "
                    f"({', '.join(write_scope)})."
                )
            elif target_rel and in_progress[0]:
                try:
                    count = ep.bump_edit(
                        root,
                        ep.task_rel_path(root, task_dir),
                        int(plan.get("revision", 1)),
                        str(in_progress[0]),
                        target_rel,
                    )
                    if isinstance(max_edits, int) and count > max_edits:
                        warnings.append(
                            f"edit #{count} on '{target_rel}' exceeds "
                            f"max_edits_per_file={max_edits}; plan.py done will refuse. "
                            "Group related edits or revise the plan consciously."
                        )
                except Exception:
                    pass

    if warnings:
        emit(
            "Trellis execution-plan reminder (advisory, not enforced here):\n- "
            + "\n- ".join(warnings)
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # a reminder hook must never break the tool flow
