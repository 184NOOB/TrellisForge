"""Generator for TrellisForge 1.3 elevator-model release assets.

This task APPENDS to the immutable 1.0/1.1/1.2 history produced by the
archived 09-07 and 09-10 generators; it never rebuilds old versions and never
rewrites committed canonical objects. Produces:
  history/embedded-c-overlay/versions/1.3/manifest.json     1.3 version manifest
  history/embedded-c-overlay/objects/<sha256>               only NEW objects
  migrations/embedded-c-overlay/structural/1.2-to-1.3.json  adjacent step

Preconditions verified before writing anything (fail closed):
  - VERSION == 1.3
  - 1.0/1.1/1.2 manifests and structural/1.0-to-1.1.json, 1.1-to-1.2.json
    byte-match the recorded pre-upgrade baseline hashes (immutable history).
  - every existing canonical object is self-consistent (file name == SHA-256
    of its LF-normalized, BOM-stripped bytes) and every 1.0/1.1/1.2 reference
    resolves.
  - 1.0 manifest fidelity re-checks against pinned commit e40a942.
  - the live template tree matches git HEAD for every path except the three
    INTENTIONAL 1.3 changes: `.opencode/package.json` deleted,
    `.opencode/.gitignore` added, and the OpenCode contract test updated.

1.3 source: templates/embedded-c-overlay/** live working tree.
Canonical objects: UTF-8 without BOM, LF-normalized (CRLF->LF only). Nothing
else is trimmed. Objects are appended only when missing; existing files are
never rewritten.
Run from the repo root (or anywhere; paths resolve from this file).
"""
from __future__ import annotations

import hashlib
import json
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
TARGET = "1.3"

# Recorded pre-upgrade baseline hashes (discover-baseline phase). Raw file
# bytes, so any rewrite of immutable history aborts generation immediately.
BASELINE_SHA256 = {
    "history/embedded-c-overlay/versions/1.0/manifest.json":
        "ac26b0975422f17068033764a734d35daddf7d640cef1b3e3856190d10c86a92",
    "history/embedded-c-overlay/versions/1.1/manifest.json":
        "f0ed1f8fbd332cd2669129126b3899227fa6b207ec597eab68a576c49a354587",
    "history/embedded-c-overlay/versions/1.2/manifest.json":
        "6e6c46839f488cccce8e0d4774080c85aecd199d3ad41dddaa721149a95abec1",
    "migrations/embedded-c-overlay/structural/1.0-to-1.1.json":
        "66222336d31259acc9baa3da25d9038c1d0deb4d2ad67b7768363f90e1afa276",
    "migrations/embedded-c-overlay/structural/1.1-to-1.2.json":
        "d2c23fbaf82ad11f1f6d30f3e93828c8b6cc712442625bd897a728b1b3d09829",
}
IMMUTABLE_VERSIONS = ("1.0", "1.1", "1.2")

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
# AGENTS.md.template) every Forge release installs. Its canonical object in
# each version manifest is the AGENTS.md.template content of that era.
AGENTS_PATH = "AGENTS.md.trellisforge-template"

# Deliberate 1.3 working-tree changes relative to HEAD (release task scope):
# package.json leaves official delivery; .gitignore enters; the OpenCode
# contract test is rewritten. Everything else must match HEAD byte-for-byte.
INTENTIONAL_DELETED = ".opencode/package.json"
INTENTIONAL_ADDED = ".opencode/.gitignore"
INTENTIONAL_MODIFIED = ".trellis/scripts/tests/test_opencode_platform_contract.py"


def die(msg: str) -> None:
    raise SystemExit(f"gen_migration: {msg}")


