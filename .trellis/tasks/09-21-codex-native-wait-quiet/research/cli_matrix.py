"""Replayable driver for the CLI acceptance matrix of this task.

Runs the real template CLI (``get_context.py --mode phase``) from the template
root and prints one named ``PASS``/``FAIL`` line per case. Exit code 0 means
every case passed; 1 means at least one failed.

This replaces the descriptive ``cli-matrix-manual`` record id from p6 with a
re-runnable artifact. It also works after installation into a downstream repo:
the template root is ``<repo>/templates/embedded-c-overlay`` when that tree
exists, otherwise the repo root itself.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK_DIR.parents[2]
_TEMPLATE = REPO_ROOT / "templates" / "embedded-c-overlay"
TEMPLATE_ROOT = (
    _TEMPLATE
    if (_TEMPLATE / ".trellis" / "scripts" / "get_context.py").is_file()
    else REPO_ROOT
)
CLI = TEMPLATE_ROOT / ".trellis" / "scripts" / "get_context.py"

STEP_2_1_2_TITLE = "#### 2.1.2 Codex 主会话：原生子代理派发与静默等待"
CODEX_ONLY_TERMS = (
    "exec_command",
    "write_stdin",
    "yield_time_ms",
    "session_id",
    "wait_agent",
    "spawn_agent",
)
CHINESE_FROZEN_PHRASES = ("取该工具允许的最大值", "交互中断", "最小最终结果")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(CLI), "--mode", "phase", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        cwd=str(TEMPLATE_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def _both_contracts(*args: str) -> bool:
    result = run(*args)
    return (
        result.returncode == 0
        and "write_stdin" in result.stdout
        and "wait_agent" in result.stdout
    )


def step_2_1_codex() -> bool:
    return _both_contracts("--step", "2.1", "--platform", "codex")


def step_2_1_plain() -> bool:
    return _both_contracts("--step", "2.1")


def step_2_1_claude() -> bool:
    result = run("--step", "2.1", "--platform", "claude")
    return (
        result.returncode == 0
        and "Spawn the implement sub-agent" in result.stdout
        and "wait_agent" not in result.stdout
    )


def step_2_1_claude_code() -> bool:
    result = run("--step", "2.1", "--platform", "claude-code")
    return (
        result.returncode == 0
        and "Spawn the implement sub-agent" in result.stdout
        and all(term not in result.stdout for term in CODEX_ONLY_TERMS)
    )


def step_2_1_opencode() -> bool:
    result = run("--step", "2.1", "--platform", "opencode")
    return (
        result.returncode == 0
        and "Spawn the implement sub-agent" in result.stdout
    )


def step_2_1_1() -> bool:
    result = run("--step", "2.1.1")
    return (
        result.returncode == 0
        and "write_stdin" in result.stdout
        and "wait_agent" not in result.stdout
    )


def step_2_1_2() -> bool:
    result = run("--step", "2.1.2")
    return (
        result.returncode == 0
        and STEP_2_1_2_TITLE in result.stdout
        and "wait_agent" in result.stdout
        and "spawn_agent" in result.stdout
    )


def step_2_1_2_claude_code_filtered() -> bool:
    result = run("--step", "2.1.2", "--platform", "claude-code")
    return (
        result.returncode == 0
        and STEP_2_1_2_TITLE in result.stdout
        and all(term not in result.stdout for term in CODEX_ONLY_TERMS)
        and all(phrase not in result.stdout for phrase in CHINESE_FROZEN_PHRASES)
    )


def step_2_2() -> bool:
    result = run("--step", "2.2")
    return (
        result.returncode == 0
        and "write_stdin" not in result.stdout
        and "wait_agent" not in result.stdout
    )


def _bare_step_exit2(step: str) -> bool:
    return run("--step", step).returncode == 2


def bare_step_1() -> bool:
    return _bare_step_exit2("1")


def bare_step_2() -> bool:
    return _bare_step_exit2("2")


def bare_step_3() -> bool:
    return _bare_step_exit2("3")


def phase_index() -> bool:
    result = run()
    return result.returncode == 0 and "Phase Index" in result.stdout


CASES = (
    ("step-2.1-codex-both-contracts", step_2_1_codex),
    ("step-2.1-plain-both-contracts", step_2_1_plain),
    ("step-2.1-claude-dispatch-no-wait", step_2_1_claude),
    ("step-2.1-claude-code-no-codex-terms", step_2_1_claude_code),
    ("step-2.1-opencode-dispatch", step_2_1_opencode),
    ("step-2.1.1-exit0", step_2_1_1),
    ("step-2.1.2-exit0", step_2_1_2),
    ("step-2.1.2-claude-code-filtered", step_2_1_2_claude_code_filtered),
    ("step-2.2-clean", step_2_2),
    ("bare-step-1-exit2", bare_step_1),
    ("bare-step-2-exit2", bare_step_2),
    ("bare-step-3-exit2", bare_step_3),
    ("phase-index", phase_index),
)


def main() -> int:
    print(f"template_root: {TEMPLATE_ROOT.as_posix()}")
    failures = 0
    for name, check in CASES:
        try:
            ok = bool(check())
        except Exception as exc:  # noqa: BLE001 - report and keep going
            ok = False
            print(f"FAIL {name} ({type(exc).__name__}: {exc})")
        else:
            print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            failures += 1
    print(f"cli matrix: {len(CASES) - failures}/{len(CASES)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())