"""Verification of the TrellisForge elevator-model assets.

Cross-checks:
  - VERSION == 1.1
  - objects library: every manifest canonical_sha256 resolves to a file in
    history/embedded-c-overlay/objects/<sha> whose LF-normalized bytes hash to
    that sha (self-consistency, dedup by content), and every object file is
    referenced by at least one manifest.
  - 1.0 manifest fidelity: the 75 managed files and the 12 adoption-baseline
    files byte-match git show e40a942:<expected-source>. The command-reference
    pairs must keep the historical trailing blank line (`**.\n\n`).
  - 1.1 manifest fidelity: every managed file byte-matches the live template
    (templates/embedded-c-overlay/**) and HEAD; command-reference carries the
    subtask-1 "Standard dispatch use:" rule and no extra trailing blank line.
  - AGENTS.md.trellisforge-template canonical == AGENTS.md.template content.
  - structural chain: schema 1, from/to versions, receipt_transition
    bootstrap-schema-1, actions == [].
  - no Plan-A assets remain (migrations/embedded-c-overlay/1.0-to-1.1/** gone),
    so the tree holds exactly one upgrade asset source.
  - git diff --check is clean for the created assets.

Run from the repo root.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "templates" / "embedded-c-overlay"
HISTORY = REPO / "history" / "embedded-c-overlay"
OBJECTS = HISTORY / "objects"
VERSIONS = HISTORY / "versions"
STRUCTURAL = REPO / "migrations" / "embedded-c-overlay" / "structural"
PLAN_A = REPO / "migrations" / "embedded-c-overlay" / "1.0-to-1.1"
E40A942 = "e40a942"
ADOPT_PATHS = [
    ".agents/skills/trellis-channel/SKILL.md",
    ".agents/skills/trellis-channel/references/command-reference.md",
    ".agents/skills/trellis-channel/references/forum.md",
    ".agents/skills/trellis-channel/references/progress-debugging.md",
    ".agents/skills/trellis-channel/references/workers.md",
    ".agents/skills/trellis-channel/references/workflows.md",
    ".claude/skills/trellis-channel/SKILL.md",
    ".claude/skills/trellis-channel/references/command-reference.md",
    ".claude/skills/trellis-channel/references/forum.md",
    ".claude/skills/trellis-channel/references/progress-debugging.md",
    ".claude/skills/trellis-channel/references/workers.md",
    ".claude/skills/trellis-channel/references/workflows.md",
]
AGENTS = "AGENTS.md.trellisforge-template"
COMMAND_REF_749 = ".agents/skills/trellis-channel/references/command-reference.md"
COMMAND_REF_750 = ".claude/skills/trellis-channel/references/command-reference.md"


def norm(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def sha(data: bytes) -> str:
    return hashlib.sha256(norm(data)).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    out = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        cwd=str(REPO),
        check=True,
    )
    return out.stdout


def read_no_bom(path: Path) -> bytes:
    data = path.read_bytes()
    return data[3:] if data.startswith(b"\xef\xbb\xbf") else data


def main() -> int:
    problems: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            print(f"{name}: OK {detail}".rstrip())
        else:
            print(f"{name}: FAIL {detail}".rstrip())
            problems.append(name)

    # ---------------------------------------------------------------- VERSION
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    check("version-fact", version == "1.1", f"VERSION={version}")

    # ------------------------------------------------------- objects library
    v10 = json.loads((VERSIONS / "1.0" / "manifest.json").read_text(encoding="utf-8"))
    v11 = json.loads((VERSIONS / "1.1" / "manifest.json").read_text(encoding="utf-8"))
    all_entries = v10["files"] + v11["files"]
    referenced: set[str] = set()
    for entry in all_entries:
        obj = OBJECTS / entry["canonical_sha256"]
        ok = (
            obj.is_file()
            and sha(read_no_bom(obj)) == entry["canonical_sha256"]
        )
        check(
            f"object[{entry['path']}]",
            ok,
            f"canonical={entry['canonical_sha256'][:12]}",
        )
        if ok:
            referenced.add(entry["canonical_sha256"])

    obj_files = {p.name for p in OBJECTS.iterdir() if p.is_file()}
    orphaned = sorted(obj_files - referenced)
    check("objects-no-orphan", not orphaned, f"orphaned={orphaned}")

    # ----------------------------------------- 1.0 fidelity to e40a942
    def expected_e40_source(rel: str) -> str:
        if rel in ADOPT_PATHS:
            # adoption-baseline: upstream Trellis root content, not template
            return rel
        return f"templates/embedded-c-overlay/{rel}"

    v10_by_path = {f["path"]: f for f in v10["files"]}
    promised_10 = sorted(set(f"templates/embedded-c-overlay/{f['path']}" for f in v10["files"] if f["path"] not in ADOPT_PATHS and f["path"] != AGENTS))
    for f in v10_by_path.values():
        if f["path"] == AGENTS:
            # AGENTS.md.trellisforge-template's canonical is AGENTS.md.template
            # content (rendered at install time); checked separately below.
            continue
        src = expected_e40_source(f["path"])
        expected = git_show(E40A942, src)
        obj = OBJECTS / f["canonical_sha256"]
        actual = read_no_bom(obj)
        check(
            f"v10-fidelity[{f['path']}]",
            norm(actual) == norm(expected),
            f"ownership={f['ownership']} src={src}",
        )

    # command-reference historical blank lines kept in 1.0
    for rel in (COMMAND_REF_749, COMMAND_REF_750):
        obj = OBJECTS / v10_by_path[rel]["canonical_sha256"]
        body = read_no_bom(obj)
        check(
            f"v10-trailing[{rel}]",
            body.endswith(b"**.\n\n"),
            "1.0 canonical must preserve historical trailing blank line",
        )

    # ----------------------------------------- 1.1 fidelity to live template
    v11_by_path = {f["path"]: f for f in v11["files"]}
    for rel, entry in v11_by_path.items():
        if rel == AGENTS:
            src = TEMPLATE / "AGENTS.md.template"
        else:
            src = TEMPLATE / rel
        live = read_no_bom(src)
        obj = OBJECTS / entry["canonical_sha256"]
        actual = read_no_bom(obj)
        check(f"v11-live[{rel}]", norm(actual) == norm(live))
        head = git_show("HEAD", f"templates/embedded-c-overlay/{rel}" if rel != AGENTS else "templates/embedded-c-overlay/AGENTS.md.template")
        check(f"v11-head[{rel}]", norm(actual) == norm(head))

    # subtask-1 rule + no trailing blank in 1.1
    for rel in (COMMAND_REF_749, COMMAND_REF_750):
        obj = OBJECTS / v11_by_path[rel]["canonical_sha256"]
        body = read_no_bom(obj)
        check(
            f"v11-rule[{rel}]",
            b"Standard dispatch use:" in body,
            "1.1 canonical must carry subtask-1 rule",
        )
        check(
            f"v11-trailing[{rel}]",
            body.endswith(b"**.\n"),
            "1.1 canonical must drop the extra blank line",
        )

    # AGENTS canonical equals AGENTS.md.template content
    agents_obj = OBJECTS / v11_by_path[AGENTS]["canonical_sha256"]
    agents_body = read_no_bom(agents_obj)
    check(
        "agents-canonical",
        norm(agents_body)
        == norm(git_show(E40A942, "templates/embedded-c-overlay/AGENTS.md.template"))
        == norm(read_no_bom(TEMPLATE / "AGENTS.md.template")),
        "AGENTS canonical == AGENTS.md.template (both eras)",
    )
    check("v10-agents-owned", v10_by_path[AGENTS]["ownership"] == "managed")
    check("v11-agents-owned", v11_by_path[AGENTS]["ownership"] == "managed")

    # ------------------------------------------------- scheme checks
    for name, manifest, ver in (("v10", v10, "1.0"), ("v11", v11, "1.1")):
        check(
            f"{name}-schema",
            manifest["schema_version"] == 1
            and manifest["overlay"] == "embedded-c"
            and manifest["trellisforge_version"] == ver
            and manifest["trellis_version"] == "0.6.10"
            and manifest["render_tokens"] == ["PROJECT_PREFIX", "PROJECT_NAME", "__PROJECT_PREFIX__"],
        )
    # no duplicate paths per manifest
    check("v10-no-dups", len({f["path"] for f in v10["files"]}) == len(v10["files"]))
    check("v11-no-dups", len({f["path"] for f in v11["files"]}) == len(v11["files"]))

    # path render tokens preserved (no unresolved branch in manifest paths)
    summary = {
        "v10_managed": sum(1 for f in v10["files"] if f["ownership"] == "managed"),
        "v10_adopt": sum(1 for f in v10["files"] if f["ownership"] == "adoption-baseline"),
        "v11_managed": sum(1 for f in v11["files"] if f["ownership"] == "managed"),
    }
    check(
        "v10-counts",
        summary == {"v10_managed": 76, "v10_adopt": 12, "v11_managed": 89},
        str(summary),
    )

    # ------------------------------------------------- structural chain
    chain = json.loads((STRUCTURAL / "1.0-to-1.1.json").read_text(encoding="utf-8"))
    check(
        "structural-schema",
        chain["schema_version"] == 1
        and chain["from_version"] == "1.0"
        and chain["to_version"] == "1.1"
        and chain["receipt_transition"] == "bootstrap-schema-1"
        and chain["actions"] == [],
    )

    # ------------------------------------------- Plan-A assets removed
    check(
        "plan-a-removed",
        not PLAN_A.exists(),
        f"{PLAN_A.relative_to(REPO)} must be gone",
    )
    forbidden = {"migration.json", "baseline", "new"}
    leftovers = []
    if PLAN_A.exists():
        for child in PLAN_A.iterdir():
            if child.name in forbidden:
                leftovers.append(child.name)
    check("plan-a-no-leftover", not leftovers, f"leftovers={leftovers}")

    # --------------------------------------------- git diff --check
    diff = subprocess.run(
        ["git", "diff", "--check", "--", "history", "migrations"],
        capture_output=True,
        cwd=str(REPO),
        text=True,
    )
    check("git-diff-check", diff.returncode == 0 and not diff.stdout.strip(), diff.stdout.strip()[:500])

    # -------------------------------------------------------- conclusion
    if problems:
        print("PROBLEMS: " + ", ".join(problems))
        return 1
    print("ALL ELEVATOR-ASSET CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())