"""Execution-plan state machine shared by plan.py and platform hooks.

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
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLAN_FILE = "execution-plan.json"
EVENTS_FILE = "execution-events.jsonl"
SCHEMA_VERSION = 2

PLAN_STATUSES = ("proposed", "approved")
TASK_STATUSES = ("pending", "in_progress", "completed", "blocked")

DEFAULT_MAX_TASKS = 8
DEFAULT_MAX_EDITS_PER_FILE = 5

# Kebab-ish identifier for task ids and registered verification check ids.
# Enforcing identifier shape (no spaces / shell metacharacters) is what keeps
# declared verification checks as declarative IDs.
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.\-]*$")

# Fields that must not be silently edited while a plan is approved.
_GUARDED_TASK_FIELDS = (
    "id",
    "title",
    "objective",
    "depends_on",
    "scope",
    "batch_groups",
    "risk",
    "verification",
)
# Fields plan.py manages inside a task; models must not hand-edit them.
_MANAGED_TASK_FIELDS = ("verification_results",)

RISK_LEVELS = ("normal", "high", "final")
VERIFICATION_LEVELS = ("minimal", "raw", "report")
MINIMUM_VERIFICATION_LEVEL = {
    "normal": "minimal",
    "high": "raw",
    "final": "report",
}
DEFAULT_MINIMAL_RESULT_ID = "phase-result"
MAX_INLINE_COMMAND_LENGTH = 512
MAX_COMMAND_SUMMARY_LENGTH = 160


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
    task_dir: Path, original_text: str, plan: dict[str, Any], event: dict[str, Any]
) -> None:
    """Save the new plan, then append its audit event.

    If the audit append fails, the plan file is restored to ``original_text``
    so the JSON state never advances without its event. This is the design's
    rollback requirement; failures here are disk-level and reported loudly.
    """
    save_plan(task_dir, plan)
    try:
        append_event(task_dir, event)
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


def _validate_string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list):
        raise PlanError(f"{where}: must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PlanError(f"{where}: entries must be non-empty strings")
        result.append(item.strip())
    if len(set(result)) != len(result):
        raise PlanError(f"{where}: duplicate entries")
    return result


def validate_plan_shape(plan: dict[str, Any], task_rel: str) -> list[str]:
    """Structural validation. Returns list of human-readable issues (empty = OK)."""
    issues: list[str] = []

    def issue(msg: str) -> None:
        issues.append(msg)

    if plan.get("schema") != SCHEMA_VERSION:
        issue(f"schema must be {SCHEMA_VERSION}")
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
        if any(field in task for field in ("required_evidence", "evidence", "check_results", "checks")):
            issue(f"{where}: legacy verification fields are not supported; use risk and verification")
        risk = task.get("risk")
        if risk not in RISK_LEVELS:
            issue(f"{where}.risk must be one of {RISK_LEVELS}")
        verification = task.get("verification")
        if not isinstance(verification, dict):
            issue(f"{where}.verification must be an object")
            verification = {}
        level = verification.get("level")
        if level not in VERIFICATION_LEVELS:
            issue(f"{where}.verification.level must be one of {VERIFICATION_LEVELS}")
        violation = _verification_level_violation(risk, level)
        if violation:
            issue(f"{where}: {violation['rule']} (requested {level})")
        try:
            checks = _validate_id_list(
                verification.get("checks", []), f"{where}.verification.checks",
                allow_empty=True,
            )
        except PlanError as exc:
            issue(str(exc))
            checks = []
        try:
            artifacts = verification.get("required_artifacts", [])
            artifacts = _validate_string_list(artifacts, f"{where}.verification.required_artifacts")
            for artifact in artifacts:
                _validate_relative_path(artifact, f"{where}.verification.required_artifacts")
            if level == "raw" and not artifacts:
                issue(f"{where}: verification.level=raw requires required_artifacts")
            report_artifacts = [
                artifact for artifact in artifacts if artifact.lower().endswith(".md")
            ]
            if level == "report" and report_artifacts != ["final-report.md"]:
                issue(
                    f"{where}: verification.level=report requires exactly "
                    "required_artifacts=[\"final-report.md\"]"
                )
        except PlanError as exc:
            issue(str(exc))
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
                        _validate_relative_path(entry, f"{where}.scope.{key}")
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
            if dep not in by_id:
                issue(f"task {tid} depends on unknown id: {dep}")
            if dep == tid:
                issue(f"task {tid} depends on itself")
    cycle = _find_cycle(by_id)
    if cycle:
        issue("dependency cycle: " + " -> ".join(cycle))

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
            if dep in by_id:
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


def _verification_level_violation(risk: Any, level: Any) -> dict[str, str] | None:
    """Return the canonical minimum-level violation for one risk/level pair."""
    minimum = MINIMUM_VERIFICATION_LEVEL.get(risk)
    if not minimum or level not in VERIFICATION_LEVELS:
        return None
    if VERIFICATION_LEVELS.index(level) >= VERIFICATION_LEVELS.index(minimum):
        return None
    return {
        "risk": str(risk),
        "requested_level": str(level),
        "minimum_level": minimum,
        "rule": f"risk={risk} requires level>={minimum}",
        "reason": "verification level is below the minimum allowed for this risk",
    }


def _verification_policy_issues(plan: dict[str, Any]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for task in plan.get("tasks", []):
        if not isinstance(task, dict):
            continue
        risk = task.get("risk")
        verification = task.get("verification")
        level = verification.get("level") if isinstance(verification, dict) else None
        violation = _verification_level_violation(risk, level)
        if violation:
            violations.append({"task_id": str(task.get("id", "")), **violation})
    return violations


def _write_reject_reports(task_dir: Path, repo_root: Path, plan: dict[str, Any], violations: list[dict[str, str]]) -> list[str]:
    report_dir = task_dir / "reject-reports"
    written: list[str] = []
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        for violation in violations:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            short_hash = secrets.token_hex(4)
            report_path = report_dir / f"reject-{timestamp}-{short_hash}.json"
            report = {
                "type": "verification-policy-rejection",
                "time": _utc_now(),
                "task": task_rel_path(repo_root, task_dir),
                "revision": plan.get("revision"),
                "plan_fingerprint": plan_fingerprint(plan),
                **violation,
                "reasons": [violation["reason"]],
            }
            _atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            written.append(rel_posix(repo_root, report_path))
    except OSError as exc:
        raise PlanError(
            "verification policy rejected the plan, and reject_report could not be written: "
            f"{exc}"
        ) from exc
    return written


def _reject_report_suffix(
    task_dir: Path,
    repo_root: Path,
    plan: dict[str, Any],
    violations: list[dict[str, str]],
) -> str:
    """Write rejection reports without hiding the original validation issues."""
    if not violations:
        return ""
    try:
        reports = _write_reject_reports(task_dir, repo_root, plan, violations)
    except PlanError as exc:
        return f"; reject report write failed: {exc}"
    return f"; reject reports: {', '.join(reports)}" if reports else ""


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
            violations = _verification_policy_issues(plan)
            suffix = _reject_report_suffix(task_dir, repo_root, plan, violations)
            raise PlanError("approved plan failed re-validation:\n- " + "\n- ".join(issues) + suffix)
        stored = plan.get("approved_fingerprint")
        if plan_fingerprint(plan) != stored:
            raise PlanError(
                "approved plan content changed without revising",
                hint="run plan.py revise --reason \"...\" before editing the plan",
            )
        if int(plan.get("revision", 0)) != _expected_revision(events):
            raise PlanError("approved plan revision disagrees with the audit history")
        return f"plan already approved at revision {plan['revision']} (no changes)"

    issues = validate_plan_shape(plan, task_rel)

    revision = plan.get("revision")
    if isinstance(revision, int) and revision != _expected_revision(events):
        issues.append(
            f"revision {revision} disagrees with audit history "
            f"(expected {_expected_revision(events)}); bump it only via plan.py revise"
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
        violations = _verification_policy_issues(plan)
        suffix = _reject_report_suffix(task_dir, repo_root, plan, violations)
        raise PlanError("plan validation failed:\n- " + "\n- ".join(issues) + suffix)

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
        raise PlanError(
            "only the currently approved plan revision may be revised",
            hint="an unapproved (proposed) plan can simply be edited, then validated",
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
        if task.get("status") in ("in_progress", "blocked"):
            reset.append(str(task.get("id")))
        task["status"] = "completed" if task.get("id") in completed else "pending"
        if task["status"] != "completed":
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


def replay_verification_results(
    events: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Replay verification results from check_recorded events.

    Mirrors replay_statuses for the managed fields so _require_mutable can
    reject hand-forged verification results, not just hand-forged
    statuses. Completed tasks compare against the whole log (their maps are
    preserved across revisions); other tasks only against events since the
    last boundary.
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
    boundary = _last_boundary_index(events)
    results: dict[str, dict[str, Any]] = {tid: {} for tid in task_ids}
    for index, event in enumerate(events):
        tid = str(event.get("task") or "")
        if tid not in task_ids:
            continue
        if tid not in completed and index <= boundary:
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
            hint="verification results may only be registered through plan.py record/check",
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
    normalized = command.strip()
    clean_summary = summary.strip() if isinstance(summary, str) and summary.strip() else None
    if len(normalized) <= MAX_INLINE_COMMAND_LENGTH:
        fields: dict[str, Any] = {"command": normalized}
        if clean_summary:
            fields["summary"] = clean_summary
        return fields
    if not clean_summary:
        clean_summary = normalized[:MAX_COMMAND_SUMMARY_LENGTH].rstrip() + "…"
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
    declared = set((task.get("verification") or {}).get("checks") or [])
    if declared and check_id not in declared:
        raise PlanError(
            f"'{check_id}' is not a registered verification check of {task_id}",
            hint=f"registered: {', '.join(sorted(declared))}",
        )
    if not declared and check_id != DEFAULT_MINIMAL_RESULT_ID:
        raise PlanError(
            f"tasks without declared checks use the fixed result id '{DEFAULT_MINIMAL_RESULT_ID}'"
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
    check_id: str | None = None,
) -> str:
    plan = load_plan(task_dir)
    task = _task_by_id(plan, task_id)
    checks = (task.get("verification") or {}).get("checks") or []
    if checks:
        if check_id is None and command in checks:
            check_id = command
        if check_id is None:
            raise PlanError(
                "record requires --check <declared-check-id> when --command is an actual command"
            )
        if not ID_RE.match(check_id):
            raise PlanError(f"--check '{check_id}' is not a kebab-case identifier")
        if check_id not in checks:
            raise PlanError(
                f"'{check_id}' is not a declared verification check of {task_id}",
                hint=f"declared: {', '.join(map(str, checks))}",
            )
    else:
        if check_id is not None:
            raise PlanError("--check is not allowed when verification.checks is empty")
        check_id = DEFAULT_MINIMAL_RESULT_ID
    return _record_result(
        repo_root, task_dir, task_id, check_id, result, command,
        exit_code, artifact_path, summary,
    )


def cmd_check(
    repo_root: Path, task_dir: Path, task_id: str, check_id: str,
    result: str, artifact_path: str | None,
) -> str:
    if result not in ("pass", "fail"):
        raise PlanError("result must be pass|fail")
    return _record_result(
        repo_root, task_dir, task_id, check_id, result, check_id,
        0 if result == "pass" else 1, artifact_path, None,
    )


def cmd_done(repo_root: Path, task_dir: Path, task_id: str) -> str:
    plan = load_plan(task_dir)
    _require_mutable(task_dir, plan)
    task = _task_by_id(plan, task_id)
    if task.get("status") != "in_progress":
        raise PlanError(
            f"task {task_id} is {task.get('status')}; done requires in_progress",
        )
    verification = task.get("verification") or {}
    level = verification.get("level")
    results = task.get("verification_results") or {}
    if not results:
        raise PlanError(
            f"task {task_id} has no verification result",
            hint="record a result with: plan.py record",
        )
    declared_checks = verification.get("checks") or []
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
            hint="record each result with: plan.py record or plan.py check",
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
    if level in ("raw", "report"):
        required_artifacts = verification.get("required_artifacts") or []
        missing_artifacts = [
            a for a in required_artifacts
            if _artifact_requirement_key(repo_root, task_dir, a) not in registered_artifacts
        ]
        if missing_artifacts:
            raise PlanError(
                f"task {task_id} missing required artifacts: {', '.join(missing_artifacts)}",
                hint="record each artifact with --artifact",
            )
    declared_reports = [
        _artifact_requirement_key(repo_root, task_dir, artifact)
        for artifact in verification.get("required_artifacts") or []
        if str(artifact).lower().endswith(".md")
    ]
    if level == "report" and not any(
        report_path in registered_artifacts for report_path in declared_reports
    ):
        raise PlanError(
            f"task {task_id} report verification requires a final Markdown artifact",
            hint="record the final report with --artifact <path>.md",
        )
    over = edits_over_limit(repo_root, plan, task_id)
    if over:
        detail = ", ".join(f"{f}:{n}" for f, n in over)
        raise PlanError(
            f"task {task_id} exceeded constraints.max_edits_per_file ({detail})",
            hint="this counter comes from the PreToolUse reminder hook; if it is "
                 "wrong, group edits or revise the plan limit consciously",
        )
    task["status"] = "completed"
    original_text = plan_path(task_dir).read_text(encoding="utf-8")
    events_after: list[str] = []
    mutate_with_audit(
        task_dir,
        original_text,
        plan,
        {
            "event": "task_completed",
            "task": task_id,
            "fingerprint": task_fingerprint(task),
        },
    )
    if all(
        isinstance(t, dict) and t.get("status") == "completed" for t in plan.get("tasks", [])
    ):
        append_event(task_dir, {"event": "plan_completed", "revision": plan["revision"]})
        events_after.append("all tasks completed")
    return f"task {task_id} → completed" + (
        "; " + "; ".join(events_after) if events_after else ""
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
            missing = [n for n in verification.get("checks") or [] if n not in results]
            failed = [
                c for c, entry in results.items()
                if not isinstance(entry, dict) or entry.get("result") != "pass"
            ]
            if missing:
                marks.append(f"missing checks: {', '.join(missing)}")
            if failed:
                marks.append(f"checks pending/failed: {', '.join(map(str, failed))}")
            level = verification.get("level")
            if level in ("raw", "report"):
                required = verification.get("required_artifacts") or []
                registered = {
                    str(entry.get("artifact")) for entry in results.values()
                    if isinstance(entry, dict) and entry.get("artifact")
                }
                absent = [
                    a for a in required
                    if _artifact_requirement_key(repo_root or task_dir, task_dir, a) not in registered
                ]
                if absent:
                    marks.append(f"missing artifacts: {', '.join(absent)}")
            required = verification.get("required_artifacts") or []
            declared_reports = {
                _artifact_requirement_key(repo_root or task_dir, task_dir, artifact)
                for artifact in required
                if str(artifact).lower().endswith(".md")
            }
            if level == "report" and not any(
                str(entry.get("artifact", "")) in declared_reports
                for entry in results.values() if isinstance(entry, dict)
            ):
                marks.append("missing final report")
            suffix = f"  ({'; '.join(marks)})" if marks else ""
            lines.append(f"  [{state:>12}] {tid}{suffix}")
    if all(t.get("status") == "completed" for t in plan.get("tasks", []) if isinstance(t, dict)):
        lines.append("ALL TASKS COMPLETED — proceed to Phase 2.2 quality check")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Edit counters (written by the optional Claude PreToolUse hook, read by done)
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


def edits_over_limit(
    repo_root: Path, plan: dict[str, Any], task_id: str
) -> list[tuple[str, int]]:
    """Return [(file, count)] beyond constraints.max_edits_per_file.

    Empty when the counting hook never ran (e.g. Codex, inline, or hooks
    disabled): the limit is advisory there, per the design's rule that all
    hard rejection must live in plan.py where it can observe the fact.
    """
    task_rel = plan.get("task")
    revision = plan.get("revision")
    if not isinstance(task_rel, str) or not isinstance(revision, int):
        return []
    path = edits_file(repo_root, task_rel)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict) or data.get("revision") != revision:
        return []
    limits = (plan.get("constraints") or {}).get("max_edits_per_file", DEFAULT_MAX_EDITS_PER_FILE)
    if not isinstance(limits, int):
        limits = DEFAULT_MAX_EDITS_PER_FILE
    task_counts = (data.get("counts") or {}).get(task_id) or {}
    return [
        (f, int(n)) for f, n in task_counts.items() if isinstance(n, int) and n > limits
    ]


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
        f"- Advance with: `{cli} --task \"<task-path>\" <command>` (validate/status/start/record/check/done/block/revise).\n"
    )
    try:
        if not plan_exists(task_dir):
            return (
                head
                + base
                + "\n**Round 1 — plan generation (MANDATORY before any source edit):**\n"
                  f"1. Read PRD/Spec/code, then create execution-plan.json (`{cli} template` prints the skeleton; "
                  "max 8 tasks, per-task depends_on/scope.write/risk/verification).\n"
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
              "Per task loop: `start <id>` → work → `record <id> --result pass|fail --command <id-or-command> --exit-code <number> [--check <declared-check-id>]` "
              "(or the compatible `check <id> <name> --result pass`; use "
              "`phase-result` as the name when no checks are declared) "
              "→ `done <id>`. When the plan itself is wrong or a phase fails: `block <id> --reason \"...\"` (this is also "
              "how failures are audited; there is no separate failed state), then `revise --reason \"...\"` "
              "→ edit → `validate`. Read-only work (search/analysis) needs no task lock, but each edit-bearing phase does.\n"
              "Note: `check --result pass` is your attestation of a run you actually performed; plan.py never executes "
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
            "batch_groups": ["<optional group ids>"],
            "risk": "normal",
            "verification": {
                "level": "minimal",
                "checks": ["<check-id>"],
                "required_artifacts": [],
            },
        },
        {
            "id": "edit-x",
            "title": "<phase title>",
            "status": "pending",
            "objective": "<what must change>",
            "depends_on": ["discover-x"],
            "scope": {"read": ["<path>"], "write": ["<path glob>"]},
            "risk": "normal",
            "verification": {
                "level": "minimal",
                "checks": ["<check-id>"],
                "required_artifacts": [],
            },
        },
        {
            "id": "verify",
            "title": "unified verification",
            "status": "pending",
            "objective": "<what proves the task>",
            "depends_on": ["edit-x"],
            "scope": {"read": ["<path>"], "write": []},
            "risk": "final",
            "verification": {
                "level": "report",
                "checks": ["final-review"],
                "required_artifacts": ["final-report.md"],
            },
        },
    ],
}


def template_text() -> str:
    return json.dumps(TEMPLATE, ensure_ascii=False, indent=2)
