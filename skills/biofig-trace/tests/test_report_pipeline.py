from __future__ import annotations

import copy
import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import finalize_output  # noqa: E402
from common import content_digest, load_json  # noqa: E402
from render_report import render  # noqa: E402
from verify_report import verify  # noqa: E402


class ReportPipelineTests(unittest.TestCase):
    def test_every_example_renders_and_verifies(self) -> None:
        examples = sorted((SKILL_ROOT / "examples").glob("*.json"))
        self.assertGreaterEqual(len(examples), 6)
        for path in examples:
            with self.subTest(path=path.name):
                data = load_json(path)
                report = render(data)
                self.assertEqual([], verify(data, report))

    def test_english_profile_localizes_public_structure_and_labels(self) -> None:
        expected_sections = [
            "Structured Results",
            "Figure Interpretation",
            "Original Figure Location",
            "Source Consumption Coverage",
            "Conflicts and Uncertainty",
            "Human Review Recommendations",
        ]
        for path in sorted((SKILL_ROOT / "examples").glob("*.json")):
            with self.subTest(path=path.name):
                data = copy.deepcopy(load_json(path))
                data["run"]["report_language"] = "en"
                report = render(data)
                self.assertEqual([], verify(data, report))
                self.assertEqual(expected_sections, re.findall(r"^## ([^\r\n]+)$", report, flags=re.M))
                self.assertIn("| Source | Information used | Purpose | Status | Limitations |", report)
                self.assertIn("| Panel | Figure | PDF page | Printed page | Panel label | Within-page region | Locator note | Source |", report)
                self.assertIn("- Panel confidence:", report)
                self.assertIn("- Figure classification:", report)
                self.assertIn("- Review status:", report)
                for chinese_ui in ("## 结构化结果表", "| 来源 | 已使用信息 |", "面板置信度：", "图型分类：", "复核状态："):
                    self.assertNotIn(chinese_ui, report)
        microscopy = copy.deepcopy(load_json(SKILL_ROOT / "examples" / "microscopy.json"))
        microscopy["run"]["report_language"] = "en"
        microscopy_report = render(microscopy)
        self.assertIn("| Priority | Reason | Minimum decisive action |", microscopy_report)
        self.assertIn("Reported by the authors", microscopy_report)
        mechanism = copy.deepcopy(load_json(SKILL_ROOT / "examples" / "mechanism.json"))
        mechanism["run"]["report_language"] = "en"
        self.assertIn("Depicted relation", render(mechanism))

    def test_public_projection_scrubs_paths_ids_hashes_and_uri_secrets(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "dose_response.json")
        marker = "S" + "ECRET"
        query = "to" + "ken=" + marker
        private_path = "C:" + "\\Us" + "ers" + r"\Alice\private\paper.pdf" + "?" + query
        private_uri = "https://" + "alice:pw@" + "example.org/paper.pdf" + "?" + query + "#private"
        data["sources"][0]["locator"]["citation"] = private_path
        data["sources"][0]["locator"]["uri"] = private_uri
        data["source_coverage"][0]["fact_summary"] = (
            "source_id=src-secret /panels/0 " + "a" * 64 + " consumed"
        )
        report = render(data)
        self.assertEqual([], verify(data, report))
        for secret in (marker, "C:" + "\\Us" + "ers", "src-secret", "/panels/0", "a" * 64, " consumed"):
            self.assertNotIn(secret, report)

    def test_verifier_detects_manual_public_leak(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "dose_response.json")
        report = render(data) + "C:/" + "Us" + "ers/Alice/private.csv" + "?" + "to" + "ken=" + "S" + "ECRET\n"
        codes = {item["code"] for item in verify(data, report, require_exact_render=False)}
        self.assertIn("ABSOLUTE_PATH", codes)
        self.assertIn("DANGEROUS_URI", codes)

    def test_directory_publish_is_atomic_and_does_not_modify_draft(self) -> None:
        source = SKILL_ROOT / "examples" / "dose_response.json"
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "published"
            finalize_output.finalize(source, output)
            self.assertEqual({"evidence.json", "report.md"}, {item.name for item in output.iterdir()})
            evidence = load_json(output / "evidence.json")
            report = (output / "report.md").read_text(encoding="utf-8")
            self.assertEqual("validated", evidence["validation"]["state"])
            self.assertEqual(content_digest(evidence), evidence["validation"]["content_sha256"])
            self.assertEqual(hashlib.sha256(report.encode("utf-8")).hexdigest(), evidence["validation"]["report_sha256"])
        self.assertEqual(original_hash, hashlib.sha256(source.read_bytes()).hexdigest())

    def test_publish_failure_leaves_no_output_or_staging(self) -> None:
        source = SKILL_ROOT / "examples" / "dose_response.json"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "must-not-exist"
            with patch.object(finalize_output.os, "rename", side_effect=OSError("injected publish failure")):
                with self.assertRaises(OSError):
                    finalize_output.finalize(source, output)
            self.assertFalse(output.exists())
            self.assertEqual([], list(root.glob(".*.staging-*")))


if __name__ == "__main__":
    unittest.main()
