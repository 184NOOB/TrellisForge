# -*- coding: utf-8 -*-
"""Automated tests for the TrellisForge overlay installer and 1.0->1.1 updater.

These tests build isolated temporary Git repositories from the versioned
1.0 migration baseline plus the current 1.1 template, then drive the Windows
PowerShell 5.1 entry scripts. They do not depend on a real downstream project,
the `trellis` CLI, or the network.
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
MIGRATION = REPO_ROOT / "migrations" / "embedded-c-overlay" / "1.0-to-1.1"
BASELINE = MIGRATION / "baseline"
INSTALLER = TOOLS / "install-embedded-c-overlay.ps1"
UPDATER = TOOLS / "update-embedded-c-overlay.ps1"
MODULE = TOOLS / "lib" / "TrellisForgeOverlay.psm1"

MERGE_PATHS = [
    ".trellis/workflow.md",
    ".trellis/agents/check.md",
    ".trellis/agents/implement.md",
]
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
ADD_PATHS = [".trellis/scripts/tests/test_trellis_channel_contract.py"]
CHANGED_PATHS = set(MERGE_PATHS) | set(ADOPT_PATHS) | set(ADD_PATHS)
EXCLUDED_NAMES = {"AGENTS.md.template", "TEMPLATE-CONTENTS.md"}
COMMAND_REF = ".agents/skills/trellis-channel/references/command-reference.md"

PREFIX = "example"
PROJECT_NAME = "Example Firmware"


def ps_exe():
    """Best-effort location of Windows PowerShell 5.1."""
    for candidate in (
        os.environ.get("POWERSHELL_EXE"),
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        shutil.which("powershell.exe"),
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return "powershell.exe"


def run_ps(script, *args):
    """Run a PowerShell script file; returns CompletedProcess-like object."""
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


def render_path(rel: str, prefix: str) -> str:
    return rel.replace("__PROJECT_PREFIX__", prefix)


def render_content(text: str, prefix: str, name: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("PROJECT_PREFIX", prefix).replace("PROJECT_NAME", name)


def sha256_of(text: str) -> str:
    data = text.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def write_text_bytes(path: Path, text: str) -> None:
    """Byte-exact UTF-8 write. Path.write_text would translate \\n -> CRLF on
    Windows and corrupt LF fixtures; we must keep the 1.0 layout's newlines."""
    path.write_bytes(text.encode("utf-8"))


