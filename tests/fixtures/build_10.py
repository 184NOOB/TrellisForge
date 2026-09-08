# -*- coding: utf-8 -*-
"""Build a clean TrellisForge 1.0 downstream layout from the elevator-model
1.0 manifest + canonical object library (used by the update smoke tests)."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "templates" / "embedded-c-overlay"
HISTORY = REPO / "history" / "embedded-c-overlay"
OBJECTS = HISTORY / "objects"
VERSIONS = HISTORY / "versions"

PREFIX = "example"
PROJECT_NAME = "Example Firmware"


def norm(text: str) -> str:
    return text.replace("\r\n", "\n")


def sha256_of(text: str) -> str:
    return hashlib.sha256(norm(text).encode("utf-8")).hexdigest()


def render_content(text: str, prefix: str, name: str) -> str:
    if text.startswith("﻿"):
        text = text[1:]
    return text.replace("PROJECT_PREFIX", prefix).replace("PROJECT_NAME", name)


def render_path(rel: str, prefix: str) -> str:
    return rel.replace("__PROJECT_PREFIX__", prefix)


def read_no_bom(path: Path) -> bytes:
    data = path.read_bytes()
    return data[3:] if data.startswith(b"\xef\xbb\xbf") else data


def build_10_target(root: Path, prefix=PREFIX, name=PROJECT_NAME) -> None:
    v10 = json.loads((VERSIONS / "1.0" / "manifest.json").read_text(encoding="utf-8"))
    for entry in v10["files"]:
        obj = OBJECTS / entry["canonical_sha256"]
        body = read_no_bom(obj).decode("utf-8")
        rel = entry["path"]
        if rel == "AGENTS.md.trellisforge-template":
            continue  # generated artifact; installers produce it
        if entry["ownership"] == "adoption-baseline":
            dest_rel = rel
        else:
            dest_rel = render_path(rel, prefix)
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(render_content(body, prefix, name).encode("utf-8"))


def make_project(tmp: Path) -> Path:
    project = tmp / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    (project / ".trellis").mkdir(exist_ok=True)
    build_10_target(project)
    return project


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="tf-build10-") as tmp:
        p = make_project(Path(tmp))
        n = len(list((p / ".trellis").rglob("*")))
        print(f"built 1.0 target at {p} ({n} files)")
        # verify command-reference has the historical trailing blank line
        ref = p / ".agents/skills/trellis-channel/references/command-reference.md"
        print("ref-tail:", ref.read_bytes()[-6:])
        print("ref-tail-ok:", ref.read_bytes().endswith(b"**.\n\n"))