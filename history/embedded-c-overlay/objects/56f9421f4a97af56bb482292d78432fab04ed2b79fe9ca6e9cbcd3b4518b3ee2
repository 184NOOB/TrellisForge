"""Execution-plan state machine shared by plan.py and platform hooks.

Design sources: the Trellis execution-plan design, superseded on the
verification model by the Trellis two-level verification PRD
(schema 3: two verification levels ``minimal`` / ``report`` plus explicit
``required_checks``; no ``risk``, ``raw``, or ``required_evidence``).

Per task directory two persisted files exist:

    <task-path>/execution-plan.json      current plan + state (single source of truth)
    <task-path>/execution-events.jsonl   append-only audit log (written via this module only)

Core correctness (dependency checks, verification checks, state transitions, audit
append) lives here so the CLI flow works identically on Claude Code, Codex,
and any platform without hooks. Hooks are optional conveniences: the
UserPromptSubmit hook only displays ``summary_lines`` and the PreToolUse hook
only warns / counts edits; neither advances state.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLAN_FILE = "execution-plan.json"
EVENTS_FILE = "execution-events.jsonl"
SCHEMA_VERSION = 3
REPORT_FILE = "final-report.md"

PLAN_STATUSES = ("proposed", "approved")
TASK_STATUSES = ("pending", "in_progress", "completed", "blocked")

DEFAULT_MAX_TASKS = 8
DEFAULT_MAX_EDITS_PER_FILE = 5

# Kebab-ish identifier for task ids and declared required-check ids.
# Enforcing identifier shape (no spaces / shell metacharacters) is what keeps
# required checks declarative IDs, not shell commands.
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.\-]*$")

# Fields that must not be silently edited while a plan is approved.
_GUARDED_TASK_FIELDS = (
    "id",
    "title",
    "objective",
    "depends_on",
    "scope",
    "batch_groups",
    "verification",
    "no_check_reason",
)
# Fields plan.py manages inside a task; models must not hand-edit them.
_MANAGED_TASK_FIELDS = ("verification_results",)

# Two-level verification model (schema 3): minimal = phase execution record,
# report = final acceptance. No risk->level mapping exists anymore.
VERIFICATION_LEVELS = ("minimal", "report")
_VERIFICATION_KEYS = ("level", "required_checks", "report_path")
# Schema-3 plans must not carry these pre-schema-3 fields (checked at plan
# top level and per task).
_LEGACY_TASK_FIELDS = (
    "risk",
    "required_evidence",
    "evidence",
    "check_results",
    "checks",
    "required_artifacts",
)
MAX_INLINE_COMMAND_LENGTH = 512


class PlanError(Exception):
    """User-facing plan failure. CLI prints the message and exits non-zero."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint


# ---------------------------------------------------------------------------
# Task directory and path resolution
# ---------------------------------------------------------------------------

def resolve_task_dir(repo_root: Path, task_ref: str | None) -> Path:
    """Resolve a task reference to an existing task directory inside the repo.

    Accepts repo-root-relative paths, absolute paths, or bare task slugs.
    Refuses anything that escapes the repository, and only accepts a concrete
    task directory (one containing ``task.json``): pointing at
    ``.trellis/tasks`` or another container would otherwise send follow-on
    "create execution-plan.json" guidance to the wrong place.
    """
    repo_root = repo_root.resolve()
    if task_ref:
        raw = task_ref.strip().replace("\\", "/").rstrip("/")
        cand = Path(raw)
        if not cand.is_absolute():
            cand = repo_root / cand
        cand = cand.resolve()
        if _is_within(cand, repo_root) and (cand / "task.json").is_file():
            return cand
        # Bare slug fallback. Only a plain name is allowed: Path joining with
        # an absolute or traversal raw would escape the tasks tree (e.g.
        # base / "/abs" -> "/abs"), and glob metacharacters would let a slug
        # like "*" silently match the first archived task. Live tasks are
        # flat under tasks/; the archiver stores them under
        # archive/<YYYY-MM>/<slug>, so the archive lookup must descend one
        # month level.
        if (
            "/" not in raw
            and raw not in (".", "..")
            and not any(ch in raw for ch in "*?[]")
        ):
            slug_candidates = [repo_root / ".trellis" / "tasks" / raw]
            slug_candidates += sorted(
                (repo_root / ".trellis" / "tasks" / "archive").glob(f"*/{raw}")
            )
            for slug_dir in slug_candidates:
                if (slug_dir / "task.json").is_file():
                    resolved = slug_dir.resolve()
                    if _is_within(resolved, repo_root):
                        return resolved
        raise PlanError(
            f"task directory (containing task.json) not found: {task_ref}",
            hint="--task must name the concrete task dir from the dispatch "
                 "prompt's 'Active task:' line (or task.py current), not a "
                 "container like .trellis/tasks",
        )
    active = _resolve_active_task_dir(repo_root)
    if active is None:
        raise PlanError(
            "no active task resolved",
            hint="pass --task <path> (recommended for sub-agents) or run task.py start first",
        )
    return active


