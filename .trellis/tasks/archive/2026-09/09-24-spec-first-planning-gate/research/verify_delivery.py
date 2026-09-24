#!/usr/bin/env python3
"""Replayable delivery checks for task 09-24-spec-first-planning-gate.

Usage:
    python research/verify_delivery.py [item ...]   # no args = run every item

Each item prints ``PASS <name>`` or ``FAIL <name>: <reason>``; the process
exits 1 when any selected item fails. Items are pure text/CLI/git checks:
they never spawn agents and never call ``trellis channel``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_ROOT = REPO_ROOT / "templates" / "embedded-c-overlay"
WORKFLOW = TEMPLATE_ROOT / ".trellis" / "workflow.md"
START_MD = TEMPLATE_ROOT / ".opencode" / "commands" / "trellis" / "start.md"
BRAINSTORM = TEMPLATE_ROOT / ".opencode" / "skills" / "trellis-brainstorm" / "SKILL.md"
ADAPTER_AGENTS = (
    TEMPLATE_ROOT / ".agents" / "skills" / "__PROJECT_PREFIX__-trellis-grill-adapter" / "SKILL.md"
)
ADAPTER_OPENCODE = (
    TEMPLATE_ROOT / ".opencode" / "skills" / "__PROJECT_PREFIX__-trellis-grill-adapter" / "SKILL.md"
)
HOOKS = (
    TEMPLATE_ROOT / ".codex" / "hooks" / "session-start.py",
    TEMPLATE_ROOT / ".claude" / "hooks" / "session-start.py",
    TEMPLATE_ROOT / ".opencode" / "lib" / "session-utils.js",
)
BASELINE = Path(__file__).resolve().parent / "scope-baseline.txt"
TASK_DIR_REL = ".trellis/tasks/09-24-spec-first-planning-gate/"

# Contiguous fragments as they appear in both the Python hooks (implicit string
# concatenation splits the sentence across lines) and the JS template literal.
# Each planning branch must contribute exactly one of each.
SPEC_FRAGMENTS = (
    "Specs: Read the relevant .trellis/spec indexes and guideline files",
    "persist consulted specs in prd.md",
    'under "## Spec References".',
)

# Lines that belong to neighbouring work or to deliberate no-touch zones.
# A diff hunk must never add or remove these literals.
FORBIDDEN_ZONE_NEEDLES = (
    "[workflow-state:no_task]",
    "No active task. Default to doing the work",
    "Next-Action: Default: do the work",
    "Phase 2 source edits require an approved live",
    "### Loading Step Detail",
    "get_context.py --mode phase --step <step>",
    "Step detail: `python ./.trellis/scripts/get_context.py --mode phase --step <X.Y>`",
    "task.py init-context` was removed",
    "python ./.trellis/scripts/get_context.py --mode phase --step 1",
    "--platform opencode",
    "#### 2.1.1",
    "#### 2.1.2",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _block(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin : finish + len(end)]


def item_step_1_1_cli() -> list[str]:
    """Real CLI delivery: --mode phase --step 1.1 from the template root."""
    proc = _run(
        [
            sys.executable,
            "-B",
            str(TEMPLATE_ROOT / ".trellis" / "scripts" / "get_context.py"),
            "--mode",
            "phase",
            "--step",
            "1.1",
        ],
        cwd=TEMPLATE_ROOT,
    )
    failures: list[str] = []
    if proc.returncode != 0:
        failures.append(f"get_context.py exit {proc.returncode}: {proc.stderr.strip()[:200]}")
        return failures
    for needle in (
        "Spec discovery (mandatory first evidence step)",
        "## Spec References",
    ):
        if needle not in proc.stdout:
            failures.append(f"step 1.1 output missing {needle!r}")
    return failures


def item_gate_text_sync() -> list[str]:
    """workflow.md state blocks / 1.4 / 1.5 and start.md describe the new gate."""
    workflow = _read(WORKFLOW)
    start_md = _read(START_MD)
    failures: list[str] = []

    for state in ("planning", "planning-inline"):
        block = _block(workflow, f"[workflow-state:{state}]", f"[/workflow-state:{state}]")
        for needle in ("## Spec References", "curated entry"):
            if needle not in block:
                failures.append(f"[workflow-state:{state}] missing {needle!r}")

    rejects = [
        line
        for line in workflow.splitlines()
        if "rejects planning tasks unless" in line
    ]
    if not rejects:
        failures.append("workflow.md 1.4 gate-rejection sentence not found")
    else:
        for needle in ("## Spec References", "curated entry"):
            if needle not in " ".join(rejects):
                failures.append(f"1.4 gate-rejection sentence missing {needle!r}")

    if "the start gate rejects missing or seed-only manifests" not in workflow:
        failures.append("workflow.md 1.4 seed-only rejection wording missing")
    if "| `prd.md` contains a `## Spec References` section" not in workflow:
        failures.append("workflow.md 1.5 completion table row missing")

    planning_bullet = _block(
        start_md,
        "- **Active task status `planning` + `prd.md` exists**",
        "never skip those gates.",
    )
    for needle in ("## Spec References", "curated entry"):
        if needle not in planning_bullet:
            failures.append(f"start.md planning bullet missing {needle!r}")
    return failures


def item_forbidden_zones() -> list[str]:
    """No diff hunk adds or removes a forbidden-zone literal."""
    proc = _run(["git", "diff", "-U0", "--", "templates/embedded-c-overlay"], cwd=REPO_ROOT)
    if proc.returncode != 0:
        return [f"git diff exit {proc.returncode}: {proc.stderr.strip()[:200]}"]
    changed = [
        line
        for line in proc.stdout.splitlines()
        if line[:1] in "+-" and not line.startswith("+++") and not line.startswith("---")
    ]
    failures: list[str] = []
    for needle in FORBIDDEN_ZONE_NEEDLES:
        hits = [line for line in changed if needle in line]
        if hits:
            failures.append(f"forbidden-zone literal changed: {needle!r}")
    return failures


def item_adapter_parity() -> list[str]:
    if ADAPTER_AGENTS.read_bytes() != ADAPTER_OPENCODE.read_bytes():
        return ["adapter copies differ (.agents vs .opencode)"]
    return []


def item_skill_gate_text() -> list[str]:
    brainstorm = _read(BRAINSTORM)
    failures: list[str] = []
    for needle in (
        "get_context.py --mode packages",
        "## Spec References",
        "(enforced by the start gate)",
    ):
        if needle not in brainstorm:
            failures.append(f"brainstorm SKILL missing {needle!r}")

    for path in (ADAPTER_AGENTS, ADAPTER_OPENCODE):
        text = _read(path)
        label = path.relative_to(TEMPLATE_ROOT).as_posix()
        for needle in ("get_context.py --mode packages", "## Spec References"):
            if needle not in text:
                failures.append(f"{label} missing {needle!r}")
        if "only verifies the persisted convergence and approval markers" in text:
            failures.append(f"{label} still carries the stale 'only verifies' gate wording")
        if "light|standard|reinforced|comprehensive|strict" not in text:
            failures.append(f"{label} lost the canonical five-level enumeration")
    return failures


def item_hook_redline() -> list[str]:
    failures: list[str] = []
    for path in HOOKS:
        text = _read(path)
        label = path.relative_to(TEMPLATE_ROOT).as_posix()
        if "validate_planning_gate" in text:
            failures.append(f"{label} leaks validate_planning_gate")
        for fragment in SPEC_FRAGMENTS:
            count = text.count(fragment)
            if count != 2:
                failures.append(
                    f"{label} fragment occurs {count} times, expected 2: {fragment!r}"
                )
    return failures


SMOKE_PRD = """# Smoke task

