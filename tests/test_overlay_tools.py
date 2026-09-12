# -*- coding: utf-8 -*-
"""Automated tests for the TrellisForge overlay installer and the elevator-model
updater (source 1.0/1.1 -> current 1.2).

These tests build isolated temporary Git repositories from the elevator-model
assets (history/embedded-c-overlay/versions/1.0 and 1.1 manifests plus the
canonical object library) and the current 1.2 manifest/template, then drive the
Windows PowerShell 5.1 entry scripts. The 1.1 downstream fixture is rendered
from the immutable 1.1 manifest/canonical objects with a real schema-1 receipt;
it is never faked by running the current installer. They do not depend on a
real downstream project, the `trellis` CLI, or the network, and they do NOT
reference the removed Plan-A baseline/new/migration.json layout.

Body-merge contract asserted here: for both sources the file bodies merge
exactly once from the SOURCE canonical + downstream current + 1.2 template
(1.0 -> 1.2 never reads or lands a 1.1 body on disk); only the STRUCTURAL
migration composes adjacent steps (1.0 -> 1.2 loads 1.0-to-1.1 AND
1.1-to-1.2; 1.1 -> 1.2 loads only the latter).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"
TEMPLATE = REPO_ROOT / "templates" / "embedded-c-overlay"
HISTORY = REPO_ROOT / "history" / "embedded-c-overlay"
OBJECTS = HISTORY / "objects"
VERSIONS = HISTORY / "versions"
STRUCTURAL = REPO_ROOT / "migrations" / "embedded-c-overlay" / "structural"
INSTALLER = TOOLS / "install-embedded-c-overlay.ps1"
UPDATER = TOOLS / "update-embedded-c-overlay.ps1"
MODULE = TOOLS / "lib" / "TrellisForgeOverlay.psm1"

TARGET_VERSION = "1.2"
SOURCE_VERSIONS = ("1.0", "1.1")
COMMAND_REF = ".agents/skills/trellis-channel/references/command-reference.md"
CHECK_MD = ".trellis/agents/check.md"
WORKFLOW_MD = ".trellis/workflow.md"
AGENTS = "AGENTS.md.trellisforge-template"
OPENCODE_GRILL = ".opencode/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md"
OPENCODE_CHECK_AGENT = ".opencode/agents/trellis-check.md"
PREFIX = "example"
PROJECT_NAME = "Example Firmware"

DESC_ANCHOR = "embedded C project quality auditor for the Trellis channel runtime."


def ps_exe():
    for candidate in (
        os.environ.get("POWERSHELL_EXE"),
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        shutil.which("powershell.exe"),
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return "powershell.exe"


def run_ps(script, *args):
    return subprocess.run(
        [ps_exe(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def run_cmd(argv, cwd=None):
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=300)


def norm(text: str) -> str:
    return text.replace("\r\n", "\n")


def sha256_of(text: str) -> str:
    return sha256_of_bytes(norm(text).encode("utf-8"))


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_path(rel: str, prefix: str) -> str:
    return rel.replace("__PROJECT_PREFIX__", prefix)


def render_content(text: str, prefix: str, name: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("PROJECT_PREFIX", prefix).replace("PROJECT_NAME", name)


def read_no_bom(path: Path) -> bytes:
    data = path.read_bytes()
    return data[3:] if data.startswith(b"\xef\xbb\xbf") else data


def write_text_bytes(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def load_manifest(version: str):
    return json.loads((VERSIONS / version / "manifest.json").read_text(encoding="utf-8"))


def entries_by_path(version: str):
    return {f["path"]: f for f in load_manifest(version)["files"]}


def canonical_body(version: str, rel: str) -> str:
    entry = entries_by_path(version)[rel]
    return read_no_bom(OBJECTS / entry["canonical_sha256"]).decode("utf-8")


def rendered_body(version: str, rel: str, prefix=PREFIX, name=PROJECT_NAME) -> str:
    return render_content(canonical_body(version, rel), prefix, name)


def double_changed_paths():
    """Paths whose canonical changed on BOTH hops 1.0->1.1 and 1.1->1.2."""
    p10 = entries_by_path("1.0")
    p11 = entries_by_path("1.1")
    p12 = entries_by_path("1.2")
    return sorted(
        rel for rel in p11
        if rel in p10 and rel in p12
        and p10[rel]["canonical_sha256"] != p11[rel]["canonical_sha256"]
        and p11[rel]["canonical_sha256"] != p12[rel]["canonical_sha256"]
    )


def build_rendered_target(root: Path, version: str, prefix=PREFIX, name=PROJECT_NAME,
                          with_receipt=False) -> None:
    """Render a pristine downstream tree for `version` from its immutable
    manifest + canonical objects. Adoption-baseline paths (1.0) are NOT
    token-rendered (they carry no token and upstream installs them verbatim).
    Optionally write a real schema-1 receipt with the three hashes."""
    v = load_manifest(version)
    receipt_files = []
    for entry in v["files"]:
        rel = entry["path"]
        body = read_no_bom(OBJECTS / entry["canonical_sha256"]).decode("utf-8")
        rendered = render_content(body, prefix, name)
        dest_rel = rel if rel == AGENTS else render_path(rel, prefix)
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(rendered.encode("utf-8"))
        if with_receipt:
            receipt_files.append({
                "path": dest_rel.replace("\\", "/"),
                "canonical_sha256": entry["canonical_sha256"],
                "baseline_sha256": sha256_of(rendered),
                "installed_sha256": sha256_of(rendered),
            })
    if with_receipt:
        receipt = {
            "schema_version": 1,
            "trellisforge_version": version,
            "overlay": "embedded-c",
            "project_prefix": prefix,
            "project_name": name,
            "files": receipt_files,
        }
        dot = root / ".trellis"
        dot.mkdir(exist_ok=True)
        (dot / "trellisforge.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_10_target(root: Path, prefix=PREFIX, name=PROJECT_NAME, include_all=True) -> None:
    """Build a clean TrellisForge 1.0 downstream layout from the 1.0 manifest
    and the canonical object library (no receipt exists for 1.0)."""
    v10 = load_manifest("1.0")
    for entry in v10["files"]:
        obj = OBJECTS / entry["canonical_sha256"]
        body = read_no_bom(obj).decode("utf-8")
        rel = entry["path"]
        if rel == AGENTS:
            if include_all:
                dest = root / AGENTS
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(render_content(body, prefix, name).encode("utf-8"))
            continue
        if entry["ownership"] == "adoption-baseline":
            dest_rel = rel
        else:
            dest_rel = render_path(rel, prefix)
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(render_content(body, prefix, name).encode("utf-8"))


class OverlayTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trellisforge-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def make_10_project(self, **kw):
        (self.project / ".trellis").mkdir(exist_ok=True)
        build_10_target(self.project, **kw)
        return self.project

    def make_11_project(self, prefix=PREFIX, name=PROJECT_NAME):
        (self.project / ".trellis").mkdir(exist_ok=True)
        build_rendered_target(self.project, "1.1", prefix=prefix, name=name, with_receipt=True)
        return self.project

    def install(self, *extra, expect=0):
        params = ["-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME]
        params += list(extra)
        r = run_ps(INSTALLER, *params)
        combined = r.stdout + r.stderr
        self.assertEqual(r.returncode, expect, "install exit code\n" + combined)
        return r, combined

    def upgrade(self, *extra, expect=0):
        params = ["-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME]
        params += list(extra)
        r = run_ps(UPDATER, *params)
        combined = r.stdout + r.stderr
        self.assertEqual(r.returncode, expect, "upgrade exit code\n" + combined)
        return r, combined

    def upgrade_bare(self, *extra):
        """Invoke the updater without project params unless passed in extra."""
        r = run_ps(UPDATER, "-TargetRoot", str(self.project), *list(extra))
        return r, r.stdout + r.stderr

    def read_json(self, rel):
        p = self.project / rel
        self.assertTrue(p.exists(), f"missing {rel}")
        return json.loads(p.read_text(encoding="utf-8"))

    def read_receipt_version(self):
        return self.read_json(".trellis/trellisforge.json")["trellisforge_version"]

    def assert_sentinels(self, files, receipt_version=None):
        receipt = self.read_json(".trellis/trellisforge.json")
        if receipt_version is not None:
            self.assertEqual(receipt["trellisforge_version"], receipt_version)
        for rel, content in files.items():
            p = self.project / rel
            self.assertTrue(p.exists(), f"sentinels {rel} deleted")
            self.assertEqual(p.read_bytes(), content, f"sentinel changed: {rel}")

    def add_sentinel_state(self):
        dot = self.project / ".trellis"
        dot.mkdir(exist_ok=True)
        version = dot / ".version"
        version.write_text("0.6.10\n", encoding="utf-8")
        hashes = dot / ".template-hashes.json"
        hashes.write_text('{"fake": true}\n', encoding="utf-8")
        business = self.project / "src/main.c"
        business.parent.mkdir(parents=True, exist_ok=True)
        business.write_text("/* user business code */\n", encoding="utf-8")
        untracked = self.project / "notes.txt"
        untracked.write_text("user untracked note\n", encoding="utf-8")
        return {
            ".trellis/.version": version.read_bytes(),
            ".trellis/.template-hashes.json": hashes.read_bytes(),
            "src/main.c": business.read_bytes(),
            "notes.txt": untracked.read_bytes(),
        }

    def assert_sentinel_untouched(self, before):
        for rel, was in before.items():
            p = self.project / rel
            self.assertTrue(p.exists(), f"sentinels {rel} deleted")
            self.assertEqual(p.read_bytes(), was, f"sentinel changed: {rel}")

    def run_ps_driver(self, body):
        driver = self.tmp / "driver.ps1"
        driver.write_text(body, encoding="utf-8-sig")
        r = run_ps(driver)
        return r, r.stdout + r.stderr


class InstallTests(OverlayTestCase):
    def test_fresh_install_full_12_writes_receipt(self):
        self.make_10_project()
        r, out = self.install("-Force", expect=0)
        self.assertTrue((self.project / ".trellis/workflow.md").exists())
        self.assertTrue((self.project / ".agents/skills/trellis-channel/SKILL.md").exists())
        # 1.2 installs the full OpenCode platform closure
        self.assertTrue((self.project / ".opencode/agents/trellis-check.md").exists())
        self.assertTrue((self.project / ".opencode/plugins/session-start.js").exists())
        self.assertTrue((self.project / ".opencode/skills/example-trellis-grill-adapter/SKILL.md").exists())
        receipt = self.read_json(".trellis/trellisforge.json")
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["trellisforge_version"], TARGET_VERSION)
        self.assertEqual(receipt["overlay"], "embedded-c")
        self.assertEqual(receipt["project_prefix"], PREFIX)
        self.assertEqual(len(receipt["files"]), 151)
        self.assertNotIn(
            b"\r\n",
            (self.project / ".trellis/trellisforge.json").read_bytes(),
            "committable receipt must use LF line endings",
        )
        for entry in receipt["files"]:
            self.assertTrue(entry["path"].startswith((".", AGENTS)))
            for key in ("canonical_sha256", "baseline_sha256", "installed_sha256"):
                self.assertRegex(entry[key], r"^[0-9a-f]{64}$")

    def test_receipt_baseline_eq_installed_on_clean_install(self):
        self.make_10_project()
        self.install("-Force", expect=0)
        receipt = self.read_json(".trellis/trellisforge.json")
        for entry in receipt["files"]:
            self.assertEqual(
                entry["baseline_sha256"], entry["installed_sha256"],
                f"clean install must not report customization for {entry['path']}",
            )
        # canonical（渲染前对象哈希）可能不同于渲染后 baseline（有 project 参数）
        sample = next(f for f in receipt["files"] if f["path"] == ".trellis/workflow.md")
        self.assertNotEqual(sample["canonical_sha256"], sample["baseline_sha256"])

    def test_blank_target_install_without_force(self):
        (self.project / ".trellis").mkdir(exist_ok=True)
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.project / ".trellis/trellisforge.json").exists())

    def test_force_backup_and_placeholder_replacement(self):
        self.make_10_project()
        self.install("-Force", expect=0)
        backups = list((self.project / ".git/trellisforge-backup").glob("*"))
        self.assertTrue(backups, "no backup dir created")
        manifest = json.loads((backups[0] / "backup-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertGreater(len(manifest["files"]), 0)
        residue = []
        for p in self.project.rglob("*"):
            if p.is_file() and p.suffix in {".md", ".yaml", ".py", ".toml", ".json"}:
                text = p.read_text(encoding="utf-8", errors="replace")
                if any(tok in text for tok in ("__PROJECT_PREFIX__", "PROJECT_PREFIX", "PROJECT_NAME")):
                    residue.append(str(p.relative_to(self.project)))
        self.assertEqual(residue, [])

    def test_conflict_preview_blocks_without_force(self):
        self.make_10_project()
        self.install("-Force", expect=0)
        r, out = self.install(expect=1)
        self.assertIn("-Force", out)
        self.assertTrue((self.project / ".trellis/workflow.md").exists())

    def test_install_does_not_touch_trellis_state_or_user_files(self):
        self.make_10_project()
        before = self.add_sentinel_state()
        self.install("-Force", expect=0)
        self.assert_sentinel_untouched(before)

    def test_incompatible_receipt_blocks_install(self):
        self.make_10_project()
        (self.project / ".trellis/trellisforge.json").write_text(
            json.dumps({"schema_version": 1, "trellisforge_version": "0.9",
                        "overlay": "different", "project_prefix": "other",
                        "project_name": "x", "files": []}),
            encoding="utf-8",
        )
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", PROJECT_NAME, "-Force")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads((self.project / ".trellis/trellisforge.json").read_text(encoding="utf-8"))["project_prefix"], "other",
                         "incompatible receipt must remain untouched")


class LiveTemplateConsistencyTests(OverlayTestCase):
    def test_live_template_matches_12_manifest(self):
        # evidence for installer/updater-live-manifest-consistent: every 1.2
        # managed file has identical LF-normalized content between live
        # template, HEAD and its canonical object.
        v12 = load_manifest("1.2")
        self.assertEqual(v12["trellisforge_version"], TARGET_VERSION)
        self.assertEqual(len(v12["files"]), 151)
        for entry in v12["files"]:
            if entry["path"] == AGENTS:
                src = TEMPLATE / "AGENTS.md.template"
            else:
                src = TEMPLATE / entry["path"]
            live = src.read_bytes()
            live = live[3:] if live.startswith(b"\xef\xbb\xbf") else live
            obj = (OBJECTS / entry["canonical_sha256"]).read_bytes()
            self.assertEqual(norm(live.decode("utf-8")), norm(obj.decode("utf-8")),
                             f"live template drifted from canonical object: {entry['path']}")

    def test_11_manifest_matches_history_and_keeps_rules(self):
        # The immutable 1.1 manifest still resolves and still carries the
        # subtask-1 channel rules (historical facts, never rewritten).
        v11 = load_manifest("1.1")
        self.assertEqual(v11["trellisforge_version"], "1.1")
        self.assertEqual(len(v11["files"]), 89)
        for entry in v11["files"]:
            obj = OBJECTS / entry["canonical_sha256"]
            self.assertTrue(obj.is_file(), f"1.1 reference lost: {entry['path']}")
            self.assertEqual(sha256_of_bytes(obj.read_bytes().replace(b"\r\n", b"\n")),
                             entry["canonical_sha256"])
        for rel in (COMMAND_REF, ".claude/skills/trellis-channel/references/command-reference.md"):
            obj = (OBJECTS / entries_by_path("1.1")[rel]["canonical_sha256"]).read_bytes()
            self.assertTrue(b"Standard dispatch use:" in obj, rel)
            self.assertTrue(obj.endswith(b"**.\n"), f"{rel} 1.1 body must drop the extra blank line")

    def test_10_manifest_keeps_historical_blank(self):
        v10 = load_manifest("1.0")
        for rel in (COMMAND_REF, ".claude/skills/trellis-channel/references/command-reference.md"):
            entry = next(f for f in v10["files"] if f["path"] == rel)
            obj = (OBJECTS / entry["canonical_sha256"]).read_bytes()
            self.assertTrue(obj.endswith(b"**.\n\n"), "1.0 canonical must keep historical blank line")
            self.assertEqual(entry["ownership"], "adoption-baseline")

    def test_12_adds_open_code_closure_without_removing_paths(self):
        v11p = set(entries_by_path("1.1"))
        v12p = set(entries_by_path("1.2"))
        added = v12p - v11p
        self.assertTrue(any(p.startswith(".opencode/") for p in added))
        self.assertGreaterEqual(sum(1 for p in added if p.startswith(".opencode/")), 59)
        # no managed path disappeared between 1.1 and 1.2 (actions == [])
        self.assertEqual(v11p - v12p, set())

    def test_live_template_drift_fails_closed(self):
        # R3/R7 the shared check Assert-OverlayLiveTemplateMatchesManifest must
        # reject both a drifted managed file and a managed file missing from the
        # live template. Installer and updater both call this before writing.
        drifted = self.tmp / "drifted-template"
        shutil.copytree(TEMPLATE, drifted)
        wf = drifted / ".trellis/workflow.md"
        wf.write_bytes(wf.read_bytes() + b"\n# drift sentinel\n")
        driver = self.tmp / "drift_check.ps1"
        driver.write_text(
            "Import-Module '%s' -Force\n"
            "$m = Get-OverlayVersionManifest -Overlay 'embedded-c' -Version '1.2'\n"
            "try {\n"
            "  Assert-OverlayLiveTemplateMatchesManifest -Overlay 'embedded-c' -Version '1.2' -TemplateRoot '%s' -Manifest $m | Out-Null\n"
            "  Write-Output 'NO-DRIFT-DETECTED'\n"
            "  exit 2\n"
            "} catch {\n"
            "  Write-Output ('DRIFT=' + $_.Exception.Message)\n"
            "  exit 0\n"
            "}" % (MODULE, drifted),
            encoding="utf-8-sig",
        )
        r = run_ps(driver)
        combined = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, combined)
        self.assertIn("DRIFT=", combined)
        self.assertIn("fail closed", combined)
        self.assertIn(".trellis/workflow.md", combined)

        # A managed file missing from the live template must also fail closed.
        (drifted / ".trellis/agents/check.md").unlink()
        r = run_ps(driver)
        combined = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, combined)
        self.assertIn("fail closed", combined)
        self.assertIn(".trellis/agents/check.md", combined)
        self.assertIn("missing from live template", combined)


class UpgradeFrom10Tests(OverlayTestCase):
    def test_clean_10_upgrade_applies_and_is_idempotent(self):
        self.make_10_project()
        r, out = self.upgrade(expect=0)
        self.assertIn("[UPDATE]", out)
        # Chinese banner text survives as ASCII version markers under cp936 pipes
        self.assertIn("1.0 -> ", out)
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists(),
                         "preflight must not write")
        r, out = self.upgrade("-Apply", expect=0)
        receipt = self.read_json(".trellis/trellisforge.json")
        self.assertEqual(receipt["trellisforge_version"], TARGET_VERSION)
        self.assertEqual(len(receipt["files"]), 151)
        for entry in receipt["files"]:
            for key in ("canonical_sha256", "baseline_sha256", "installed_sha256"):
                self.assertRegex(entry[key], r"^[0-9a-f]{64}$")
            if "project_prefix" not in entry["path"]:
                self.assertEqual(
                    entry["baseline_sha256"], entry["installed_sha256"],
                    f"clean upgrade must not report customization for {entry['path']}",
                )
        r, out = self.upgrade(expect=0)
        self.assertIn("already-current", out)

    def test_clean_10_bodies_merge_once_from_10_canonical_never_land_11(self):
        # 1.0 -> 1.2 file bodies are merged DIRECTLY (old = 1.0 canonical,
        # new = 1.2 template). For every path that changed on both hops the
        # resulting worktree file must equal the 1.2 rendering and must never
        # equal the intermediate 1.1 rendering on disk.
        double = double_changed_paths()
        self.assertGreaterEqual(len(double), 5)  # workflow.md, check.md, workers.md, ...
        self.make_10_project()
        self.upgrade("-Apply", expect=0)
        for rel in double:
            target = self.project / render_path(rel, PREFIX)
            text = norm(target.read_text(encoding="utf-8"))
            self.assertEqual(text, norm(rendered_body("1.2", rel)),
                             f"1.0->1.2 result must equal 1.2 rendering: {rel}")
            self.assertNotEqual(text, norm(rendered_body("1.1", rel)),
                                f"intermediate 1.1 body must never land on disk: {rel}")
        receipt = self.read_json(".trellis/trellisforge.json")
        by_path = {f["path"]: f for f in receipt["files"]}
        sample = by_path[render_path(WORKFLOW_MD, PREFIX)]
        self.assertEqual(sample["canonical_sha256"], entries_by_path("1.2")[WORKFLOW_MD]["canonical_sha256"],
                         "receipt canonical must be the 1.2 canonical, not 1.0 or 1.1")

    def test_open_code_new_paths_added_on_upgrade(self):
        self.make_10_project()
        self.upgrade("-Apply", expect=0)
        for rel in (OPENCODE_CHECK_AGENT, OPENCODE_GRILL):
            target = self.project / render_path(rel, PREFIX)
            self.assertTrue(target.is_file(), f"1.2 added path missing: {rel}")
            self.assertEqual(norm(target.read_text(encoding="utf-8")), norm(rendered_body("1.2", rel)))

    def test_open_code_new_path_existing_identical_is_already_current(self):
        self.make_10_project()
        target = self.project / render_path(OPENCODE_GRILL, PREFIX)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered_body("1.2", OPENCODE_GRILL), encoding="utf-8")
        r, out = self.upgrade(expect=0)
        self.assertIn(f"[ALREADY-CURRENT] {OPENCODE_GRILL}", out)
        self.assertNotIn("[CONFLICT]", out)

    def test_open_code_new_path_existing_different_conflicts_zero_write(self):
        self.make_10_project()
        target = self.project / render_path(OPENCODE_GRILL, PREFIX)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text_bytes(target, "# my local opencode skill\n")
        r, out = self.upgrade(expect=1)
        self.assertIn("[CONFLICT]", out)
        self.assertIn(OPENCODE_GRILL, out)
        self.assertEqual(target.read_bytes(), b"# my local opencode skill\n")
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())
        self.assertFalse((self.project / ".opencode/agents/trellis-check.md").exists(),
                         "conflict must block the whole apply (zero worktree writes)")

    def test_clean_10_command_reference_gets_rules_and_drops_blank(self):
        self.make_10_project()
        for rel in (COMMAND_REF, ".claude/skills/trellis-channel/references/command-reference.md"):
            text = (self.project / rel).read_text(encoding="utf-8")
            self.assertTrue(text.endswith("**.\n\n"), f"fixture must keep 1.0 blank tail: {rel}")
        self.upgrade("-Apply", expect=0)
        for rel in (COMMAND_REF, ".claude/skills/trellis-channel/references/command-reference.md"):
            text = (self.project / rel).read_text(encoding="utf-8")
            self.assertIn("Standard dispatch use:", text, rel)
            self.assertTrue(text.endswith("**.\n"), f"{rel} must drop the extra blank line")
        a = (self.project / COMMAND_REF).read_bytes()
        b = (self.project / ".claude/skills/trellis-channel/references/command-reference.md").read_bytes()
        self.assertEqual(a, b)

    def test_user_edit_away_from_change_regions_merges(self):
        self.make_10_project()
        ref = self.project / COMMAND_REF
        text = ref.read_text(encoding="utf-8")
        text = text.replace("### `create <name>`", "### `create <name>` (team note)", 1)
        write_text_bytes(ref, text)
        r, out = self.upgrade(expect=0)
        self.assertIn("[USER-MERGED]", out)
        self.assertNotIn("[CONFLICT]", out)
        self.upgrade("-Apply", expect=0)
        text = (self.project / COMMAND_REF).read_text(encoding="utf-8")
        self.assertIn("(team note)", text)
        self.assertIn("Standard dispatch use:", text)

    def test_user_edit_overlapping_change_region_conflicts_zero_write(self):
        self.make_10_project()
        chk = self.project / CHECK_MD
        text = chk.read_text(encoding="utf-8")
        # edit the exact description line that changed 1.0 -> 1.2
        self.assertIn(DESC_ANCHOR, text)
        text = text.replace(DESC_ANCHOR, DESC_ANCHOR + " (team fork)", 1)
        write_text_bytes(chk, text)
        r, out = self.upgrade(expect=1)
        self.assertIn("[CONFLICT]", out)
        upgrade_root = self.project / ".git/trellisforge-upgrade"
        dirs = list(upgrade_root.glob("*")) if upgrade_root.exists() else []
        self.assertEqual(len(dirs), 1)
        report_dir = dirs[0]
        self.assertTrue((report_dir / "report.json").exists())
        self.assertTrue((report_dir / "report.txt").exists())
        report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "conflict")
        self.assertEqual(report["from_version"], "1.0")
        self.assertEqual(report["to_version"], TARGET_VERSION)
        self.assertIn(CHECK_MD, [p["path"] for p in report["paths"]])
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())
        self.assertIn("(team fork)", chk.read_text(encoding="utf-8"))
        self.assertFalse((self.project / ".opencode").exists(),
                         "no partial 1.2 application on conflict")

    def test_new_file_conflict(self):
        self.make_10_project()
        addf = self.project / ".trellis/scripts/tests/test_trellis_channel_contract.py"
        write_text_bytes(addf, "# user custom test\n")
        r, out = self.upgrade(expect=1)
        self.assertIn("test_trellis_channel_contract.py", out)
        self.assertEqual(addf.read_bytes(), b"# user custom test\n")
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_unsupported_source_version(self):
        self.make_10_project()
        r = run_ps(UPDATER, "-TargetRoot", str(self.project), "-FromVersion", "0.9",
                   "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unsupported", (r.stdout + r.stderr).lower())
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_no_receipt_rejects_from_version_11(self):
        # Without a receipt only the 1.0 adoption entry is allowed; a 1.1
        # source must come from a real receipt, never be guessed.
        self.make_10_project()
        r = run_ps(UPDATER, "-TargetRoot", str(self.project), "-FromVersion", "1.1",
                   "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unsupported", (r.stdout + r.stderr).lower())
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_missing_project_params_without_receipt(self):
        self.make_10_project()
        r, out = self.upgrade_bare()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ProjectPrefix", out)
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_receipt_param_conflict_fails_closed(self):
        # A valid but older receipt (1.0) with conflicting project params must
        # fail closed instead of guessing; no writes happen.
        self.make_10_project()
        (self.project / ".trellis/trellisforge.json").write_text(
            json.dumps({"schema_version": 1, "trellisforge_version": "1.0",
                        "overlay": "embedded-c", "project_prefix": "other",
                        "project_name": "Other", "files": []}),
            encoding="utf-8",
        )
        r = run_ps(UPDATER, "-TargetRoot", str(self.project),
                   "-ProjectPrefix", "different", "-ProjectName", PROJECT_NAME)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fail closed", r.stdout + r.stderr)

    def test_upgrade_does_not_touch_state_or_user_files(self):
        self.make_10_project()
        before = self.add_sentinel_state()
        self.upgrade("-Apply", expect=0)
        self.assert_sentinel_untouched(before)

    def test_unmodified_canonical_paths_do_not_rewrite_worktree(self):
        # Files whose canonical_sha256 is identical between 1.0 and 1.2 are
        # never rewritten; the new receipt still records baseline/installed.
        self.make_10_project()
        p10 = entries_by_path("1.0")
        p12 = entries_by_path("1.2")
        unchanged = [
            rel for rel, e in p10.items()
            if rel in p12 and rel != AGENTS and e["ownership"] == "managed"
            and e["canonical_sha256"] == p12[rel]["canonical_sha256"]
        ]
        simple = next(p for p in unchanged if "__PROJECT_PREFIX__" not in p)
        target = self.project / simple
        before = target.read_bytes()
        mtime_before = target.stat().st_mtime_ns
        self.upgrade("-Apply", expect=0)
        self.assertEqual(target.read_bytes(), before, f"unchanged canonical path rewritten: {simple}")
        self.assertLessEqual(target.stat().st_mtime_ns - mtime_before, 3_000_000_000)

    def test_lf_target_clean(self):
        self.make_10_project()
        self.upgrade("-Apply", expect=0)
        ref = (self.project / COMMAND_REF).read_bytes()
        self.assertIn(b"Standard dispatch use:", ref)
        self.assertNotIn(b"\r\n", ref, "LF style must be preserved")

    def test_crlf_target_clean(self):
        self.make_10_project()
        for rel in (COMMAND_REF, WORKFLOW_MD, CHECK_MD):
            p = self.project / rel
            p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        r, out = self.upgrade(expect=0)
        self.assertNotIn("[CONFLICT]", out)
        self.upgrade("-Apply", expect=0)
        ref = (self.project / COMMAND_REF).read_bytes()
        self.assertIn(b"Standard dispatch use:", ref)
        self.assertIn(b"\r\n", ref, "CRLF style must be preserved")
        self.assertTrue(ref.endswith(b"**.\r\n"), "trailing blank must be dropped, CRLF kept")

    def test_from_version_10_explicit_accepted(self):
        self.make_10_project()
        self.upgrade("-FromVersion", "1.0", "-Apply", expect=0)
        self.assertTrue((self.project / ".trellis/trellisforge.json").exists())


class UpgradeFrom11Tests(OverlayTestCase):
    def test_clean_11_receipt_upgrade_applies_and_is_idempotent(self):
        self.make_11_project()
        self.assertEqual(self.read_receipt_version(), "1.1")
        r, out = self.upgrade_bare()
        self.assertIn("1.1 -> ", out)
        self.assertIn("[UPDATE]", out)
        self.assertEqual(self.read_receipt_version(), "1.1", "preflight must not touch the old receipt")
        r, out = self.upgrade_bare("-Apply")
        self.assertEqual(r.returncode, 0, out)
        receipt = self.read_json(".trellis/trellisforge.json")
        self.assertEqual(receipt["trellisforge_version"], TARGET_VERSION)
        self.assertEqual(len(receipt["files"]), 151)
        self.assertEqual(receipt["project_prefix"], PREFIX)
        for entry in receipt["files"]:
            for key in ("canonical_sha256", "baseline_sha256", "installed_sha256"):
                self.assertRegex(entry[key], r"^[0-9a-f]{64}$")
        # newly added OpenCode paths were installed on top of the 1.1 tree
        self.assertEqual(
            norm((self.project / OPENCODE_CHECK_AGENT).read_text(encoding="utf-8")),
            norm(rendered_body("1.2", OPENCODE_CHECK_AGENT)))
        r, out = self.upgrade_bare()
        self.assertIn("already-current", out)
        self.assertEqual(r.returncode, 0, out)

    def test_11_upgrade_preserves_nonoverlapping_customization(self):
        self.make_11_project()
        chk = self.project / CHECK_MD
        text = chk.read_text(encoding="utf-8")
        # the "## Residual risks" tail is unchanged 1.1 -> 1.2; a note beyond
        # every changed hunk must survive the direct merge
        self.assertTrue(text.rstrip().endswith("```"))
        write_text_bytes(chk, text + "\n## Local team notes\n\nKeep me.\n")
        r, out = self.upgrade(expect=0)
        self.assertIn("[USER-MERGED]", out)
        self.assertNotIn("[CONFLICT]", out)
        self.upgrade("-Apply", expect=0)
        final = (self.project / CHECK_MD).read_text(encoding="utf-8")
        self.assertIn("## Local team notes", final)
        self.assertIn("Keep me.", final)
        self.assertIn("fixes only mechanical, small, and determinate in-scope issues", final,
                      "1.2 review-fix-ownership contract must be merged in")

    def test_11_upgrade_conflict_zero_write_keeps_11_receipt(self):
        self.make_11_project()
        chk = self.project / CHECK_MD
        text = chk.read_text(encoding="utf-8")
        # edit the exact line 1.2 rewrites -> overlapping change
        self.assertIn(DESC_ANCHOR, text)
        text = text.replace(DESC_ANCHOR, DESC_ANCHOR + " (team fork)", 1)
        write_text_bytes(chk, text)
        wf_before = (self.project / WORKFLOW_MD).read_bytes()
        r, out = self.upgrade(expect=1)
        self.assertIn("[CONFLICT]", out)
        report_dirs = list((self.project / ".git/trellisforge-upgrade").glob("*"))
        self.assertEqual(len(report_dirs), 1)
        report = json.loads((report_dirs[0] / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["from_version"], "1.1")
        self.assertEqual(report["to_version"], TARGET_VERSION)
        self.assertEqual(self.read_receipt_version(), "1.1", "conflict must leave the 1.1 receipt intact")
        self.assertEqual((self.project / WORKFLOW_MD).read_bytes(), wf_before,
                         "conflict must leave the worktree unchanged")
        self.assertIn("(team fork)", chk.read_text(encoding="utf-8"))

    def test_11_upgrade_multiple_conflicts_are_reported_with_candidate(self):
        self.make_11_project()
        chk = self.project / CHECK_MD
        text = chk.read_text(encoding="utf-8")
        context_anchor = "Before reviewing, read in this order:"
        self.assertIn(DESC_ANCHOR, text)
        self.assertIn(context_anchor, text)
        text = text.replace(DESC_ANCHOR, DESC_ANCHOR + " (team fork)", 1)
        text = text.replace(context_anchor, context_anchor + " (team fork)", 1)
        write_text_bytes(chk, text)

        _, out = self.upgrade(expect=1)
        self.assertIn(f"[CONFLICT] {CHECK_MD}", out)
        self.assertNotIn(f"[UNSUPPORTED] {CHECK_MD}", out)

        report_dirs = list((self.project / ".git/trellisforge-upgrade").glob("*"))
        self.assertEqual(len(report_dirs), 1)
        report = json.loads((report_dirs[0] / "report.json").read_text(encoding="utf-8"))
        entry = next(p for p in report["paths"] if p["path"] == CHECK_MD)
        self.assertEqual(entry["status"], "conflict")
        candidate = report_dirs[0] / entry["candidate"]
        self.assertTrue(candidate.is_file(), "multi-conflict merge must retain its candidate")
        candidate_text = candidate.read_text(encoding="utf-8")
        self.assertGreaterEqual(candidate_text.count("<<<<<<< target"), 2)
        self.assertEqual(self.read_receipt_version(), "1.1")

    def test_11_receipt_upgrade_does_not_touch_state_or_user_files(self):
        self.make_11_project()
        before = self.add_sentinel_state()
        self.upgrade_bare("-Apply")
        self.assert_sentinel_untouched(before)

    def test_11_source_uses_only_later_structural_step(self):
        # Structural composition is observable through the shared module:
        # 1.1 -> 1.2 loads exactly one step, 1.0 -> 1.2 composes two.
        _, out = self.run_ps_driver(
            "Import-Module '%s' -Force\n"
            "$a = Get-OverlayStructuralChain -Overlay 'embedded-c' -FromVersion '1.1' -ToVersion '1.2'\n"
            "$b = Get-OverlayStructuralChain -Overlay 'embedded-c' -FromVersion '1.0' -ToVersion '1.2'\n"
            "Write-Output ('S11=' + $a.Steps.Count + ' A11=' + $a.Actions.Count + ' T11=' + $a.ReceiptTransition)\n"
            "Write-Output ('S10=' + $b.Steps.Count + ' A10=' + $b.Actions.Count + ' T10=' + $b.ReceiptTransition)\n"
            % MODULE)
        self.assertIn("S11=1 A11=0 T11=preserve-schema-1", out)
        self.assertIn("S10=2 A10=0 T10=bootstrap-schema-1 + preserve-schema-1", out)

    def test_11_receipt_with_mismatched_project_name_fails_closed(self):
        self.make_11_project()
        r = run_ps(UPDATER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", "Wrong Name")
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fail closed", out)
        self.assertEqual(self.read_receipt_version(), "1.1")


class StructuralAndSafetyTests(OverlayTestCase):
    def test_structural_chain_files(self):
        for frm, to, transition in (("1.0", "1.1", "bootstrap-schema-1"),
                                    ("1.1", TARGET_VERSION, "preserve-schema-1")):
            chain = json.loads((STRUCTURAL / f"{frm}-to-{to}.json").read_text(encoding="utf-8"))
            self.assertEqual(chain["schema_version"], 1)
            self.assertEqual(chain["from_version"], frm)
            self.assertEqual(chain["to_version"], to)
            self.assertEqual(chain["receipt_transition"], transition)
            self.assertEqual(chain["actions"], [])
        # no direct 1.0-to-1.2 structural snapshot exists
        self.assertFalse((STRUCTURAL / "1.0-to-1.2.json").exists())

    def _synthetic_release(self):
        """Copy the module + history into a temp release root and fabricate
        tampered structural steps so chain rejection is testable without
        mutating real assets."""
        release = self.tmp / "release"
        (release / "tools" / "lib").mkdir(parents=True)
        shutil.copy(MODULE, release / "tools" / "lib" / "TrellisForgeOverlay.psm1")
        shutil.copytree(HISTORY, release / "history" / "embedded-c-overlay")
        steps = release / "migrations" / "embedded-c-overlay" / "structural"
        steps.mkdir(parents=True)
        shutil.copy(STRUCTURAL / "1.0-to-1.1.json", steps / "1.0-to-1.1.json")
        shutil.copy(STRUCTURAL / "1.1-to-1.2.json", steps / "1.1-to-1.2.json")
        return release, steps

    def _chain_driver(self, module_path, cases):
        """Every case must be rejected (throw). A case that succeeds prints
        UNEXPECTED-SUCCESS; a throwing case prints PASS."""
        lines = [f"Import-Module '{module_path}' -Force"]
        for name, frm, to in cases:
            lines.append("try {")
            lines.append(f"  Get-OverlayStructuralChain -Overlay 'embedded-c' -FromVersion '{frm}' -ToVersion '{to}' | Out-Null")
            lines.append(f"  Write-Output ('{name}=UNEXPECTED-SUCCESS')")
            lines.append("} catch {")
            lines.append(f"  Write-Output ('{name}=PASS')")
            lines.append("}")
        driver = self.tmp / "chain_cases.ps1"
        driver.write_text("\n".join(lines), encoding="utf-8-sig")
        return run_ps(driver)

    def test_chain_rejects_broken_step(self):
        release, steps = self._synthetic_release()
        (steps / "1.1-to-1.2.json").unlink()
        r = self._chain_driver(release / "tools" / "lib" / "TrellisForgeOverlay.psm1",
                               [("BROKEN", "1.0", "1.2")])
        out = r.stdout + r.stderr
        self.assertIn("BROKEN=PASS", out, "missing adjacent step must be rejected")

    def test_chain_rejects_illegal_action(self):
        release, steps = self._synthetic_release()
        step = json.loads((steps / "1.1-to-1.2.json").read_text(encoding="utf-8"))
        step["actions"] = [{"action": "nuke", "path": ".trellis/workflow.md"}]
        (steps / "1.1-to-1.2.json").write_text(json.dumps(step), encoding="utf-8")
        r = self._chain_driver(release / "tools" / "lib" / "TrellisForgeOverlay.psm1",
                               [("ACTION", "1.1", "1.2")])
        out = r.stdout + r.stderr
        self.assertIn("ACTION=PASS", out, "unknown structural action must be rejected")

    def test_chain_rejects_illegal_receipt_transition(self):
        release, steps = self._synthetic_release()
        step = json.loads((steps / "1.1-to-1.2.json").read_text(encoding="utf-8"))
        step["receipt_transition"] = "drop-all-receipts"
        (steps / "1.1-to-1.2.json").write_text(json.dumps(step), encoding="utf-8")
        r = self._chain_driver(release / "tools" / "lib" / "TrellisForgeOverlay.psm1",
                               [("TRANS", "1.1", "1.2")])
        out = r.stdout + r.stderr
        self.assertIn("TRANS=PASS", out, "unknown receipt transition must be rejected")

    def test_chain_rejects_version_order_violations(self):
        r = self._chain_driver(MODULE, [
            ("EQUAL", "1.2", "1.2"),
            ("REV", "1.1", "1.0"),
            ("NOSRC", "0.9", "1.2"),
        ])
        out = r.stdout + r.stderr
        self.assertIn("EQUAL=PASS", out)
        self.assertIn("REV=PASS", out)
        self.assertIn("NOSRC=PASS", out)

    def test_object_library_complete_and_consistent(self):
        refs = set()
        for version in ("1.0", "1.1", "1.2"):
            m = load_manifest(version)
            for entry in m["files"]:
                self.assertRegex(entry["canonical_sha256"], r"^[0-9a-f]{64}$")
                obj = OBJECTS / entry["canonical_sha256"]
                self.assertTrue(obj.is_file(), f"missing object {entry['canonical_sha256']}")
                data = read_no_bom(obj)
                self.assertEqual(sha256_of_bytes(norm(data.decode("utf-8")).encode("utf-8")),
                                 entry["canonical_sha256"])
                refs.add(entry["canonical_sha256"])
        for obj in OBJECTS.iterdir():
            if obj.is_file():
                self.assertIn(obj.name, refs, f"orphan object file {obj.name}")

    def test_plan_a_assets_removed(self):
        self.assertFalse((REPO_ROOT / "migrations" / "embedded-c-overlay" / "1.0-to-1.1").exists(),
                         "Plan-A pair-wise migration dir must be gone")

    def test_target_path_is_directory_blocked(self):
        (self.project / ".trellis").mkdir(exist_ok=True)
        (self.project / ".trellis/workflow.md").mkdir()
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", PROJECT_NAME, "-Force")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.project / ".trellis/workflow.md").is_dir())
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_invalid_project_prefix_rejected(self):
        for bad in ("BadPrefix", "..", "a\\b"):
            with self.subTest(prefix=bad):
                self.setUp()
                self.make_10_project()
                r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", bad,
                           "-ProjectName", PROJECT_NAME)
                self.assertNotEqual(r.returncode, 0, f"prefix {bad!r} must fail binding")

    def test_template_cache_rejection(self):
        cache_tree = self.tmp / "fake-template"
        (cache_tree / "__pycache__").mkdir(parents=True)
        (cache_tree / "__pycache__/x.pyc").write_bytes(b"\x00")
        (cache_tree / "ok.md").write_text("ok\n", encoding="utf-8")
        driver = self.tmp / "cache_check.ps1"
        driver.write_text(
            "Import-Module '%s' -Force\n"
            "$files = @(Get-OverlayTemplateCacheFiles -SourceRoot '%s')\n"
            "Write-Output ('COUNT=' + $files.Count)\n"
            "if ($files.Count -ne 1) { exit 1 }" % (MODULE, cache_tree),
            encoding="utf-8-sig",
        )
        r = run_ps(driver)
        combined = r.stdout + r.stderr
        self.assertEqual(r.returncode, 0, combined)
        self.assertIn("COUNT=1", combined)

    def test_write_failure_rolls_back(self):
        self.make_10_project()
        new_skill = self.project / ".agents/skills/trellis-channel/SKILL.md"
        new_skill.unlink()
        target = self.project / ".claude/settings.json"
        original = target.read_bytes()
        os.chmod(target, 0o444)
        self.addCleanup(lambda: os.chmod(target, 0o644) if target.exists() else None)
        workflow = self.project / ".trellis/workflow.md"
        workflow_before = workflow.read_bytes()
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", PROJECT_NAME, "-Force")
        self.assertNotEqual(r.returncode, 0, "write into read-only file must not silently succeed")
        self.assertFalse(new_skill.exists(), "newly created file must be removed on rollback")
        self.assertEqual(target.read_bytes(), original, "failed target unchanged")
        self.assertEqual(workflow.read_bytes(), workflow_before,
                         "file written before the failure must be restored from backup")
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists(),
                         "no receipt may remain after a failed fresh install")
        backup_dir = self.project / ".git/trellisforge-backup"
        self.assertTrue(backup_dir.exists(), "backup dir must exist for diagnosis")
        manifests = list(backup_dir.glob("*/backup-manifest.json"))
        self.assertTrue(manifests, "backup manifest must exist after a failed install")


if __name__ == "__main__":
    unittest.main()
