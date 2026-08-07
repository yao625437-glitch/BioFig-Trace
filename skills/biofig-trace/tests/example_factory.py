"""Build independent v3 synthetic examples from raw fixture concepts."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]


def confidence(level: str = "high", rationale: str = "图像、图注与方法信息一致。") -> dict[str, Any]:
    score = {"high": 0.9, "medium": 0.7, "low": 0.35, "unknown": None}[level]
    return {
        "level": level,
        "score": score,
        "rationale": rationale,
        "source_quality": "high" if level == "high" else "medium" if level == "medium" else "low",
        "legibility": "high" if level == "high" else "medium" if level == "medium" else "low",
        "agreement": "consistent" if level in {"high", "medium"} else "single_source",
    }


def value(
    raw: Any,
    unit: str | None = None,
    *,
    evidence: list[str] | None = None,
    precision: str = "exact",
    tolerance: float | None = None,
    basis: str | None = "作者在图注或图内明确报告。",
) -> dict[str, Any]:
    return {
        "value": raw,
        "unit": unit,
        "state": "present",
        "precision": precision,
        "tolerance": tolerance,
        "basis": basis,
        "evidence_ids": evidence or ["ev-caption"],
    }


def missing(state: str, reason: str, *, evidence: list[str] | None = None) -> dict[str, Any]:
    return {
        "value": None,
        "unit": None,
        "state": state,
        "precision": "not_applicable",
        "tolerance": None,
        "basis": reason,
        "evidence_ids": evidence or ["ev-caption"],
    }


def base_example(name: str, category: str, figure_type: str, template: str, record: dict[str, Any], objective: str) -> dict[str, Any]:
    image_source = {
        "source_id": "src-image",
        "kind": "figure_image",
        "access_basis": "user_provided",
        "availability": "available",
        "locator": {"uri": None, "path": f"tests/fixtures/{name}.svg", "citation": f"{name}.svg", "detail": "合成前向测试图"},
        "sha256": None,
        "media_type": "image/svg+xml",
        "size_bytes": None,
        "visual_inspection": {"status": "completed", "page_or_region": "完整图像", "dpi": 300, "limitations": None},
    }
    text_source = {
        "source_id": "src-context",
        "kind": "methods_text",
        "access_basis": "user_provided",
        "availability": "available",
        "locator": {"uri": None, "path": f"tests/fixtures/{name}.txt", "citation": f"{name}.txt", "detail": "合成图注与方法"},
        "sha256": None,
        "media_type": "text/plain",
        "size_bytes": None,
        "visual_inspection": {"status": "not_performed", "page_or_region": None, "dpi": None, "limitations": "文本来源不需要视觉核验。"},
    }
    return {
        "schema_id": "https://biofig-trace.local/schema/evidence/3.0",
        "schema_version": "3.0.0",
        "run": {"run_id": f"run-example-{name}", "status": "complete", "report_language": "zh-CN", "created_at": "2026-08-08T00:00:00Z", "limitations": []},
        "paper": {"title": f"BioFig Trace 独立合成示例：{name}", "doi": None, "identifiers": [f"synthetic:{name}"], "public_access_confirmed": False},
        "sources": [image_source, text_source],
        "activities": [],
        "figures": [{"figure_id": "fig-1", "label": "Figure 1", "caption": objective, "evidence_ids": ["ev-caption"]}],
        "panels": [
            {
                "panel_id": "panel-A",
                "figure_id": "fig-1",
                "location": {
                    "source_id": "src-image",
                    "pdf_page": None,
                    "printed_page": None,
                    "panel_label": "A",
                    "bbox": {"x": 0.02, "y": 0.02, "width": 0.96, "height": 0.96, "coordinate_system": "normalized_page"},
                    "locator_note": "Figure 1，面板 A，完整合成图。",
                },
                "visual_check": {"status": "completed", "page_or_region": "面板 A", "dpi": 300, "limitations": None},
                "classification": {
                    "status": "resolved",
                    "function_category": category,
                    "figure_type": figure_type,
                    "result_template": template,
                    "alternatives": [],
                    "rationale": "依据图注、轴/图例语义和科学用途分类。",
                    "confidence": confidence(),
                    "evidence_ids": ["ev-visual", "ev-caption"],
                },
                "reporting_scope": {"mode": "full", "displayed_count": 1, "total_count": 1, "selection_rule": None},
                "objective": objective,
                "conditions": [
                    {
                        "condition_id": "cond-system",
                        "role": "system",
                        "factor": "实验系统",
                        "value": value("合成生物医学实验系统", evidence=["ev-method"]),
                        "evidence_ids": ["ev-method"],
                        "confidence": confidence(),
                    }
                ],
                "results": {"template": template, "records": [record]},
                "derived_values": [],
                "claims": [
                    {
                        "claim_id": "claim-main",
                        "text": objective,
                        "nature": "reported",
                        "premise_ids": [],
                        "inference_rule": None,
                        "evidence_ids": ["ev-caption"],
                        "confidence": confidence(),
                        "limitation": None,
                    }
                ],
                "confidence": confidence(),
                "review": {"required": False, "highest_priority": "none", "suggestions": []},
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "ev-visual",
                "source_id": "src-image",
                "anchor": {"page": None, "printed_page": None, "panel_label": "A", "bbox": {"x": 0.02, "y": 0.02, "width": 0.96, "height": 0.96, "coordinate_system": "normalized_page"}, "text_span": None, "table_cell": None, "region_description": "面板 A 的图形、坐标轴与图例"},
                "nature": "observed",
                "capture_method": "visual_observation",
                "content": "面板视觉形式和主要标记清晰可见。",
                "supports": ["/panels/0/location", "/panels/0/classification"],
                "confidence": confidence(),
                "limitations": [],
            },
            {
                "evidence_id": "ev-caption",
                "source_id": "src-context",
                "anchor": {"page": None, "printed_page": None, "panel_label": "A", "bbox": None, "text_span": "caption:1", "table_cell": None, "region_description": None},
                "nature": "reported",
                "capture_method": "text_transcription",
                "content": objective,
                "supports": ["/figures/0/caption", "/panels/0/results/records/0", "/panels/0/claims/0"],
                "confidence": confidence(),
                "limitations": [],
            },
            {
                "evidence_id": "ev-method",
                "source_id": "src-context",
                "anchor": {"page": None, "printed_page": None, "panel_label": None, "bbox": None, "text_span": "methods:1", "table_cell": None, "region_description": None},
                "nature": "reported",
                "capture_method": "text_transcription",
                "content": "合成方法文本明确给出实验系统和统计语境。",
                "supports": ["/panels/0/conditions/0"],
                "confidence": confidence(),
                "limitations": [],
            },
        ],
        "source_coverage": [
            {"coverage_id": "cov-image", "source_id": "src-image", "fact_summary": "视觉形式与面板定位", "purpose": "面板定位和图型核验", "status": "consumed", "field_paths": ["/panels/0/location", "/panels/0/classification"], "reason": None},
            {"coverage_id": "cov-context", "source_id": "src-context", "fact_summary": "图注、实验条件和作者报告结果", "purpose": "重建实验语境与结果", "status": "consumed", "field_paths": ["/panels/0/conditions/0", "/panels/0/results/records/0"], "reason": None},
        ],
        "conflicts": [],
        "review": {"required": False, "highest_priority": "none", "suggestions": []},
        "validation": {"state": "unvalidated", "schema_passed": False, "semantic_passed": False, "report_passed": False, "validator": "biofig-trace-finalizer/3.0", "validated_at": None, "content_sha256": None, "report_sha256": None},
    }


def record_base(record_id: str, origin: str = "author_measured", evidence: list[str] | None = None) -> dict[str, Any]:
    return {"record_id": record_id, "measurement_origin": origin, "evidence_ids": evidence or ["ev-caption"], "confidence": confidence()}


def examples() -> dict[str, dict[str, Any]]:
    group = record_base("rec-group") | {
        "group": value("Treatment"), "endpoint": value("Cell viability"), "result": value(72.0, "%"),
        "error_definition": value("SEM"), "sample_size": value(3, "biological replicates"), "statistical_method": value("one-way ANOVA"),
    }
    basic = base_example("basic_statistics", "basic_statistics", "bar_chart", "group_comparison", group, "作者报告处理组细胞活力为 72%（SEM，n=3）。")

    omics_record = record_base("rec-feature", "author_calculated") | {
        "feature": value("GENE-A"), "direction": value("up"), "contrast": value("treated vs control"),
        "effect_size": value(2.1, "log₂FC"), "significance": value(0.004, "FDR"),
        "thresholds": value("|log₂FC| ≥ 1 and FDR < 0.05"), "multiple_testing": value("Benjamini-Hochberg"),
    }
    omics = base_example("omics_volcano", "omics_bioinformatics", "volcano_plot", "omics_feature", omics_record, "作者报告 GENE-A 在处理组上调，log₂FC=2.1，FDR=0.004。")
    omics["panels"][0]["reporting_scope"] = {"mode": "selected", "displayed_count": 1, "total_count": 12000, "selection_rule": "展示满足 |log₂FC|≥1 且 FDR<0.05 的代表性标注特征。"}

    clinical_record = record_base("rec-effect", "author_calculated") | {
        "endpoint": value("Overall survival"), "population": value("Adults with advanced disease"),
        "effect_measure": value("HR"), "estimate": value(0.72), "confidence_interval": value([0.58, 0.90], "95% CI"),
        "p_value": value(0.004), "reference_group": value("Standard care"), "adjustment_model": value("Adjusted Cox model"),
    }
    clinical = base_example("clinical_forest", "clinical_epidemiology", "forest_plot", "clinical_effect", clinical_record, "作者报告治疗相对标准护理的总生存 HR 为 0.72（95% CI 0.58–0.90，P=0.004）。")

    image_record = record_base("rec-image") | {
        "sample": value("Tumour organoid"), "modality": value("Confocal fluorescence microscopy"),
        "stain_or_channel": value("DAPI / EpCAM"), "observation": value("EpCAM 信号主要位于细胞膜周边", evidence=["ev-visual"]),
        "scale_bar": value(50, "µm", evidence=["ev-visual"]),
        "quantification": missing("unknown", "图注未报告组水平定量。"),
        "limitations": value("仅为代表性视野，不能据此推断组均值或方差。", evidence=["ev-visual"]),
    }
    microscopy = base_example("microscopy", "experimental_image", "microscopy", "image_observation", image_record, "图中可见 EpCAM 膜周信号；该代表性视野不能替代组水平定量。")
    review = {"code": "REPRESENTATIVE_IMAGE_ONLY", "priority": "medium", "panel_ids": ["panel-A"], "reason": "只有代表性视野且无组水平定量。", "action": "核对原始视野选择规则和独立样本定量。", "evidence_ids": ["ev-visual"]}
    microscopy["panels"][0]["review"] = {"required": True, "highest_priority": "medium", "suggestions": [review]}
    microscopy["panels"][0]["confidence"] = confidence("medium", "图像清晰，但组水平代表性未知。")
    microscopy["review"] = {"required": True, "highest_priority": "medium", "suggestions": [copy.deepcopy(review)]}

    step1 = record_base("rec-step-1", "not_applicable") | {
        "step": value("1"), "input": value("Raw images"), "operation": value("Background correction"),
        "parameters": value("rolling-ball radius 25 px"), "output": value("Corrected images"), "predecessors": [], "branch": missing("not_applicable", "首个步骤无分支。"),
    }
    step2 = record_base("rec-step-2", "not_applicable") | {
        "step": value("2"), "input": value("Corrected images"), "operation": value("Cell segmentation"),
        "parameters": value("threshold 0.42"), "output": value("Cell masks"), "predecessors": ["rec-step-1"], "branch": value("QC pass / manual review"),
    }
    workflow = base_example("workflow", "workflow_mechanism", "workflow", "workflow_step", step1, "图示流程从背景校正进入细胞分割，并在质量控制处分支。")
    workflow["panels"][0]["results"]["records"].append(step2)
    workflow["panels"][0]["reporting_scope"] = {"mode": "full", "displayed_count": 2, "total_count": 2, "selection_rule": None}

    mechanism_record = record_base("rec-edge", "not_applicable", ["ev-edge"]) | {
        "upstream": "AKT", "relation": "activates", "downstream": "mTOR", "direction": "directed", "evidence_nature": "depicted",
    }
    mechanism = base_example("mechanism", "workflow_mechanism", "mechanism_diagram", "mechanism_relation", mechanism_record, "图示关系为 AKT 指向 mTOR 的激活箭头；该箭头本身不等于实验因果验证。")
    mechanism["evidence_items"][0] = {
        "evidence_id": "ev-edge", "source_id": "src-image",
        "anchor": {"page": None, "printed_page": None, "panel_label": "A", "bbox": {"x": 0.2, "y": 0.35, "width": 0.6, "height": 0.3, "coordinate_system": "normalized_page"}, "text_span": None, "table_cell": None, "region_description": "AKT→mTOR 箭头"},
        "nature": "depicted", "capture_method": "visual_observation", "content": "图中绘制 AKT 激活 mTOR 的有向边。",
        "supports": ["/panels/0/classification", "/panels/0/results/records/0"], "confidence": confidence(), "limitations": ["图示关系不能单独证明因果机制。"],
    }
    mechanism["panels"][0]["classification"]["evidence_ids"] = ["ev-edge", "ev-caption"]
    mechanism["panels"][0]["claims"][0] = {"claim_id": "claim-main", "text": "图中绘制 AKT 激活 mTOR 的关系。", "nature": "depicted", "premise_ids": [], "inference_rule": None, "evidence_ids": ["ev-edge"], "confidence": confidence(), "limitation": "仅表示作者绘制的关系，不代表实验因果验证。"}
    mechanism["source_coverage"][0]["field_paths"] = ["/panels/0/classification", "/panels/0/results/records/0"]

    dose_record = record_base("rec-dose", "author_calculated") | {
        "agent": value("Compound X-17"), "experimental_system": value("HEK293 viability assay"),
        "dose_range": value([0.01, 10.0], "µM"), "response_endpoint": value("Normalized viability", "%"),
        "potency": value(1.4, "µM"), "interval": value([1.1, 1.8], "95% CI"), "fit_model": value("4-parameter logistic (4PL)"),
    }
    dose = base_example("dose_response", "specialized_table", "dose_response", "dose_response", dose_record, "作者报告 Compound X-17 的 IC50 为 1.4 µM（95% CI 1.1–1.8 µM，4PL）。")
    dose["panels"][0]["conditions"].append({"condition_id": "cond-duration", "role": "duration", "factor": "Exposure", "value": value(24, "h", evidence=["ev-method"]), "evidence_ids": ["ev-method"], "confidence": confidence()})
    dose["evidence_items"][2]["supports"].append("/panels/0/conditions/1")

    blot_record = record_base("rec-blot") | {
        "lane": value("Lane 2: Compound X", evidence=["ev-visual", "ev-caption"]),
        "target": value("p-AKT", evidence=["ev-caption"]),
        "molecular_weight": value(60, "kDa", evidence=["ev-visual"]),
        "loading_control": value("β-actin", evidence=["ev-visual", "ev-caption"]),
        "control": value("Vehicle, Lane 1", evidence=["ev-caption"]),
        "band_observation": value("Lane 2 p-AKT band is visually darker than Lane 1", evidence=["ev-visual"]),
        "quantification": missing("unknown", "No normalized densitometry was reported.", evidence=["ev-caption"]),
    }
    blot = base_example("western_blot", "experimental_image", "western_blot", "blot_lane", blot_record, "图中可见处理泳道的 p-AKT 条带较深；未报告规范化灰度定量，不能据此生成倍数变化。")
    blot_review = {"code": "BLOT_QUANTIFICATION_MISSING", "priority": "medium", "panel_ids": ["panel-A"], "reason": "图中有内参但未报告规范化灰度定量。", "action": "核对未裁切原图、曝光线性范围和以 β-actin 归一化的独立重复灰度值。", "evidence_ids": ["ev-visual", "ev-caption"]}
    blot["panels"][0]["review"] = {"required": True, "highest_priority": "medium", "suggestions": [blot_review]}
    blot["panels"][0]["confidence"] = confidence("medium", "泳道和内参清晰，但没有可复核的组水平灰度定量。")
    blot["review"] = {"required": True, "highest_priority": "medium", "suggestions": [copy.deepcopy(blot_review)]}

    flow_record = record_base("rec-flow", "author_calculated") | {
        "population": value("CD3+CD8+ T cells"),
        "gating_hierarchy": value("Live singlets → CD3+ → CD8+"),
        "markers": value("CD3-APC; CD8-FITC"),
        "denominator": value("Parent CD3+ gate"),
        "proportion_or_count": value(37.2, "% of parent CD3+ gate"),
    }
    flow = base_example("flow_cytometry", "experimental_image", "flow_cytometry", "flow_population", flow_record, "作者在父 CD3+ 门内报告 CD8+ 细胞占 37.2%，门控层级和分母均明确。")
    flow["panels"][0]["conditions"].append({"condition_id": "cond-control", "role": "control", "factor": "Gate control", "value": value("FMO control", evidence=["ev-method"]), "evidence_ids": ["ev-method"], "confidence": confidence()})
    flow["evidence_items"][2]["supports"].append("/panels/0/conditions/1")

    return {
        "basic_statistics": basic,
        "omics_volcano": omics,
        "clinical_forest": clinical,
        "microscopy": microscopy,
        "workflow": workflow,
        "mechanism": mechanism,
        "dose_response": dose,
        "western_blot": blot,
        "flow_cytometry": flow,
    }


def main() -> int:
    output = SKILL_ROOT / "examples"
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in examples().items():
        (output / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(examples())} examples to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
