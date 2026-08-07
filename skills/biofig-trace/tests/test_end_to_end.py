from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import atomic_write_json, load_json  # noqa: E402
from finalize_output import FinalizationError, finalize  # noqa: E402


class EndToEndTests(unittest.TestCase):
    def test_every_independent_example_publishes_and_validates_from_random_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            for source in sorted((SKILL_ROOT / "examples").glob("*.json")):
                with self.subTest(source=source.name):
                    output = temp_root / source.stem
                    finalize(source, output)
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            "-X",
                            "utf8",
                            str(SCRIPTS / "validate_evidence.py"),
                            str(output / "evidence.json"),
                            "--require-validated",
                            "--json",
                        ],
                        cwd=temp_root,
                        env={"PYTHONPATH": ""},
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=20,
                    )
                    self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                    self.assertEqual("validated", load_json(output / "evidence.json")["validation"]["state"])
                    self.assertTrue((output / "report.md").read_text(encoding="utf-8").strip())

    def test_schema_and_semantic_failures_never_publish_output(self) -> None:
        source = load_json(SKILL_ROOT / "examples" / "dose_response.json")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cases = []

            bad_schema = copy.deepcopy(source)
            del bad_schema["schema_version"]
            cases.append(("bad-schema", bad_schema, "schema"))

            bad_semantic = copy.deepcopy(source)
            bad_semantic["run"]["status"] = "failed"
            cases.append(("bad-semantic", bad_semantic, "semantic"))

            for name, payload, expected_phase in cases:
                with self.subTest(name=name):
                    draft = root / f"{name}.json"
                    output = root / f"{name}-out"
                    atomic_write_json(draft, payload)
                    with self.assertRaises(FinalizationError) as raised:
                        finalize(draft, output)
                    self.assertEqual(expected_phase, raised.exception.phase)
                    self.assertFalse(output.exists())
                    self.assertEqual([], list(root.glob(f".{output.name}.staging-*")))

    def test_duplicate_key_input_fails_cleanly_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "duplicate.json"
            bad.write_text('{"schema_version":"3.0.0","schema_version":"3.0.0"}', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", "-X", "utf8", str(SCRIPTS / "validate_evidence.py"), str(bad), "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertIn('"passed": false', completed.stdout)
            self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
