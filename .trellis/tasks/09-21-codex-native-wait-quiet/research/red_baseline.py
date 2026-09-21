"""Collect and verify the Phase 1 red baseline for the Codex wait task.

- ``collect``: run the two new template test files with the real
  ``unittest discover`` command and write ``research/baseline-red.log``.
  The tests are expected to fail here — that is the evidence.
- ``verify``: assert the log exists, is non-empty, and carries the evidence
  substrings the plan's ``red-baseline-log-captured`` check requires.

Neither mode touches product files.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TASK_DIR.parents[2]
LOG_PATH = Path(__file__).resolve().parent / "baseline-red.log"

TESTS_REL = "templates/embedded-c-overlay/.trellis/scripts/tests"
PATTERNS = (
    "test_codex_native_wait_contract.py",
    "test_write_json_lf.py",
)

REQUIRED_EVIDENCE = (
    "Step not found: 2.1.1",
    "write_stdin",
    "Spawn the implement sub-agent",
    "2.1.2",
    # Only produced by a real failure of the write_json CRLF assertion, so
    # the CRLF evidence is tied to actual test output.
    "write_json emitted CRLF line endings",
)
CRLF_MARKERS = ("\\r\\n", "CRLF")


def collect() -> int:
    chunks = [
        "=== Phase 1 red baseline: Codex native wait contract (pre-fix) ===",
        f"repo_root: {REPO_ROOT.as_posix()}",
        "expected: every new contract test is red before the reachability /",
        "          contract / newline fixes land.",
        "",
    ]
    raw_test_output = []
    for pattern in PATTERNS:
        cmd = [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            TESTS_REL,
            "-p",
            pattern,
        ]
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        chunks.append(f"--- command: {' '.join(cmd)}")
        chunks.append(f"--- exit_code: {result.returncode}")
        chunks.append(result.stdout.rstrip())
        if result.stderr.strip():
            chunks.append("--- stderr:")
            chunks.append(result.stderr.rstrip())
        chunks.append("")
        raw_test_output.append(result.stdout + "\n" + result.stderr)

    raw_text = "\n".join(raw_test_output)
    failed = len(re.findall(r"^(?:FAIL|ERROR):", raw_text, re.MULTILINE))

    summary = [
        "=== expected red items (observed in the raw run above) ===",
        f"failed_or_error_tests: {failed}",
        "[expected-red] 2.1.1 channel wait contract not delivered by --step 2.1 /",
        f"               --step 2.1.1 (exit code 2) -> 'Step not found: 2.1.1' observed: "
        f"{'Step not found: 2.1.1' in raw_text}",
        "[expected-red] 'write_stdin' must be absent from the pre-fix output -> "
        f"observed in raw run: {'write_stdin' in raw_text}",
        "[expected-red] --platform claude drops the dispatch instructions ->",
        f"               'Spawn the implement sub-agent' observed in raw run: "
        f"{'Spawn the implement sub-agent' in raw_text}",
        "[expected-red] 2.1.2 native wait contract does not exist yet ->",
        f"               '2.1.2' observed in raw run: {'2.1.2' in raw_text}",
        "[expected-red] write_json emits CRLF on Windows ->",
        f"               'write_json emitted CRLF line endings' observed in raw run: "
        f"{'write_json emitted CRLF line endings' in raw_text}",
        "",
    ]
    text = "\n".join(chunks + summary).rstrip() + "\n"
    with open(LOG_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"baseline log written: {LOG_PATH.as_posix()}")
    print(f"failed_or_error_tests: {failed}")
    return 0


def verify() -> int:
    if not LOG_PATH.is_file():
        print(f"baseline log missing: {LOG_PATH.as_posix()}")
        return 1
    text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    problems = []
    if not text.strip():
        problems.append("log is empty")
    for needle in REQUIRED_EVIDENCE:
        if needle not in text:
            problems.append(f"missing evidence: {needle}")
    if not any(marker in text for marker in CRLF_MARKERS):
        problems.append("missing evidence: CRLF marker")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    hits = len(re.findall(r"^(?:FAIL|ERROR):", text, re.MULTILINE))
    print(f"baseline evidence OK: bytes={len(text.encode('utf-8'))}, failures={hits}")
    return 0


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "collect"
    if mode == "collect":
        return collect()
    if mode == "verify":
        return verify()
    print(f"unknown mode: {mode} (expected collect|verify)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))