## Workflow Settings

- Review level: standard

## Goal

Smoke.

## Spec References

- `.trellis/spec/smoke/index.md` — smoke reason.

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
"""

SMOKE_ENTRY = json.dumps(
    {"file": ".trellis/spec/smoke/index.md", "reason": "smoke"}, ensure_ascii=False
)
SMOKE_SEED = json.dumps({"_example": "seed"}, ensure_ascii=False)


def _smoke_repo(tmp: Path, *, prd: str, implement_lines: list[str]) -> Path:
    root = tmp
    shutil.copytree(TEMPLATE_ROOT / ".trellis" / "scripts", root / ".trellis" / "scripts")
    (root / ".claude").mkdir()
    task_dir = root / ".trellis" / "tasks" / "t1"
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(
        json.dumps(
            {"status": "planning", "meta": {"planning_ready": "true", "plan_approved": "true"}}
        ),
        encoding="utf-8",
    )
    (task_dir / "prd.md").write_text(prd, encoding="utf-8")
    (task_dir / "implement.jsonl").write_text("\n".join(implement_lines) + "\n", encoding="utf-8")
    (task_dir / "check.jsonl").write_text(SMOKE_ENTRY + "\n", encoding="utf-8")
    return root


def _start(root: Path) -> subprocess.CompletedProcess:
    return _run(
        [sys.executable, "-B", ".trellis/scripts/task.py", "start", ".trellis/tasks/t1"],
        cwd=root,
    )


def item_gate_cli_smoke() -> list[str]:
    """`task.py start` wiring: repo_root passed, gate A/B enforced, ready passes."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _smoke_repo(Path(tmp), prd=SMOKE_PRD, implement_lines=[SMOKE_SEED])
        proc = _start(root)
        if proc.returncode == 0 or "implement.jsonl" not in proc.stdout:
            failures.append(
                "seed-only manifest was not rejected by `task.py start` "
                f"(exit {proc.returncode})"
            )

    with tempfile.TemporaryDirectory() as tmp:
        prd = SMOKE_PRD.replace(
            "## Spec References\n\n- `.trellis/spec/smoke/index.md` — smoke reason.\n\n", ""
        )
        root = _smoke_repo(Path(tmp), prd=prd, implement_lines=[SMOKE_ENTRY])
        proc = _start(root)
        if proc.returncode == 0 or "Spec References" not in proc.stdout:
            failures.append(
                "missing Spec References section was not rejected by `task.py start` "
                f"(exit {proc.returncode})"
            )

    with tempfile.TemporaryDirectory() as tmp:
        root = _smoke_repo(Path(tmp), prd=SMOKE_PRD, implement_lines=[SMOKE_ENTRY])
        proc = _start(root)
        if proc.returncode != 0:
            failures.append(
                "ready task was rejected by `task.py start`: "
                + textwrap.shorten((proc.stdout + proc.stderr).strip(), 200)
            )
        else:
            status = json.loads(
                (root / ".trellis" / "tasks" / "t1" / "task.json").read_text(encoding="utf-8")
            ).get("status")
            if status != "in_progress":
                failures.append(f"ready smoke task status is {status!r}, expected in_progress")
    return failures


