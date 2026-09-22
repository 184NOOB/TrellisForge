#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task-local audit for the 09-22 task-triage-consent wording change.

This file is a TASK ARTIFACT, not a published template test. The triage text is
AI-facing guidance prose with no programmatic consumer, so the frozen-string
checks intentionally live here instead of in
templates/embedded-c-overlay/.trellis/scripts/tests/ (see task design.md
"测试取舍").

Modes:
  pre       assert the old wording is present and the new wording is absent
            (run before any template edit)
  post      assert the new wording is present, the old wording is absent, the
            [workflow-state:no_task] tag pair is intact, the other
            [workflow-state:*] block bodies and the non-branch code of the
            touched Python/JS files are byte-identical to HEAD
  snapshot  write the pre-edit `git status --porcelain` baseline
  scope     assert the change set since the snapshot only touches the 5
            template files and this task directory
  report    assert final-report.md exists with the required sections

Groups for pre/post: workflow | hooks | opencode | all

Exit code 0 = every named check passed; 1 = at least one failed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TASK_DIR = Path(__file__).resolve().parent
SNAPSHOT = TASK_DIR / "baseline-git-status.txt"
TPL = "templates/embedded-c-overlay"

FILES = {
    "workflow": f"{TPL}/.trellis/workflow.md",
    "claude": f"{TPL}/.claude/hooks/session-start.py",
    "codex": f"{TPL}/.codex/hooks/session-start.py",
    "js": f"{TPL}/.opencode/lib/session-utils.js",
    "start": f"{TPL}/.opencode/commands/trellis/start.md",
}
GROUP_FILES = {
    "workflow": ["workflow"],
    "hooks": ["claude", "codex"],
    "opencode": ["js", "start"],
    "all": ["workflow", "claude", "codex", "js", "start"],
}
EXPECTED_SCOPE = {
    f"{TPL}/.trellis/workflow.md",
    f"{TPL}/.claude/hooks/session-start.py",
    f"{TPL}/.codex/hooks/session-start.py",
    f"{TPL}/.opencode/lib/session-utils.js",
    f"{TPL}/.opencode/commands/trellis/start.md",
}
TASK_PREFIX = ".trellis/tasks/09-22-refine-task-triage-consent/"
FORBIDDEN_PREFIXES = (
    "VERSION",
    "history/",
    "README.md",
    "docs/",
    ".claude/",
    ".codex/",
    ".opencode/",
    ".agents/",
    ".trellis/scripts/",
    ".trellis/spec/",
    ".trellis/workflow.md",
    ".trellis/.template-hashes.json",
)

# --------------------------------------------------------------------------
# Unified wording (single source: task design.md / implement.md)
# --------------------------------------------------------------------------

DEFAULT_SENTENCE = (
    "Default: do the work. Code analysis, Q&A, and single-file local edits "
    "proceed directly with no Trellis prompt."
)
CONSENT_SENTENCE_SHORT = (
    "Ask about creating a Trellis task only when the user explicitly wants code written "
    "AND it is complex (multi-file, workflow/Hook/contract mechanism, design tradeoffs "
    "or multi-step, or template-affecting)."
)
CONSENT_SENTENCE_FULL = (
    "Ask about creating a Trellis task only when the user explicitly wants code written "
    "AND it is complex (spans multiple files, touches workflow/Hook/contract mechanisms, "
    "needs design tradeoffs or multi-step implementation, or affects the published template)."
)
REJECT_SENTENCE = (
    "If the user says no, do not do broad inline implementation; explain, clarify scope, "
    "or suggest a smaller split."
)
APPROVAL_SENTENCE = (
    "User approval to create a task is not approval to start implementation. "
    "Planning still happens first."
)
NO_TASK_LINE1 = (
    "No active task. Default to doing the work: code analysis, Q&A, and single-file "
    "local edits proceed directly with no Trellis prompt."
)
NO_TASK_LINE2 = f"{CONSENT_SENTENCE_SHORT} {REJECT_SENTENCE}"
INVARIANT = (
    "No active task must triage first; ask for task-creation consent only for "
    "explicitly-requested complex code changes before creating a Trellis task."
)
INDEX_LINE = (
    "Phase 1: Plan    \u2192 triage; ask task-creation consent only for complex coding "
    "work, then run Grill Me and write planning artifacts"
)
START_BULLET = (
    "- **No active task** \u2192 triage. Default to doing the work: code analysis, Q&A, "
    "and single-file local edits proceed directly with no Trellis prompt. "
    f"{CONSENT_SENTENCE_SHORT} If the user says no, skip Trellis for this session."
)

