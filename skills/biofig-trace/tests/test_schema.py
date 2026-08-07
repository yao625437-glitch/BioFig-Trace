from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import load_json  # noqa: E402
from schema_engine import validate as fallback_validate  # noqa: E402
from validate_evidence import audit, schema_errors, semantic_errors  # noqa: E402


class SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.example_paths = sorted((SKILL_ROOT / "examples").glob("*.json"))
        self.assertEqual(9, len(self.example_paths))

    def test_all_examples_pass_schema_and_semantics(self) -> None:
        categories: set[str] = set()
        for path in self.example_paths:
            with self.subTest(path=path.name):
                data = load_json(path)
                self.assertEqual([], schema_errors(data))
                self.assertEqual([], semantic_errors(data))
                categories.update(panel["classification"]["function_category"] for panel in data["panels"])
        self.assertEqual(
            {"basic_statistics", "omics_bioinformatics", "clinical_epidemiology", "experimental_image", "workflow_mechanism", "specialized_table"},
            categories,
        )

    def test_missing_required_and_extra_field_fail(self) -> None:
        data = load_json(self.example_paths[0])
        missing = copy.deepcopy(data)
        del missing["activities"]
        self.assertTrue(schema_errors(missing))
        extra = copy.deepcopy(data)
        extra["unexpected"] = True
        self.assertTrue(schema_errors(extra))

    def test_wrong_tagged_union_fails_schema(self) -> None:
        data = load_json(SKILL_ROOT / "examples" / "dose_response.json")
        data["panels"][0]["results"]["records"][0].pop("fit_model")
        self.assertTrue(schema_errors(data))

    def test_report_profile_instance_matches_its_schema(self) -> None:
        schema = load_json(SKILL_ROOT / "schemas" / "report_profile_schema_v3.json")
        instance = load_json(SKILL_ROOT / "schemas" / "report_profile_v3.json")
        self.assertEqual([], fallback_validate(instance, schema))

    def test_strict_loader_rejects_duplicate_keys_and_nonfinite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_json(duplicate)
            nonfinite = Path(directory) / "nonfinite.json"
            nonfinite.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_json(nonfinite)

    def test_registry_uses_orthogonal_compatibility_sets(self) -> None:
        registry = load_json(SKILL_ROOT / "schemas" / "figure_registry_v3.json")
        for figure_type, rule in registry["figure_types"].items():
            with self.subTest(figure_type=figure_type):
                self.assertIn("allowed_categories", rule)
                self.assertIn("allowed_templates", rule)
                self.assertNotIn("category", rule)
                self.assertNotIn("template", rule)


if __name__ == "__main__":
    unittest.main()
