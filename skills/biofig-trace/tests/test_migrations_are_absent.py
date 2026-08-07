from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]


class IndependenceTests(unittest.TestCase):
    def test_no_legacy_runtime_or_contract_files(self) -> None:
        forbidden_names = ["migr" + "ate", "legacy", "output_schema_" + "v2"]
        runtime_files = list((SKILL_ROOT / "scripts").glob("*")) + list((SKILL_ROOT / "schemas").glob("*"))
        for path in runtime_files:
            lowered = path.name.casefold()
            self.assertFalse(any(token in lowered for token in forbidden_names), path)

    def test_runtime_does_not_reference_external_project_paths(self) -> None:
        forbidden = ["G:" + os.sep, "biofig-" + "evidence", "schema_version" + "\": \"2"]
        for folder in ("scripts", "schemas", "examples", "references"):
            for path in (SKILL_ROOT / folder).glob("**/*"):
                if path.is_file() and path.suffix in {".py", ".json", ".md"}:
                    text = path.read_text(encoding="utf-8")
                    self.assertFalse(any(token in text for token in forbidden), path)

    def test_validator_runs_from_random_cwd_with_empty_pythonpath(self) -> None:
        script = SKILL_ROOT / "scripts" / "validate_evidence.py"
        example = SKILL_ROOT / "examples" / "dose_response.json"
        env = dict(os.environ)
        env["PYTHONPATH"] = ""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-X", "utf8", str(script), str(example)], cwd=directory, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