# name -> (file key, fragment) that must be present after the edit.
NEW_PRESENT = [
    ("workflow-index-new", "workflow", INDEX_LINE),
    ("workflow-triage-default-new", "workflow", f"- {DEFAULT_SENTENCE}"),
    ("workflow-triage-consent-new", "workflow", CONSENT_SENTENCE_FULL),
    ("workflow-triage-reject-new", "workflow", REJECT_SENTENCE),
    ("workflow-triage-approval-kept", "workflow", APPROVAL_SENTENCE),
    ("workflow-no-task-line1-new", "workflow", NO_TASK_LINE1),
    ("workflow-no-task-line2-new", "workflow", NO_TASK_LINE2),
    ("workflow-invariant-new", "workflow", INVARIANT),
    ("claude-next-new", "claude", f"Next-Action: {DEFAULT_SENTENCE}"),
    ("claude-consent-new", "claude", CONSENT_SENTENCE_SHORT),
    ("claude-no-active-kept", "claude", "Status: NO ACTIVE TASK"),
    ("codex-next-new", "codex", f"Next: {DEFAULT_SENTENCE}"),
    ("codex-consent-new", "codex", CONSENT_SENTENCE_SHORT),
    ("codex-no-active-kept", "codex", "Status: NO ACTIVE TASK"),
    ("js-next-new", "js", f"Next-Action: {DEFAULT_SENTENCE}"),
    ("js-consent-new", "js", CONSENT_SENTENCE_SHORT),
    ("js-ambiguous-kept", "js", "Session state: AMBIGUOUS"),
    ("start-bullet-new", "start", START_BULLET),
]

# name -> (file key, fragment) that must be absent after the edit.
OLD_ABSENT = [
    ("workflow-index-old", "workflow", "classify, get task-creation consent, run Grill Me"),
    ("workflow-simple-old", "workflow", "ask only whether this turn should create a Trellis task"),
    ("workflow-first-classify-old", "workflow", "No active task. First classify the current turn"),
    ("workflow-invariant-old", "workflow", "must triage first and ask for task-creation consent"),
    ("claude-classify-old", "claude", "Next-Action: Classify the current turn"),
    ("codex-classify-old", "codex", "Next: Classify the current turn and ask for task-creation consent"),
    ("js-classify-old", "js", "Next-Action: Classify the current turn"),
    ("start-classify-old", "start", "classify first. For simple conversation / small task"),
    ("start-ask-old", "start", "ask only whether this turn should create a Trellis task"),
]

# Pre-edit baseline: old wording present in every file.
OLD_PRESENT = [
    ("workflow-index-old-present", "workflow", "classify, get task-creation consent, run Grill Me"),
    ("workflow-simple-old-present", "workflow", "ask only whether this turn should create a Trellis task"),
    ("workflow-first-classify-old-present", "workflow", "No active task. First classify the current turn"),
    ("workflow-invariant-old-present", "workflow", "No active task must triage first and ask for task-creation consent"),
    ("claude-classify-old-present", "claude", "Next-Action: Classify the current turn"),
    ("codex-classify-old-present", "codex", "Next: Classify the current turn and ask for task-creation consent"),
    ("js-classify-old-present", "js", "Next-Action: Classify the current turn"),
    ("start-classify-old-present", "start", "classify first. For simple conversation / small task"),
]

# Pre-edit baseline: new wording absent everywhere (subset that is unambiguous;
# APPROVAL_SENTENCE and REJECT_SENTENCE are intentionally excluded because they
# are retained fragments that already exist before the edit).
NEW_ABSENT_PRE = [
    ("workflow-index-new-absent", "workflow", INDEX_LINE),
    ("workflow-default-new-absent", "workflow", DEFAULT_SENTENCE),
    ("workflow-consent-full-new-absent", "workflow", CONSENT_SENTENCE_FULL),
    ("workflow-no-task-line1-absent", "workflow", NO_TASK_LINE1),
    ("workflow-invariant-new-absent", "workflow", INVARIANT),
    ("claude-default-new-absent", "claude", f"Next-Action: {DEFAULT_SENTENCE}"),
    ("codex-default-new-absent", "codex", f"Next: {DEFAULT_SENTENCE}"),
    ("js-default-new-absent", "js", f"Next-Action: {DEFAULT_SENTENCE}"),
    ("start-bullet-new-absent", "start", START_BULLET),
]

