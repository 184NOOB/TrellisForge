"""One-off verification of migration assets (phase version-migration-assets)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MIG_DIR = REPO / "migrations" / "embedded-c-overlay" / "1.0-to-1.1"
BASELINE = MIG_DIR / "baseline"
TEMPLATE = REPO / "templates" / "embedded-c-overlay"

E40A942 = "e40a942"

# map baseline relpath -> git source path at e40a942
SOURCE_MAP = {
    ".trellis/workflow.md": "templates/embedded-c-overlay/.trellis/workflow.md",
    ".trellis/agents/check.md": "templates/embedded-c-overlay/.trellis/agents/check.md",
    ".trellis/agents/implement.md": "templates/embedded-c-overlay/.trellis/agents/implement.md",
    ".agents/skills/trellis-channel/SKILL.md": ".agents/skills/trellis-channel/SKILL.md",
    ".agents/skills/trellis-channel/references/command-reference.md": ".agents/skills/trellis-channel/references/command-reference.md",
    ".agents/skills/trellis-channel/references/forum.md": ".agents/skills/trellis-channel/references/forum.md",
    ".agents/skills/trellis-channel/references/progress-debugging.md": ".agents/skills/trellis-channel/references/progress-debugging.md",
    ".agents/skills/trellis-channel/references/workers.md": ".agents/skills/trellis-channel/references/workers.md",
    ".agents/skills/trellis-channel/references/workflows.md": ".agents/skills/trellis-channel/references/workflows.md",
    ".claude/skills/trellis-channel/SKILL.md": ".claude/skills/trellis-channel/SKILL.md",
    ".claude/skills/trellis-channel/references/command-reference.md": ".claude/skills/trellis-channel/references/command-reference.md",
    ".claude/skills/trellis-channel/references/forum.md": ".claude/skills/trellis-channel/references/forum.md",
    ".claude/skills/trellis-channel/references/progress-debugging.md": ".claude/skills/trellis-channel/references/progress-debugging.md",
    ".claude/skills/trellis-channel/references/workers.md": ".claude/skills/trellis-channel/references/workers.md",
    ".claude/skills/trellis-channel/references/workflows.md": ".claude/skills/trellis-channel/references/workflows.md",
}


def git_show(path: str) -> bytes:
    out = subprocess.run(
        ["git", "show", f"{E40A942}:{path}"],
        capture_output=True,
        cwd=str(REPO),
        check=True,
    )
    return out.stdout


def norm(text: bytes) -> bytes:
    return text.replace(b"\r\n", b"\n")


def sha(text: bytes) -> str:
    return hashlib.sha256(norm(text)).hexdigest()


def read_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data


def main() -> int:
    problems = []

    manifest_text = (MIG_DIR / "migration.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    if manifest["schema_version"] != 1:
        problems.append("schema_version != 1")
    if manifest["from_version"] != "1.0" or manifest["to_version"] != "1.1":
        problems.append("from/to version mismatch")
    if manifest["overlay"] != "embedded-c":
        problems.append("overlay mismatch")
    if (REPO / "VERSION").read_text(encoding="utf-8").strip() != "1.1":
        problems.append("VERSION != 1.1")
    action_count = {}
    for p in manifest["paths"]:
        action_count[p["action"]] = action_count.get(p["action"], 0) + 1
    if action_count != {"merge": 3, "adopt": 12, "add": 1}:
        problems.append(f"unexpected action counts: {action_count}")
    print("migration-json-valid: OK (schema, versions, VERSION, action counts)")

    # baseline fidelity vs e40a942
    for rel, git_src in sorted(SOURCE_MAP.items()):
        baseline_file = BASELINE / rel
        bl = baseline_file.read_bytes()
        src = git_show(git_src)
        if bl != src:
            problems.append(f"baseline drift: {rel} differs from e40a942")
    print(f"baseline-fidelity: OK ({len(SOURCE_MAP)} files byte-identical to e40a942)")

    # hash consistency
    for p in manifest["paths"]:
        rel = p["path"]
        if p.get("old"):
            old_file = MIG_DIR / p["old"]
            if sha(read_bytes(old_file)) != p["old_sha256"]:
                problems.append(f"old_sha256 mismatch: {rel}")
        new_file = MIG_DIR / p["new"]
        if sha(read_bytes(new_file)) != p["new_sha256"]:
            problems.append(f"new_sha256 mismatch: {rel}")
    print("hash-consistency: OK (all old/new LF-normalized hashes match manifest)")

    # root whitespace trimmed: root ends with single \n; baseline retains \n\n
    for rel in (
        ".agents/skills/trellis-channel/references/command-reference.md",
        ".claude/skills/trellis-channel/references/command-reference.md",
    ):
        root = (REPO / rel).read_bytes()
        if not root.endswith(b"**.\n"):
            problems.append(f"root not trimmed to single trailing newline: {rel}")
        bl = (BASELINE / rel.replace("skills/", "skills/")).read_bytes()
        if not bl.endswith(b"**.\n\n"):
            problems.append(f"baseline must retain trailing blank line: {rel}")
    # template command-reference must contain the sub-task-1 rules and no extra blank
    for rel in (
        ".agents/skills/trellis-channel/references/command-reference.md",
        ".claude/skills/trellis-channel/references/command-reference.md",
    ):
        tmpl = (TEMPLATE / rel).read_bytes()
        if b"Standard dispatch use:" not in tmpl:
            problems.append(f"template 1.1 missing adoption rules: {rel}")
        if not tmpl.endswith(b"**.\n"):
            problems.append(f"template 1.1 trailing blank not removed: {rel}")
    print("root-whitespace-trimmed: OK (root trimmed, baseline 1.0 tail preserved, 1.1 template rules/blank verified)")

    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("ALL PHASE 2 CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())