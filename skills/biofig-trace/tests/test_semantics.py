from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from common import load_json  # noqa: E402
from validate_evidence import semantic_errors  # noqa: E402


def codes(data: dict) -> set[str]:
    return {item["code"] for item in semantic_errors(data)}


class SemanticTests(unittest.TestCase):
    def test_failed_run_cannot_be_published_as_evidence(self) -> None:
        data = self.dose()
        data["run"]["status"] = "failed"
        self.assertIn("RUN_FAILED", codes(data))

    def dose(self) -> dict:
        return load_json(SKILL_ROOT / "examples" / "dose_response.json")

    def test_unavailable_source_cannot_support_visual_evidence(self) -> None:
        data = self.dose()
        data["sources"][0]["availability"] = "unavailable"
        data["sources"][0]["visual_inspection"]["status"] = "not_possible"
        self.assertTrue({"SOURCE_UNAVAILABLE", "VISUAL_ACCESS"} & codes(data))

    def test_evidence_and_coverage_cannot_point_to_validation(self) -> None:
        data = self.dose()
        data["evidence_items"][0]["supports"].append("/validation/schema_passed")
        data["source_coverage"][0]["field_paths"].append("/validation/schema_passed")
        found = codes(data)
        self.assertIn("BAD_FIELD_PATH", found)
        self.assertIn("COVERAGE_PATH", found)

    def test_estimate_requires_positive_tolerance_and_basis(self) -> None:
        data = self.dose()
        potency = data["panels"][0]["results"]["records"][0]["potency"]
        potency["precision"] = "approximate"
        potency["tolerance"] = None
        potency["basis"] = None
        self.assertIn("ESTIMATE_TOLERANCE", codes(data))

    def test_derived_value_recalculation_conflict_is_detected(self) -> None:
        data = self.dose()
        data["panels"][0]["derived_values"] = [{
            "derived_id": "derived-rate",
            "label": "potency per hour",
            "formula": "x0 / x1",
            "inputs": [
                {"field_path": "/panels/0/results/records/0/potency/value", "value": 1.4},
                {"field_path": "/panels/0/conditions/1/value/value", "value": 24.0},
            ],
            "recalculated": 99.0,
            "reported": None,
            "absolute_tolerance": 0.001,
            "relative_tolerance": 0.0,
            "comparison": "not_evaluable",
            "evidence_ids": ["ev-caption", "ev-method"],
            "review_action": None,
        }]
        self.assertIn("DERIVED_RECALCULATION", codes(data))

    def test_mechanism_arrow_must_remain_depicted(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "mechanism.json")
        data["panels"][0]["results"]["records"][0]["evidence_nature"] = "reported"
        self.assertIn("MECHANISM_EVIDENCE", codes(data))

    def test_high_dimensional_scope_cannot_be_silently_truncated(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "omics_volcano.json")
        data["panels"][0]["reporting_scope"] = {"mode": "full", "displayed_count": 1, "total_count": 12000, "selection_rule": None}
        self.assertIn("SILENT_TRUNCATION", codes(data))

    def test_template_and_registry_mismatch_are_rejected(self) -> None:
        data = self.dose()
        data["panels"][0]["classification"]["result_template"] = "group_comparison"
        found = codes(data)
        self.assertIn("CLASSIFICATION_MISMATCH", found)
        self.assertIn("TEMPLATE_MISMATCH", found)

    def test_workflow_self_loop_and_cycle_are_rejected(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "workflow.json")
        records = data["panels"][0]["results"]["records"]
        records[0]["predecessors"] = ["rec-step-2"]
        records[1]["predecessors"] = ["rec-step-1", "rec-step-2"]
        self.assertIn("WORKFLOW_CYCLE", codes(data))

    def test_bbox_must_fit_inside_normalized_page(self) -> None:
        data = self.dose()
        data["panels"][0]["location"]["bbox"].update({"x": 0.7, "width": 0.5})
        self.assertIn("BBOX_BOUNDS", codes(data))

    def test_provisional_classification_requires_alternative_review_and_nonhigh_confidence(self) -> None:
        data = self.dose()
        classification = data["panels"][0]["classification"]
        classification["status"] = "provisional"
        classification["alternatives"] = []
        found = codes(data)
        self.assertTrue({"PROVISIONAL_CONFIDENCE", "PROVISIONAL_ALTERNATIVES", "PROVISIONAL_REVIEW"}.issubset(found))

    def test_inference_requires_premises_rule_limit_and_nonhigh_confidence(self) -> None:
        data = self.dose()
        claim = data["panels"][0]["claims"][0]
        claim["nature"] = "inferred"
        claim["limitation"] = None
        found = codes(data)
        self.assertTrue({"INFERENCE_CONFIDENCE", "INFERENCE_LIMIT", "INFERENCE_PREMISES"}.issubset(found))

    def test_conflicted_value_requires_resolvable_conflict(self) -> None:
        data = self.dose()
        potency = data["panels"][0]["results"]["records"][0]["potency"]
        potency.update({"state": "conflicted", "value": None, "precision": "not_applicable", "conflict_id": None})
        self.assertIn("CONFLICT_STATE", codes(data))


if __name__ == "__main__":
    unittest.main()
