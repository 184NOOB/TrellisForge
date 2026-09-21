"""Regression test: the template write_json must emit LF-only JSON files.

Root cause: ``os.fdopen(fd, "w", encoding="utf-8")`` without ``newline=""``
translates ``\\n`` to ``\\r\\n`` on Windows, so ``task.json`` picks up CRLF
noise and trips ``git diff --check``. This test never reads or writes a real
repository ``task.json``.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# "from common import io" would return the stdlib io module: common/__init__.py
# binds the name `io` before the submodule attribute is (re)set. Import the
# submodule explicitly instead.
import common.io as tio  # noqa: E402


class WriteJsonLineEndingTests(unittest.TestCase):
    def test_write_json_emits_lf_only(self) -> None:
        payload = {
            "id": "demo-任务",
            "status": "in_progress",
            "nested": {"列表": [1, 2, {"键": "值"}]},
        }
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "task.json"
            self.assertTrue(tio.write_json(target, payload))

            raw = target.read_bytes()
            self.assertIn(b"\n", raw)
            self.assertNotIn(
                b"\r\n",
                raw,
                f"write_json emitted CRLF line endings: {raw[:80]!r}",
            )
            self.assertEqual(json.loads(raw.decode("utf-8")), payload)

            leftovers = sorted(
                p.name for p in Path(tmp).iterdir() if p.name != "task.json"
            )
            self.assertEqual(
                leftovers,
                [],
                f"atomic write left temp files behind: {leftovers}",
            )


if __name__ == "__main__":
    unittest.main()