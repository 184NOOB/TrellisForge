#!/usr/bin/env python3
"""Trellis execution-plan CLI — the only sanctioned state advancer.

Platform-neutral: works identically under Claude Code, Codex, and inline
sessions because it is plain command-line flow; hooks may DISPLAY plan state
but never advance it. Two-level verification (schema 3): minimal records
declared required_checks, report produces the single final-report.md.
See .trellis/workflow.md Phase 2, the Trellis execution-plan design,
and the Trellis two-level verification PRD.

Usage (from the repo root):

    python .trellis/scripts/plan.py [--task <path>] template
    python .trellis/scripts/plan.py [--task <path>] validate
    python .trellis/scripts/plan.py [--task <path>] status [--quiet]
    python .trellis/scripts/plan.py [--task <path>] start <task-id>
    python .trellis/scripts/plan.py [--task <path>] record <task-id> --check <check-id> --result pass|fail --command <command-id> --exit-code <number> --summary <text> [--artifact <task-relative-path>]
    python .trellis/scripts/plan.py [--task <path>] done <task-id>
    python .trellis/scripts/plan.py [--task <path>] block <task-id> --reason "..."
    python .trellis/scripts/plan.py [--task <path>] revise --reason "..."

Exit codes: 0 = success, 1 = rejected or invalid state (reason printed to
stderr), 2 = argparse usage error (bad/missing flags). `--task` may appear
before or after the subcommand. Sub-agents should always pass --task with the
path from their dispatch prompt's `Active task:` line for deterministic
resolution.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.execution_plan import (  # noqa: E402
    PlanError,
    cmd_block,
    cmd_done,
    cmd_record,
    cmd_revise,
    cmd_start,
    cmd_validate,
    format_status,
    plan_exists,
    resolve_task_dir,
    template_text,
)
from common.paths import get_repo_root  # noqa: E402

if sys.platform.startswith("win"):
    for _name in ("stdout", "stderr"):
        _stream = getattr(sys, _name, None)
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    # --task is accepted globally AND on every subcommand (SUPPRESS default so
    # a not-given sub-level flag never clobbers the global value).
    task_parent = argparse.ArgumentParser(add_help=False)
    task_parent.add_argument(
        "--task",
        default=argparse.SUPPRESS,
        help="task directory (path or slug)",
    )
    parser = argparse.ArgumentParser(
        prog="plan.py",
        description="Trellis execution-plan advancer (execution-plan.json + audit log).",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="task directory (path or slug); defaults to the resolved active task",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("template", parents=[task_parent],
                   help="print an execution-plan.json skeleton")
    sub.add_parser("validate", parents=[task_parent],
                   help="validate the model-authored plan; approves it")
    status_p = sub.add_parser("status", parents=[task_parent],
                              help="show plan and task state")
    status_p.add_argument("--quiet", action="store_true", help="compact summary only")
    start_p = sub.add_parser("start", parents=[task_parent],
                             help="start a dependency-ready task")
    start_p.add_argument("task_id")
    record_p = sub.add_parser("record", parents=[task_parent],
                              help="record a required-check result; does not execute commands")
    record_p.add_argument("task_id")
    record_p.add_argument("--check", required=True, help="declared verification.required_checks id")
    record_p.add_argument("--result", required=True, choices=("pass", "fail"))
    record_p.add_argument("--command", required=True, help="command identifier (not full shell output)")
    record_p.add_argument("--exit-code", required=True, type=int)
    record_p.add_argument("--summary", required=True, help="short human-readable result text")
    record_p.add_argument("--artifact", default=None, help="optional task-relative reference (build log, report, …)")
    done_p = sub.add_parser("done", parents=[task_parent],
                            help="complete a task (verification checks enforced)")
    done_p.add_argument("task_id")
    block_p = sub.add_parser("block", parents=[task_parent],
                             help="mark a task blocked with a reason")
    block_p.add_argument("task_id")
    block_p.add_argument("--reason", required=True)
    rev_p = sub.add_parser("revise", parents=[task_parent],
                           help="open an approved plan for revision")
    rev_p.add_argument("--reason", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = get_repo_root()

    try:
        if args.subcommand == "template":
            print(template_text())
            return 0

        task_dir = resolve_task_dir(repo_root, args.task)

        if args.subcommand == "validate":
            print(cmd_validate(repo_root, task_dir))
        elif args.subcommand == "status":
            if not plan_exists(task_dir):
                print("no execution plan yet — create execution-plan.json, "
                      "then run: python .trellis/scripts/plan.py validate")
                return 0
            print(format_status(task_dir, repo_root, verbose=not args.quiet))
        elif args.subcommand == "start":
            print(cmd_start(repo_root, task_dir, args.task_id))
        elif args.subcommand == "record":
            print(cmd_record(
                repo_root, task_dir, args.task_id, args.result, args.command,
                args.exit_code, args.artifact, args.summary, args.check,
            ))
        elif args.subcommand == "done":
            print(cmd_done(repo_root, task_dir, args.task_id))
        elif args.subcommand == "block":
            print(cmd_block(repo_root, task_dir, args.task_id, args.reason))
        elif args.subcommand == "revise":
            print(cmd_revise(repo_root, task_dir, args.reason))
        else:  # argparse keeps this unreachable
            return 2
    except PlanError as exc:
        print(f"plan.py {args.subcommand}: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"  hint: {exc.hint}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        print(f"plan.py {args.subcommand}: unexpected I/O error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
