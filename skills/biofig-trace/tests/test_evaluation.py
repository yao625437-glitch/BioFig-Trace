from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TEST_DIR / "fixtures"
sys.path.insert(0, str(TEST_DIR))

import evaluate_uplift as scorer


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def make_task(atoms: list[dict]) -> dict:
    return {"task_id": "unit-task", "category": "unit", "atoms": atoms}


def make_run(atoms: list[dict], run_id: str = "unit-run") -> dict:
    return {"run_id": run_id, "status": "completed", "atoms": atoms}


class AtomicScoringTests(unittest.TestCase):
    def test_scientific_key_is_order_independent_and_normalizes_label_text(self) -> None:
        gold = make_task(
            [
                {
                    "key": {"panel": "A", "entity": "Drug X", "endpoint": "IC50"},
                    "value": "reported",
                    "match": {"type": "exact"},
                }
            ]
        )
        prediction = make_run(
            [
                {
                    "key": {"endpoint": "ic50", "entity": "  drug   x ", "panel": "a"},
                    "value": "reported",
                }
            ]
        )
        result = scorer.score_run(gold, prediction)
        self.assertEqual(1, result["matched_atoms"])
        self.assertEqual(1.0, result["score"])

    def test_numeric_match_uses_maximum_of_abs_relative_and_digitization_tolerance(self) -> None:
        gold = make_task(
            [
                {
                    "key": {"attribute": "absolute"},
                    "value": 1.4,
                    "unit": "µM",
                    "match": {"type": "numeric", "abs_tol": 0.05},
                },
                {
                    "key": {"attribute": "relative"},
                    "value": 100.0,
                    "unit": "%",
                    "match": {"type": "numeric", "abs_tol": 0.1, "rel_tol": 0.05},
                },
                {
                    "key": {"attribute": "digitized"},
                    "value": 58.0,
                    "unit": "%",
                    "match": {
                        "type": "numeric",
                        "abs_tol": 0.1,
                        "rel_tol": 0.001,
                        "digitization_tol": 3.0,
                    },
                },
            ]
        )
        prediction = make_run(
            [
                {"key": {"attribute": "absolute"}, "value": 1.44, "unit": "μM"},
                {"key": {"attribute": "relative"}, "value": 104.9, "unit": "%"},
                {"key": {"attribute": "digitized"}, "value": 60.9, "unit": "%"},
            ]
        )
        result = scorer.score_run(gold, prediction)
        self.assertEqual(3, result["matched_atoms"])
        self.assertEqual(1.0, result["score"])

        outside = copy.deepcopy(prediction)
        outside["atoms"][0]["value"] = 1.451
        outside["atoms"][1]["value"] = 105.1
        outside["atoms"][2]["value"] = 61.1
        result = scorer.score_run(gold, outside)
        self.assertEqual(0, result["matched_atoms"])
        self.assertEqual(0.0, result["score"])

    def test_numeric_unit_must_match_after_unicode_normalization(self) -> None:
        gold = make_task(
            [
                {
                    "key": {"endpoint": "IC50"},
                    "value": 1.4,
                    "unit": "µM",
                    "match": {"type": "numeric", "abs_tol": 0.1},
                }
            ]
        )
        wrong_unit = make_run([{"key": {"endpoint": "IC50"}, "value": 1.4, "unit": "mM"}])
        self.assertEqual(0.0, scorer.score_run(gold, wrong_unit)["score"])

    def test_unsupported_fact_and_duplicate_prediction_increase_denominator(self) -> None:
        gold = make_task(
            [{"key": {"attribute": "figure_type"}, "value": "dose_response"}]
        )
        run = make_run(
            [
                {"key": {"attribute": "figure_type"}, "value": "dose_response"},
                {"key": {"attribute": "figure_type"}, "value": "dose_response"},
                {"key": {"attribute": "invented_p_value"}, "value": 0.01},
            ]
        )
        result = scorer.score_run(gold, run)
        self.assertEqual(1, result["matched_atoms"])
        self.assertEqual(2, result["unsupported_extra_atoms"])
        self.assertEqual(1 / 3, result["score"])

    def test_failed_or_timed_out_run_scores_zero(self) -> None:
        gold = make_task([{"key": {"attribute": "x"}, "value": 1}])
        result = scorer.score_run(gold, {"run_id": "failed-run", "status": "timeout"})
        self.assertEqual(0.0, result["score"])
        self.assertEqual(1, len(result["missed_keys"]))


class RepetitionAndUpliftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = load_fixture("scoring_gold.json")
        cls.skill = load_fixture("scoring_skill_runs.json")
        cls.baseline = load_fixture("scoring_baseline_runs.json")

    def test_unit_fixtures_are_explicitly_not_real_performance_results(self) -> None:
        for document in (self.gold, self.skill, self.baseline):
            self.assertEqual("scorer_unit_fixture", document["fixture_kind"])
            notice = document["notice"].casefold()
            self.assertIn("synthetic", notice)
            self.assertRegex(notice, r"not (?:a )?real")

    def test_three_run_medians_and_uplift_are_reproducible(self) -> None:
        result = scorer.evaluate_uplift(self.gold, self.skill, self.baseline)
        task = result["tasks"][0]
        self.assertEqual([1.0, 2 / 3, 5 / 6], [run["score"] for run in task["skill_runs"]])
        self.assertEqual([1 / 3, 3 / 7, 1 / 5], [run["score"] for run in task["baseline_runs"]])
        self.assertAlmostEqual(5 / 6, task["skill_median"])
        self.assertAlmostEqual(1 / 3, task["baseline_median"])
        self.assertAlmostEqual(1 / 2, task["uplift"])
        self.assertAlmostEqual(1 / 2, result["summary"]["macro_uplift"])
        self.assertEqual(3, result["runs_per_task"])

    def test_exactly_three_runs_are_required(self) -> None:
        skill = copy.deepcopy(self.skill)
        skill["tasks"][0]["runs"].pop()
        with self.assertRaises(scorer.ScoringError):
            scorer.evaluate_uplift(self.gold, skill, self.baseline)

    def test_task_sets_must_be_identical(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["tasks"][0]["task_id"] = "different-task"
        with self.assertRaises(scorer.ScoringError):
            scorer.evaluate_uplift(self.gold, self.skill, baseline)

    def test_cli_emits_the_same_reproducible_summary(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(TEST_DIR / "evaluate_uplift.py"),
                "--gold",
                str(FIXTURE_DIR / "scoring_gold.json"),
                "--skill-runs",
                str(FIXTURE_DIR / "scoring_skill_runs.json"),
                "--baseline-runs",
                str(FIXTURE_DIR / "scoring_baseline_runs.json"),
                "--compact",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertAlmostEqual(0.5, result["summary"]["macro_uplift"])


class IndependenceTests(unittest.TestCase):
    def test_scorer_imports_only_standard_library_modules(self) -> None:
        source = (TEST_DIR / "evaluate_uplift.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        allowed = {
            "__future__",
            "argparse",
            "json",
            "math",
            "statistics",
            "sys",
            "unicodedata",
            "pathlib",
            "typing",
        }
        self.assertEqual(set(), imported_roots - allowed)


if __name__ == "__main__":
    unittest.main()