OTHER_TAG_STATUSES = (
    "planning",
    "planning-inline",
    "in_progress",
    "in_progress-inline",
    "completed",
)

REPORT_SECTIONS = (
    "## 改动文件",
    "## 阶段结果",
    "## 逐项检查结果",
    "## 未运行",
    "## 已知风险",
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

class Audit:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS {name}")
            self.passed += 1
        else:
            print(f"FAIL {name} :: {detail}")
            self.failures.append(name)

    def finish(self) -> int:
        if self.failures:
            print(f"RESULT: FAILED ({self.passed} pass, {len(self.failures)} fail)")
            return 1
        print(f"RESULT: OK ({self.passed} pass, 0 fail)")
        return 0


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout


def git_show(rel: str) -> str:
    code, out = git("show", f"HEAD:{rel}")
    if code != 0:
        raise SystemExit(f"git show HEAD:{rel} failed (exit {code})")
    return out


def read_rel(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def parse_status_paths(lines: list[str]) -> set[str]:
    paths: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        rest = line[3:].strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        paths.add(rest.replace("\\", "/").rstrip("/"))
    return paths


def branch_marker(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + "<NO-ACTIVE-TASK-BRANCH>\n" + text[j:]


def extract_tag_block(text: str, status: str) -> str | None:
    """Extract the real `[workflow-state:status]` block.

    Line-exact anchoring: the Phase Index HTML comment and the customization
    table mention tag names with trailing text, so raw substring counting would
    over-count. Only a line that is exactly the tag opens a block.
    """
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"[workflow-state:{status}]":
            inside = True
            out = [line]
            continue
        if inside:
            out.append(line)
            if stripped == f"[/workflow-state:{status}]":
                return "\n".join(out)
    return None


def branch_text(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


BRANCH_MARKERS = {
    "claude": ("if not active.task_path:", "task_ref = active.task_path"),
    "codex": ("if not active.task_path:", "task_ref = active.task_path"),
    "js": ("if (!taskRef) {", "const taskDir = ctx.resolveTaskDir(taskRef)"),
}


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------

def mode_pre(group: str, audit: Audit) -> None:
    for name, key, frag in OLD_PRESENT:
        if key not in GROUP_FILES[group]:
            continue
        audit.check(name, frag in read_rel(FILES[key]), f"old fragment missing in {FILES[key]}")
    for name, key, frag in NEW_ABSENT_PRE:
        if key not in GROUP_FILES[group]:
            continue
        audit.check(name, frag not in read_rel(FILES[key]), f"new fragment already present in {FILES[key]}")


def mode_post(group: str, audit: Audit) -> None:
    texts = {key: read_rel(FILES[key]) for key in GROUP_FILES[group]}
    for name, key, frag in NEW_PRESENT:
        if key not in texts:
            continue
        audit.check(name, frag in texts[key], f"new fragment missing in {FILES[key]}")
    for name, key, frag in OLD_ABSENT:
        if key not in texts:
            continue
        audit.check(name, frag not in texts[key], f"old fragment still present in {FILES[key]}")

    if "workflow" in texts:
        wf = texts["workflow"]
        opens = sum(1 for line in wf.splitlines() if line.strip() == "[workflow-state:no_task]")
        closes = sum(1 for line in wf.splitlines() if line.strip() == "[/workflow-state:no_task]")
        audit.check("workflow-no-task-tag-pair", opens == 1 and closes == 1, f"opens={opens} closes={closes}")
        block = extract_tag_block(wf, "no_task")
        audit.check(
            "workflow-no-task-body-nonempty",
            bool(block) and "Default to doing the work" in block,
            "tag block not extractable or body missing the new default sentence",
        )
        head = git_show(FILES["workflow"])
        all_intact = True
        detail = ""
        for status in OTHER_TAG_STATUSES:
            a = extract_tag_block(head, status)
            b = extract_tag_block(wf, status)
            if not a or not b or a != b:
                all_intact = False
                detail += f"{status} changed; "
        audit.check("workflow-other-tags-intact", all_intact, detail or "other tag block differs from HEAD")

    for key in ("claude", "codex", "js"):
        if key not in texts:
            continue
        start, end = BRANCH_MARKERS[key]
        head = git_show(FILES[key])
        work = texts[key]
        try:
            rest_same = branch_marker(head, start, end) == branch_marker(work, start, end)
            branch_changed = branch_text(head, start, end) != branch_text(work, start, end)
            branch_has_new = "Default: do the work." in branch_text(work, start, end)
            detail = ""
            if not rest_same:
                detail += "code outside the NO ACTIVE TASK branch changed; "
            if not branch_changed:
                detail += "branch text unchanged; "
            if not branch_has_new:
                detail += "branch missing the new default sentence; "
        except ValueError as exc:
            rest_same = branch_changed = branch_has_new = False
            detail = f"branch marker not found: {exc}"
        audit.check(f"{key}-branch-only-diff", rest_same and branch_changed and branch_has_new, detail or "branch shape check failed")


def mode_snapshot(audit: Audit) -> None:
    code, out = git("status", "--porcelain")
    audit.check("snapshot-git-status", code == 0, f"git status exit {code}")
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(out)
    saved = SNAPSHOT.read_text(encoding="utf-8")
    audit.check(
        "snapshot-written",
        saved == out and bool(out.strip()),
        f"snapshot content differs from live git status ({len(saved)} vs {len(out)} chars)",
    )
    count = len(parse_status_paths(out.splitlines()))
    print(f"SNAPSHOT {SNAPSHOT.relative_to(REPO)} entries={count}")


def mode_scope(audit: Audit) -> None:
    if not SNAPSHOT.is_file():
        audit.check("scope-snapshot-exists", False, f"missing {SNAPSHOT}")
        return
    base = parse_status_paths(SNAPSHOT.read_text(encoding="utf-8").splitlines())
    code, out = git("status", "--porcelain")
    current = parse_status_paths(out.splitlines())
    new = sorted(current - base)

    unexpected = [p for p in new if p not in EXPECTED_SCOPE and not p.startswith(TASK_PREFIX)]
    audit.check("scope-new-paths-allowed", not unexpected, f"unexpected new entries: {unexpected}")
    missing = sorted(EXPECTED_SCOPE - set(new))
    audit.check("scope-five-template-files-changed", not missing, f"not changed: {missing}")
    forbidden = [
        p for p in new
        if any(p == f or p.startswith(f) for f in FORBIDDEN_PREFIXES)
    ]
    audit.check("scope-root-and-release-assets-untouched", not forbidden, f"forbidden new entries: {forbidden}")

    code, out = git("diff", "--name-status", "--", TPL)
    rows = [line for line in out.splitlines() if line.strip()]
    statuses = {row.split("\t", 1)[0] for row in rows}
    paths = {row.split("\t", 1)[1].strip() for row in rows}
    audit.check(
        "scope-template-diff-modify-only",
        statuses <= {"M"} and paths == EXPECTED_SCOPE,
        f"statuses={sorted(statuses)} paths={sorted(paths)}",
    )
    print(f"NEW-ENTRIES {len(new)}: {new}")


def mode_report(audit: Audit) -> None:
    report = TASK_DIR / "final-report.md"
    if not report.is_file():
        audit.check("report-exists", False, f"missing {report}")
        return
    text = report.read_text(encoding="utf-8")
    audit.check("report-exists", True)
    audit.check("report-substantial", len(text) > 500, f"only {len(text)} chars")
    for section in REPORT_SECTIONS:
        audit.check(
            f"report-section-{section.strip('# ')}",
            section in text,
            f"missing section {section}",
        )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect", choices=("pre", "post"), help="pre/post wording expectation")
    parser.add_argument("--group", choices=("workflow", "hooks", "opencode", "all"), default="all")
    parser.add_argument(
        "--mode",
        choices=("snapshot", "scope", "report"),
        help="non-wording modes",
    )
    args = parser.parse_args()
    audit = Audit()
    if args.mode == "snapshot":
        mode_snapshot(audit)
    elif args.mode == "scope":
        mode_scope(audit)
    elif args.mode == "report":
        mode_report(audit)
    elif args.expect == "pre":
        mode_pre(args.group, audit)
    elif args.expect == "post":
        mode_post(args.group, audit)
    else:
        parser.error("one of --expect pre|post or --mode snapshot|scope|report is required")
    return audit.finish()


if __name__ == "__main__":
    sys.exit(main())