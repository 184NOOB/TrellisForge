"""Generator for the 1.0-to-1.1 migration manifest (run from repo root).

Computes LF-normalized SHA-256 for baseline (old) and template (new) content,
materializes the frozen 1.1 ``new/`` snapshot next to the manifest, and emits
migrations/embedded-c-overlay/1.0-to-1.1/migration.json.

方案 A（迁移资产自包含）: both the 1.0 old baseline (``baseline/``) AND the
1.1 new target (``new/``) are frozen inside the migration dir, so later
template edits (1.2+) can never change what a 1.0->1.1 migration produces.
Re-run this script whenever a template file listed in the manifest changes,
so the snapshot and hashes stay in sync with the live template. Content hashes
normalize CRLF->LF and compare on bytes otherwise (no trimming of trailing
whitespace or trailing blank lines).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "templates" / "embedded-c-overlay"
MIG_DIR = REPO / "migrations" / "embedded-c-overlay" / "1.0-to-1.1"
BASELINE = MIG_DIR / "baseline"
NEW = MIG_DIR / "new"

ADOPT = [
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
MERGE = [
    ".trellis/workflow.md",
    ".trellis/agents/check.md",
    ".trellis/agents/implement.md",
]
ADD = [".trellis/scripts/tests/test_trellis_channel_contract.py"]


def norm(text: bytes) -> bytes:
    return text.replace(b"\r\n", b"\n")


def sha(text: bytes) -> str:
    return hashlib.sha256(norm(text)).hexdigest()


def read_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data


def snapshot_new(rel: str) -> None:
    """Byte-exact copy of the 1.1 template file into the frozen ``new/`` dir."""
    src = TEMPLATE / rel
    dst = NEW / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(src), str(dst))


paths = []
for rel in MERGE:
    snapshot_new(rel)
    paths.append(
        {
            "path": rel,
            "action": "merge",
            "old": f"baseline/{rel}",
            "old_sha256": sha(read_bytes(BASELINE / rel)),
            "new": f"new/{rel}",
            "new_sha256": sha(read_bytes(TEMPLATE / rel)),
        }
    )
for rel in ADOPT:
    if not (BASELINE / rel).is_file():
        raise SystemExit(f"missing baseline old: {BASELINE / rel}")
    snapshot_new(rel)
    paths.append(
        {
            "path": rel,
            "action": "adopt",
            "old": f"baseline/{rel}",
            "old_sha256": sha(read_bytes(BASELINE / rel)),
            "new": f"new/{rel}",
            "new_sha256": sha(read_bytes(TEMPLATE / rel)),
        }
    )
for rel in ADD:
    snapshot_new(rel)
    paths.append(
        {
            "path": rel,
            "action": "add",
            "new": f"new/{rel}",
            "new_sha256": sha(read_bytes(TEMPLATE / rel)),
        }
    )

manifest = {
    "schema_version": 1,
    "from_version": "1.0",
    "to_version": "1.1",
    "overlay": "embedded-c",
    "trellis_baseline": "0.6.10",
    "version_source": "VERSION",
    "description": "TrellisForge 1.0 -> 1.1 embedded-c overlay migration. "
    "merge: files Forge 1.0 managed that changed in 1.1; "
    "adopt: trellis-channel skills upstream Trellis 0.6.10 generated on the "
    "downstream project that Forge 1.1 now publishes into the overlay; "
    "add: files new in 1.1 with no 1.0/upstream counterpart.",
    "hash_normalization": "LF (CRLF->LF only); trailing whitespace and "
    "trailing blank lines are preserved for hashing and merging.",
    "paths": paths,
}

out = MIG_DIR / "migration.json"
# Byte write so the manifest is LF regardless of platform (write_text would
# emit CRLF on Windows via os.linesep, tripping `git diff --check`).
out.write_bytes((json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))
print(f"wrote {out}")
print(f"wrote new/ snapshot ({len(paths)} files)")
print(f"paths: {len(paths)} (merge={len(MERGE)}, adopt={len(ADOPT)}, add={len(ADD)})")
for p in paths:
    print(f"  {p['action']:<6} {p['path']}")