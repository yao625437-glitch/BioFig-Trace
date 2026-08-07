from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from classify_figure import classify  # noqa: E402
from ingest_sources import build_manifest  # noqa: E402


class RawForwardFixtureTests(unittest.TestCase):
    CASES = {
        "basic_statistics": ("bar_chart", "The inspected panel is a bar chart with two vertical bars."),
        "omics_volcano": ("volcano_plot", "The inspected panel is a volcano plot."),
        "clinical_forest": ("forest_plot", "The inspected panel is a forest plot."),
        "microscopy": ("microscopy", "The inspected panel is confocal microscopy with a scale bar."),
        "workflow": ("workflow", "The inspected panel is a workflow flowchart with a branch."),
        "mechanism": ("mechanism_diagram", "The inspected panel is a mechanism diagram with a schematic arrow."),
        "dose_response": ("dose_response", "The inspected panel is a dose response curve."),
        "western_blot": ("western_blot", "The inspected panel is a western blot with lanes and a loading control."),
        "flow_cytometry": ("flow_cytometry", "The inspected panel is a flow cytometry gating plot."),
    }

    def test_raw_assets_are_ingested_and_classified_without_prefilled_json(self) -> None:
        for stem, (expected_type, visual_description) in self.CASES.items():
            with self.subTest(stem=stem):
                image = FIXTURES / f"{stem}.svg"
                context = FIXTURES / f"{stem}.txt"
                self.assertTrue(image.is_file())
                self.assertTrue(context.is_file())
                manifest = build_manifest([str(image), str(context)])
                self.assertEqual(2, len(manifest["sources"]))
                self.assertTrue(all(item["availability"] == "available" for item in manifest["sources"]))
                self.assertTrue(all(item["sha256"] for item in manifest["sources"]))

                # The classifier accepts a faithful visual description plus
                # raw context; it deliberately does not pretend to be an SVG
                # or pixel vision engine.
                raw_description = visual_description + "\n" + context.read_text(encoding="utf-8")
                classification = classify(raw_description)
                self.assertEqual(expected_type, classification.get("figure_type"))
                self.assertIn(classification["status"], {"resolved", "provisional"})

    def test_specific_scale_bar_phrase_outranks_generic_bar_token(self) -> None:
        result = classify("Representative confocal image with DAPI and a scale bar of 50 µm.")
        self.assertEqual("microscopy", result.get("figure_type"))

    def test_forward_assets_do_not_contain_gold_or_evidence_json(self) -> None:
        for path in FIXTURES.glob("*.svg"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn('"evidence_items"', text)
            self.assertNotIn('"validation"', text)
        for path in FIXTURES.glob("*.txt"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn('"evidence_items"', text)
            self.assertNotIn('"validation"', text)


if __name__ == "__main__":
    unittest.main()
