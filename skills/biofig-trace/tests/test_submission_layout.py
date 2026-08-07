from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]


class SubmissionLayoutTests(unittest.TestCase):
    def test_exactly_one_skill_and_root_requirements(self) -> None:
        skill_dirs = [path for path in (REPO_ROOT / "skills").iterdir() if path.is_dir()]
        self.assertEqual(["biofig-trace"], [path.name for path in skill_dirs])
        self.assertTrue((REPO_ROOT / "requirements.txt").is_file())
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())

    def test_frontmatter_has_only_name_and_description(self) -> None:
        lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual("---", lines[0])
        end = lines.index("---", 1)
        pairs = [line.split(":", 1) for line in lines[1:end] if line.strip()]
        metadata = {key.strip(): value.strip() for key, value in pairs}
        self.assertEqual({"name", "description"}, set(metadata))
        self.assertRegex(metadata["name"], r"^[a-z0-9-]{1,64}$")
        self.assertLessEqual(len(metadata["description"]), 1024)
        self.assertIn("BioFig Trace 是", metadata["description"])
        self.assertLess(len(lines), 500)
        self.assertNotIn("TODO", "\n".join(lines))

    def test_package_size_and_file_limits(self) -> None:
        files = [path for path in REPO_ROOT.glob("**/*") if path.is_file() and "__pycache__" not in path.parts]
        self.assertLessEqual(sum(path.stat().st_size for path in files), 50 * 1024 * 1024)
        self.assertTrue(all(path.stat().st_size <= 10 * 1024 * 1024 for path in files))

    def test_no_persistent_runtime_environment_or_second_skill(self) -> None:
        # Importing the package may legitimately create __pycache__ while this
        # suite is running.  The archive builder removes and independently
        # scans interpreter caches immediately before packaging.
        forbidden_parts = {".pytest_cache", ".venv", "tmp", "temp"}
        offenders = [path for path in REPO_ROOT.glob("**/*") if forbidden_parts.intersection(path.parts)]
        self.assertEqual([], offenders)

    def test_openai_metadata_mentions_skill(self) -> None:
        text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$biofig-trace", text)
        self.assertRegex(text, r'display_name:\s+"BioFig Trace"')


if __name__ == "__main__":
    unittest.main()