def norm_bytes(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def strip_bom(data: bytes) -> bytes:
    return data[3:] if data.startswith(b"\xef\xbb\xbf") else data


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(norm_bytes(strip_bom(data))).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def live_template_paths() -> list[str]:
    rels = []
    for path in TEMPLATE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(TEMPLATE).as_posix()
        name = rel.rsplit("/", 1)[-1]
        if name in EXCLUDED_NAMES:
            continue
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")):
            continue
        rels.append(rel)
    return sorted(rels)


def add_object(body: bytes) -> str:
    obj_name = sha256_of(body)
    dst = OBJECTS / obj_name
    if not dst.exists():
        dst.write_bytes(norm_bytes(strip_bom(body)))
    return obj_name


def verify_immutable_history() -> None:
    for rel, expected in BASELINE_SHA256.items():
        actual = raw_sha256(REPO / rel)
        if actual != expected:
            die(f"immutable history changed, refusing to generate: {rel} sha={actual} != {expected}")

    for obj in sorted(OBJECTS.iterdir()):
        if not obj.is_file():
            continue
        if sha256_of(obj.read_bytes()) != obj.name:
            die(f"canonical object self-hash mismatch: {obj.name}")

    for version in IMMUTABLE_VERSIONS:
        manifest = json.loads((VERSIONS / version / "manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if not (OBJECTS / entry["canonical_sha256"]).is_file():
                die(f"{version} manifest references missing object: {entry['path']}")

    # 1.0 re-check against the pinned source commit.
    v10 = json.loads((VERSIONS / "1.0" / "manifest.json").read_text(encoding="utf-8"))
    for entry in v10["files"]:
        rel = entry["path"]
        if rel == AGENTS_PATH:
            src = "templates/embedded-c-overlay/AGENTS.md.template"
        elif rel in ADOPT_PATHS:
            src = rel
        else:
            src = f"templates/embedded-c-overlay/{rel}"
        expected = norm_bytes(strip_bom(git_show(E40A942, src)))
        actual = norm_bytes((OBJECTS / entry["canonical_sha256"]).read_bytes())
        if expected != actual:
            die(f"1.0 object drifted from {E40A942}:{src}")


def verify_live_matches_head_with_intent() -> None:
    head_paths = set(git_ls_template("HEAD"))
    live_paths = set(live_template_paths())

    if INTENTIONAL_DELETED not in head_paths:
        die(f"expected {INTENTIONAL_DELETED} in HEAD (the 1.2-era managed file)")
    if INTENTIONAL_DELETED in live_paths:
        die(f"{INTENTIONAL_DELETED} must be deleted from the live template (1.3)")
    if INTENTIONAL_ADDED in head_paths:
        die(f"{INTENTIONAL_ADDED} unexpectedly already tracked; review this task's intent")
    if INTENTIONAL_ADDED not in live_paths:
        die(f"{INTENTIONAL_ADDED} missing from the live template")
    if INTENTIONAL_MODIFIED not in live_paths:
        die(f"{INTENTIONAL_MODIFIED} missing from the live template")

    unexpected_head_only = head_paths - live_paths - {INTENTIONAL_DELETED}
    if unexpected_head_only:
        die(f"unintended template deletions vs HEAD: {sorted(unexpected_head_only)}")
    unexpected_live_only = live_paths - head_paths - {INTENTIONAL_ADDED}
    if unexpected_live_only:
        die(f"unintended template additions vs HEAD: {sorted(unexpected_live_only)}")

    for rel in sorted((head_paths & live_paths) - {INTENTIONAL_MODIFIED}):
        live = norm_bytes(strip_bom((TEMPLATE / rel).read_bytes()))
        head = norm_bytes(strip_bom(git_show("HEAD", f"templates/embedded-c-overlay/{rel}")))
        if live != head:
            die(f"live template differs from HEAD: {rel}")


def build() -> None:
    if (REPO / "VERSION").read_text(encoding="utf-8").strip() != TARGET:
        die(f"VERSION must be {TARGET} before generating assets")

    verify_immutable_history()
    verify_live_matches_head_with_intent()

    # ------------------------------------------------------------ 1.3 manifest
    v13_entries = []
    for rel in live_template_paths():
        live = (TEMPLATE / rel).read_bytes()
        obj_sha = add_object(live)
        v13_entries.append(
            {
                "path": rel,
                "ownership": "managed",
                "canonical_sha256": obj_sha,
            }
        )

    agents_body = (TEMPLATE / "AGENTS.md.template").read_bytes()
    agents_sha = add_object(agents_body)
    v13_entries.append(
        {"path": AGENTS_PATH, "ownership": "managed", "canonical_sha256": agents_sha}
    )

    v13_manifest = {
        "schema_version": 1,
        "overlay": "embedded-c",
        "trellisforge_version": TARGET,
        "trellis_version": "0.6.10",
        "render_tokens": RENDER_TOKENS,
        "files": sorted(v13_entries, key=lambda f: f["path"]),
    }

    (VERSIONS / TARGET).mkdir(exist_ok=True)
    (VERSIONS / TARGET / "manifest.json").write_bytes(
        (json.dumps(v13_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    # ------------------------------------------------- adjacent structural step
    STRUCTURAL.mkdir(parents=True, exist_ok=True)
    step_path = STRUCTURAL / "1.2-to-1.3.json"
    structural = {
        "schema_version": 1,
        "from_version": "1.2",
        "to_version": TARGET,
        "receipt_transition": "preserve-schema-1",
        # Source-only path coverage: `.opencode/package.json` leaves official
        # delivery. The updater classifies it structural-remove and never
        # deletes the downstream disk file.
        "actions": [{"action": "remove", "path": INTENTIONAL_DELETED}],
    }
    step_path.write_bytes(
        (json.dumps(structural, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )

    obj_count = len([p for p in OBJECTS.iterdir() if p.is_file()])
    print(f"{TARGET} manifest: {len(v13_manifest['files'])} files (managed={len(v13_entries)})")
    print(f"objects library: {obj_count} files (append-only)")
    print(f"wrote history/embedded-c-overlay/versions/{TARGET}/manifest.json")
    print(f"wrote {step_path.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    build()
    # Re-assert baseline hashes after generation: append-only guarantee.
    for rel, expected in BASELINE_SHA256.items():
        actual = raw_sha256(REPO / rel)
        if actual != expected:
            die(f"baseline asset was modified during generation: {rel}")
    sys.exit(0)