def build_10_target(root: Path, prefix=PREFIX, name=PROJECT_NAME):
    """Reconstruct a TrellisForge 1.0 downstream layout.

    Uses the fact that only the 16 migration paths differ between 1.0 and 1.1:
    the rest of the 1.1 template is byte-identical to 1.0. Migration paths are
    then replaced with their historical 1.0 baseline (rendered), and the 1.1
    `add` file is removed again. All content is written byte-exact (LF);
    tests that need a CRLF target convert explicitly afterwards.
    """
    for src in TEMPLATE.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATE).as_posix()
        if rel.split("/")[-1] in EXCLUDED_NAMES or rel in CHANGED_PATHS:
            continue
        dest = root / render_path(rel, prefix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8-sig")
        write_text_bytes(dest, render_content(text, prefix, name))
    for rel in MERGE_PATHS + ADOPT_PATHS:
        text = (BASELINE / rel).read_text(encoding="utf-8-sig")
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_text_bytes(dest, render_content(text, prefix, name))
    for rel in ADD_PATHS:
        dest = root / rel
        if dest.exists():
            dest.unlink()


class OverlayTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trellisforge-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def make_10_project(self, **kw):
        build_10_target(self.project, **kw)
        return self.project

    def install(self, *extra, expect=0, **kwargs):
        params = ["-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME]
        params += list(extra)
        if kwargs.get("expect_success") is True:
            expect = 0
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

    def read_json(self, rel):
        p = self.project / rel
        self.assertTrue(p.exists(), f"missing {rel}")
        return json.loads(p.read_text(encoding="utf-8"))

    def add_sentinel_state(self):
        """Create upstream Trellis state and unrelated dirty/business files."""
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


class InstallTests(OverlayTestCase):
    def test_fresh_install_full_11_writes_receipt(self):
        self.make_10_project()
        r, out = self.install("-Force", expect=0)
        # full overlay installed
        self.assertTrue((self.project / ".trellis/workflow.md").exists())
        self.assertTrue((self.project / ".agents/skills/trellis-channel/SKILL.md").exists())
        self.assertTrue((self.project / ".claude/skills/trellis-channel/SKILL.md").exists())
        receipt = self.read_json(".trellis/trellisforge.json")
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["trellisforge_version"], "1.1")
        self.assertEqual(receipt["overlay"], "embedded-c")
        self.assertEqual(receipt["project_prefix"], PREFIX)
        self.assertEqual(receipt["project_name"], PROJECT_NAME)
        self.assertGreater(len(receipt["files"]), 80)
        for entry in receipt["files"]:
            self.assertTrue(entry["path"].startswith((".", "AGENTS.md.trellisforge")))
            self.assertRegex(entry["template_sha256"], r"^[0-9a-f]{64}$")

    def test_blank_target_install_without_force(self):
        # a blank .trellis/ target has no conflicts, so install succeeds
        # without -Force and still writes the receipt
        (self.project / ".trellis").mkdir(exist_ok=True)
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX, "-ProjectName", PROJECT_NAME)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.project / ".trellis/trellisforge.json").exists())

    def test_force_backup_and_placeholder_replacement(self):
        self.make_10_project()
        r, out = self.install("-Force", expect=0)
        backups = list((self.project / ".git/trellisforge-backup").glob("*"))
        self.assertTrue(backups, "no backup dir created")
        manifest = json.loads((backups[0] / "backup-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertGreater(len(manifest["files"]), 0)
        # placeholders replaced everywhere
        residue = []
        for p in (self.project / ".agents").rglob("*"):
            if p.is_file() and p.suffix in {".md", ".yaml"}:
                text = p.read_text(encoding="utf-8", errors="replace")
                if "__PROJECT_PREFIX__" in text or "PROJECT_PREFIX" in text or "PROJECT_NAME" in text:
                    residue.append(str(p.relative_to(self.project)))
        for rel in [".trellis/workflow.md", ".trellis/config.yaml"]:
            text = (self.project / rel).read_text(encoding="utf-8", errors="replace")
            if "PROJECT_PREFIX" in text or "PROJECT_NAME" in text:
                residue.append(rel)
        self.assertEqual(residue, [])

    def test_conflict_preview_blocks_without_force(self):
        self.make_10_project()
        self.install("-Force", expect=0)
        # second install without -Force must fail (preview)
        r, out = self.install(expect=1)
        self.assertIn("-Force", out)
        # and must not corrupt the working tree
        self.assertTrue((self.project / ".trellis/workflow.md").exists())

    def test_install_does_not_touch_trellis_state_or_user_files(self):
        self.make_10_project()
        before = self.add_sentinel_state()
        self.install("-Force", expect=0)
        self.assert_sentinel_untouched(before)

    def test_incompatible_receipt_blocks_install(self):
        self.make_10_project()
        (self.project / ".trellis").mkdir(exist_ok=True)
        (self.project / ".trellis/trellisforge.json").write_text(
            json.dumps({"schema_version": 1, "trellisforge_version": "0.9",
                        "overlay": "different", "project_prefix": "other",
                        "project_name": "x", "files": []}),
            encoding="utf-8",
        )
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", PROJECT_NAME, "-Force")
        self.assertNotEqual(r.returncode, 0)
        receipt_path = self.project / ".trellis/trellisforge.json"
        self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8"))["project_prefix"], "other",
                         "incompatible receipt must remain untouched")
        self.assertNotIn("Channel Termination Contract",
                         (self.project / ".trellis/agents/implement.md").read_text(encoding="utf-8"),
                         "install over an incompatible receipt must be blocked before writes")


class UpgradeTests(OverlayTestCase):
    def test_clean_10_upgrade_applies_and_is_idempotent(self):
        self.make_10_project()
        r, out = self.upgrade(expect=0)
        self.assertIn("[UPDATE]", out)
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists(),
                         "preflight must not write")
        r, out = self.upgrade("-Apply", expect=0)
        receipt = self.read_json(".trellis/trellisforge.json")
        self.assertEqual(receipt["trellisforge_version"], "1.1")
        self.assertEqual(len(receipt["files"]), 16)
        # A clean upgrade does no placeholders replacement vs. template, so
        # template_sha256 must equal installed_sha256 for every managed file.
        for entry in receipt["files"]:
            self.assertEqual(
                entry["template_sha256"], entry["installed_sha256"],
                f"clean upgrade must not report customization for {entry['path']}",
            )
        # second run is already-current and never rewrites
        r, out = self.upgrade(expect=0)
        self.assertIn("already-current", out)

    def test_clean_10_command_reference_gets_rules_and_drops_blank(self):
        self.make_10_project()
        for rel in (
            ".agents/skills/trellis-channel/references/command-reference.md",
            ".claude/skills/trellis-channel/references/command-reference.md",
        ):
            text = (self.project / rel).read_text(encoding="utf-8")
            self.assertTrue(text.endswith("**.\n\n"), f"fixture must keep 1.0 blank tail: {rel}")
        self.upgrade("-Apply", expect=0)
        for rel in (
            ".agents/skills/trellis-channel/references/command-reference.md",
            ".claude/skills/trellis-channel/references/command-reference.md",
        ):
            text = (self.project / rel).read_text(encoding="utf-8")
            self.assertIn("Standard dispatch use:", text, rel)
            self.assertTrue(text.endswith("**.\n"), f"{rel} must drop the extra blank line")
        # mirrors still identical to each other
        a = (self.project / ".agents/skills/trellis-channel/references/command-reference.md").read_bytes()
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
        r, out = self.upgrade("-Apply", expect=0)
        text = (self.project / COMMAND_REF).read_text(encoding="utf-8")
        self.assertIn("(team note)", text)
        self.assertIn("Standard dispatch use:", text)

    def test_user_edit_overlapping_change_region_conflicts_zero_write(self):
        self.make_10_project()
        chk = self.project / ".trellis/agents/check.md"
        text = chk.read_text(encoding="utf-8")
        text = text.replace("## Workflow\n", "## Workflow (team)\n", 1)
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
        self.assertEqual(report["to_version"], "1.1")
        self.assertIn(".trellis/agents/check.md", [p["path"] for p in report["paths"]])
        candidate = report_dir / "candidates/.trellis/agents/check.md"
        self.assertTrue(candidate.exists(), "conflict candidate missing")
        self.assertIn("<<<<<<<", candidate.read_text(encoding="utf-8"))
        # worktree untouched
        self.assertIn("(team)", chk.read_text(encoding="utf-8"))
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())
        self.assertNotIn("Channel Termination Contract",
                         (self.project / ".trellis/agents/implement.md").read_text(encoding="utf-8"))

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

    def test_missing_project_params_without_receipt(self):
        self.make_10_project()
        r = run_ps(UPDATER, "-TargetRoot", str(self.project))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ProjectPrefix", r.stdout + r.stderr)
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists())

    def test_receipt_param_conflict_fails_closed(self):
        self.make_10_project()
        self.upgrade("-Apply", expect=0)
        r = run_ps(UPDATER, "-TargetRoot", str(self.project),
                   "-ProjectPrefix", "different", "-ProjectName", PROJECT_NAME)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fail closed", r.stdout + r.stderr)

    def test_upgrade_does_not_touch_state_or_user_files(self):
        self.make_10_project()
        before = self.add_sentinel_state()
        self.upgrade("-Apply", expect=0)
        self.assert_sentinel_untouched(before)

    def test_lf_target_clean(self):
        self.make_10_project()
        self.upgrade(expect=0)
        self.upgrade("-Apply", expect=0)
        ref = (self.project / COMMAND_REF).read_bytes()
        self.assertIn(b"Standard dispatch use:", ref)
        self.assertNotIn(b"\r\n", ref, "LF style must be preserved")

    def test_crlf_target_clean(self):
        self.make_10_project()
        for rel in (COMMAND_REF, ".trellis/workflow.md", ".trellis/agents/check.md"):
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


class SafetyAndRollbackTests(OverlayTestCase):
    def test_target_path_is_directory_blocked(self):
        # .trellis/workflow.md as a directory blocks the install write
        (self.project / ".trellis").mkdir(exist_ok=True)
        (self.project / ".trellis/workflow.md").mkdir()
        r = run_ps(INSTALLER, "-TargetRoot", str(self.project), "-ProjectPrefix", PREFIX,
                   "-ProjectName", PROJECT_NAME, "-Force")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.project / ".trellis/workflow.md").is_dir(),
                        "directory conflict must abort before any write")
        self.assertFalse((self.project / ".trellis/trellisforge.json").exists(),
                         "no receipt may be written after a directory-conflict abort")

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
        # nested reads: .agents subdir is written before the failing .claude file
        new_skill = self.project / ".agents/skills/trellis-channel/SKILL.md"
        new_skill.unlink()  # make this file "new" during install
        target = self.project / ".claude/settings.json"
        original = target.read_bytes()
        os.chmod(target, 0o444)  # read-only on Windows blocks File.WriteAllText
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