"""Verification of TrellisForge elevator-model assets for the 1.3 release.

Cross-checks (fail closed, deterministic, re-runnable):
  - VERSION == 1.3.
  - Immutable history: 1.0/1.1/1.2 manifests and structural/1.0-to-1.1.json,
    1.1-to-1.2.json byte-match the recorded pre-upgrade baseline hashes.
  - Object library: every object file is self-consistent (name == SHA-256 of
    its LF-normalized, BOM-stripped bytes); every canonical_sha256 referenced
    by any of the four manifests resolves to such a file; no orphan objects.
  - 1.0 fidelity: managed + adoption-baseline bodies match git e40a942; the
    channel command-reference objects keep the historical trailing blank line.
  - 1.3 fidelity: every managed entry matches the live template and (where the
    path exists at HEAD) HEAD; the live template enumeration equals the 1.3
    manifest path set exactly; `.opencode/package.json` is neither delivered
    nor on disk, and `.opencode/.gitignore` covers it.
  - Manifest schema: schema 1, overlay embedded-c, trellis baseline 0.6.10,
    render tokens, no duplicate paths, per-version counts (1.0: 76+12,
    1.1: 89, 1.2: 151, 1.3: 158).
  - Structural chain: adjacent steps 1.0->1.1 (bootstrap-schema-1),
    1.1->1.2 and 1.2->1.3 (preserve-schema-1), contiguous to the current
    VERSION; 1.2->1.3 carries exactly the remove action for
    `.opencode/package.json`; no Plan-A pair-wise assets and no cross-version
    shortcut files.
  - git diff --check clean for history/ and migrations/.

Run from the repo root (paths resolve from this file).
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
PLAN_A = REPO / "migrations" / "embedded-c-overlay" / "1.0-to-1.1"
E40A942 = "e40a942"
TARGET_VERSION = "1.3"
SUPPORTED = ["1.0", "1.1", "1.2", "1.3"]

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

EXCLUDED_NAMES = {"AGENTS.md.template", "TEMPLATE-CONTENTS.md"}
RENDER_TOKENS = ["PROJECT_PREFIX", "PROJECT_NAME", "__PROJECT_PREFIX__"]
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
ALLOWED_ACTIONS = {"rename", "remove", "receipt"}
ALLOWED_TRANSITIONS = {"bootstrap-schema-1", "preserve-schema-1"}
PACKAGE_JSON = ".opencode/package.json"
OPENCODE_GITIGNORE = ".opencode/.gitignore"
INTENTIONAL_MODIFIED = ".trellis/scripts/tests/test_opencode_platform_contract.py"
NEW_13_TESTS = (
    ".trellis/scripts/tests/test_codex_native_wait_contract.py",
    ".trellis/scripts/tests/test_dispatch_chain_contract.py",
    ".trellis/scripts/tests/test_review_severity_adjudication_contract.py",
    ".trellis/scripts/tests/test_small_patch_and_sequel_contract.py",
    ".trellis/scripts/tests/test_step_detail_platform_hints.py",
    ".trellis/scripts/tests/test_task_dir_time_prefix.py",
    ".trellis/scripts/tests/test_write_json_lf.py",
)


def norm(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def strip_bom(data: bytes) -> bytes:
    return data[3:] if data.startswith(b"\xef\xbb\xbf") else data


def sha(data: bytes) -> str:
    return hashlib.sha256(norm(strip_bom(data))).hexdigest()


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    out = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        cwd=str(REPO),
        check=True,
    )
    return out.stdout


def git_show_optional(commit: str, path: str) -> bytes | None:
    out = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        cwd=str(REPO),
    )
    if out.returncode != 0:
        return None
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


def read_no_bom(path: Path) -> bytes:
    return strip_bom(path.read_bytes())


def load(version: str) -> dict:
    return json.loads((VERSIONS / version / "manifest.json").read_text(encoding="utf-8"))


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
    check("version-fact", version == TARGET_VERSION, f"VERSION={version}")

    # ----------------------------------------------- immutable history bytes
    for rel, expected in BASELINE_SHA256.items():
        p = REPO / rel
        check(
            f"immutable[{rel}]",
            p.is_file() and raw_sha(p) == expected,
            f"expected={expected[:12]}",
        )

    # ------------------------------------------------------ objects library
    obj_files = sorted(p.name for p in OBJECTS.iterdir() if p.is_file())
    bad_self = [n for n in obj_files if sha((OBJECTS / n).read_bytes()) != n]
    check("objects-self-consistent", not bad_self, f"bad={bad_self[:5]}")

    manifests = {v: load(v) for v in SUPPORTED}
    referenced: set[str] = set()
    missing_refs = []
    for v, manifest in manifests.items():
        for entry in manifest["files"]:
            obj = OBJECTS / entry["canonical_sha256"]
            if not obj.is_file():
                missing_refs.append(f"{v}:{entry['path']}")
            else:
                referenced.add(entry["canonical_sha256"])
    check("references-resolve", not missing_refs, f"missing={missing_refs[:5]}")
    orphans = sorted(set(obj_files) - referenced)
    check("objects-no-orphan", not orphans, f"orphaned={orphans[:5]}")

    # ------------------------------------------- 1.0 fidelity to e40a942
    v10_by_path = {f["path"]: f for f in manifests["1.0"]["files"]}
    v10_mismatch = []
    for rel, entry in v10_by_path.items():
        if rel == AGENTS:
            src = "templates/embedded-c-overlay/AGENTS.md.template"
        elif rel in ADOPT_PATHS:
            src = rel
        else:
            src = f"templates/embedded-c-overlay/{rel}"
        expected = norm(git_show(E40A942, src))
        actual = norm(read_no_bom(OBJECTS / entry["canonical_sha256"]))
        if expected != actual:
            v10_mismatch.append(rel)
    check("v10-fidelity-e40a942", not v10_mismatch, f"mismatch={v10_mismatch[:5]}")

    # 1.0 keeps the historical trailing blank line on channel command refs
    v10_blank = True
    for rel in (COMMAND_REF_749, COMMAND_REF_750):
        body = read_no_bom(OBJECTS / v10_by_path[rel]["canonical_sha256"])
        v10_blank = v10_blank and body.endswith(b"**.\n\n")
    check("v10-trailing-blank", v10_blank)

    # ------------------------------------------- 1.3 fidelity to live tree
    v13_by_path = {f["path"]: f for f in manifests["1.3"]["files"]}
    drift = []
    for rel, entry in v13_by_path.items():
        src = TEMPLATE / ("AGENTS.md.template" if rel == AGENTS else rel)
        if not src.is_file():
            drift.append(f"{rel} (missing live file)")
            continue
        live = norm(read_no_bom(src))
        obj = norm(read_no_bom(OBJECTS / entry["canonical_sha256"]))
        if live != obj:
            drift.append(rel)
            continue
        if rel == INTENTIONAL_MODIFIED:
            continue
        head = git_show_optional("HEAD", f"templates/embedded-c-overlay/{src.name if rel == AGENTS else rel}")
        if head is not None and norm(strip_bom(head)) != live:
            drift.append(f"{rel} (differs from HEAD)")
    check("v13-live-and-head", not drift, f"drift={drift[:5]}")

    live_paths = set(live_template_paths())
    check(
        "v13-path-set-exact",
        set(v13_by_path) == live_paths | {AGENTS},
        f"manifest={len(v13_by_path)} live={len(live_paths)} +1 AGENTS",
    )

    # package.json retired from 1.3 delivery; gitignore takes over
    check(
        "v13-package-json-retired",
        PACKAGE_JSON not in v13_by_path and not (TEMPLATE / PACKAGE_JSON).exists(),
        PACKAGE_JSON,
    )
    ignore_path = TEMPLATE / OPENCODE_GITIGNORE
    ignore_lines = set()
    if ignore_path.is_file():
        ignore_lines = {line.strip() for line in ignore_path.read_text(encoding="utf-8").splitlines()}
    check(
        "v13-opencode-gitignore",
        OPENCODE_GITIGNORE in v13_by_path
        and {"package.json", "package-lock.json"} <= ignore_lines,
        f"lines={sorted(ignore_lines)}",
    )
    check(
        "v13-new-tests-delivered",
        set(NEW_13_TESTS) <= set(v13_by_path) and all((TEMPLATE / rel).is_file() for rel in NEW_13_TESTS),
        f"new_tests={len(NEW_13_TESTS)}",
    )

    # ------------------------------------------------------- manifest schema
    for v, manifest in manifests.items():
        check(
            f"v{v.replace('.', '')}-schema",
            manifest["schema_version"] == 1
            and manifest["overlay"] == "embedded-c"
            and manifest["trellisforge_version"] == v
            and manifest["trellis_version"] == "0.6.10"
            and manifest["render_tokens"] == RENDER_TOKENS,
        )
        paths = [f["path"] for f in manifest["files"]]
        check(f"v{v.replace('.', '')}-no-dups", len(set(paths)) == len(paths))
        ownership_ok = all(
            f["ownership"] in ("managed", "adoption-baseline") for f in manifest["files"]
        )
        check(f"v{v.replace('.', '')}-ownership", ownership_ok)

    summary = {
        "v10_managed": sum(1 for f in manifests["1.0"]["files"] if f["ownership"] == "managed"),
        "v10_adopt": sum(1 for f in manifests["1.0"]["files"] if f["ownership"] == "adoption-baseline"),
        "v11_managed": sum(1 for f in manifests["1.1"]["files"] if f["ownership"] == "managed"),
        "v12_managed": sum(1 for f in manifests["1.2"]["files"] if f["ownership"] == "managed"),
        "v13_managed": sum(1 for f in manifests["1.3"]["files"] if f["ownership"] == "managed"),
        "v13_adopt": sum(1 for f in manifests["1.3"]["files"] if f["ownership"] == "adoption-baseline"),
    }
    check(
        "manifest-counts",
        summary == {"v10_managed": 76, "v10_adopt": 12, "v11_managed": 89,
                    "v12_managed": 151, "v13_managed": 158, "v13_adopt": 0},
        str(summary),
    )
    check("v11-no-adopt", all(f["ownership"] == "managed" for f in manifests["1.1"]["files"]))

    # --------------------------------------------------- structural chain
    steps = {}
    for i in range(len(SUPPORTED) - 1):
        frm, to = SUPPORTED[i], SUPPORTED[i + 1]
        step_path = STRUCTURAL / f"{frm}-to-{to}.json"
        ok = step_path.is_file()
        check(f"structural-exists[{frm}->{to}]", ok, str(step_path.relative_to(REPO)))
        if not ok:
            continue
        chain = json.loads(step_path.read_text(encoding="utf-8"))
        check(
            f"structural-schema[{frm}->{to}]",
            chain["schema_version"] == 1
            and chain["from_version"] == frm
            and chain["to_version"] == to
            and chain["receipt_transition"] in ALLOWED_TRANSITIONS
            and isinstance(chain["actions"], list)
            and all([a.get("action") in ALLOWED_ACTIONS for a in chain["actions"]]),
            f"transition={chain['receipt_transition']} actions={len(chain['actions'])}",
        )
        steps[(frm, to)] = chain
    check(
        "structural-1.1-to-1.2-empty",
        steps.get(("1.1", "1.2"), {}).get("actions") == []
        and steps.get(("1.1", "1.2"), {}).get("receipt_transition") == "preserve-schema-1",
    )
    check(
        "structural-1.2-to-1.3-remove",
        steps.get(("1.2", "1.3"), {}).get("receipt_transition") == "preserve-schema-1"
        and steps.get(("1.2", "1.3"), {}).get("actions") == [{"action": "remove", "path": PACKAGE_JSON}],
        str(steps.get(("1.2", "1.3"), {}).get("actions")),
    )
    # contiguity: supported sources chain forward to the current VERSION
    contiguous = all(
        steps.get((SUPPORTED[i], SUPPORTED[i + 1]), {}).get("to_version")
        == steps.get((SUPPORTED[i + 1], SUPPORTED[i + 2]), {}).get("from_version")
        for i in range(len(SUPPORTED) - 2)
    )
    check("structural-contiguous-to-version", bool(contiguous) and SUPPORTED[-1] == TARGET_VERSION)
    expected_steps = {f"{SUPPORTED[i]}-to-{SUPPORTED[i + 1]}.json" for i in range(len(SUPPORTED) - 1)}
    extra = [p.name for p in STRUCTURAL.glob("*.json") if p.name not in expected_steps]
    check("structural-no-extra-or-shortcut-steps", not extra, f"extra={extra}")
    missing_manifests = [
        v for v in SUPPORTED if not (VERSIONS / v / "manifest.json").is_file()
    ]
    check("all-supported-versions-manifested", not missing_manifests, f"missing={missing_manifests}")

    # ------------------------------------------- Plan-A assets removed
    check("plan-a-removed", not PLAN_A.exists(), f"{PLAN_A.relative_to(REPO)} must be gone")
    forbidden = {"migration.json", "baseline", "new"}
    leftovers = [c.name for c in (PLAN_A.iterdir() if PLAN_A.exists() else []) if c.name in forbidden]
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
    print("ALL ELEVATOR-ASSET CHECKS PASSED (1.0/1.1/1.2/1.3)")
    return 0


if __name__ == "__main__":
    sys.exit(main())