def item_scope_status() -> list[str]:
    """git status stays inside the allowed scope; no bytecode caches."""
    baseline = {
        line[3:].strip()
        for line in _read(BASELINE).splitlines()
        if line.strip()
    }
    proc = _run(["git", "status", "--porcelain"], cwd=REPO_ROOT)
    if proc.returncode != 0:
        return [f"git status exit {proc.returncode}"]
    failures: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if path in baseline:
            continue
        if path.startswith("templates/embedded-c-overlay/") or path.startswith(TASK_DIR_REL):
            continue
        failures.append(f"out-of-scope change: {path}")

    for pattern in ("__pycache__", "*.pyc", "*.pyo"):
        cached = sorted(TEMPLATE_ROOT.rglob(pattern))
        if cached:
            failures.append(
                f"bytecode cache in template: {cached[0].relative_to(TEMPLATE_ROOT).as_posix()}"
            )
    return failures


ITEMS = {
    "step-1-1-cli": item_step_1_1_cli,
    "gate-text-sync": item_gate_text_sync,
    "forbidden-zones": item_forbidden_zones,
    "adapter-parity": item_adapter_parity,
    "skill-gate-text": item_skill_gate_text,
    "hook-redline": item_hook_redline,
    "gate-cli-smoke": item_gate_cli_smoke,
    "scope-status": item_scope_status,
}


def main(argv: list[str]) -> int:
    selected = argv or list(ITEMS)
    unknown = [name for name in selected if name not in ITEMS]
    if unknown:
        print(f"FAIL unknown item(s): {', '.join(unknown)}")
        return 1
    failed = 0
    for name in selected:
        failures = ITEMS[name]()
        if failures:
            failed += 1
            for reason in failures:
                print(f"FAIL {name}: {reason}")
        else:
            print(f"PASS {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))