def _resolve_active_task_dir(repo_root: Path) -> Path | None:
    scripts_dir = repo_root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]
    except Exception:
        return None
    active = resolve_active_task(
        repo_root, None, allow_single_session_fallback=True
    )
    if not active.task_path or active.stale:
        return None
    path = Path(active.task_path)
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()
    return path if path.is_dir() else None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def rel_posix(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def task_rel_path(repo_root: Path, task_dir: Path) -> str:
    try:
        return task_dir.relative_to(repo_root).as_posix()
    except ValueError:
        return task_dir.as_posix()


# ---------------------------------------------------------------------------
# Plan / event IO
# ---------------------------------------------------------------------------

def plan_path(task_dir: Path) -> Path:
    return task_dir / PLAN_FILE


def events_path(task_dir: Path) -> Path:
    return task_dir / EVENTS_FILE


def plan_exists(task_dir: Path) -> bool:
    return plan_path(task_dir).is_file()


def load_plan_raw(task_dir: Path) -> str:
    text = plan_path(task_dir).read_text(encoding="utf-8")
    # Reject a BOM up front: json.loads tolerates it but later re-saves drift.
    if text.startswith("﻿"):
        raise PlanError("execution-plan.json must be UTF-8 without BOM")
    return text


def load_plan(task_dir: Path) -> dict[str, Any]:
    if not plan_path(task_dir).is_file():
        raise PlanError(
            f"missing {task_rel_or_name(task_dir)}/{PLAN_FILE}",
            hint="create the plan file first, then run: python .trellis/scripts/plan.py validate",
        )
    try:
        data = json.loads(load_plan_raw(task_dir))
    except json.JSONDecodeError as exc:
        raise PlanError(f"execution-plan.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanError("execution-plan.json must contain a JSON object")
    return data


def task_rel_or_name(task_dir: Path) -> str:
    return task_dir.as_posix()


def save_plan(task_dir: Path, plan: dict[str, Any]) -> None:
    text = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(plan_path(task_dir), text)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_events(task_dir: Path) -> tuple[list[dict[str, Any]], list[int]]:
    """Return (events, corrupt_line_numbers). Missing file yields empty lists."""
    path = events_path(task_dir)
    if not path.is_file():
        return [], []
    events: list[dict[str, Any]] = []
    corrupt: list[int] = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            corrupt.append(lineno)
            continue
        if isinstance(item, dict) and isinstance(item.get("event"), str):
            events.append(item)
        else:
            corrupt.append(lineno)
    return events, corrupt


def require_clean_audit(task_dir: Path) -> list[dict[str, Any]]:
    """Return events or refuse all new mutations when the audit log is damaged."""
    events, corrupt = read_events(task_dir)
    if corrupt:
        raise PlanError(
            "execution-events.jsonl has unparseable lines: "
            + ", ".join(str(n) for n in corrupt),
            hint="repair the audit log first; state-changing commands are paused",
        )
    return events


def append_event(task_dir: Path, event: dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault("time", _utc_now())
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path = events_path(task_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def mutate_with_audit(
    task_dir: Path,
    original_text: str,
    plan: dict[str, Any],
    event: dict[str, Any] | list[dict[str, Any]],
) -> None:
    """Save the new plan, then append its audit event(s).

    If any audit append fails, the plan file is restored to ``original_text``
    so the JSON state never advances without its event. This is the design's
    rollback requirement; failures here are disk-level and reported loudly.
    """
    save_plan(task_dir, plan)
    events = event if isinstance(event, list) else [event]
    try:
        for one in events:
            append_event(task_dir, one)
    except OSError as exc:
        try:
            _atomic_write(plan_path(task_dir), original_text)
            raise PlanError(
                f"audit append failed, plan state rolled back: {exc}",
                hint="fix audit log writability, then rerun the command",
            ) from exc
        except PlanError:
            raise
        except OSError as restore_exc:
            raise PlanError(
                f"audit append failed AND rollback failed: {restore_exc}",
                hint="plan file may carry an unlogged mutation; once the audit log "
                     "is writable again recover with plan.py revise + validate",
            ) from restore_exc


def history_of(events: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event") == name]


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------

def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def task_guarded(task: dict[str, Any]) -> dict[str, Any]:
    return {k: task.get(k) for k in _GUARDED_TASK_FIELDS if task.get(k) is not None}


def task_fingerprint(task: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(task_guarded(task)).encode("utf-8")).hexdigest()


def plan_guarded(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": plan.get("goal"),
        "constraints": plan.get("constraints"),
        "tasks": [task_guarded(t) for t in plan.get("tasks", []) if isinstance(t, dict)],
    }


def plan_fingerprint(plan: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(plan_guarded(plan)).encode("utf-8")).hexdigest()


def require_plan_intact(plan: dict[str, Any]) -> None:
    """Approved plans must not be hand-edited outside the sanctioned fields."""
    if plan.get("status") != "approved":
        return
    stored = plan.get("approved_fingerprint")
    if not isinstance(stored, str):
        raise PlanError(
            "approved plan is missing its fingerprint",
            hint="rerun: python .trellis/scripts/plan.py validate",
        )
    if plan_fingerprint(plan) != stored:
        raise PlanError(
            "approved plan content changed without revising",
            hint="run: python .trellis/scripts/plan.py revise --reason \"...\" "
                 "then edit the plan and validate again",
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_relative_path(entry: Any, where: str) -> str:
    if not isinstance(entry, str) or not entry.strip():
        raise PlanError(f"{where}: path entry must be a non-empty string")
    normalized = entry.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise PlanError(f"{where}: absolute path not allowed in plan: {entry}")
    parts = normalized.split("/")
    if ".." in parts:
        raise PlanError(f"{where}: path escapes the repository: {entry}")
    return normalized


def _validate_id_list(value: Any, where: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise PlanError(f"{where}: must be a list" + ("" if allow_empty else " with at least the contract fields"))
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not ID_RE.match(item):
            raise PlanError(
                f"{where}: '{item}' is not a kebab-case identifier "
                "(registered verification check ids are IDs, not shell commands)"
            )
        result.append(item)
    if len(set(result)) != len(result):
        raise PlanError(f"{where}: duplicate entries")
    return result


def validate_plan_shape(plan: dict[str, Any], task_rel: str) -> list[str]:
    """Structural validation. Returns list of human-readable issues (empty = OK)."""
    issues: list[str] = []

    def issue(msg: str) -> None:
        issues.append(msg)

    if plan.get("schema") != SCHEMA_VERSION:
        issue(
            f"schema must be {SCHEMA_VERSION} (legacy plans are not migrated; "
            "regenerate with `plan.py template` — do not edit the schema field "
            "of an old plan to force it through)"
        )
    top_legacy = [f for f in _LEGACY_TASK_FIELDS if f in plan]
    if top_legacy:
        issue(
            "schema 3 does not accept these top-level fields: "
            + ", ".join(top_legacy)
        )
    if not isinstance(plan.get("revision"), int) or plan.get("revision", 0) < 1:
        issue("revision must be an integer >= 1")
    if plan.get("status") not in PLAN_STATUSES:
        issue(f"status must be one of {PLAN_STATUSES}")
    if not isinstance(plan.get("goal"), str) or not plan["goal"].strip():
        issue("goal must be a non-empty string")
    audit = plan.get("audit")
    if not isinstance(audit, dict) or audit.get("required") is not True:
        issue("audit.required must be true")

    constraints = plan.get("constraints")
    if constraints is None:
        constraints = {}
        issue("constraints block missing (defaults apply)")
    if not isinstance(constraints, dict):
        issue("constraints must be an object")
        constraints = {}
    max_tasks = constraints.get("max_tasks", DEFAULT_MAX_TASKS)
    if not isinstance(max_tasks, int) or max_tasks < 1:
        max_tasks = DEFAULT_MAX_TASKS
        issue("constraints.max_tasks must be an integer >= 1")
    max_edits = constraints.get("max_edits_per_file", DEFAULT_MAX_EDITS_PER_FILE)
    if not isinstance(max_edits, int) or max_edits < 1:
        max_edits = DEFAULT_MAX_EDITS_PER_FILE
    forbidden = constraints.get("forbidden_git_operations", [])
    if not isinstance(forbidden, list) or any(
        not isinstance(x, str) for x in forbidden
    ):
        issue("constraints.forbidden_git_operations must be a list of strings")
    allow_parallel = constraints.get("allow_parallel_tasks", False)
    if not isinstance(allow_parallel, bool):
        issue("constraints.allow_parallel_tasks must be a boolean")
        allow_parallel = False

    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        issue("tasks must be a non-empty list")
        return issues
    if len(tasks) > max_tasks:
        issue(f"tasks count {len(tasks)} exceeds constraints.max_tasks={max_tasks}")

    ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(tasks):
        where = f"tasks[{index}]"
        if not isinstance(task, dict):
            issue(f"{where}: must be an object")
            continue
        tid = task.get("id")
        if not isinstance(tid, str) or not ID_RE.match(tid):
            issue(f"{where}.id '{tid}' is not a kebab-case identifier")
            continue
        if tid in by_id:
            issue(f"duplicate task id: {tid}")
            continue
        ids.append(tid)
        by_id[tid] = task
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            issue(f"{where}.title must be a non-empty string")
        if not isinstance(task.get("objective"), str) or not task["objective"].strip():
            issue(f"{where}.objective must be a non-empty string")
        if task.get("status") not in TASK_STATUSES:
            issue(f"{where}.status must be one of {TASK_STATUSES}")
        legacy = [f for f in _LEGACY_TASK_FIELDS if f in task]
        if legacy:
            issue(
                f"{where}: schema 3 does not accept these fields: "
                + ", ".join(legacy)
                + "; declare checks as verification.required_checks "
                "(minimal|report levels only)"
            )
        verification = task.get("verification")
        if not isinstance(verification, dict):
            issue(f"{where}.verification must be an object")
            verification = {}
        unknown_verif = sorted(set(verification) - set(_VERIFICATION_KEYS))
        if unknown_verif:
            issue(
                f"{where}.verification has unsupported keys: "
                + ", ".join(unknown_verif)
                + " (allowed: " + ", ".join(_VERIFICATION_KEYS) + ")"
            )
        level = verification.get("level")
        if level not in VERIFICATION_LEVELS:
            issue(f"{where}.verification.level must be one of {VERIFICATION_LEVELS}")
        try:
            required_checks = _validate_id_list(
                verification.get("required_checks"),
                f"{where}.verification.required_checks",
                allow_empty=True,
            )
        except PlanError as exc:
            issue(str(exc))
            required_checks = []
        no_check_reason = task.get("no_check_reason")
        if no_check_reason is not None and (
            not isinstance(no_check_reason, str) or not no_check_reason.strip()
        ):
            issue(f"{where}.no_check_reason must be a non-empty string when present")
        scope_obj = task.get("scope")
        has_writes = bool(
            isinstance(scope_obj, dict)
            and isinstance(scope_obj.get("write"), list)
            and any(isinstance(w, str) and w.strip() for w in scope_obj["write"])
        )
        # An empty required_checks may never bypass verification: it is legal
        # only for a pure read-only/analysis phase that states why (PRD 5.2).
        if not required_checks:
            if has_writes:
                issue(
                    f"{where}: phases with non-empty scope.write must declare at "
                    "least one verification.required_checks"
                )
            elif level == "report":
                issue(
                    f"{where}: level=report must declare at least one "
                    "verification.required_checks"
                )
            elif not (isinstance(no_check_reason, str) and no_check_reason.strip()):
                issue(
                    f"{where}: empty verification.required_checks requires a "
                    "non-empty no_check_reason (read-only/analysis phases only)"
                )
        elif isinstance(no_check_reason, str) and no_check_reason.strip():
            issue(
                f"{where}: no_check_reason is only valid when "
                "verification.required_checks is empty"
            )
        report_path = verification.get("report_path")
        if level == "report":
            if report_path != REPORT_FILE:
                issue(
                    f"{where}: verification.level=report requires "
                    f"verification.report_path == \"{REPORT_FILE}\""
                )
        elif report_path is not None:
            issue(f"{where}: verification.report_path is only valid for level=report")
        for field in _MANAGED_TASK_FIELDS:
            # Only a proposed (pre-approval / post-revise) plan must be clean:
            # Active approved plans legitimately carry verification_results.
            if (
                field in task
                and plan.get("status") == "proposed"
                and task.get("status") != "completed"
            ):
                issue(
                    f"{where}.{field} is managed by plan.py and must be absent "
                    "in a proposed plan"
                )
        scope = task.get("scope")
        if not isinstance(scope, dict):
            issue(f"{where}.scope must be an object with read/write lists")
        else:
            for key in ("read", "write"):
                entries = scope.get(key, [])
                if not isinstance(entries, list):
                    issue(f"{where}.scope.{key} must be a list of repo-relative paths")
                    continue
                for entry in entries:
                    try:
                        normalized = _validate_relative_path(
                            entry, f"{where}.scope.{key}"
                        )
                        # A pattern made only of wildcards (no fixed segment)
                        # matches every repo path, defeating scope entirely.
                        segments = [s for s in normalized.split("/") if s]
                        if key == "write" and segments and all(
                            s in ("*", "**") for s in segments
                        ):
                            issue(
                                f"{where}.scope.write: unbounded pattern "
                                f"'{entry}' would match the whole repository"
                            )
                    except PlanError as exc:
                        issue(str(exc))
        deps = task.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            issue(f"{where}.depends_on must be a list of task ids")
        if "batch_groups" in task:
            try:
                _validate_id_list(
                    task["batch_groups"], f"{where}.batch_groups", allow_empty=True
                )
            except PlanError as exc:
                issue(str(exc))

    for tid, task in by_id.items():
        for dep in task.get("depends_on") or []:
            if not isinstance(dep, str):
                continue  # non-string entries already reported above
            if dep not in by_id:
                issue(f"task {tid} depends on unknown id: {dep}")
            if dep == tid:
                issue(f"task {tid} depends on itself")
    cycle = _find_cycle(by_id)
    if cycle:
        issue("dependency cycle: " + " -> ".join(cycle))

    # PRD 8.2: at most one report phase per plan; when present it must be
    # terminal and cover every other phase. Every real task should end with
    # one so final acceptance produces final-report.md (2.2 review confirms).
    report_ids = [
        tid
        for tid, t in by_id.items()
        if isinstance(t.get("verification"), dict)
        and t["verification"].get("level") == "report"
    ]
    if len(report_ids) > 1:
        issue(
            "at most one verification.level=report task is allowed, found: "
            + ", ".join(sorted(report_ids))
        )
    if len(report_ids) == 1:
        rid = report_ids[0]
        dependents = sorted(
            tid for tid, t in by_id.items() if rid in (t.get("depends_on") or [])
        )
        if dependents:
            issue(
                f"report task {rid} must be terminal; these tasks depend on it: "
                + ", ".join(dependents)
            )
        # Final acceptance must come after ALL work: the report phase has to
        # (transitively) depend on every other phase, or it could complete
        # before the phases it is supposed to summarize.
        reachable: set[str] = set()
        stack = [
            d for d in by_id[rid].get("depends_on") or []
            if isinstance(d, str) and d in by_id
        ]
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(
                d for d in by_id[node].get("depends_on") or []
                if isinstance(d, str) and d in by_id
            )
        uncovered = sorted(set(by_id) - reachable - {rid})
        if uncovered:
            issue(
                f"report task {rid} must (transitively) depend on every other "
                "task; not covered: " + ", ".join(uncovered)
            )

    for entry in plan.get("tasks", []):
        if isinstance(entry, dict) and entry.get("status") == "in_progress" and plan.get("status") == "proposed":
            issue("a proposed plan must not contain in_progress tasks")

    return issues


def _find_cycle(by_id: dict[str, dict[str, Any]]) -> list[str] | None:
    state: dict[str, int] = {}

    def visit(node: str, stack: list[str]) -> list[str] | None:
        marker = state.get(node, 0)
        if marker == 1:
            return stack[stack.index(node):] + [node]
        if marker == 2:
            return None
        state[node] = 1
        for dep in by_id[node].get("depends_on") or []:
            if isinstance(dep, str) and dep in by_id:
                found = visit(dep, stack + [node])
                if found:
                    return found
        state[node] = 2
        return None

    for node in by_id:
        found = visit(node, [])
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# Validate / approve / revise
# ---------------------------------------------------------------------------

def _expected_revision(events: list[dict[str, Any]]) -> int:
    return 1 + len(history_of(events, "plan_revised"))


def cmd_validate(repo_root: Path, task_dir: Path) -> str:
    events, corrupt = read_events(task_dir)
    if corrupt:
        raise PlanError(
            "execution-events.jsonl has unparseable lines: "
            + ", ".join(str(n) for n in corrupt),
            hint="repair the audit log before validating",
        )
    plan = load_plan(task_dir)
    task_rel = task_rel_path(repo_root, task_dir)

    if plan.get("status") == "approved":
        issues = validate_plan_shape(plan, task_rel)
        if issues:
            raise PlanError("approved plan failed re-validation:\n- " + "\n- ".join(issues))
        stored = plan.get("approved_fingerprint")
        if plan_fingerprint(plan) != stored:
            raise PlanError(
                "approved plan content changed without revising",
                hint="run plan.py revise --reason \"...\" before editing the plan",
            )
        if int(plan.get("revision", 0)) != _expected_revision(events):
            expected_rev = _expected_revision(events)
            raise PlanError(
                f"approved plan revision {plan.get('revision')} disagrees with "
                f"the audit history (expected {expected_rev})",
                hint=f"the revision was likely hand-edited: set it back to "
                     f"{expected_rev} keeping \"status\": \"approved\", then use "
                     "plan.py revise to change the plan (approve itself never "
                     "changes the revision, so a mismatch is not a crash "
                     "artifact)",
            )
        approvals = history_of(events, "plan_approved")
        if (
            not approvals
            or int(approvals[-1].get("revision", -1)) != int(plan.get("revision", -2))
        ):
            raise PlanError(
                "approved plan has no matching plan_approved event at this revision",
                hint="a crash likely saved the plan before its plan_approved "
                     "event landed; hand-edit \"status\" back to \"proposed\" "
                     "and run validate to redo the approval",
            )
        return f"plan already approved at revision {plan['revision']} (no changes)"

    issues = validate_plan_shape(plan, task_rel)

    revision = plan.get("revision")
    if isinstance(revision, int) and revision != _expected_revision(events):
        expected_rev = _expected_revision(events)
        if revision == expected_rev + 1:
            issues.append(
                f"revision {revision} disagrees with audit history (expected "
                f"{expected_rev}); if a crash interrupted revise before its "
                "plan_revised event landed, run plan.py revise --reason \"...\" "
                "again — it heals the missing event — then edit and validate"
            )
        elif revision > expected_rev:
            issues.append(
                f"revision {revision} disagrees with audit history (expected "
                f"{expected_rev}); only plan.py revise bumps revisions. To "
                f"recover: set revision back to {expected_rev} with status "
                "\"approved\" and run revise, or to exactly "
                f"{expected_rev + 1} and run revise to heal a crashed revise"
            )
        else:
            issues.append(
                f"revision {revision} disagrees with audit history "
                f"(expected {expected_rev}); bump it only via plan.py revise"
            )
    approvals = history_of(events, "plan_approved")
    if (
        approvals
        and isinstance(revision, int)
        and int(approvals[-1].get("revision", -1)) == revision
    ):
        # The sanctioned paths never leave a plan 'proposed' at an already
        # approved revision: that only happens when a model hand-flips the
        # status to dodge revise. Refuse the silent re-approval.
        issues.append(
            f"revision {revision} is already approved in the audit log but the "
            "plan says 'proposed' — a status hand-flip cannot re-approve it; "
            "restore \"status\": \"approved\" and use plan.py revise to reopen "
            "the plan (revise reverts unauthorized guarded edits to the "
            "last-approved snapshot)"
        )

    # Completed tasks exist only by audit history: a model cannot mark work
    # done by editing the JSON.
    historical_completed = {
        e.get("task") for e in history_of(events, "task_completed")
    }
    claimed_completed = {
        t.get("id") for t in plan.get("tasks", []) if isinstance(t, dict) and t.get("status") == "completed"
    }
    if not claimed_completed <= historical_completed:
        issues.append(
            "tasks marked completed without audit history: "
            + ", ".join(sorted(claimed_completed - historical_completed))
        )
    by_id = {
        t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)
    }
    for tid in historical_completed:
        task = by_id.get(tid)
        if task is None:
            issues.append(f"completed task '{tid}' disappeared from the plan")
        elif task.get("status") != "completed":
            issues.append(f"completed task '{tid}' cannot be downgraded by editing the plan")
    for e in history_of(events, "task_completed"):
        task = by_id.get(e.get("task"))
        if task is not None and e.get("fingerprint") and task_fingerprint(task) != e["fingerprint"]:
            issues.append(
                f"completed task '{task.get('id')}' content was rewritten after completion"
            )

    if plan.get("status") == "proposed":
        for task in plan.get("tasks", []):
            if isinstance(task, dict) and task.get("status") in ("in_progress",):
                issues.append(f"proposed plan must not have in_progress task {task.get('id')}")

    # Managed maps must equal the audit replay in both directions: no forged
    # or deleted verification result entries, on completed (whole log) and non-completed
    # (post-boundary) tasks alike.
    for line in managed_drift(plan, events):
        issues.append(f"verification result map does not match the audit log: {line}")

    if issues:
        raise PlanError("plan validation failed:\n- " + "\n- ".join(issues))

    plan["task"] = task_rel
    plan.setdefault("created_by", "trellis-implement")
    if not history_of(events, "plan_created"):
        append_event(task_dir, {"event": "plan_created", "revision": plan["revision"]})
    plan["status"] = "approved"
    plan["approved_fingerprint"] = plan_fingerprint(plan)
    fingerprint = plan["approved_fingerprint"]
    completed_now = [
        t["id"] for t in plan["tasks"] if t.get("status") == "completed"
    ]
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    mutate_with_audit(
        task_dir,
        original_text,
        plan,
        {
            "event": "plan_approved",
            "revision": plan["revision"],
            "fingerprint": fingerprint,
            "completed": completed_now,
            "snapshot": plan_guarded(plan),
        },
    )
    return f"plan approved: revision {plan['revision']}, {len(plan['tasks'])} tasks"


def cmd_revise(repo_root: Path, task_dir: Path, reason: str) -> str:
    if not reason.strip():
        raise PlanError("--reason is required for revise")
    events = require_clean_audit(task_dir)
    plan = load_plan(task_dir)
    if plan.get("status") != "approved":
        # Crash self-heal: a revise that saved its proposed plan but died
        # before appending plan_revised would otherwise deadlock between
        # validate ("bump only via revise") and revise ("only approved may be
        # revised"). The file state proves the revise happened; finish it.
        expected_rev = _expected_revision(events)
        approvals_seen = history_of(events, "plan_approved")
        if (
            plan.get("status") == "proposed"
            and isinstance(plan.get("revision"), int)
            and plan["revision"] == expected_rev + 1
            and approvals_seen
            and int(approvals_seen[-1].get("revision", -1)) == expected_rev
        ):
            append_event(task_dir, {
                "event": "plan_revised",
                "from_revision": expected_rev,
                "to_revision": int(plan["revision"]),
                "reason": reason.strip()
                + " (healed missing plan_revised event; heal replays the event "
                  "only — content is not trusted, validate re-applies every rule)",
                "recovered": True,
            })
            return (
                f"audit healed for revision {plan['revision']} (the earlier "
                "revise saved the plan before its event landed). The heal "
                "validates nothing about the current content: edit "
                "execution-plan.json if needed, then plan.py validate, and the "
                "2.2 review should treat this revision as a normal plan change"
            )
        raise PlanError(
            "only the currently approved plan revision may be revised",
            hint="an unapproved (proposed) plan can simply be edited, then "
                 "validated; a proposed plan whose revision was already bumped "
                 "is recovered by running revise again (it heals the audit event)",
        )
    approvals = history_of(events, "plan_approved")
    if not approvals or int(approvals[-1].get("revision", -1)) != int(plan.get("revision", -2)):
        raise PlanError(
            "plan revision has no matching approval in the audit log",
            hint="run plan.py validate before revising",
        )
    try:
        require_plan_intact(plan)
    except PlanError:
        # The approved plan was hand-edited without revising. Revise is the
        # sanctioned exit: discard the unauthorized guarded edits, restore the
        # last-approved snapshot, then bump revision. Managed per-task fields
        # (verification_results) are carried over from the current file and
        # statuses are re-derived from the audit log below.
        restored = approvals[-1].get("snapshot")
        if not isinstance(restored, dict):
            raise PlanError(
                "approved plan was edited without revising and no approved "
                "snapshot exists in the audit log",
                hint="rebuild the plan JSON from the last plan_approved snapshot or start over",
            )
        current_by_id = {
            t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)
        }
        snapshot_tasks: list[dict[str, Any]] = []
        for task in restored.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task = copy.deepcopy(task)
            current = current_by_id.get(task.get("id")) or {}
            for field in _MANAGED_TASK_FIELDS:
                if field in current:
                    task[field] = copy.deepcopy(current[field])
            snapshot_tasks.append(task)
        plan = {**plan, "goal": restored.get("goal"), "constraints": restored.get("constraints"), "tasks": snapshot_tasks}
        note = "\nwarning: unauthorized guarded edits were reverted to the last-approved snapshot"
    else:
        note = ""
    completed = {
        str(e.get("task")) for e in history_of(events, "task_completed")
    }
    by_id = {
        t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)
    }
    for tid in completed:
        if tid not in by_id:
            raise PlanError(
                f"completed task '{tid}' disappeared from the plan",
                hint="history may not be deleted; escalate before continuing",
            )
    reset: list[str] = []
    for task in plan.get("tasks", []):
        if not isinstance(task, dict):
            continue
        new_status = (
            "completed" if task.get("id") in completed else "pending"
        )
        # Only tasks that actually fall back to pending belong in the reset
        # note; an audit-completed task re-derived to completed was not reset
        # even if its JSON said in_progress/blocked.
        if (
            task.get("status") in ("in_progress", "blocked")
            and new_status == "pending"
        ):
            reset.append(str(task.get("id")))
        task["status"] = new_status
        if new_status != "completed":
            for field in _MANAGED_TASK_FIELDS:
                task.pop(field, None)
    plan["revision"] = int(plan["revision"]) + 1
    plan["status"] = "proposed"
    plan.pop("approved_fingerprint", None)
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    mutate_with_audit(
        task_dir,
        original_text,
        plan,
        {
            "event": "plan_revised",
            "from_revision": int(plan["revision"]) - 1,
            "to_revision": int(plan["revision"]),
            "reason": reason.strip(),
            "reset": reset,
        },
    )
    return (
        f"plan revision {plan['revision']} is proposed"
        + (f"; reset to pending: {', '.join(reset)}" if reset else "")
        + note
        + "\nedit execution-plan.json if needed, then run plan.py validate"
    )


# ---------------------------------------------------------------------------
# Task advancement
# ---------------------------------------------------------------------------

def replay_statuses(
    events: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, str]:
    """Derive each task's status by replaying the audit log after approval.

    Task statuses are a pure function of the event stream; a JSON status that
    disagrees with the replay was hand-edited and every mutation must refuse.
    """
    approvals = history_of(events, "plan_approved")
    if not approvals:
        return {}
    last = approvals[-1]
    last_index = len(events) - 1 - events[::-1].index(last)
    completed = {str(t) for t in last.get("completed") or []}
    statuses = {
        str(t.get("id")): ("completed" if t.get("id") in completed else "pending")
        for t in plan.get("tasks", [])
        if isinstance(t, dict) and t.get("id")
    }
    for event in events[last_index + 1:]:
        name = event.get("event")
        tid = str(event.get("task") or "")
        if name == "task_started" and tid in statuses:
            statuses[tid] = "in_progress"
        elif name == "task_completed" and tid in statuses:
            statuses[tid] = "completed"
        elif name == "task_blocked" and tid in statuses:
            statuses[tid] = "blocked"
    return statuses


def _last_boundary_index(events: list[dict[str, Any]]) -> int:
    """Index of the newest plan_approved / plan_revised event (-1 when none).

    Non-completed tasks may only carry managed fields registered after this
    boundary; earlier events belong to a superseded revision and were cleared
    from the JSON by revise.
    """
    for index in range(len(events) - 1, -1, -1):
        if events[index].get("event") in ("plan_approved", "plan_revised"):
            return index
    return -1


def _replay_start_index(
    events: list[dict[str, Any]], tid: str, is_completed: bool
) -> int:
    """First event index whose check_recorded entries count for the task's map.

    A completed task's map is preserved across revisions, but revise cleared
    any superseded record set, so its window starts at the last plan_revised
    before completion (whole log when there was none). A non-completed task
    counts only events after the latest plan_approved / plan_revised boundary.
    """
    if is_completed:
        done = [
            i for i, e in enumerate(events)
            if e.get("event") == "task_completed" and str(e.get("task")) == tid
        ]
        if done:
            prior = [
                i for i, e in enumerate(events)
                if e.get("event") == "plan_revised" and i < done[-1]
            ]
            return prior[-1] if prior else -1
    return _last_boundary_index(events)


def replay_verification_results(
    events: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Replay verification results from check_recorded events.

    Mirrors replay_statuses for the managed fields so _require_mutable can
    reject hand-forged verification results, not just hand-forged
    statuses. Each task replays from its own window start (see
    _replay_start_index).
    """
    task_ids = {
        str(t.get("id"))
        for t in plan.get("tasks", [])
        if isinstance(t, dict) and t.get("id")
    }
    completed = {
        str(t.get("id"))
        for t in plan.get("tasks", [])
        if isinstance(t, dict) and t.get("status") == "completed"
    }
    starts = {
        tid: _replay_start_index(events, tid, tid in completed) for tid in task_ids
    }
    results: dict[str, dict[str, Any]] = {tid: {} for tid in task_ids}
    for index, event in enumerate(events):
        tid = str(event.get("task") or "")
        if tid not in task_ids:
            continue
        if index <= starts[tid]:
            continue
        name = event.get("event")
        if name == "check_recorded":
            entry: dict[str, Any] = {
                "result": event.get("result"),
                "exit_code": event.get("exit_code"),
            }
            for field in (
                "command", "command_sha256", "command_length", "artifact", "summary"
            ):
                if field in event:
                    entry[field] = event[field]
            results[tid][str(event.get("check"))] = entry
    return results


def status_drift(plan: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    """Diffs between JSON task statuses and the audit replay (empty = match)."""
    expected = replay_statuses(events, plan)
    return [
        f"{t.get('id')}: {t.get('status')} (audit says {expected.get(t.get('id'))})"
        for t in plan.get("tasks", [])
        if isinstance(t, dict)
        and expected.get(str(t.get("id"))) not in (None, t.get("status"))
    ]


def managed_drift(plan: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    """Human-readable diffs between verification results and audit replay."""
    expected_results = replay_verification_results(events, plan)
    drift: list[str] = []
    for task in plan.get("tasks", []):
        if not isinstance(task, dict):
            continue
        tid = str(task.get("id"))
        actual_results = {
            str(name): {
                key: value for key, value in entry.items()
                if key != "time" and value is not None
            }
            for name, entry in (task.get("verification_results") or {}).items()
            if isinstance(entry, dict)
        }
        if actual_results != expected_results.get(tid, {}):
            drift.append(
                f"{tid}.verification_results {actual_results} != audit replay "
                f"{expected_results.get(tid, {})}"
            )
    return drift


def _require_mutable(task_dir: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Common preconditions for every state-changing task command."""
    events = require_clean_audit(task_dir)
    verification_drift = managed_drift(plan, events)
    if verification_drift:
        raise PlanError(
            "verification result map does not match the audit replay: "
            + "; ".join(verification_drift),
            hint="verification results may only be registered through plan.py record; "
                 "if the plan JSON led the audit after a crash between save and append, "
                 "recover with plan.py revise --reason \"...\" and re-validate",
        )
    require_plan_intact(plan)
    if plan.get("status") != "approved":
        raise PlanError(
            "plan is not approved",
            hint="run plan.py validate first",
        )
    approvals = history_of(events, "plan_approved")
    if not approvals or int(approvals[-1].get("revision", -1)) != int(plan.get("revision", -2)):
        raise PlanError("plan revision has no matching approval in the audit log")
    drifted = status_drift(plan, events)
    if drifted:
        raise PlanError(
            "task statuses do not match the audit replay: " + "; ".join(drifted),
            hint="statuses may only change through plan.py start/done/block/revise; "
                 "if plan.json led the audit after a crash between save and append, "
                 "recover with plan.py revise --reason \"...\" and re-validate",
        )
    return events


def _task_by_id(plan: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in plan.get("tasks", []):
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    raise PlanError(f"unknown task id: {task_id}")


def cmd_start(repo_root: Path, task_dir: Path, task_id: str) -> str:
    plan = load_plan(task_dir)
    _require_mutable(task_dir, plan)
    task = _task_by_id(plan, task_id)
    if task.get("status") == "completed":
        raise PlanError(f"task {task_id} is already completed")
    if task.get("status") == "in_progress":
        raise PlanError(f"task {task_id} is already in_progress")
    by_id = {t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)}
    unmet = [
        dep for dep in task.get("depends_on") or []
        if by_id.get(dep, {}).get("status") != "completed"
    ]
    if unmet:
        raise PlanError(f"task {task_id} has unmet dependencies: {', '.join(unmet)}")
    constraints = plan.get("constraints") or {}
    if not constraints.get("allow_parallel_tasks", False):
        busy = [
            t.get("id") for t in plan.get("tasks", [])
            if isinstance(t, dict) and t.get("status") == "in_progress"
        ]
        if busy:
            raise PlanError(
                f"task(s) already in_progress: {', '.join(map(str, busy))}",
                hint="finish (done) or block them first, or set "
                     "constraints.allow_parallel_tasks in a revised plan",
            )
    task["status"] = "in_progress"
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    mutate_with_audit(
        task_dir, original_text, plan, {"event": "task_started", "task": task_id}
    )
    return f"task {task_id} → in_progress (scope.write: {len((task.get('scope') or {}).get('write', []))} patterns)"


def _task_local_artifact_path(task_dir: Path, raw: str, *, must_exist: bool) -> Path:
    """Resolve an artifact inside its task directory without following symlink aliases."""
    normalized = raw.strip().replace("\\", "/")
    if not normalized:
        raise PlanError("artifact path must be a non-empty string")
    task_root = task_dir.resolve()
    candidate = Path(normalized)
    probe = candidate if candidate.is_absolute() else task_root / candidate
    lexical = Path(os.path.abspath(probe))
    if not _is_within(lexical, task_root):
        raise PlanError(f"artifact path is outside the task directory: {raw}")
    current = task_root
    for part in lexical.relative_to(task_root).parts:
        current /= part
        if current.is_symlink():
            raise PlanError(f"artifact path must not contain symbolic links: {raw}")
    try:
        resolved = lexical.resolve()
    except OSError as exc:
        raise PlanError(f"artifact path cannot be resolved: {raw}: {exc}") from exc
    if not _is_within(resolved, task_root):
        raise PlanError(f"artifact path resolves outside the task directory: {raw}")
    if must_exist and not resolved.is_file():
        raise PlanError(f"artifact path not found in task directory: {raw}")
    return resolved


def _resolve_artifact_path(repo_root: Path, task_dir: Path, raw: str) -> str:
    resolved = _task_local_artifact_path(task_dir, raw, must_exist=True)
    return rel_posix(repo_root, resolved)


def _artifact_requirement_key(
    repo_root: Path, task_dir: Path, raw: str
) -> str:
    """Normalize a declared artifact to the same repo-relative key as events."""
    resolved = _task_local_artifact_path(task_dir, raw, must_exist=False)
    return rel_posix(repo_root, resolved)


def _validate_result_exit_code(result: str, exit_code: int) -> None:
    if result not in ("pass", "fail"):
        raise PlanError("result must be pass|fail")
    if not isinstance(exit_code, int):
        raise PlanError("exit_code must be an integer")
    if result == "pass" and exit_code != 0:
        raise PlanError("result=pass requires exit_code=0")
    if result == "fail" and exit_code == 0:
        raise PlanError("result=fail requires a non-zero exit_code")


def _command_record_fields(command: str, summary: str | None) -> dict[str, Any]:
    if not isinstance(command, str) or not command.strip():
        raise PlanError("--command must be a non-empty string")
    # PRD 5.2/8.1: every check record carries command id, exit code, and a
    # short summary; the summary is mandatory so results stay readable
    # without preserving full command output.
    if not isinstance(summary, str) or not summary.strip():
        raise PlanError("--summary is required (short human-readable result text)")
    normalized = command.strip()
    clean_summary = summary.strip()
    if len(normalized) <= MAX_INLINE_COMMAND_LENGTH:
        return {"command": normalized, "summary": clean_summary}
    return {
        "command_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "command_length": len(normalized),
        "summary": clean_summary,
    }


def _record_result(
    repo_root: Path,
    task_dir: Path,
    task_id: str,
    check_id: str,
    result: str,
    command: str,
    exit_code: int,
    artifact_path: str | None,
    summary: str | None,
) -> str:
    plan = load_plan(task_dir)
    _require_mutable(task_dir, plan)
    task = _task_by_id(plan, task_id)
    if task.get("status") != "in_progress":
        raise PlanError(f"task {task_id} is not in_progress; start it first")
    _validate_result_exit_code(result, exit_code)
    declared = set((task.get("verification") or {}).get("required_checks") or [])
    if check_id not in declared:
        raise PlanError(
            f"'{check_id}' is not a declared required check of {task_id}",
            hint=f"declared: {', '.join(sorted(declared)) or '(none — read-only '
                 'phases with no_check_reason need no record at all)'}",
        )
    existing = (task.get("verification_results") or {}).get(check_id)
    if isinstance(existing, dict) and existing.get("result") == "fail":
        raise PlanError(
            f"{task_id}/{check_id} is recorded as fail and cannot be ignored or "
            "overwritten in this revision",
            hint="plan.py block this phase, revise the plan, and re-run the check "
                 "in the new revision",
        )
    command_fields = _command_record_fields(command, summary)
    stored = _resolve_artifact_path(repo_root, task_dir, artifact_path) if artifact_path else None
    entry: dict[str, Any] = {
        "result": result,
        "exit_code": exit_code,
        "time": _utc_now(),
        **command_fields,
    }
    if stored:
        entry["artifact"] = stored
    task.setdefault("verification_results", {})[check_id] = entry
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    event: dict[str, Any] = {
        "event": "check_recorded",
        "task": task_id,
        "check": check_id,
        "result": result,
        "exit_code": exit_code,
        **command_fields,
    }
    if stored:
        event["artifact"] = stored
    mutate_with_audit(
        task_dir,
        original_text,
        plan,
        event,
    )
    return f"verification recorded: {task_id}/{check_id} → {result}"


def cmd_record(
    repo_root: Path,
    task_dir: Path,
    task_id: str,
    result: str,
    command: str,
    exit_code: int,
    artifact_path: str | None,
    summary: str | None,
    check_id: str,
) -> str:
    if not isinstance(check_id, str) or not ID_RE.match(check_id):
        raise PlanError("--check must be a kebab-case declared check id")
    return _record_result(
        repo_root, task_dir, task_id, check_id, result, command,
        exit_code, artifact_path, summary,
    )


def cmd_done(repo_root: Path, task_dir: Path, task_id: str) -> str:
    plan = load_plan(task_dir)
    _require_mutable(task_dir, plan)
    task = _task_by_id(plan, task_id)
    if task.get("status") != "in_progress":
        raise PlanError(
            f"task {task_id} is {task.get('status')}; done requires in_progress",
        )
    by_id = {t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)}
    unmet = [
        dep for dep in task.get("depends_on") or []
        if by_id.get(dep, {}).get("status") != "completed"
    ]
    if unmet:
        raise PlanError(
            f"task {task_id} has unmet dependencies: {', '.join(unmet)}",
            hint="dependencies must be completed before done (they should also "
                 "have been before start; a drifted plan needs revise)",
        )
    verification = task.get("verification") or {}
    level = verification.get("level")
    results = task.get("verification_results") or {}
    declared_checks = verification.get("required_checks") or []
    missing_checks = [c for c in declared_checks if c not in results]
    failed = [
        check for check, entry in results.items()
        if not isinstance(entry, dict) or entry.get("result") != "pass"
    ]
    if missing_checks:
        failed.extend(f"missing:{c}" for c in missing_checks)
    if failed:
        raise PlanError(
            f"task {task_id} verification checks not all passed: {', '.join(map(str, failed))}",
            hint="record each declared check with: plan.py record <id> --check <check-id> "
                 "--result pass --command <command-id> --exit-code 0 --summary \"...\"",
        )
    registered_artifacts = {
        str(entry.get("artifact"))
        for entry in results.values()
        if isinstance(entry, dict) and entry.get("artifact")
    }
    for artifact in registered_artifacts:
        try:
            current = _resolve_artifact_path(repo_root, task_dir, str(repo_root / artifact))
        except PlanError as exc:
            raise PlanError(f"artifact file is no longer valid: {artifact}: {exc}") from exc
        if current != artifact:
            raise PlanError(f"artifact path changed after registration: {artifact}")
    if level == "report":
        # PRD 8.2: the single final acceptance report must exist in the task
        # directory and be registered through record --artifact.
        if not (task_dir / REPORT_FILE).is_file():
            raise PlanError(
                f"task {task_id} report verification requires the task-directory "
                f"file {REPORT_FILE}",
                hint=f"write {REPORT_FILE}, then: plan.py record {task_id} "
                     f"--check <check-id> --result pass --command <id> "
                     f"--exit-code 0 --summary \"...\" --artifact {REPORT_FILE}",
            )
        report_key = _artifact_requirement_key(repo_root, task_dir, REPORT_FILE)
        if report_key not in registered_artifacts:
            raise PlanError(
                f"task {task_id} must register {REPORT_FILE} through plan.py "
                "record --artifact",
                hint=f"plan.py record {task_id} --check <declared-check> --result pass "
                     f"--command <id> --exit-code 0 --summary \"...\" --artifact {REPORT_FILE}",
            )
    task["status"] = "completed"
    all_done = all(
        isinstance(t, dict) and t.get("status") == "completed"
        for t in plan.get("tasks", [])
    )
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    audit_events: list[dict[str, Any]] = [
        {
            "event": "task_completed",
            "task": task_id,
            "fingerprint": task_fingerprint(task),
        }
    ]
    if all_done:
        # Same atomic write as the completion event (AC5: no state change
        # without its audit trail, no bare append outside the rollback path).
        audit_events.append(
            {"event": "plan_completed", "revision": plan["revision"]}
        )
    mutate_with_audit(task_dir, original_text, plan, audit_events)
    return f"task {task_id} → completed" + (
        "; all tasks completed" if all_done else ""
    )


def cmd_block(repo_root: Path, task_dir: Path, task_id: str, reason: str) -> str:
    if not reason.strip():
        raise PlanError("--reason is required for block")
    plan = load_plan(task_dir)
    _require_mutable(task_dir, plan)
    task = _task_by_id(plan, task_id)
    if task.get("status") not in ("in_progress", "pending", "blocked"):
        raise PlanError(f"cannot block task {task_id} in state {task.get('status')}")
    if task.get("status") == "blocked":
        raise PlanError(f"task {task_id} is already blocked")
    task["status"] = "blocked"
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    mutate_with_audit(
        task_dir,
        original_text,
        plan,
        {"event": "task_blocked", "task": task_id, "reason": reason.strip()},
    )
    return (
        f"task {task_id} → blocked. If the plan itself is wrong, run "
        "plan.py revise; otherwise plan.py start to resume after unblocking."
    )


# ---------------------------------------------------------------------------
# Status / summaries
# ---------------------------------------------------------------------------

def compute_status(plan: dict[str, Any]) -> dict[str, Any]:
    by_id = {t.get("id"): t for t in plan.get("tasks", []) if isinstance(t, dict)}
    runnable: list[str] = []
    for task in by_id.values():
        if task.get("status") != "pending":
            continue
        if all(by_id.get(d, {}).get("status") == "completed" for d in task.get("depends_on") or []):
            runnable.append(str(task.get("id")))
    in_progress = [
        str(t.get("id")) for t in by_id.values() if t.get("status") == "in_progress"
    ]
    blocked = [str(t.get("id")) for t in by_id.values() if t.get("status") == "blocked"]
    completed = [str(t.get("id")) for t in by_id.values() if t.get("status") == "completed"]
    return {
        "revision": plan.get("revision"),
        "plan_status": plan.get("status"),
        "in_progress": in_progress,
        "runnable": sorted(runnable),
        "blocked": blocked,
        "completed": completed,
        "total": len(by_id),
    }


def format_status(task_dir: Path, repo_root: Path | None = None, *, verbose: bool = True) -> str:
    if not plan_exists(task_dir):
        return "no execution plan yet — create execution-plan.json, then run plan.py validate"
    plan = load_plan(task_dir)
    events, corrupt = read_events(task_dir)
    audit_note = (
        f"audit OK ({len(events)} events)"
        if not corrupt
        else f"AUDIT DAMAGED at lines {', '.join(map(str, corrupt))} — mutations paused"
    )
    status = compute_status(plan)
    lines = [
        f"execution plan: revision={status['revision']} status={status['plan_status']} "
        f"tasks={len(status['completed'])}/{status['total']} completed | {audit_note}",
        f"goal: {plan.get('goal', '')}",
    ]
    if not corrupt:
        # Display-only preview of the rejections that _require_mutable will
        # enforce on the next mutation (statuses and managed maps alike), so a
        # drifted plan never looks healthy in `status` and then surprises the
        # model mid-task.
        try:
            drift = status_drift(plan, events) + managed_drift(plan, events)
        except Exception:
            drift = []
        if drift:
            lines.append(
                "DRIFT (mutations will be refused until repaired via revise): "
                + "; ".join(drift)
            )
    if status["in_progress"]:
        lines.append("in_progress: " + ", ".join(status["in_progress"]))
    if status["runnable"]:
        lines.append("next runnable: " + ", ".join(status["runnable"]))
    if status["blocked"]:
        lines.append("blocked: " + ", ".join(status["blocked"]))
    if verbose:
        for task in plan.get("tasks", []):
            if not isinstance(task, dict):
                continue
            tid = task.get("id")
            state = task.get("status")
            marks: list[str] = []
            verification = task.get("verification") or {}
            results = task.get("verification_results") or {}
            missing = [
                n for n in verification.get("required_checks") or []
                if n not in results
            ]
            failed = [
                c for c, entry in results.items()
                if not isinstance(entry, dict) or entry.get("result") != "pass"
            ]
            if missing:
                marks.append(f"missing checks: {', '.join(missing)}")
            if failed:
                marks.append(f"checks pending/failed: {', '.join(map(str, failed))}")
            if verification.get("level") == "report":
                registered = {
                    str(entry.get("artifact")) for entry in results.values()
                    if isinstance(entry, dict) and entry.get("artifact")
                }
                report_key = _artifact_requirement_key(
                    repo_root or task_dir, task_dir, REPORT_FILE
                )
                if not (task_dir / REPORT_FILE).is_file():
                    marks.append(f"missing {REPORT_FILE} file")
                elif report_key not in registered:
                    marks.append(f"{REPORT_FILE} not registered via record --artifact")
            suffix = f"  ({'; '.join(marks)})" if marks else ""
            lines.append(f"  [{state:>12}] {tid}{suffix}")
    if all(t.get("status") == "completed" for t in plan.get("tasks", []) if isinstance(t, dict)):
        lines.append("ALL TASKS COMPLETED — proceed to Phase 2.2 quality check")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Edit counters (written by the optional Claude PreToolUse hook for its own
# advisory reminders). Per the two-level PRD, hooks never feed state: plan.py
# done does NOT consult these counters.
# ---------------------------------------------------------------------------

def edits_dir(repo_root: Path) -> Path:
    return repo_root / ".trellis" / ".runtime" / "plan-edits"


def edits_file(repo_root: Path, task_rel: str) -> Path:
    digest = hashlib.sha1(task_rel.encode("utf-8")).hexdigest()[:16]
    return edits_dir(repo_root) / f"{digest}.json"


def bump_edit(
    repo_root: Path, task_rel: str, revision: int, task_id: str, file_path: str
) -> int:
    """Increment and return the per-file edit count for (revision, task)."""
    path = edits_file(repo_root, task_rel)
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("revision") == revision:
                data = loaded
        except (json.JSONDecodeError, OSError):
            data = {}
    counts = data.setdefault("counts", {})
    task_counts = counts.setdefault(task_id, {})
    task_counts[file_path] = int(task_counts.get(file_path, 0)) + 1
    new_count = task_counts[file_path]
    data["revision"] = revision
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
    except OSError:
        pass  # counters are advisory; never break the edit flow over them
    return new_count


# ---------------------------------------------------------------------------
# Pattern matching for scope.write warnings (advisory only)
# ---------------------------------------------------------------------------

def scope_match(pattern: str, rel_path: str) -> bool:
    import fnmatch

    pattern = pattern.replace("\\", "/").rstrip("/")
    target = rel_path.replace("\\", "/")
    # Directory-prefix semantics: "Foo/Bar" matches everything under it.
    if fnmatch.fnmatchcase(target, pattern):
        return True
    if fnmatch.fnmatchcase(target, pattern + "/*"):
        return True
    # Translate ** so it may cross separators like the design's globs.
    translated = re.escape(pattern).replace(r"\*\*", "§§")
    translated = re.sub(r"(?<!§)\\\*", "[^/]*", translated)
    translated = translated.replace("§§", ".*")
    try:
        return re.match(f"^{translated}$", target) is not None
    except re.error:
        return False


# ---------------------------------------------------------------------------
# Compact plan breadcrumb (shared by both UserPromptSubmit hook copies)
# ---------------------------------------------------------------------------

def plan_breadcrumb(repo_root: Path, task_dir: Path) -> str:
    """Return an <execution-plan> block, or '' when the task has no plan.

    Never raises: hooks degrade silently rather than blocking the session.
    """
    try:
        if not plan_exists(task_dir):
            return ""
        lines = format_status(task_dir, repo_root, verbose=False)
        return f"<execution-plan>\n{lines}\n</execution-plan>"
    except Exception:
        return "<execution-plan>\nstate: unreadable — run plan.py status for details\n</execution-plan>"


def plan_protocol_block(repo_root: Path, task_dir: Path) -> str:
    """Execution-plan protocol + current state for implement-agent prompts.

    Works for every platform that consumes it (Claude PreToolUse rewrite,
    Codex SubagentStart, inline main sessions via workflow.md): the protocol
    text is plain markdown around shared status output.
    """
    cli = "python .trellis/scripts/plan.py"
    head = "## Trellis execution plan protocol\n"
    task_display = task_rel_dir(task_dir)
    if repo_root is not None:
        try:
            task_display = task_dir.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    base = (
        f"- State files: `{task_display}/{PLAN_FILE}` + "
        f"`{task_display}/{EVENTS_FILE}`.\n"
        f"- plan.py is the ONLY sanctioned state advancer; never hand-edit task statuses.\n"
        f"- Advance with: `{cli} --task \"<task-path>\" <command>` (validate/status/start/record/done/block/revise).\n"
        f"- Verification is two-level: `minimal` = record every declared `required_checks` result "
        f"(no phase Markdown, no mandatory raw logs); `report` = the single terminal acceptance "
        f"phase that also writes `{REPORT_FILE}` and registers it via `record --artifact`.\n"
    )
    try:
        if not plan_exists(task_dir):
            return (
                head
                + base
                + "\n**Round 1 — plan generation (MANDATORY before any source edit):**\n"
                  f"1. Read PRD/Spec/code, then create execution-plan.json (`{cli} template` prints the skeleton; "
                  "max 8 tasks, per-task depends_on/scope.write/verification {level, required_checks}; "
                  "empty required_checks only for read-only phases with a no_check_reason; "
                  "end it with a terminal level=report task (report_path "
                  "final-report.md) transitively depending on every other "
                  "phase; validation allows at most one).\n"
                  "2. Do NOT modify business source code while the plan is unapproved.\n"
                  f"3. Run `{cli} validate`. Only an approved plan unlocks editing.\n"
            )
        plan = load_plan(task_dir)
        if plan.get("status") != "approved":
            return (
                head
                + base
                + f"\nPlan exists but is '{plan.get('status')}'. Finish edits, then run `{cli} validate` "
                  "before touching source code.\n"
            )
        status = compute_status(plan)
        active = ", ".join(status["in_progress"]) or "(none)"
        return (
            head
            + base
            + f"\nApproved at revision {status['revision']}. Current in_progress: {active}; "
              f"next runnable: {', '.join(status['runnable']) or '(none)'}.\n"
              "Per phase loop: `start <id>` → batch read / batch edit / batch check inside scope.write "
              "→ `record <id> --check <declared-check> --result pass|fail --command <command-id> "
              "--exit-code <number> --summary \"<short text>\" [--artifact <task-relative-path>]` "
              "for every declared required check → `done <id>`. "
              "Do not write per-phase Markdown and do not reformat full command output; record results only.\n"
              "The terminal level=report phase additionally: confirm all dependencies completed, run and "
              f"record every declared final check, write `{task_display}/{REPORT_FILE}` summarizing changed "
              f"files, phase results, check results, skipped items, and known risks, then `record` it with "
              f"`--artifact {REPORT_FILE}` before `done`.\n"
              "A recorded fail is permanent for the revision — done refuses; recover with "
              "`block <id> --reason \"...\"` (this is also how failures are audited; there is no separate "
              "failed state) → `revise --reason \"...\"` → edit → `validate`. "
              "Read-only work (search/analysis) needs no task lock, but each edit-bearing phase does.\n"
              f"Note: `record --result pass` is your attestation of a run you actually performed; plan.py never executes "
              "checks, and independent verification stays with the Phase 2.2 review/check stage.\n"
            + "\n"
            + format_status(task_dir, repo_root, verbose=True)
            + "\n"
        )
    except PlanError as exc:
        return head + base + f"\nPlan state error: {exc}\nResolve it before editing source code.\n"
    except Exception:
        return ""


def task_rel_dir(task_dir: Path) -> str:
    return task_dir.as_posix()


# ---------------------------------------------------------------------------
# Template (printed by plan.py template)
# ---------------------------------------------------------------------------

TEMPLATE: dict[str, Any] = {
    "schema": SCHEMA_VERSION,
    "task": "<task-path>",
    "revision": 1,
    "status": "proposed",
    "audit": {"required": True, "file": EVENTS_FILE},
    "created_by": "trellis-implement",
    "goal": "<one-line goal>",
    "constraints": {
        "forbidden_git_operations": [
            "commit",
            "push",
            "tag",
            "reset",
            "restore-modified-source",
        ],
        "max_tasks": DEFAULT_MAX_TASKS,
        "max_edits_per_file": DEFAULT_MAX_EDITS_PER_FILE,
        "allow_parallel_tasks": False,
    },
    "tasks": [
        {
            "id": "discover-x",
            "title": "<phase title>",
            "status": "pending",
            "objective": "<what must be established>",
            "depends_on": [],
            "scope": {"read": ["<repo-relative glob>"], "write": []},
            "verification": {
                "level": "minimal",
                "required_checks": [],
            },
            "no_check_reason": "<why this phase is pure read-only/analysis>",
        },
        {
            "id": "edit-x",
            "title": "<phase title>",
            "status": "pending",
            "objective": "<what must change>",
            "depends_on": ["discover-x"],
            "scope": {"read": ["<path>"], "write": ["<path glob>"]},
            "verification": {
                "level": "minimal",
                "required_checks": ["<check-id>"],
            },
        },
        {
            "id": "verify-final",
            "title": "final acceptance",
            "status": "pending",
            "objective": "<what proves the task>",
            "depends_on": ["edit-x"],
            "scope": {"read": ["<path>"], "write": [REPORT_FILE]},
            "verification": {
                "level": "report",
                "required_checks": ["build", "test", "diff-check"],
                "report_path": REPORT_FILE,
            },
        },
    ],
}


def template_text() -> str:
    return json.dumps(TEMPLATE, ensure_ascii=False, indent=2)
