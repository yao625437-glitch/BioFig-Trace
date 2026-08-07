#!/usr/bin/env python3
"""Verify the public 5C report without requiring machine identifiers to leak."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from migrate_v21_to_v22 import migrate as migrate_v21_to_v22
from report_labels import COVERAGE_STATUS


SECTIONS = ["## 结构化结果表", "## 图表解释", "## 原图定位", "## 来源消费覆盖", "## 冲突与不确定性", "## 人工复核建议"]
COVERAGE_HEADER = "| 来源 | 已使用信息 | 用途 | 状态 | 限制 |"
PROFILE_MARKERS = {
    "group_comparison": "| 组别/条件 |",
    "continuous_series": "| 系列 | 自变量/剂量/时间 |",
    "association": "| 对象/系列 | 变量 X | 变量 Y |",
    "distribution_composition": "| 组别/类别 |",
    "multivariate": "| 对象/系列 | 维度/指标 |",
    "feature_significance": "| 特征/位点 | 方向/系列 | 比较 | 效应量/横轴 | 显著性/纵轴 | 判定阈值 |",
    "matrix_embedding": "| 对象/群组 | 维度/列 |",
    "enrichment_set": "| 条目/集合 |",
    "survival_outcome": "| 组别 | 时间 | 结局指标 |",
    "diagnostic_prediction": "| 模型/组别 | 阈值/时间 |",
    "effect_estimate": "| 变量/比较 | 效应量 |",
    "dose_response": "| 药物/刺激 | 实验系统 | 剂量/范围 | 响应指标 |",
    "image_observation": "| 样本/系统 | 组别/比较 | 观察特征 | 图像所见 |",
    "band_lane": "| 泳道/组别 | 靶标/特征 |",
    "cytometry_gate": "| 细胞群/门 | 标记或坐标 |",
    "spectrum_trace": "| 峰/变异/系列 | 位置 |",
    "workflow_flow": "| 步骤 | 输入 | 操作 | 关键参数 | 输出 | 前置/分支 |",
    "mechanism_relationship": "| 上游/来源实体 | 关系 | 下游/目标实体 |",
    "structured_table": "| 变量/指标 | 组别/模型 |",
    "model_explanation": "| 特征/模型 | 解释指标 |",
    "signal_trajectory": "| 对象/信号 | 时间/事件 |",
}


def section(report: str, heading: str, next_heading: str | None) -> str:
    start = report.find(heading)
    if start < 0:
        return ""
    end = report.find(next_heading, start + len(heading)) if next_heading else len(report)
    return report[start:end if end >= 0 else len(report)]


def panel_block(results: str, panel_id: str) -> str:
    marker = f"### 面板 {panel_id}｜"
    start = results.find(marker)
    if start < 0:
        return ""
    end = results.find("\n### 面板 ", start + len(marker))
    return results[start:end if end >= 0 else len(results)]


def _factor_visible(block: str, factor: dict[str, Any]) -> bool:
    if factor.get("value") is not None:
        number = f"{factor['value']:g}"
        return number in block and (not factor.get("unit") or str(factor["unit"]) in block)
    if factor.get("level"):
        return str(factor["level"]) in block
    return str(factor.get("name") or "") in block


def verify(data: dict[str, Any], report: str) -> list[str]:
    if data.get("schema_version") == "2.1":
        data = migrate_v21_to_v22(data)
    issues = [f"missing section {item}" for item in SECTIONS if item not in report]
    if re.search(r"\$\.[A-Za-z_]", report):
        issues.append("report exposes a JSON field path")
    for token in ("field_paths", "消费字段", "reported=", "calculated=", "tolerance=", '"coordinate_space"'):
        if token in report:
            issues.append(f"report exposes machine token {token!r}")

    results = section(report, SECTIONS[0], SECTIONS[1])
    for panel in data.get("panels", []):
        panel_id = str(panel.get("panel_id"))
        block = panel_block(results, panel_id)
        if not block:
            issues.append(f"panel {panel_id!r} is absent from the results section")
            continue
        profile = panel.get("result_profile")
        marker = PROFILE_MARKERS.get(profile)
        has_rows = bool(panel.get("measurements") or panel.get("qualitative_observations") or panel.get("process_steps") or panel.get("relationships"))
        if marker and has_rows and marker not in block:
            issues.append(f"panel {panel_id!r} does not use the {profile!r} table profile")
        if profile == "workflow_flow":
            for forbidden in ("| 不确定性 |", "| 误差 |", "| P 值 |", "| 变量 X |", "| 变量 Y |"):
                if forbidden in block:
                    issues.append(f"workflow panel {panel_id!r} exposes inapplicable column {forbidden!r}")
            for step in panel.get("process_steps", []):
                if str(step.get("label")) not in block:
                    issues.append(f"workflow step {step.get('label')!r} is absent from panel {panel_id!r}")
                for factor in step.get("parameters", []):
                    if not _factor_visible(block, factor):
                        issues.append(f"workflow parameter {factor.get('name')!r} is absent from panel {panel_id!r}")
        if profile in {"image_observation", "band_lane", "cytometry_gate"}:
            for forbidden in ("| 变量 X |", "| 变量 Y |", "| 自变量/剂量/时间 |"):
                if forbidden in block:
                    issues.append(f"image panel {panel_id!r} exposes inapplicable column {forbidden!r}")

        summary = panel.get("academic_summary", {})
        for key in ("key_finding", "critical_appraisal"):
            text = str(summary.get(key) or "")
            if text and text not in report:
                issues.append(f"panel {panel_id!r} academic_summary.{key} is absent from report")
        scope = panel.get("reporting_scope", {})
        if scope.get("mode") != "full" and str(scope.get("selection_rule") or "") not in block:
            issues.append(f"panel {panel_id!r} omits its report selection rule")

    coverage_text = section(report, SECTIONS[3], SECTIONS[4])
    if COVERAGE_HEADER not in coverage_text:
        issues.append("source coverage table does not use the required five public columns")
    if re.search(r"\$\.[A-Za-z_]", coverage_text):
        issues.append("source coverage section exposes a machine audit path")
    for item in data.get("source_coverage", []):
        label = COVERAGE_STATUS.get(item.get("status"))
        if label and label not in coverage_text:
            issues.append(f"localized source status {label!r} is absent")
        public_fact = str(item.get("fact_summary")).replace("|", "\\|")
        if item.get("status") in {"consumed", "partially_consumed"} and public_fact not in coverage_text:
            issues.append(f"consumed fact {item.get('id')!r} is absent from source coverage summary")
        for field_path in item.get("field_paths", []):
            if field_path in coverage_text:
                issues.append(f"source coverage path {field_path!r} leaked into public report")
        if str(item.get("id")) in coverage_text:
            issues.append(f"source coverage internal id {item.get('id')!r} leaked into public report")

    for reason in data.get("review_reasons", []):
        if str(reason.get("code")) in report or str(reason.get("field_path")) in report:
            issues.append("root review machine identifier leaked into public report")
        if str(reason.get("detail")) not in report or str(reason.get("suggested_action")) not in report:
            issues.append(f"root review action for {reason.get('code')!r} is incomplete in report")
    for panel in data.get("panels", []):
        for reason in panel.get("review_reasons", []):
            if str(reason.get("code")) in report or str(reason.get("field_path")) in report:
                issues.append(f"panel {panel.get('panel_id')!r} review machine identifier leaked into public report")
            if str(reason.get("detail")) not in report or str(reason.get("suggested_action")) not in report:
                issues.append(f"panel {panel.get('panel_id')!r} review action is incomplete in report")
    for conflict in data.get("conflicts", []):
        if str(conflict.get("id")) in report:
            issues.append(f"conflict internal id {conflict.get('id')!r} leaked into public report")
        if str(conflict.get("description")) not in report or str(conflict.get("review_action")) not in report:
            issues.append(f"conflict {conflict.get('id')!r} is incomplete in report")
    return list(dict.fromkeys(issues))


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: verify_report.py <evidence.json> <report.md>", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        report = Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"REPORT INVALID: {exc}", file=sys.stderr)
        return 1
    issues = verify(data, report)
    if issues:
        print(f"REPORT INVALID: {len(issues)} issue(s)")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("REPORT VALID: 5C sections, typed tables, source summary, conflicts, and reviews are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
