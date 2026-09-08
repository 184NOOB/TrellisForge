"""Generator for the TrellisForge elevator-model 1.0/1.1 assets.

Replaces the Plan-A pair-wise generator. Produces:
  history/embedded-c-overlay/objects/<sha256>            canonical overlay file bodies
  history/embedded-c-overlay/versions/1.0/manifest.json  1.0 version manifest
  history/embedded-c-overlay/versions/1.1/manifest.json  1.1 version manifest
  migrations/embedded-c-overlay/structural/1.0-to-1.1.json  structural chain

Sources are pinned:
  - 1.0 managed files   : templates/embedded-c-overlay/** at commit e40a942
  - 1.0 adoption-baseline: .agents/skills/trellis-channel/** and
    .claude/skills/trellis-channel/** at commit e40a942 (upstream Trellis
    0.6.10 content Forge 1.1 takes over)
  - 1.1 managed files   : templates/embedded-c-overlay/** at HEAD (live template)

Canonical objects: UTF-8 without BOM, LF-normalized (CRLF->LF only). Nothing
else is trimmed (trailing whitespace and trailing blank lines are preserved),
so the 1.0 command-reference.md keeps its historical trailing blank line
(e40a942) while the 1.1 body carries the subtask-1 rules without it.
Run from the repo root.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "templates" / "embedded-c-overlay"
HISTORY = REPO / "history" / "embedded-c-overlay"
OBJECTS = HISTORY / "objects"
VERSIONS = HISTORY / "versions"
STRUCTURAL = REPO / "migrations" / "embedded-c-overlay" / "structural"
E40A942 = "e40a942"

EXCLUDED_NAMES = {"AGENTS.md.template", "TEMPLATE-CONTENTS.md"}
RENDER_TOKENS = ["PROJECT_PREFIX", "PROJECT_NAME", "__PROJECT_PREFIX__"]

ADOPT_PATHS = sorted(
    [
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
)

# AGENTS.md.trellisforge-template is a generated delivery (from
# AGENTS.md.template) that both 1.0 and 1.1 Forge installers manage. Its
# canonical body is the template content; both versions share the object.
AGENTS_PATH = "AGENTS.md.trellisforge-template"


def norm_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(norm_bytes(data)).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    out = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        cwd=str(REPO),
        check=True,
    )
    return out.stdout


def git_ls_template(commit: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit, "--", "templates/embedded-c-overlay"],
        capture_output=True,
        cwd=str(REPO),
        check=True,
    )
    rels = []
    for line in out.stdout.decode("utf-8").splitlines():
        if not line.strip():
            continue
        rel = line.strip()[len("templates/embedded-c-overlay/") :]
        name = rel.rsplit("/", 1)[-1]
        if name in EXCLUDED_NAMES:
            continue
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")):
            continue
        rels.append(rel)
    return sorted(rels)


def add_object(body: bytes, objects_dir: Path) -> str:
    obj_name = sha256_of(body)
    dst = objects_dir / obj_name
    if not dst.exists():
        dst.write_bytes(norm_bytes(body))
    return obj_name


def build() -> None:
    if (REPO / "VERSION").read_text(encoding="utf-8").strip() != "1.1":
        raise SystemExit("VERSION must be 1.1 before generating assets")

    if OBJECTS.exists():
        shutil.rmtree(OBJECTS)
    OBJECTS.mkdir(parents=True)

    # ---------------------------------------------------------------- 1.0
    v10_managed = []
    for rel in git_ls_template(E40A942):
        body = git_show(E40A942, f"templates/embedded-c-overlay/{rel}")
        body = body[3:] if body.startswith(b"\xef\xbb\xbf") else body
        obj_sha = add_object(body, OBJECTS)
        v10_managed.append(
            {
                "path": rel,
                "ownership": "managed",
                "canonical_sha256": obj_sha,
            }
        )

    v10_adopt = []
    for rel in ADOPT_PATHS:
        body = git_show(E40A942, rel)
        body = body[3:] if body.startswith(b"\xef\xbb\xbf") else body
        obj_sha = add_object(body, OBJECTS)
        v10_adopt.append(
            {
                "path": rel,
                "ownership": "adoption-baseline",
                "canonical_sha256": obj_sha,
            }
        )

    # AGENTS.md.trellisforge-template (both versions share the same canonical
    # because AGENTS.md.template is byte-identical at e40a942 and HEAD).
    agents_body = git_show(E40A942, "templates/embedded-c-overlay/AGENTS.md.template")
    agents_body = agents_body[3:] if agents_body.startswith(b"\xef\xbb\xbf") else agents_body
    agents_sha = add_object(agents_body, OBJECTS)

    v10_manifest = {
        "schema_version": 1,
        "overlay": "embedded-c",
        "trellisforge_version": "1.0",
        "trellis_version": "0.6.10",
        "render_tokens": RENDER_TOKENS,
        "files": sorted(v10_managed + v10_adopt + [{"path": AGENTS_PATH, "ownership": "managed", "canonical_sha256": agents_sha}], key=lambda f: f["path"]),
    }

    # ---------------------------------------------------------------- 1.1
    v11_managed = []
    seen_live = 0
    for rel in git_ls_template("HEAD"):
        body = (TEMPLATE / rel).read_bytes()
        body = body[3:] if body.startswith(b"\xef\xbb\xbf") else body
        obj_sha = add_object(body, OBJECTS)
        v11_managed.append(
            {
                "path": rel,
                "ownership": "managed",
                "canonical_sha256": obj_sha,
            }
        )
        seen_live += 1

    # live tree == HEAD check for every managed file
    for rel in v11_managed:
        live = (TEMPLATE / rel["path"]).read_bytes()
        head = git_show("HEAD", f"templates/embedded-c-overlay/{rel['path']}")
        if norm_bytes(live) != norm_bytes(head):
            raise SystemExit(f"live template differs from HEAD: {rel['path']}")

    v11_manifest = {
        "schema_version": 1,
        "overlay": "embedded-c",
        "trellisforge_version": "1.1",
        "trellis_version": "0.6.10",
        "render_tokens": RENDER_TOKENS,
        "files": sorted(v11_managed + [{"path": AGENTS_PATH, "ownership": "managed", "canonical_sha256": agents_sha}], key=lambda f: f["path"]),
    }

    (VERSIONS / "1.0").mkdir(parents=True)
    (VERSIONS / "1.1").mkdir(parents=True)
    (VERSIONS / "1.0" / "manifest.json").write_bytes(
        (json.dumps(v10_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    (VERSIONS / "1.1" / "manifest.json").write_bytes(
        (json.dumps(v11_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    # -------------------------------------------------------- structural chain
    STRUCTURAL.mkdir(parents=True)
    structural = {
        "schema_version": 1,
        "from_version": "1.0",
        "to_version": "1.1",
        "receipt_transition": "bootstrap-schema-1",
        "actions": [],
    }
    (STRUCTURAL / "1.0-to-1.1.json").write_bytes(
        (json.dumps(structural, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    obj_count = len(list(OBJECTS.iterdir()))
    print(f"objects: {obj_count} deduplicated files in {OBJECTS}")
    print(f"1.0 manifest: {len(v10_manifest['files'])} files (managed={len(v10_managed)}, adopt={len(v10_adopt)})")
    print(f"1.1 manifest: {len(v11_manifest['files'])} files (managed={len(v11_managed)})")
    print("wrote history/embedded-c-overlay/{objects,versions}/...")
    print("wrote migrations/embedded-c-overlay/structural/1.0-to-1.1.json")


if __name__ == "__main__":
    build()
    sys.exit(0)