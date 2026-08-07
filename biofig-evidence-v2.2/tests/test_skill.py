from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from figure_registry import load_registry
from migrate_v20_to_v21 import migrate as migrate_v20_to_v21
from migrate_v21_to_v22 import migrate as migrate_v21_to_v22
from normalize_units import normalize
from render_report import render
from report_labels import COVERAGE_STATUS, REVIEW_CODE
from semantic_check import audit
from validate_output import audit as schema_audit
from verify_report import COVERAGE_HEADER, verify


EXAMPLES = (
    "quantitative_dual_axis.json",
    "omics_volcano.json",
    "clinical_forest.json",
    "microscopy_review.json",
    "process_workflow.json",
    "specialized_dose_response.json",
)


def example(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def report_section(report: str, start: str, end: str) -> str:
    return report.split(start, 1)[1].split(end, 1)[0]


def to_v21(data: dict) -> dict:
    legacy = copy.deepcopy(data)
    legacy["schema_version"] = "2.1"
    for panel in legacy["panels"]:
        for key in ("figure_category", "result_profile", "reporting_scope", "relationships", "academic_summary"):
            panel.pop(key, None)
        for measurement in panel["measurements"]:
            for point in measurement["points"]:
                point["x"].pop("category", None)
                point["y"].pop("category", None)
        for step in panel["process_steps"]:
            step.pop("input", None)
            step.pop("output", None)
    return legacy


def to_v20(data: dict) -> dict:
    legacy = to_v21(data)
    legacy["schema_version"] = "2.0"
    legacy.pop("source_coverage", None)
    for panel in legacy["panels"]:
        for measurement in panel["measurements"]:
            method = measurement.pop("extraction_method")
            if method == "image_estimate":
                measurement["origin"] = "image_estimate"
    return legacy


class ContractTests(unittest.TestCase):
    def test_all_six_category_examples_pass_schema_and_semantics(self) -> None:
        categories = set()
        for name in EXAMPLES:
            with self.subTest(name=name):
                data = example(name)
                self.assertEqual([], schema_audit(data)[0])
                self.assertEqual([], audit(data))
                categories.update(panel["figure_category"] for panel in data["panels"])
        self.assertEqual(set(load_registry()["categories"]), categories)

    def test_registry_maps_every_type_to_known_category_and_profile(self) -> None:
        registry = load_registry()
        self.assertEqual(6, len(registry["categories"]))
        for panel_type, rule in registry["panel_types"].items():
            with self.subTest(panel_type=panel_type):
                self.assertIn(rule["category"], registry["categories"])
                self.assertIn(rule["profile"], registry["profiles"])
                self.assertTrue(rule["label_zh"])

    def test_schema_and_label_registries_are_complete(self) -> None:
        schema = json.loads((ROOT / "schemas" / "output_schema.json").read_text(encoding="utf-8"))
        panel = schema["$defs"]["panel"]["properties"]
        self.assertEqual(set(load_registry()["categories"]), set(panel["figure_category"]["enum"]))
        self.assertEqual(set(load_registry()["profiles"]), set(panel["result_profile"]["enum"]))
        review_codes = set(schema["$defs"]["reviewReason"]["properties"]["code"]["enum"])
        self.assertEqual(review_codes, set(REVIEW_CODE))
        statuses = set(schema["$defs"]["sourceCoverage"]["properties"]["status"]["enum"])
        self.assertTrue(statuses.issubset(COVERAGE_STATUS))

    def test_rejects_missing_nested_required_field(self) -> None:
        data = example("quantitative_dual_axis.json")
        del data["document"]["title"]
        errors, _ = schema_audit(data)
        self.assertTrue(any("document.title" in error for error in errors))

    def test_rejects_extra_root_field(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["unexpected"] = 1
        errors, _ = schema_audit(data)
        self.assertTrue(any("unexpected" in error for error in errors))

    def test_rejects_invalid_claim_enum(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["panels"][0]["claims"][0]["claim_type"] = "chat_summary"
        errors, _ = schema_audit(data)
        self.assertTrue(any("claim_type" in error for error in errors))

    def test_registry_prevents_category_or_profile_drift(self) -> None:
        data = example("omics_volcano.json")
        data["panels"][0]["figure_category"] = "basic_statistics"
        data["panels"][0]["result_profile"] = "group_comparison"
        errors = audit(data)
        self.assertTrue(any("figure_category" in error for error in errors))
        self.assertTrue(any("result_profile" in error for error in errors))

    def test_reporting_scope_matches_actual_records(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["panels"][0]["reporting_scope"]["displayed_count"] = 2
        self.assertTrue(any("displayed_count" in error for error in audit(data)))

    def test_categorical_coordinate_is_exact_without_fake_number(self) -> None:
        data = example("clinical_forest.json")
        self.assertEqual([], audit(data))
        point = data["panels"][0]["measurements"][0]["points"][0]
        self.assertIsNone(point["x"]["numeric"])
        self.assertEqual("高风险组 vs 低风险组", point["x"]["category"])

    def test_approximate_point_requires_numeric_tolerance(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["panels"][0]["measurements"][0]["points"][0]["y"]["tolerance"] = None
        self.assertTrue(any("tolerance" in error for error in audit(data)))

    def test_direct_measurement_cannot_hide_approximate_points(self) -> None:
        data = example("quantitative_dual_axis.json")
        measurement = data["panels"][0]["measurements"][0]
        measurement["origin"] = "direct_measurement"
        measurement["extraction_method"] = "direct_report"
        self.assertTrue(any("direct_measurement" in error for error in audit(data)))

    def test_extraction_method_cannot_claim_image_estimate_as_direct(self) -> None:
        data = example("quantitative_dual_axis.json")
        measurement = data["panels"][0]["measurements"][0]
        measurement["origin"] = "direct_measurement"
        measurement["extraction_method"] = "image_estimate"
        self.assertTrue(any("image_estimate cannot be paired" in error for error in audit(data)))

    def test_calculated_error_bars_require_propagation_audit(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["panels"][0]["measurements"][0]["origin"] = "calculated"
        data["panels"][0]["measurements"][0]["extraction_method"] = "calculated_from_evidence"
        self.assertTrue(any("error_propagation" in error for error in audit(data)))

    def test_calculation_conflict_cannot_be_silenced(self) -> None:
        data = example("quantitative_dual_axis.json")
        derived = data["panels"][0]["measurements"][1]["derived_values"][0]
        derived["reported"] = 20.0
        derived["comparison_status"] = "conflict"
        derived["relative_difference"] = 0.44
        self.assertTrue(any("top-level conflict" in error for error in audit(data)))

    def test_conflicting_derived_value_requires_rounding_interval_audit(self) -> None:
        data = example("quantitative_dual_axis.json")
        derived = data["panels"][0]["measurements"][1]["derived_values"][0]
        derived["reported"] = 30.0
        derived["comparison_status"] = "conflict"
        derived["relative_difference"] = abs(derived["calculated"] - 30.0) / 30.0
        self.assertTrue(any("rounding_interval_check" in error for error in audit(data)))

    def test_rounding_interval_bounds_are_recomputed(self) -> None:
        data = example("quantitative_dual_axis.json")
        derived = data["panels"][0]["measurements"][1]["derived_values"][0]
        derived.update({"reported": 30.0, "comparison_status": "conflict", "relative_difference": abs(derived["calculated"] - 30.0) / 30.0})
        derived["rounding_interval_check"] = {
            "status": "evaluated", "precision": 1,
            "input_intervals": [
                {"symbol": "axial", "lower": 1.75, "upper": 1.85, "evidence_ids": ["img"]},
                {"symbol": "radial", "lower": 3.95, "upper": 4.05, "evidence_ids": ["img"]},
            ],
            "calculated_interval": {"lower": 27.304375, "upper": 30.344625},
            "reported_inside_interval": True,
            "notes": "The reported value falls inside the explicit one-decimal rounding interval.",
            "evidence_ids": ["img"],
        }
        self.assertFalse(any("calculated_interval" in error for error in audit(data)))

    def test_replicate_type_requires_explicit_evidence(self) -> None:
        data = example("quantitative_dual_axis.json")
        sample = data["panels"][0]["statistics"]["sample_sizes"][0]
        sample["replicate_type"] = "technical"
        sample["raw"] = "three times measured"
        self.assertTrue(any("replicate_type" in error for error in audit(data)))

    def test_source_coverage_requires_methods_or_results_decision(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["sources"].append({
            "id": "methods", "type": "methods", "content_status": "present",
            "locator": {"file": "synthetic.pdf", "page": 3, "panel": None, "paragraph": "methods", "bbox": None},
            "quote": "The actuator has a diameter of 10 mm.",
        })
        self.assertTrue(any("requires a consumed/not-consumed coverage record" in error for error in audit(data)))

    def test_source_coverage_path_must_fully_resolve(self) -> None:
        data = example("quantitative_dual_axis.json")
        data["source_coverage"][0]["field_paths"] = ["$.panels[999].banana"]
        self.assertTrue(any("must resolve" in error for error in audit(data)))

    def test_workflow_requires_steps_and_forbids_error_bars(self) -> None:
        data = example("process_workflow.json")
        data["panels"][0]["process_steps"] = []
        data["panels"][0]["reporting_scope"].update({"displayed_count": 0, "total_count": 0})
        self.assertTrue(any("workflow profile requires" in error for error in audit(data)))
        data = example("process_workflow.json")
        data["panels"][0]["statistics"]["error_bar"]["kind"] = "sd"
        self.assertTrue(any("cannot declare variance" in error for error in audit(data)))

    def test_mechanism_profile_requires_explicit_relationship(self) -> None:
        data = example("process_workflow.json")
        panel = data["panels"][0]
        panel["panel_type"] = "mechanism_diagram"
        panel["result_profile"] = "mechanism_relationship"
        self.assertTrue(any("explicit relationship" in error for error in audit(data)))


class MigrationTests(unittest.TestCase):
    def test_v20_to_v21_separates_origin_and_extraction_method(self) -> None:
        migrated = migrate_v20_to_v21(to_v20(example("quantitative_dual_axis.json")))
        self.assertEqual("2.1", migrated["schema_version"])
        self.assertEqual("unknown", migrated["panels"][0]["measurements"][0]["origin"])
        self.assertEqual("image_estimate", migrated["panels"][0]["measurements"][0]["extraction_method"])
        self.assertIn("source_coverage", migrated)

    def test_v21_to_v22_adds_classification_scope_and_public_fields(self) -> None:
        legacy = to_v21(example("process_workflow.json"))
        migrated = migrate_v21_to_v22(legacy)
        panel = migrated["panels"][0]
        self.assertEqual("2.2", migrated["schema_version"])
        self.assertEqual("mechanism_workflow_schematic", panel["figure_category"])
        self.assertEqual("workflow_flow", panel["result_profile"])
        self.assertIn("academic_summary", panel)
        self.assertIn("reporting_scope", panel)
        self.assertIn("input", panel["process_steps"][0])
        self.assertEqual([], schema_audit(migrated)[0])
        self.assertEqual([], audit(migrated))

    def test_legacy_v21_still_validates_and_renders_through_adapter(self) -> None:
        legacy = to_v21(example("quantitative_dual_axis.json"))
        self.assertEqual([], schema_audit(legacy)[0])
        self.assertEqual([], audit(legacy))
        report = render(legacy)
        self.assertIn("## 结构化结果表", report)
        self.assertNotIn("$.panels", report)


class ReportTests(unittest.TestCase):
    def test_report_has_required_human_layers(self) -> None:
        report = render(example("quantitative_dual_axis.json"))
        for heading in ("结构化结果表", "图表解释", "原图定位", "来源消费覆盖", "冲突与不确定性", "人工复核建议"):
            self.assertIn(heading, report)

    def test_source_coverage_has_exact_public_columns_and_no_paths(self) -> None:
        data = example("quantitative_dual_axis.json")
        report = render(data)
        coverage = report_section(report, "## 来源消费覆盖", "## 冲突与不确定性")
        self.assertIn(COVERAGE_HEADER, coverage)
        self.assertNotIn("$.", coverage)
        self.assertNotIn("field_paths", coverage)
        self.assertNotIn("cov_cap_n", coverage)
        self.assertNotIn("consumed", coverage)

    def test_all_four_source_statuses_are_localized(self) -> None:
        data = example("quantitative_dual_axis.json")
        base = data["source_coverage"][0]
        data["source_coverage"] = [
            {**base, "id": "c1", "status": "consumed", "reason": "无"},
            {**base, "id": "c2", "status": "partially_consumed", "reason": "仍缺少误差条幅度"},
            {**base, "id": "c3", "status": "not_consumed", "field_paths": [], "reason": "与当前终点无关"},
            {**base, "id": "c4", "status": "unavailable", "field_paths": [], "reason": "补充文件不可读"},
        ]
        report = render(data)
        for label in ("已使用", "部分使用", "未使用", "不可用"):
            self.assertIn(label, report)

    def test_workflow_uses_specific_columns_and_preserves_parameters(self) -> None:
        report = render(example("process_workflow.json"))
        results = report_section(report, "## 结构化结果表", "## 图表解释")
        self.assertIn("| 步骤 | 输入 | 操作 | 关键参数 | 输出 | 前置/分支 |", results)
        self.assertIn("温度：25 °C", results)
        self.assertIn("步骤 1：Prepare sample", results)
        for token in ("| 误差 |", "| 不确定性 |", "| P 值 |", "| 变量 X |", "| 变量 Y |"):
            self.assertNotIn(token, results)

    def test_microscopy_uses_image_columns_and_human_review(self) -> None:
        data = example("microscopy_review.json")
        report = render(data)
        results = report_section(report, "## 结构化结果表", "## 图表解释")
        self.assertIn("图像所见", results)
        self.assertNotIn("变量 X", results)
        reason = data["panels"][0]["review_reasons"][0]
        self.assertIn(reason["detail"], report)
        self.assertIn(reason["suggested_action"], report)
        self.assertNotIn(reason["code"], report)
        self.assertNotIn(reason["field_path"], report)

    def test_dose_response_has_pharmacology_columns(self) -> None:
        report = render(example("specialized_dose_response.json"))
        self.assertIn("| 药物/刺激 | 实验系统 | 剂量/范围 | 响应指标 | 响应/药效参数 |", report)
        self.assertIn("IC50", report)
        self.assertIn("1.4 µM", report)
        self.assertIn("四参数 Logistic", report)
        self.assertIn("暴露时间：72 h", report)
        self.assertNotIn("exposure=", report)
        self.assertNotIn("fit model=", report)

    def test_omics_feature_table_is_self_contained(self) -> None:
        report = render(example("omics_volcano.json"))
        self.assertIn("| 特征/位点 | 方向/系列 | 比较 | 效应量/横轴 | 显著性/纵轴 | 判定阈值 |", report)
        self.assertIn("TP53", report)
        self.assertIn("log₂FC：1.8", report)
        self.assertIn("FDR = 0.0001", report)
        self.assertIn("FDR 阈值：0.05", report)
        self.assertIn("\\|log₂FC\\| 阈值：1", report)

    def test_clinical_effect_keeps_estimate_ci_and_p_separate(self) -> None:
        report = render(example("clinical_forest.json"))
        self.assertIn("| 变量/比较 | 效应量 | 点估计 | 95% CI | P 值/调整模型 |", report)
        self.assertIn("1.85 ratio", report)
        self.assertIn("置信区间 [1.2, 2.85]", report)
        self.assertIn("P=0.006", report)
        self.assertNotIn("高风险组 vs 低风险组；高风险组 vs 低风险组", report)

    def test_derived_value_uses_academic_labels_not_code_fragments(self) -> None:
        report = render(example("quantitative_dual_axis.json"))
        self.assertIn("作者报告值", report)
        self.assertIn("复算值", report)
        self.assertIn("一致性结论", report)
        for token in ("reported=", "calculated=", "consistent", "tolerance="):
            self.assertNotIn(token, report)

    def test_report_does_not_duplicate_unit_already_in_raw_value(self) -> None:
        data = example("quantitative_dual_axis.json")
        value = data["panels"][0]["measurements"][0]["points"][0]["y"]
        value.update({"raw": ">6.4 wt%", "numeric": 6.4, "category": None, "unit": "wt%", "qualifier": "greater_than", "status": "bounded", "tolerance": 0.1})
        report = render(data)
        self.assertIn(">6.4 wt%", report)
        self.assertNotIn(">6.4 wt% wt%", report)

    def test_review_reasons_are_deduplicated_without_machine_code(self) -> None:
        data = example("microscopy_review.json")
        reason = copy.deepcopy(data["panels"][0]["review_reasons"][0])
        data["review_reasons"] = [reason]
        report = render(data)
        self.assertEqual(1, report.count(reason["detail"]))
        self.assertNotIn(reason["code"], report)

    def test_selected_scope_is_disclosed(self) -> None:
        data = example("omics_volcano.json")
        scope = data["panels"][0]["reporting_scope"]
        scope.update({"mode": "selected", "total_count": 12000, "selection_rule": "仅展示作者标注且满足预设阈值的特征"})
        self.assertEqual([], audit(data))
        report = render(data)
        self.assertIn("当前展示 1/12000 条记录", report)
        self.assertIn(scope["selection_rule"], report)

    def test_bbox_is_human_readable_not_json(self) -> None:
        report = render(example("quantitative_dual_axis.json"))
        self.assertIn("页内 x 10%–90%", report)
        self.assertNotIn("coordinate_space", report)

    def test_report_verifier_accepts_all_examples(self) -> None:
        for name in EXAMPLES:
            with self.subTest(name=name):
                data = example(name)
                self.assertEqual([], verify(data, render(data)))


class UnitTests(unittest.TestCase):
    def test_core_and_biomedical_units(self) -> None:
        expected = {
            "kPa": "pressure", "N": "force", "wt%": "mass_fraction", "mm³": "volume", "µm": "length",
            "mM": "molar_concentration", "µM": "molar_concentration", "mg/mL": "mass_concentration",
            "°C": "temperature", "mV": "voltage", "pA": "current",
        }
        for unit, dimension in expected.items():
            with self.subTest(unit=unit):
                result = normalize(unit)
                self.assertEqual("recognized", result["status"])
                self.assertEqual(dimension, result["dimension"])

    def test_case_sensitive_molarity_does_not_collide_with_length(self) -> None:
        self.assertEqual("molar_concentration", normalize("mM")["dimension"])
        self.assertEqual("length", normalize("mm")["dimension"])
        self.assertEqual("pressure", normalize("Pa")["dimension"])
        self.assertEqual("current", normalize("pA")["dimension"])

    def test_unknown_unit_is_explicit(self) -> None:
        self.assertEqual("unknown_unit", normalize("furlong/fortnight")["status"])


class EndToEndTests(unittest.TestCase):
    def test_finalizer_stamps_and_publishes_synchronized_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            report = Path(directory) / "report.md"
            evidence.write_text(json.dumps(example("process_workflow.json"), ensure_ascii=False, indent=2), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "finalize_output.py"), str(evidence), str(report)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            data = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertTrue(data["validation"]["schema_passed"])
            self.assertTrue(data["validation"]["semantic_passed"])
            self.assertTrue(data["validation"]["report_generated"])
            self.assertEqual([], verify(data, report.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
