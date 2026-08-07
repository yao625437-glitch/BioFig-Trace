from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from classify_figure import classify  # noqa: E402
from extract_evidence import draft_from_manifest  # noqa: E402
from ingest_sources import build_manifest  # noqa: E402
from normalize_units import normalize  # noqa: E402


class CliAndUnitTests(unittest.TestCase):
    def test_ingest_assigns_stable_hash_based_ids(self) -> None:
        fixture = SKILL_ROOT / "tests" / "fixtures" / "dose_response.txt"
        first = build_manifest([str(fixture)])
        second = build_manifest([str(fixture)])
        self.assertEqual(first["sources"][0]["source_id"], second["sources"][0]["source_id"])
        self.assertEqual("available", first["sources"][0]["availability"])
        self.assertEqual(64, len(first["sources"][0]["sha256"]))

    def test_ingest_preserves_unavailable_path_as_limitation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = build_manifest([str(Path(directory) / "missing.pdf")])
        self.assertEqual("unavailable", manifest["sources"][0]["availability"])
        self.assertIsNone(manifest["sources"][0]["sha256"])

    def test_classification_uses_scientific_specificity(self) -> None:
        dose = classify("4PL concentration response with IC50 and normalized viability")
        self.assertEqual("dose_response", dose["figure_type"])
        survival = classify("Kaplan-Meier survival curve with number at risk and log-rank test")
        self.assertEqual("kaplan_meier", survival["figure_type"])
        enrichment = classify("GO pathway enrichment bar plot with FDR")
        self.assertEqual("enrichment_plot", enrichment["figure_type"])

    def test_ambiguous_description_is_not_silently_resolved(self) -> None:
        result = classify("a colored figure")
        self.assertEqual("unresolved", result["status"])
        self.assertTrue(result["needs_review"])

    def test_draft_is_explicitly_partial_and_unvalidated(self) -> None:
        fixture = SKILL_ROOT / "tests" / "fixtures" / "workflow.txt"
        draft = draft_from_manifest(build_manifest([str(fixture)]))
        self.assertEqual("partial", draft["run"]["status"])
        self.assertEqual([], draft["panels"])
        self.assertEqual("unvalidated", draft["validation"]["state"])
        self.assertIn("activities", draft)

    def test_unit_normalization_is_case_sensitive_and_dimension_safe(self) -> None:
        micro_molar = normalize("µM")
        micro_meter = normalize("µm")
        self.assertEqual("amount_concentration", micro_molar["dimension"])
        self.assertEqual("length", micro_meter["dimension"])
        self.assertNotEqual(micro_molar["scale_to_si"], micro_meter["scale_to_si"])
        self.assertEqual(1000.0, normalize("M")["scale_to_si"])
        self.assertFalse(normalize(None)["recognized"])


if __name__ == "__main__":
    unittest.main()
