#!/usr/bin/env python3
"""Render a deterministic, 5C-oriented Chinese report from evidence.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from figure_registry import load_registry
from migrate_v21_to_v22 import migrate as migrate_v21_to_v22
from report_labels import (
    COMPARISON_STATUS,
    CONDITION_NAME,
    CONFIDENCE,
    CONFLICT_KIND,
    COVERAGE_STATUS,
    DIRECTION,
    EPISTEMIC_STATUS,
    ERROR_KIND,
    EXTRACTION_STATUS,
    RESOLUTION,
    REVIEW_CODE,
    SEVERITY,
    SIGN,
    SOURCE_SCOPE,
    SOURCE_TYPE,
)


def esc(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def format_value(value: dict[str, Any] | None) -> str:
    value = value or {}
    status = value.get("status")
    if status == "not_applicable":
        return "不适用"
    if status == "not_recoverable":
        return "未能可靠读取"
    raw = value.get("raw")
    category = value.get("category")
    if raw:
        text = str(raw)
    elif category:
        text = str(category)
    elif value.get("numeric") is not None:
        text = f"{value['numeric']:g}"
    else:
        text = "未报告"
    unit = value.get("unit")
    if unit:
        compact_text = re.sub(r"\s+", "", text).lower()
        compact_unit = re.sub(r"\s+", "", str(unit)).lower()
        if not compact_text.endswith(compact_unit):
            text += f" {unit}"
    if status == "approximate" and value.get("tolerance") is not None:
        text += f"（估读容差 ±{value['tolerance']:g}）"
    return text


def format_factor(factor: dict[str, Any]) -> str:
    raw_name = str(factor.get("name") or "条件").strip()
    name = CONDITION_NAME.get(raw_name.lower(), raw_name.replace("_", " "))
    parts: list[str] = []
    level = str(factor.get("level") or "").strip()
    numeric_text = ""
    if factor.get("value") is not None:
        numeric = f"{factor['value']:g}"
        numeric_text = f"{numeric} {factor.get('unit')}" if factor.get("unit") else numeric
    if level and re.sub(r"\s+", "", level).lower() != re.sub(r"\s+", "", numeric_text).lower():
        parts.append(level)
    if numeric_text:
        parts.append(numeric_text)
    return f"{name}：{'；'.join(parts)}" if parts else name


def format_conditions(factors: Iterable[dict[str, Any]]) -> str:
    values = [format_factor(item) for item in factors]
    return "；".join(values) if values else "—"


def format_error(error: dict[str, Any]) -> str:
    kind = ERROR_KIND.get(error.get("kind"), "未说明")
    lower, upper = error.get("lower"), error.get("upper")
    if lower is not None or upper is not None:
        kind += f" [{esc(lower)}, {esc(upper)}]"
    elif error.get("raw"):
        kind += f"（{error['raw']}）"
    return kind


def source_locator(source: dict[str, Any]) -> str:
    label = SOURCE_TYPE.get(source.get("type"), "来源")
    locator = source.get("locator", {})
    parts: list[str] = []
    if locator.get("page") is not None:
        parts.append(f"第 {locator['page']} 页")
    if locator.get("panel"):
        parts.append(f"面板 {locator['panel']}")
    paragraph = str(locator.get("paragraph") or "").strip()
    if paragraph and paragraph.lower() not in {"caption", "results", "methods", "supplement"}:
        parts.append(paragraph)
    return f"{label}（{'，'.join(parts)}）" if parts else label


def evidence_label(ids: Iterable[str], sources: dict[str, dict[str, Any]]) -> str:
    labels = [source_locator(sources[source_id]) for source_id in ids if source_id in sources]
    return "；".join(dict.fromkeys(labels)) if labels else "—"


def format_bbox(bbox: dict[str, Any] | None) -> str:
    if not bbox:
        return "未记录"
    x0, x1, y0, y1 = bbox.get("x0"), bbox.get("x1"), bbox.get("y0"), bbox.get("y1")
    space = bbox.get("coordinate_space")
    if space == "normalized_0_1":
        return f"页内 x {x0 * 100:g}%–{x1 * 100:g}%，y {y0 * 100:g}%–{y1 * 100:g}%"
    unit = "px" if space == "pixels" else "pt"
    return f"x {x0:g}–{x1:g} {unit}，y {y0:g}–{y1:g} {unit}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(esc(cell) for cell in row) + " |" for row in rows)
    return lines


def series_label(panel: dict[str, Any], series_id: str | None) -> str:
    if not series_id:
        return "—"
    for series in panel.get("series", []):
        if series.get("id") == series_id:
            return str(series.get("label") or "—")
    return "—"


def sample_and_statistics(panel: dict[str, Any]) -> str:
    statistics = panel.get("statistics", {})
    parts: list[str] = []
    for sample in statistics.get("sample_sizes", []):
        if sample.get("value") is not None:
            scope = str(sample.get("scope") or "样本")
            parts.append(f"{scope}: n={sample['value']}")
    if statistics.get("tests"):
        parts.append("检验：" + "；".join(statistics["tests"]))
    p_values = []
    for item in statistics.get("p_values", []):
        raw = item.get("raw")
        if raw:
            value = str(raw)
        elif item.get("numeric") is not None:
            value = f"P {item.get('relation', '=')} {item['numeric']:g}"
        else:
            value = "P 值未能读取"
        if item.get("comparison"):
            value += f"（{item['comparison']}）"
        p_values.append(value)
    if p_values:
        parts.append("；".join(p_values))
    return "；".join(parts) if parts else "未报告"


def point_records(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    statistics = sample_and_statistics(panel)
    for measurement in panel.get("measurements", []):
        for point in measurement.get("points", []):
            series = series_label(panel, point.get("series_id"))
            x_text = format_value(point.get("x"))
            conditions = format_conditions(point.get("at_conditions", []))
            group_items = [item for item in (series, x_text, conditions) if item != "—"]
            group_condition = "；".join(dict.fromkeys(group_items)) or "—"
            records.append({
                "series": series,
                "system": str(panel.get("experiment", {}).get("system") or "未说明"),
                "endpoint": str(measurement.get("endpoint") or "—"),
                "x": x_text,
                "y": format_value(point.get("y")),
                "error": format_error(point.get("error", {})),
                "conditions": conditions,
                "group_condition": group_condition,
                "statistics": statistics,
                "evidence": evidence_label(point.get("evidence_ids", []), sources),
                "confidence": f"{CONFIDENCE.get(point.get('confidence'), '待定')}（{point.get('confidence_rationale', '未说明')}）",
            })
    return records


PROFILE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "group_comparison": [("组别/条件", "group_condition"), ("指标", "endpoint"), ("结果", "y"), ("不确定性", "error"), ("样本量与统计", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "continuous_series": [("系列", "series"), ("自变量/剂量/时间", "x"), ("终点", "endpoint"), ("结果", "y"), ("不确定性", "error"), ("其他条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "association": [("对象/系列", "series"), ("变量 X", "x"), ("变量 Y", "y"), ("关联或一致性检验", "statistics"), ("其他条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "distribution_composition": [("组别/类别", "group_condition"), ("分布或构成指标", "endpoint"), ("数值", "y"), ("分母/条件", "conditions"), ("统计说明", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "multivariate": [("对象/系列", "series"), ("维度/指标", "endpoint"), ("坐标或结果", "y"), ("比较条件", "group_condition"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "feature_significance": [("特征/系列", "series"), ("比较或坐标", "x"), ("效应/结果", "y"), ("显著性与阈值", "statistics"), ("分析条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "matrix_embedding": [("对象/群组", "series"), ("维度/列", "x"), ("值/坐标", "y"), ("变换或分群条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "enrichment_set": [("条目/集合", "series"), ("富集指标", "endpoint"), ("结果", "y"), ("基因数/显著性/条件", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "survival_outcome": [("组别", "series"), ("时间", "x"), ("结局指标", "endpoint"), ("生存/发生结果", "y"), ("95% CI/不确定性", "error"), ("风险人数与检验", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "diagnostic_prediction": [("模型/组别", "series"), ("阈值/时间", "x"), ("性能指标", "endpoint"), ("结果", "y"), ("95% CI/不确定性", "error"), ("验证与统计", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "effect_estimate": [("变量/比较", "group_condition"), ("效应量", "endpoint"), ("点估计", "y"), ("95% CI", "error"), ("P 值/调整模型", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "dose_response": [("药物/刺激", "series"), ("实验系统", "system"), ("剂量/范围", "x"), ("响应指标", "endpoint"), ("响应/药效参数", "y"), ("95% CI/不确定性", "error"), ("模型与关键条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "structured_table": [("变量/指标", "endpoint"), ("组别/模型", "group_condition"), ("数值", "y"), ("区间/离散度", "error"), ("统计与条件", "statistics"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "model_explanation": [("特征/模型", "series"), ("解释指标", "endpoint"), ("归因/性能", "y"), ("排名/条件", "group_condition"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "signal_trajectory": [("对象/信号", "series"), ("时间/事件", "x"), ("响应指标", "endpoint"), ("结果", "y"), ("不确定性", "error"), ("采集/处理条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
    "spectrum_trace": [("峰/变异/系列", "series"), ("位置", "x"), ("强度/结果", "y"), ("鉴定或条件", "conditions"), ("证据定位", "evidence"), ("置信度", "confidence")],
}


def format_formula(formula: str) -> str:
    text = re.sub(r"\*\*\s*2\b", "²", formula)
    text = re.sub(r"\*\*\s*3\b", "³", text)
    return text.replace("*", " × ")


def render_derived(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[list[Any]] = []
    for measurement in panel.get("measurements", []):
        for item in measurement.get("derived_values", []):
            unit = f" {item['unit']}" if item.get("unit") else ""
            reported = f"{item['reported']:g}{unit}" if item.get("reported") is not None else "未报告"
            calculated = f"{item['calculated']:g}{unit}" if item.get("calculated") is not None else "未能复算"
            rows.append([
                item.get("label"), format_formula(str(item.get("formula") or "")), reported, calculated,
                f"±{item.get('tolerance'):g}{unit}", COMPARISON_STATUS.get(item.get("comparison_status"), "待定"),
                evidence_label(item.get("evidence_ids", []), sources),
            ])
    if not rows:
        return []
    return ["", "**派生指标复核**", ""] + markdown_table(
        ["指标", "计算关系", "作者报告值", "复算值", "允许差异", "一致性结论", "证据定位"], rows
    )


def render_quantitative(panel: dict[str, Any], sources: dict[str, dict[str, Any]], profile: str | None = None) -> list[str]:
    profile = profile or panel.get("result_profile", "group_comparison")
    columns = PROFILE_COLUMNS.get(profile, PROFILE_COLUMNS["group_comparison"])
    records = point_records(panel, sources)
    if not records:
        lines = ["未恢复可可靠呈现的定量结果；具体缺失原因见人工复核建议。"]
    else:
        lines = markdown_table([label for label, _ in columns], [[record[key] for _, key in columns] for record in records])
    lines.extend(render_derived(panel, sources))
    return lines


def _axis_display(panel: dict[str, Any], role: str) -> str:
    for axis in panel.get("axes", []):
        if axis.get("role") == role:
            label = str(axis.get("label") or role)
            return {
                "log2 fold change": "log₂FC",
                "-log10 fdr": "−log₁₀(FDR)",
                "-log10 p": "−log₁₀(P)",
                "-log10 p value": "−log₁₀(P)",
            }.get(label.strip().lower(), label)
    return "横轴" if role == "x" else "纵轴"


def _factor_payload(factor: dict[str, Any]) -> str:
    if factor.get("level") not in {None, ""}:
        return str(factor["level"])
    if factor.get("value") is not None:
        unit = f" {factor['unit']}" if factor.get("unit") else ""
        return f"{factor['value']:g}{unit}"
    return str(factor.get("name") or "未说明")


def render_feature_significance(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    """Render omics/genomic feature evidence without anonymous x/y numbers."""
    rows: list[list[Any]] = []
    experiment = panel.get("experiment", {})
    comparison_factors = experiment.get("factors", [])
    threshold_factors = experiment.get("fixed_conditions", [])
    comparison = format_conditions(comparison_factors)
    thresholds = format_conditions(threshold_factors)
    p_values = panel.get("statistics", {}).get("p_values", [])
    x_label, y_label = _axis_display(panel, "x"), _axis_display(panel, "y")
    context_evidence = [
        source_id
        for factor in comparison_factors + threshold_factors
        for source_id in factor.get("evidence_ids", [])
    ]
    p_evidence = [source_id for item in p_values for source_id in item.get("evidence_ids", [])]
    for measurement in panel.get("measurements", []):
        for point in measurement.get("points", []):
            feature_factors = [
                factor for factor in point.get("at_conditions", [])
                if str(factor.get("name") or "").strip().lower() in {"feature", "gene", "variant", "snp", "locus", "protein", "metabolite"}
            ]
            feature = _factor_payload(feature_factors[0]) if feature_factors else str(measurement.get("endpoint") or "未说明")
            significance_parts: list[str] = []
            for item in p_values:
                if item.get("raw"):
                    significance_parts.append(str(item["raw"]))
                elif item.get("numeric") is not None:
                    significance_parts.append(f"P {item.get('relation', '=')} {item['numeric']:g}")
            if point.get("y", {}).get("status") not in {"not_applicable", "not_recoverable"}:
                significance_parts.append(f"{y_label}：{format_value(point.get('y'))}")
            evidence_ids = list(dict.fromkeys(point.get("evidence_ids", []) + context_evidence + p_evidence))
            rows.append([
                feature,
                series_label(panel, point.get("series_id")),
                comparison,
                f"{x_label}：{format_value(point.get('x'))}",
                "；".join(dict.fromkeys(significance_parts)) or "未报告",
                thresholds,
                evidence_label(evidence_ids, sources),
                f"{CONFIDENCE.get(point.get('confidence'), '待定')}（{point.get('confidence_rationale', '未说明')}）",
            ])
    if not rows:
        return ["未恢复可可靠呈现的特征、效应量或显著性结果。"]
    lines = markdown_table(
        ["特征/位点", "方向/系列", "比较", "效应量/横轴", "显著性/纵轴", "判定阈值", "证据定位", "置信度"],
        rows,
    )
    lines.extend(render_derived(panel, sources))
    return lines


def render_observations(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    system = panel.get("experiment", {}).get("system") or "未说明"
    rows = [
        [system, item.get("comparison"), item.get("feature") or "直接观察", item.get("observation"),
         evidence_label(item.get("evidence_ids", []), sources),
         f"{CONFIDENCE.get(item.get('confidence'), '待定')}（{item.get('confidence_rationale', '未说明')}）"]
        for item in panel.get("qualitative_observations", [])
    ]
    if not rows:
        return ["未恢复可可靠呈现的图像观察。"]
    return markdown_table(["样本/系统", "组别/比较", "观察特征", "图像所见", "证据定位", "置信度"], rows)


def render_band_lane(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[list[Any]] = []
    treatment = format_conditions(panel.get("experiment", {}).get("factors", []) + panel.get("experiment", {}).get("controls", []))
    for item in panel.get("qualitative_observations", []):
        rows.append([item.get("comparison"), item.get("feature") or "条带/泳道", treatment, item.get("observation"), "—", evidence_label(item.get("evidence_ids", []), sources), CONFIDENCE.get(item.get("confidence"), "待定")])
    for record in point_records(panel, sources):
        rows.append([record["series"], record["endpoint"], record["conditions"], "已记录定量结果", record["y"], record["evidence"], record["confidence"]])
    if not rows:
        return ["未恢复可可靠呈现的泳道、靶标或条带信息。"]
    return markdown_table(["泳道/组别", "靶标/特征", "处理/对照", "条带或凝胶所见", "定量结果（如有）", "证据定位", "置信度"], rows)


def render_cytometry(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    rows: list[list[Any]] = []
    for item in panel.get("qualitative_observations", []):
        rows.append([item.get("comparison"), item.get("feature"), item.get("observation"), "—", evidence_label(item.get("evidence_ids", []), sources), CONFIDENCE.get(item.get("confidence"), "待定")])
    for record in point_records(panel, sources):
        rows.append([record["series"], record["endpoint"], record["conditions"], record["y"], record["evidence"], record["confidence"]])
    if not rows:
        return ["未恢复可可靠呈现的门控、群体或比例。"]
    return markdown_table(["细胞群/门", "标记或坐标", "父门/条件", "比例或计数", "证据定位", "置信度"], rows)


def render_workflow(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    steps = panel.get("process_steps", [])
    labels = {step.get("id"): f"步骤 {step.get('order')}：{step.get('label')}" for step in steps}
    rows: list[list[Any]] = []
    for step in sorted(steps, key=lambda item: item.get("order", 0)):
        predecessors = "；".join(labels.get(item, item) for item in step.get("predecessor_ids", [])) or "起点"
        rows.append([
            step.get("order"), step.get("input"), step.get("label"), format_conditions(step.get("parameters", [])),
            step.get("output"), predecessors, evidence_label(step.get("evidence_ids", []), sources),
            CONFIDENCE.get(step.get("confidence"), "待定"),
        ])
    if not rows:
        return ["未恢复可可靠呈现的流程步骤。"]
    return markdown_table(["步骤", "输入", "操作", "关键参数", "输出", "前置/分支", "证据定位", "置信度"], rows)


def render_relationships(panel: dict[str, Any], sources: dict[str, dict[str, Any]]) -> list[str]:
    rows = [[
        item.get("source_entity"), item.get("relation"), item.get("target_entity"),
        f"{DIRECTION.get(item.get('direction'), '方向未明')}；{SIGN.get(item.get('sign'), '作用未明')}",
        EPISTEMIC_STATUS.get(item.get("epistemic_status"), "证据性质未明"),
        format_value(item.get("magnitude")) if item.get("magnitude") else "—",
        evidence_label(item.get("evidence_ids", []), sources),
        f"{CONFIDENCE.get(item.get('confidence'), '待定')}（{item.get('confidence_rationale', '未说明')}）",
    ] for item in panel.get("relationships", [])]
    if not rows:
        return ["未恢复可可靠呈现的实体关系；不得据此补画或推断机制链。"]
    return markdown_table(["上游/来源实体", "关系", "下游/目标实体", "方向/作用", "证据性质", "权重/数值", "证据定位", "置信度"], rows)


def render_panel_results(panel: dict[str, Any], sources: dict[str, dict[str, Any]], registry: dict[str, Any]) -> list[str]:
    rule = registry["panel_types"][panel["panel_type"]]
    category = registry["categories"][panel["figure_category"]]
    lines = [f"### 面板 {esc(panel['panel_id'])}｜{esc(rule['label_zh'])}（{esc(category)}）", ""]
    profile = panel["result_profile"]
    if profile == "workflow_flow":
        lines.extend(render_workflow(panel, sources))
    elif profile == "feature_significance":
        lines.extend(render_feature_significance(panel, sources))
    elif profile == "mechanism_relationship":
        lines.extend(render_relationships(panel, sources))
    elif profile == "image_observation":
        lines.extend(render_observations(panel, sources))
        if panel.get("measurements"):
            lines.extend(["", "**图像定量结果（如有）**", ""] + render_quantitative(panel, sources, "group_comparison"))
    elif profile == "band_lane":
        lines.extend(render_band_lane(panel, sources))
    elif profile == "cytometry_gate":
        lines.extend(render_cytometry(panel, sources))
    elif profile == "mixed":
        produced = False
        if panel.get("measurements"):
            lines.extend(["**定量结果**", ""] + render_quantitative(panel, sources, "group_comparison"))
            produced = True
        if panel.get("qualitative_observations"):
            lines.extend(["", "**图像或定性观察**", ""] + render_observations(panel, sources))
            produced = True
        if panel.get("process_steps"):
            lines.extend(["", "**流程步骤**", ""] + render_workflow(panel, sources))
            produced = True
        if panel.get("relationships"):
            lines.extend(["", "**实体关系**", ""] + render_relationships(panel, sources))
            produced = True
        if not produced:
            lines.append("未恢复可可靠呈现的结构化结果。")
    else:
        lines.extend(render_quantitative(panel, sources, profile))
        if panel.get("qualitative_observations"):
            lines.extend(["", "**定性补充**", ""] + render_observations(panel, sources))
    scope = panel.get("reporting_scope", {})
    if scope.get("mode") != "full":
        displayed = scope.get("displayed_count") if scope.get("displayed_count") is not None else "若干"
        total = scope.get("total_count") if scope.get("total_count") is not None else "总数未明"
        lines.extend(["", f"> 呈现范围：当前展示 {displayed}/{total} 条记录；筛选或汇总依据：{esc(scope.get('selection_rule'))}。"])
    return lines


def unique_review_reasons(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = [("全局", reason) for reason in data.get("review_reasons", [])]
    for panel in data.get("panels", []):
        items.extend((f"面板 {panel.get('panel_id')}", reason) for reason in panel.get("review_reasons", []))
    seen: set[tuple[Any, ...]] = set()
    result: list[tuple[str, dict[str, Any]]] = []
    for scope, reason in items:
        key = (reason.get("code"), reason.get("detail"), reason.get("suggested_action"))
        if key not in seen:
            seen.add(key)
            result.append((scope, reason))
    return result


def render(data: dict[str, Any]) -> str:
    if data.get("schema_version") == "2.1":
        data = migrate_v21_to_v22(data)
    registry = load_registry()
    sources = {source["id"]: source for source in data["sources"]}
    figure = data["figure"]
    lines = [f"# {esc(figure['figure_id'])} 实验图证据报告", ""]
    if data.get("document", {}).get("title"):
        lines.append(f"- 论文：{esc(data['document']['title'])}")
    if data.get("document", {}).get("doi"):
        lines.append(f"- DOI：{esc(data['document']['doi'])}")
    page = f"第 {figure['pdf_page']} 页" if figure.get("pdf_page") is not None else "页码未记录"
    lines.extend([
        f"- 图号与位置：{esc(figure['figure_id'])}，{page}",
        f"- 抽取完整性：{EXTRACTION_STATUS.get(data.get('extraction_status'), '待定')}",
        f"- 人工复核：{'需要' if data.get('review_required') else '暂无强制项'}",
        "",
        "## 结构化结果表",
        "",
    ])
    for index, panel in enumerate(data["panels"]):
        if index:
            lines.append("")
        lines.extend(render_panel_results(panel, sources, registry))

    lines.extend(["", "## 图表解释", ""])
    for panel in data["panels"]:
        rule = registry["panel_types"][panel["panel_type"]]
        summary = panel["academic_summary"]
        lines.extend([f"### 面板 {esc(panel['panel_id'])}｜{esc(rule['label_zh'])}", ""])
        if summary.get("objective"):
            lines.append(f"- 研究目的：{esc(summary['objective'])}")
        if summary.get("approach"):
            lines.append(f"- 方法语境：{esc(summary['approach'])}")
        lines.append(f"- 主要发现：{esc(summary['key_finding'])}")
        lines.append(f"- 评判性说明：{esc(summary['critical_appraisal'])}")
        if summary.get("limitations"):
            lines.append(f"- 主要限制：{esc('；'.join(summary['limitations']))}")
        lines.append(f"- 置信度：{CONFIDENCE.get(panel.get('confidence'), '待定')}（{esc(panel.get('confidence_rationale'))}）")

    lines.extend(["", "## 原图定位", "", "| 面板 | 图型 | PDF 页 | 面板标识 | 页内区域 | 原文件/图像 |", "|---|---|---:|---|---|---|"])
    for panel in data["panels"]:
        location = panel["location"]
        rule = registry["panel_types"][panel["panel_type"]]
        source = sources.get(location.get("source_id"), {})
        source_file = source.get("locator", {}).get("file") or figure.get("image_file") or data.get("document", {}).get("source_file")
        lines.append("| " + " | ".join([
            esc(panel["panel_id"]), esc(rule["label_zh"]), esc(location.get("pdf_page")), esc(location.get("panel_label")),
            esc(format_bbox(location.get("bbox"))), esc(source_file),
        ]) + " |")

    lines.extend(["", "## 来源消费覆盖", "", "| 来源 | 已使用信息 | 用途 | 状态 | 限制 |", "|---|---|---|---|---|"])
    coverage = data.get("source_coverage", [])
    if coverage:
        for item in coverage:
            status = item.get("status")
            used = item.get("fact_summary") if status in {"consumed", "partially_consumed"} else "—"
            reason = str(item.get("reason") or "").strip()
            if status == "consumed" and reason.lower() in {"", "none", "无", "n/a", "not applicable"}:
                reason = "无"
            elif status == "not_applicable":
                reason = reason or "与当前提取目标不相关"
            elif not reason:
                reason = "未说明"
            lines.append("| " + " | ".join([
                esc(source_locator(sources.get(item.get("source_id"), {}))), esc(used),
                esc(SOURCE_SCOPE.get(item.get("scope"), "其他")), esc(COVERAGE_STATUS.get(status, "待定")), esc(reason),
            ]) + " |")
    else:
        lines.append("| 尚无可审计的正文来源 | — | — | 未使用 | 当前仅有图像或未提供可消费的正文来源 |")

    lines.extend(["", "## 冲突与不确定性", ""])
    if data.get("conflicts"):
        for conflict in data["conflicts"]:
            text = f"- {CONFLICT_KIND.get(conflict.get('kind'), '来源不一致')}：{esc(conflict.get('description'))}"
            if conflict.get("calculation"):
                text += f"；复核计算：{esc(format_formula(str(conflict['calculation'])))}"
            if conflict.get("relative_difference") is not None:
                text += f"；相对差异：{conflict['relative_difference']:.2%}"
            text += f"；当前处置：{RESOLUTION.get(conflict.get('resolution'), '待定')}；复核建议：{esc(conflict.get('review_action'))}。"
            lines.append(text)
    else:
        lines.append("- 在已纳入且可读取的来源范围内，未登记图文、单位或复算冲突。")
    approximate_count = sum(
        1 for panel in data["panels"] for measurement in panel.get("measurements", []) for point in measurement.get("points", [])
        for coordinate in (point.get("x", {}), point.get("y", {})) if coordinate.get("status") == "approximate"
    )
    if approximate_count:
        lines.append(f"- 共 {approximate_count} 个坐标来自图上估读；相应容差已在结果表中逐项列出。")

    lines.extend(["", "## 人工复核建议", ""])
    reasons = unique_review_reasons(data)
    if reasons:
        rows = [[
            SEVERITY.get(reason.get("severity"), "待定"), scope,
            f"{REVIEW_CODE.get(reason.get('code'), '需复核事项')}：{reason.get('detail', '未说明')}",
            reason.get("suggested_action"), evidence_label(reason.get("evidence_ids", []), sources),
        ] for scope, reason in reasons]
        lines.extend(markdown_table(["优先级", "影响对象", "问题", "复核建议", "证据定位"], rows))
    else:
        lines.append("- 暂无强制人工复核项；如结果用于定量合并、临床决策或关键机制结论，仍建议按原图定位抽查核心数值与分组映射。")
    lines.extend(["", "---", "本报告由 evidence.json 自动生成；机器审计路径、完整来源映射和验证记录保留在该文件中。", ""])
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: render_report.py <evidence.json> <report.md>", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        Path(sys.argv[2]).write_text(render(data), encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"REPORT FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"REPORT GENERATED: {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
