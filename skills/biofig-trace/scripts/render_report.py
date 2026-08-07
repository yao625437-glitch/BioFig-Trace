"""Render the public 5C report from an explicit, machine-field-free projection."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from common import SCHEMA_ROOT, atomic_write_text, load_json


REPORT_PROFILE_PATH = SCHEMA_ROOT / "report_profile_v3.json"

TEMPLATE_COLUMNS_ZH: dict[str, list[tuple[str, str, str]]] = {
    "group_comparison": [
        ("group", "组别/条件", "value"),
        ("endpoint", "终点", "value"),
        ("result", "结果", "value"),
        ("error_definition", "误差/区间定义", "value"),
        ("sample_size", "样本量", "value"),
        ("statistical_method", "统计方法", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "dose_response": [
        ("agent", "药物/刺激", "value"),
        ("experimental_system", "实验系统", "value"),
        ("dose_range", "剂量范围", "value"),
        ("response_endpoint", "响应指标", "value"),
        ("potency", "IC50/EC50/药效参数", "value"),
        ("interval", "区间", "value"),
        ("fit_model", "拟合模型", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "omics_feature": [
        ("feature", "特征", "value"),
        ("direction", "方向", "value"),
        ("contrast", "比较", "value"),
        ("effect_size", "效应量", "value"),
        ("significance", "P/FDR", "value"),
        ("thresholds", "阈值", "value"),
        ("multiple_testing", "多重检验", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "clinical_effect": [
        ("endpoint", "终点", "value"),
        ("population", "人群", "value"),
        ("effect_measure", "效应量类型", "value"),
        ("estimate", "点估计", "value"),
        ("confidence_interval", "置信区间", "value"),
        ("p_value", "P 值", "value"),
        ("reference_group", "参考组", "value"),
        ("adjustment_model", "调整模型", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "image_observation": [
        ("sample", "样本", "value"),
        ("modality", "成像模态", "value"),
        ("stain_or_channel", "染色/通道", "value"),
        ("observation", "图像所见", "value"),
        ("scale_bar", "比例尺", "value"),
        ("quantification", "定量结果", "value"),
        ("limitations", "限制", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "blot_lane": [
        ("lane", "泳道/组别", "value"),
        ("target", "靶标", "value"),
        ("molecular_weight", "分子量", "value"),
        ("loading_control", "内参", "value"),
        ("control", "对照", "value"),
        ("band_observation", "条带观察", "value"),
        ("quantification", "定量结果", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "flow_population": [
        ("population", "细胞群", "value"),
        ("gating_hierarchy", "门控层级", "value"),
        ("markers", "标记", "value"),
        ("denominator", "父门/分母", "value"),
        ("proportion_or_count", "比例/计数", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "workflow_step": [
        ("step", "步骤", "value"),
        ("input", "输入", "value"),
        ("operation", "操作", "value"),
        ("parameters", "关键参数", "value"),
        ("output", "输出", "value"),
        ("predecessors", "前置步骤", "predecessors"),
        ("branch", "分支", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "mechanism_relation": [
        ("upstream", "上游实体", "text"),
        ("relation", "关系", "text"),
        ("downstream", "下游实体", "text"),
        ("direction", "方向", "direction"),
        ("evidence_nature", "证据性质", "nature"),
        ("confidence", "记录置信度", "confidence"),
    ],
    "specialized_table": [
        ("variable", "变量", "value"),
        ("group", "分组", "value"),
        ("statistic", "统计量", "value"),
        ("missingness", "缺失值", "value"),
        ("interval", "区间", "value"),
        ("footnote_definition", "脚注定义", "value"),
        ("confidence", "记录置信度", "confidence"),
    ],
}

TEMPLATE_COLUMNS_EN: dict[str, list[tuple[str, str, str]]] = {
    "group_comparison": [
        ("group", "Group / condition", "value"),
        ("endpoint", "Endpoint", "value"),
        ("result", "Result", "value"),
        ("error_definition", "Error / interval definition", "value"),
        ("sample_size", "Sample size", "value"),
        ("statistical_method", "Statistical method", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "dose_response": [
        ("agent", "Agent / stimulus", "value"),
        ("experimental_system", "Experimental system", "value"),
        ("dose_range", "Dose range", "value"),
        ("response_endpoint", "Response endpoint", "value"),
        ("potency", "IC50 / EC50 / potency", "value"),
        ("interval", "Interval", "value"),
        ("fit_model", "Fit model", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "omics_feature": [
        ("feature", "Feature", "value"),
        ("direction", "Direction", "value"),
        ("contrast", "Contrast", "value"),
        ("effect_size", "Effect size", "value"),
        ("significance", "P / FDR", "value"),
        ("thresholds", "Thresholds", "value"),
        ("multiple_testing", "Multiple testing", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "clinical_effect": [
        ("endpoint", "Endpoint", "value"),
        ("population", "Population", "value"),
        ("effect_measure", "Effect measure", "value"),
        ("estimate", "Point estimate", "value"),
        ("confidence_interval", "Confidence interval", "value"),
        ("p_value", "P value", "value"),
        ("reference_group", "Reference group", "value"),
        ("adjustment_model", "Adjustment model", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "image_observation": [
        ("sample", "Sample", "value"),
        ("modality", "Imaging modality", "value"),
        ("stain_or_channel", "Stain / channel", "value"),
        ("observation", "Image observation", "value"),
        ("scale_bar", "Scale bar", "value"),
        ("quantification", "Quantification", "value"),
        ("limitations", "Limitations", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "blot_lane": [
        ("lane", "Lane / group", "value"),
        ("target", "Target", "value"),
        ("molecular_weight", "Molecular weight", "value"),
        ("loading_control", "Loading control", "value"),
        ("control", "Control", "value"),
        ("band_observation", "Band observation", "value"),
        ("quantification", "Quantification", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "flow_population": [
        ("population", "Population", "value"),
        ("gating_hierarchy", "Gating hierarchy", "value"),
        ("markers", "Markers", "value"),
        ("denominator", "Parent gate / denominator", "value"),
        ("proportion_or_count", "Proportion / count", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "workflow_step": [
        ("step", "Step", "value"),
        ("input", "Input", "value"),
        ("operation", "Operation", "value"),
        ("parameters", "Key parameters", "value"),
        ("output", "Output", "value"),
        ("predecessors", "Predecessors", "predecessors"),
        ("branch", "Branch", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "mechanism_relation": [
        ("upstream", "Upstream entity", "text"),
        ("relation", "Relation", "text"),
        ("downstream", "Downstream entity", "text"),
        ("direction", "Direction", "direction"),
        ("evidence_nature", "Evidence nature", "nature"),
        ("confidence", "Record confidence", "confidence"),
    ],
    "specialized_table": [
        ("variable", "Variable", "value"),
        ("group", "Group", "value"),
        ("statistic", "Statistic", "value"),
        ("missingness", "Missingness", "value"),
        ("interval", "Interval", "value"),
        ("footnote_definition", "Footnote definition", "value"),
        ("confidence", "Record confidence", "confidence"),
    ],
}

TEMPLATE_COLUMNS = TEMPLATE_COLUMNS_ZH

SOURCE_KIND = {
    "paper_pdf": "论文 PDF",
    "figure_image": "原图",
    "caption": "图注",
    "results_text": "结果正文",
    "methods_text": "方法正文",
    "supplement": "补充材料",
    "text_excerpt": "文本摘录",
    "metadata_or_web": "公开网页/元数据",
    "user_note": "用户说明",
    "other": "其他来源",
}
STATUS_LABELS = {
    "consumed": "已使用",
    "partially_consumed": "部分使用",
    "not_consumed": "未使用",
    "unavailable": "不可用",
}
CONFIDENCE_LABELS = {"high": "高", "medium": "中", "low": "低", "unknown": "待定"}
NATURE_LABELS = {"observed": "图中可见", "reported": "作者报告", "depicted": "图示关系", "inferred": "基于证据推断"}
DIRECTION_LABELS = {"directed": "单向", "undirected": "无向", "bidirectional": "双向", "unknown": "方向未明"}
VISUAL_LABELS = {"completed": "已完成", "partial": "部分完成", "not_performed": "未执行", "not_possible": "无法执行"}
PRIORITY_LABELS = {"low": "一般", "medium": "中等", "high": "重要", "critical": "关键"}
RUN_STATUS = {"complete": "完整", "partial": "部分完成", "failed": "未完成"}
CONFLICT_KIND = {
    "source_disagreement": "来源不一致",
    "derived_value_mismatch": "派生值复算不一致",
    "unit_ambiguity": "单位含义不明确",
    "classification_ambiguity": "图型分类不明确",
    "other": "其他冲突",
}
RESOLUTION_LABELS = {
    "unresolved": "尚未解决",
    "source_precedence_applied": "已按来源优先级处理",
    "author_value_preserved": "保留作者报告值并注明限制",
    "not_evaluable": "目前无法判定",
}
CONDITION_ROLE = {
    "system": "实验系统",
    "population": "研究人群",
    "assay": "检测方法",
    "treatment": "处理",
    "dose": "剂量",
    "duration": "时间/暴露",
    "control": "对照",
    "normalization": "归一化",
    "protocol": "实验流程",
    "database": "数据库",
    "background_set": "背景集",
    "multiple_testing": "多重检验",
    "fixed_condition": "固定条件",
    "other": "其他条件",
}
DERIVED_COMPARISON = {"consistent": "复算一致", "conflict": "复算冲突", "not_evaluable": "无法复算"}
UNCERTAINTY_KIND = {
    "sd": "SD",
    "sem": "SEM",
    "ci": "置信区间",
    "credible_interval": "可信区间",
    "prediction_interval": "预测区间",
    "iqr": "IQR",
    "range": "范围",
    "whisker": "箱线图须线",
    "unknown": "类型未说明的不确定性",
}

SOURCE_KIND_EN = {
    "paper_pdf": "Paper PDF",
    "figure_image": "Original figure",
    "caption": "Figure caption",
    "results_text": "Results text",
    "methods_text": "Methods text",
    "supplement": "Supplementary material",
    "text_excerpt": "Text excerpt",
    "metadata_or_web": "Public webpage / metadata",
    "user_note": "User note",
    "other": "Other source",
}
STATUS_LABELS_EN = {
    "consumed": "Used",
    "partially_consumed": "Partially used",
    "not_consumed": "Not used",
    "unavailable": "Unavailable",
}
CONFIDENCE_LABELS_EN = {"high": "High", "medium": "Medium", "low": "Low", "unknown": "Pending"}
NATURE_LABELS_EN = {
    "observed": "Visible in the figure",
    "reported": "Reported by the authors",
    "depicted": "Depicted relation",
    "inferred": "Evidence-based inference",
}
DIRECTION_LABELS_EN = {"directed": "Directed", "undirected": "Undirected", "bidirectional": "Bidirectional", "unknown": "Direction unclear"}
VISUAL_LABELS_EN = {"completed": "Completed", "partial": "Partially completed", "not_performed": "Not performed", "not_possible": "Not possible"}
PRIORITY_LABELS_EN = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}
RUN_STATUS_EN = {"complete": "Complete", "partial": "Partially complete", "failed": "Incomplete"}
CONFLICT_KIND_EN = {
    "source_disagreement": "Source disagreement",
    "derived_value_mismatch": "Derived-value recalculation mismatch",
    "unit_ambiguity": "Ambiguous unit meaning",
    "classification_ambiguity": "Ambiguous figure classification",
    "other": "Other conflict",
}
RESOLUTION_LABELS_EN = {
    "unresolved": "Unresolved",
    "source_precedence_applied": "Source precedence applied",
    "author_value_preserved": "Author-reported value retained with a limitation",
    "not_evaluable": "Not currently evaluable",
}
CONDITION_ROLE_EN = {
    "system": "Experimental system",
    "population": "Study population",
    "assay": "Assay",
    "treatment": "Treatment",
    "dose": "Dose",
    "duration": "Time / exposure",
    "control": "Control",
    "normalization": "Normalization",
    "protocol": "Experimental workflow",
    "database": "Database",
    "background_set": "Background set",
    "multiple_testing": "Multiple testing",
    "fixed_condition": "Fixed condition",
    "other": "Other condition",
}
DERIVED_COMPARISON_EN = {"consistent": "Recalculation consistent", "conflict": "Recalculation conflict", "not_evaluable": "Cannot recalculate"}
UNCERTAINTY_KIND_EN = {
    "sd": "SD",
    "sem": "SEM",
    "ci": "confidence interval",
    "credible_interval": "credible interval",
    "prediction_interval": "prediction interval",
    "iqr": "IQR",
    "range": "range",
    "whisker": "box-plot whisker",
    "unknown": "uncertainty of unspecified type",
}

INTERNAL_ID_RE = re.compile(r"\b(?:run|src|act|ev|cov|conflict|panel|fig|rec|claim|cond|derived)-[A-Za-z0-9._:-]+\b", re.I)
HASH_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
MACHINE_FIELD_RE = re.compile(
    r"\b(?:field_paths?|run_id|source_id|activity_id|evidence_id|coverage_id|conflict_id|panel_id|"
    r"figure_id|record_id|claim_id|condition_id|derived_id|validation_state|"
    r"content_sha256|report_sha256|schema_passed|semantic_passed|report_passed)\b",
    re.I,
)
JSON_POINTER_RE = re.compile(r"/(?:run|paper|sources|activities|figures|panels|evidence_items|source_coverage|conflicts|review|validation)(?:/[^\s|,;，；。]*)?", re.I)
WINDOWS_PATH_RE = re.compile(r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\)[^\s|<>()]+")
POSIX_PRIVATE_PATH_RE = re.compile(r"(?<![\w:])/(?:Users|home|root|tmp|var|private|Volumes|mnt|opt|workspace|work)/[^\s|<>()]+", re.I)
URI_RE = re.compile(r"(?:[a-z][a-z0-9+.-]*)://[^\s|<>()]+", re.I)
DANGEROUS_QUERY_RE = re.compile(r"(?P<base>[^\s|?#]+)[?&](?:token|api[_-]?key|key|secret|signature|sig|auth|password)=[^\s|]+", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RAW_ENUM_TRANSLATIONS = {
    "partially_consumed": "部分使用",
    "not_consumed": "未使用",
    "not_recoverable": "无法可靠恢复",
    "not_applicable": "不适用",
    "not_performed": "未执行",
    "not_possible": "无法执行",
    "summary_only": "仅汇总",
    "single_source": "单一来源",
    "minor_conflict": "轻微冲突",
    "major_conflict": "重大冲突",
    "consumed": "已使用",
    "unavailable": "不可用",
    "observed": "图中可见",
    "reported": "作者报告",
    "depicted": "图示关系",
    "inferred": "基于证据推断",
}
RAW_ENUM_TRANSLATIONS_EN = {
    "partially_consumed": "partially used",
    "not_consumed": "not used",
    "not_recoverable": "not reliably recoverable",
    "not_applicable": "not applicable",
    "not_performed": "not performed",
    "not_possible": "not possible",
    "summary_only": "summary only",
    "single_source": "single source",
    "minor_conflict": "minor conflict",
    "major_conflict": "major conflict",
    "consumed": "used",
    "unavailable": "unavailable",
    "observed": "visible in the figure",
    "reported": "reported by the authors",
    "depicted": "depicted relation",
    "inferred": "evidence-based inference",
}


def report_language(data: dict[str, Any]) -> str:
    language = data.get("run", {}).get("report_language", "zh-CN")
    if language not in {"zh-CN", "en"}:
        raise ValueError(f"unsupported report language: {language}")
    return str(language)


def _tr(language: str, zh: str, en: str) -> str:
    return en if language == "en" else zh


def _template_columns(language: str) -> dict[str, list[tuple[str, str, str]]]:
    return TEMPLATE_COLUMNS_EN if language == "en" else TEMPLATE_COLUMNS_ZH


def _localized_map(language: str, zh: dict[str, str], en: dict[str, str]) -> dict[str, str]:
    return en if language == "en" else zh


def _basename(value: str, language: str = "zh-CN") -> str:
    trimmed = value.rstrip(".,;，；。)]}")
    parts = re.split(r"[\\/]", trimmed)
    return parts[-1] or _tr(language, "[本地文件]", "[local file]")


def _safe_uri_token(value: str, language: str = "zh-CN") -> str:
    trailing = ""
    while value and value[-1] in ".,;，；。)]}":
        trailing = value[-1] + trailing
        value = value[:-1]
    try:
        parsed = urlsplit(value)
        if parsed.scheme.casefold() == "file":
            return _basename(parsed.path, language) + trailing
        host = parsed.hostname or _tr(language, "公开来源", "public source")
        if parsed.port:
            host += f":{parsed.port}"
        safe = urlunsplit((parsed.scheme.casefold(), host, parsed.path, "", ""))
        return safe + trailing
    except (TypeError, ValueError):
        return _tr(language, "[公开链接已净化]", "[public link sanitized]") + trailing


def sanitize_public_text(value: Any, language: str = "zh-CN") -> str:
    """Return one-line public text with paths, IDs, hashes and URI secrets removed."""
    if value is None:
        return ""
    text = CONTROL_RE.sub(" ", str(value)).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = URI_RE.sub(lambda match: _safe_uri_token(match.group(0), language), text)
    text = DANGEROUS_QUERY_RE.sub(lambda match: match.group("base"), text)
    text = WINDOWS_PATH_RE.sub(lambda match: _basename(match.group(0), language), text)
    text = POSIX_PRIVATE_PATH_RE.sub(lambda match: _basename(match.group(0), language), text)
    text = JSON_POINTER_RE.sub(_tr(language, "[内部路径已隐藏]", "[internal path hidden]"), text)
    text = MACHINE_FIELD_RE.sub(_tr(language, "[机器字段已隐藏]", "[machine field hidden]"), text)
    text = INTERNAL_ID_RE.sub(_tr(language, "[内部标识已隐藏]", "[internal identifier hidden]"), text)
    text = HASH_RE.sub(_tr(language, "[摘要已隐藏]", "[digest hidden]"), text)
    translations = RAW_ENUM_TRANSLATIONS_EN if language == "en" else RAW_ENUM_TRANSLATIONS
    for raw, translated in sorted(translations.items(), key=lambda item: -len(item[0])):
        text = re.sub(rf"\b{re.escape(raw)}\b", translated, text, flags=re.I)
    return text


def _md(value: Any, language: str = "zh-CN") -> str:
    # Markdown only receives values that have already passed through public_projection.
    # Do not sanitize twice: enum localization such as "Reported by the authors"
    # must remain stable and deterministic.
    text = str(value).strip() if value is not None else ""
    text = text or "—"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def markdown_table(headers: list[str], rows: list[list[str]], language: str = "zh-CN") -> list[str]:
    lines = ["| " + " | ".join(_md(item, language) for item in headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(_md(item, language) for item in row) + " |" for row in rows)
    return lines


def _format_scalar(value: Any, language: str = "zh-CN") -> str:
    if isinstance(value, bool):
        return _tr(language, "是" if value else "否", "Yes" if value else "No")
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, list):
        parts = [_format_scalar(item, language) for item in value]
        return "–".join(parts) if len(parts) == 2 else _tr(language, "；", "; ").join(parts)
    return sanitize_public_text(value, language)


def format_data_value(item: dict[str, Any] | None, language: str = "zh-CN") -> str:
    item = item or {}
    state = item.get("state")
    basis = sanitize_public_text(item.get("basis"), language)
    if state == "unknown":
        return _tr(language, "作者未说明", "Not reported by the authors") + (f"（{basis}）" if language == "zh-CN" and basis else f" ({basis})" if basis else "")
    if state == "not_recoverable":
        return _tr(language, "无法可靠恢复", "Not reliably recoverable") + (f"（{basis}）" if language == "zh-CN" and basis else f" ({basis})" if basis else "")
    if state == "not_applicable":
        return _tr(language, "不适用", "Not applicable")
    if state == "conflicted":
        return _tr(language, "来源冲突，暂不合并", "Conflicting sources; not merged") + (f"（{basis}）" if language == "zh-CN" and basis else f" ({basis})" if basis else "")
    if state != "present":
        return _tr(language, "状态待核验", "Status pending verification")
    text = _format_scalar(item.get("value"), language)
    unit = sanitize_public_text(item.get("unit"), language)
    if unit:
        text += f"（{unit}）" if language == "zh-CN" and ("ci" in unit.casefold() or "区间" in unit) else f" ({unit})" if language == "en" and "ci" in unit.casefold() else f" {unit}"
    precision = item.get("precision")
    if precision == "approximate":
        tolerance = item.get("tolerance")
        detail = _tr(language, f"估读容差 ±{_format_scalar(tolerance, language)}", f"visual-estimation tolerance ±{_format_scalar(tolerance, language)}")
        if unit and "ci" not in unit.casefold():
            detail += f" {unit}"
        if basis:
            detail += _tr(language, f"；依据：{basis}", f"; basis: {basis}")
        text = _tr(language, f"约 {text}（{detail}）", f"approximately {text} ({detail})")
    elif precision == "bounded" and basis:
        text += _tr(language, f"（边界依据：{basis}）", f" (bound basis: {basis})")
    uncertainty = item.get("scientific_uncertainty")
    if isinstance(uncertainty, dict):
        kind = _localized_map(language, UNCERTAINTY_KIND, UNCERTAINTY_KIND_EN).get(
            uncertainty.get("kind"), _tr(language, "不确定性", "uncertainty")
        )
        level = uncertainty.get("level")
        if isinstance(level, (int, float)):
            kind += f" {level * 100:g}%"
        lower, upper = uncertainty.get("lower"), uncertainty.get("upper")
        interval = ""
        if lower is not None or upper is not None:
            interval = _tr(language, f"：{_format_scalar(lower, language)}–{_format_scalar(upper, language)}", f": {_format_scalar(lower, language)}–{_format_scalar(upper, language)}")
        definition = sanitize_public_text(uncertainty.get("definition"), language)
        applies = sanitize_public_text(uncertainty.get("applies_to"), language)
        detail = f"{kind}{interval}"
        if definition:
            detail += _tr(language, f"；定义：{definition}", f"; definition: {definition}")
        if applies:
            detail += _tr(language, f"；适用于：{applies}", f"; applies to: {applies}")
        text += _tr(language, f"（{detail}）", f" ({detail})")
    return text or _tr(language, "未记录", "Not recorded")


def format_confidence(item: dict[str, Any] | None, language: str = "zh-CN") -> str:
    item = item or {}
    level = _localized_map(language, CONFIDENCE_LABELS, CONFIDENCE_LABELS_EN).get(item.get("level"), _tr(language, "待定", "Pending"))
    score = item.get("score")
    rationale = sanitize_public_text(item.get("rationale"), language)
    details: list[str] = []
    if isinstance(score, (int, float)):
        details.append(f"{score:.2f}")
    if rationale:
        details.append(rationale)
    if not details:
        return level
    return level + (_tr(language, f"（{'；'.join(details)}）", f" ({'; '.join(details)})"))


def _column_is_applicable(records: list[dict[str, Any]], field: str, kind: str) -> bool:
    if kind != "value":
        return True
    values = [record.get(field) for record in records]
    return not values or any(not isinstance(value, dict) or value.get("state") != "not_applicable" for value in values)


def project_result_table(template: str, records: list[dict[str, Any]], language: str = "zh-CN") -> tuple[list[str], list[list[str]]]:
    specs = _template_columns(language).get(template)
    if specs is None:
        raise ValueError(_tr(language, f"未知结果模板: {template}", f"unknown result template: {template}"))
    active = [spec for spec in specs if _column_is_applicable(records, spec[0], spec[2])]
    step_names = {
        str(record.get("record_id")): format_data_value(record.get("step"), language)
        for record in records
        if template == "workflow_step"
    }
    rows: list[list[str]] = []
    for record in records:
        row: list[str] = []
        for field, _header, kind in active:
            value = record.get(field)
            if kind == "value":
                row.append(format_data_value(value, language))
            elif kind == "confidence":
                row.append(format_confidence(value, language))
            elif kind == "predecessors":
                names = [step_names.get(str(item), _tr(language, "未解析前置步骤", "Unresolved predecessor")) for item in (value or [])]
                row.append(_tr(language, "；", "; ").join(names) if names else _tr(language, "起点", "Start"))
            elif kind == "direction":
                row.append(_localized_map(language, DIRECTION_LABELS, DIRECTION_LABELS_EN).get(value, _tr(language, "方向待核验", "Direction pending verification")))
            elif kind == "nature":
                row.append(_localized_map(language, NATURE_LABELS, NATURE_LABELS_EN).get(value, _tr(language, "证据性质待核验", "Evidence nature pending verification")))
            else:
                row.append(sanitize_public_text(value, language) or _tr(language, "未记录", "Not recorded"))
        rows.append(row)
    return [header for _field, header, _kind in active], rows


def _safe_source_label(source: dict[str, Any], language: str = "zh-CN") -> str:
    kind = _localized_map(language, SOURCE_KIND, SOURCE_KIND_EN).get(source.get("kind"), _tr(language, "来源", "Source"))
    locator = source.get("locator", {})
    citation = sanitize_public_text(locator.get("citation"), language)
    if citation.startswith(_tr(language, "[内部", "[internal")) or not citation:
        uri = locator.get("uri")
        path = locator.get("path")
        citation = _safe_uri_token(uri, language) if isinstance(uri, str) and uri else sanitize_public_text(_basename(path, language), language) if isinstance(path, str) and path else ""
    detail = sanitize_public_text(locator.get("detail"), language)
    extras = _tr(language, "；", "; ").join(item for item in (citation, detail) if item)
    if not extras:
        return kind
    return _tr(language, f"{kind}（{extras}）", f"{kind} ({extras})")


def _bbox_text(bbox: dict[str, Any] | None, language: str = "zh-CN") -> str:
    if not bbox:
        return _tr(language, "未记录页内区域", "Within-page region not recorded")
    x0 = float(bbox.get("x", 0)) * 100
    y0 = float(bbox.get("y", 0)) * 100
    x1 = (float(bbox.get("x", 0)) + float(bbox.get("width", 0))) * 100
    y1 = (float(bbox.get("y", 0)) + float(bbox.get("height", 0))) * 100
    return _tr(
        language,
        f"页内横向 {x0:.1f}%–{x1:.1f}%，纵向 {y0:.1f}%–{y1:.1f}%",
        f"within-page horizontal {x0:.1f}%–{x1:.1f}%, vertical {y0:.1f}%–{y1:.1f}%",
    )


def _scope_text(scope: dict[str, Any], language: str = "zh-CN") -> str:
    mode = scope.get("mode")
    if mode == "full":
        count = scope.get("total_count")
        if language == "en":
            count_text = f"; {count} {'record' if count == 1 else 'records'} in total" if count is not None else ""
            return f"Full display{count_text}."
        return f"完整展示{f'，共 {count} 条记录' if count is not None else ''}。"
    displayed = scope.get("displayed_count")
    total = scope.get("total_count")
    rule = sanitize_public_text(scope.get("selection_rule"), language) or _tr(language, "筛选规则未说明", "Selection rule not reported")
    if language == "en":
        label = "Selected display" if mode == "selected" else "Summary display"
        return f"{label}: showing {displayed}/{total} records; selection or summary rule: {rule}."
    label = "选取展示" if mode == "selected" else "汇总展示"
    return f"{label}：展示 {displayed}/{total} 条记录；筛选或汇总规则：{rule}。"


def _missing_items(panel: dict[str, Any], language: str = "zh-CN") -> list[str]:
    template = panel.get("results", {}).get("template")
    labels = {field: header for field, header, _kind in _template_columns(language).get(template, [])}
    items: list[str] = []
    for record in panel.get("results", {}).get("records", []):
        for field, header in labels.items():
            value = record.get(field)
            if isinstance(value, dict) and value.get("state") in {"unknown", "not_recoverable", "conflicted"}:
                text = _tr(language, f"{header}：{format_data_value(value, language)}", f"{header}: {format_data_value(value, language)}")
                if text not in items:
                    items.append(text)
    for condition in panel.get("conditions", []):
        value = condition.get("value", {})
        if value.get("state") in {"unknown", "not_recoverable", "conflicted"}:
            factor = sanitize_public_text(condition.get("factor"), language) or _localized_map(language, CONDITION_ROLE, CONDITION_ROLE_EN).get(condition.get("role"), _tr(language, "实验条件", "Experimental condition"))
            text = _tr(language, f"{factor}：{format_data_value(value, language)}", f"{factor}: {format_data_value(value, language)}")
            if text not in items:
                items.append(text)
    return items


def _condition_lines(panel: dict[str, Any], language: str = "zh-CN") -> list[str]:
    lines: list[str] = []
    for item in panel.get("conditions", []):
        value = item.get("value", {})
        if value.get("state") == "not_applicable":
            continue
        role = _localized_map(language, CONDITION_ROLE, CONDITION_ROLE_EN).get(item.get("role"), _tr(language, "实验条件", "Experimental condition"))
        factor = sanitize_public_text(item.get("factor"), language) or role
        lines.append(_tr(language, f"{role}（{factor}）：{format_data_value(value, language)}", f"{role} ({factor}): {format_data_value(value, language)}"))
    return lines


def _claim_lines(panel: dict[str, Any], language: str = "zh-CN") -> list[str]:
    lines: list[str] = []
    for claim in panel.get("claims", []):
        prefix = _localized_map(language, NATURE_LABELS, NATURE_LABELS_EN).get(claim.get("nature"), _tr(language, "证据性质待核验", "Evidence nature pending verification"))
        text = sanitize_public_text(claim.get("text"), language) or _tr(language, "未记录结论", "Conclusion not recorded")
        limitation = sanitize_public_text(claim.get("limitation"), language)
        line = _tr(language, f"{prefix}：{text}", f"{prefix}: {text}")
        if limitation:
            line += _tr(language, f"；边界：{limitation}", f"; boundary: {limitation}")
        lines.append(line)
    return lines


def _derived_lines(panel: dict[str, Any], language: str = "zh-CN") -> list[str]:
    lines: list[str] = []
    for item in panel.get("derived_values", []):
        label = sanitize_public_text(item.get("label"), language) or _tr(language, "派生指标", "Derived metric")
        reported = item.get("reported")
        recalculated = item.get("recalculated")
        comparison = _localized_map(language, DERIVED_COMPARISON, DERIVED_COMPARISON_EN).get(item.get("comparison"), _tr(language, "复算状态待核验", "Recalculation status pending verification"))
        if language == "en":
            line = f"{label}: author value {reported if reported is not None else 'not reported'}; recalculated value {recalculated}; {comparison}"
        else:
            line = f"{label}：作者值 {reported if reported is not None else '未报告'}；复算值 {recalculated}；{comparison}"
        action = sanitize_public_text(item.get("review_action"), language)
        if action:
            line += _tr(language, f"；建议：{action}", f"; recommendation: {action}")
        lines.append(line)
    return lines


def public_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Build the only object the Markdown renderer is allowed to consume."""
    language = report_language(data)
    sources = {source.get("source_id"): source for source in data.get("sources", [])}
    source_labels = {key: _safe_source_label(value, language) for key, value in sources.items()}
    figures = {figure.get("figure_id"): figure for figure in data.get("figures", [])}
    panels: list[dict[str, Any]] = []
    for index, panel in enumerate(data.get("panels", []), start=1):
        figure = figures.get(panel.get("figure_id"), {})
        figure_label = sanitize_public_text(figure.get("label"), language) or _tr(language, f"图 {index}", f"Figure {index}")
        location = panel.get("location", {})
        panel_label = sanitize_public_text(location.get("panel_label"), language)
        descriptor = _tr(language, f"{figure_label}，面板 {panel_label}", f"{figure_label}, panel {panel_label}") if panel_label else figure_label
        title = _tr(language, f"面板 {index}｜{descriptor}", f"Panel {index} — {descriptor}")
        template = panel.get("results", {}).get("template")
        records = panel.get("results", {}).get("records", [])
        headers, rows = project_result_table(template, records, language)
        review = panel.get("review", {})
        suggestions = [
            {
                "priority": _localized_map(language, PRIORITY_LABELS, PRIORITY_LABELS_EN).get(item.get("priority"), _tr(language, "待定", "Pending")),
                "reason": sanitize_public_text(item.get("reason"), language),
                "action": sanitize_public_text(item.get("action"), language),
            }
            for item in review.get("suggestions", [])
        ]
        panels.append({
            "ordinal": index,
            "short_name": _tr(language, f"面板 {index}", f"Panel {index}"),
            "title": title,
            "template": template,
            "headers": headers,
            "rows": rows,
            "objective": sanitize_public_text(panel.get("objective"), language),
            "classification": (
                _tr(language, "已确认；", "Resolved; ")
                if panel.get("classification", {}).get("status") == "resolved"
                else _tr(language, "暂定，需复核；", "Provisional; review required; ")
            ) + sanitize_public_text(panel.get("classification", {}).get("rationale"), language),
            "classification_provisional": panel.get("classification", {}).get("status") != "resolved",
            "conditions": _condition_lines(panel, language),
            "claims": _claim_lines(panel, language),
            "scope": _scope_text(panel.get("reporting_scope", {}), language),
            "scope_mode": panel.get("reporting_scope", {}).get("mode"),
            "confidence": format_confidence(panel.get("confidence"), language),
            "visual_status": _localized_map(language, VISUAL_LABELS, VISUAL_LABELS_EN).get(panel.get("visual_check", {}).get("status"), _tr(language, "待核验", "Pending verification")),
            "visual_limit": sanitize_public_text(panel.get("visual_check", {}).get("limitations"), language),
            "missing": _missing_items(panel, language),
            "derived": _derived_lines(panel, language),
            "review_required": bool(review.get("required")),
            "review_suggestions": suggestions,
            "location": [
                _tr(language, f"面板 {index}", f"Panel {index}"),
                figure_label,
                str(location.get("pdf_page")) if location.get("pdf_page") is not None else _tr(language, "未记录", "Not recorded"),
                sanitize_public_text(location.get("printed_page"), language) or _tr(language, "未记录", "Not recorded"),
                panel_label or _tr(language, "未标注", "Unlabeled"),
                _bbox_text(location.get("bbox"), language),
                sanitize_public_text(location.get("locator_note"), language) or _tr(language, "未补充定位说明", "No additional locator note"),
                source_labels.get(location.get("source_id"), _tr(language, "来源待核验", "Source pending verification")),
            ],
            "internal_index": index - 1,
        })

    conflicts_by_panel: dict[int, list[dict[str, str]]] = {index: [] for index in range(len(panels))}
    global_conflicts: list[dict[str, str]] = []
    for conflict in data.get("conflicts", []):
        projected = {
            "kind": _localized_map(language, CONFLICT_KIND, CONFLICT_KIND_EN).get(conflict.get("kind"), _tr(language, "冲突", "Conflict")),
            "statements": _tr(language, "；", "; ").join(sanitize_public_text(item.get("statement"), language) for item in conflict.get("statements", [])),
            "resolution": _localized_map(language, RESOLUTION_LABELS, RESOLUTION_LABELS_EN).get(conflict.get("resolution"), _tr(language, "处置待核验", "Resolution pending verification")),
            "action": sanitize_public_text(conflict.get("review_action"), language),
        }
        linked: set[int] = set()
        for pointer in conflict.get("field_paths", []):
            match = re.match(r"^/panels/(\d+)(?:/|$)", str(pointer))
            if match and int(match.group(1)) in conflicts_by_panel:
                linked.add(int(match.group(1)))
        if linked:
            for panel_index in linked:
                conflicts_by_panel[panel_index].append(projected)
        else:
            global_conflicts.append(projected)
    for panel in panels:
        panel["conflicts"] = conflicts_by_panel[panel.pop("internal_index")]

    coverage = []
    for item in data.get("source_coverage", []):
        status = item.get("status")
        used = sanitize_public_text(item.get("fact_summary"), language) if status in {"consumed", "partially_consumed"} else _tr(language, "未纳入结果", "Not included in results")
        reason = sanitize_public_text(item.get("reason"), language)
        coverage.append([
            source_labels.get(item.get("source_id"), _tr(language, "来源待核验", "Source pending verification")),
            used or _tr(language, "未说明", "Not reported"),
            sanitize_public_text(item.get("purpose"), language) or _tr(language, "用途待核验", "Purpose pending verification"),
            _localized_map(language, STATUS_LABELS, STATUS_LABELS_EN).get(status, _tr(language, "状态待核验", "Status pending verification")),
            reason or (_tr(language, "无已登记限制", "No registered limitation") if status == "consumed" else _tr(language, "原因待核验", "Reason pending verification")),
        ])

    root_review = data.get("review", {})
    global_review = [
        {
            "priority": _localized_map(language, PRIORITY_LABELS, PRIORITY_LABELS_EN).get(item.get("priority"), _tr(language, "待定", "Pending")),
            "reason": sanitize_public_text(item.get("reason"), language),
            "action": sanitize_public_text(item.get("action"), language),
        }
        for item in root_review.get("suggestions", [])
    ]
    panel_review_keys = {
        (item["priority"], item["reason"], item["action"])
        for panel in panels
        for item in panel["review_suggestions"]
    }
    global_review = [
        item for item in global_review
        if (item["priority"], item["reason"], item["action"]) not in panel_review_keys
    ]
    paper = data.get("paper", {})
    run = data.get("run", {})
    return {
        "language": language,
        "title": sanitize_public_text(paper.get("title"), language) or _tr(language, "题名未提供", "Title not provided"),
        "doi": sanitize_public_text(paper.get("doi"), language),
        "run_status": _localized_map(language, RUN_STATUS, RUN_STATUS_EN).get(run.get("status"), _tr(language, "状态待核验", "Status pending verification")),
        "panels": panels,
        "coverage": coverage,
        "global_conflicts": global_conflicts,
        "global_limitations": [sanitize_public_text(item, language) for item in run.get("limitations", []) if sanitize_public_text(item, language)],
        "global_review_required": bool(global_review),
        "global_review": global_review,
    }


def _render_review_rows(items: list[dict[str, str]], language: str = "zh-CN") -> list[list[str]]:
    return [
        [
            item.get("priority", _tr(language, "待定", "Pending")),
            item.get("reason", _tr(language, "原因待核验", "Reason pending verification")),
            item.get("action", _tr(language, "行动待核验", "Action pending verification")),
        ]
        for item in items
    ]


def render(data: dict[str, Any]) -> str:
    projection = public_projection(data)
    language = projection["language"]
    profile = load_json(REPORT_PROFILE_PATH)
    language_profile = profile["languages"][language]
    sections = language_profile["required_sections"]
    structured_section, interpretation_section, location_section, coverage_section, uncertainty_section, review_section = sections
    if language == "en":
        report_title = "Biomedical Paper Figure Evidence Report"
        paper_label = "Paper"
        extraction_label = "Extraction status"
        scope_label = "Reporting scope"
        objective_label = "Research objective / use"
        classification_label = "Figure classification"
        context_label = "Experimental and statistical context"
        no_context = "No applicable recovered condition is available for this template."
        confidence_label = "Panel confidence"
        high_dimensional_label = "High-dimensional result scope"
        visual_label = "Original-figure visual verification"
        limit_label = "limitation"
        classification_uncertainty_label = "Figure-classification uncertainty"
        missing_label = "Missing or unrecoverable"
        no_missing = "No key missing item affecting the current interpretation is registered."
        derived_label = "Derived-value audit"
        resolution_label = "resolution"
        review_action_label = "review action"
        no_conflict = "No conflict at the panel level is registered within the included sources."
        global_limitations_heading = "Global Limitations"
        review_required_text = "Review status: human review required."
        review_not_required_text = "Review status: no mandatory human-review item is currently registered; spot-check the original figure before critical quantitative pooling or clinical use."
        global_review_heading = "Global Review"
    else:
        report_title = "生物医学论文图表证据报告"
        paper_label = "论文"
        extraction_label = "抽取状态"
        scope_label = "呈现范围"
        objective_label = "研究目标/用途"
        classification_label = "图型分类"
        context_label = "实验与统计语境"
        no_context = "当前模板无已恢复的适用条件。"
        confidence_label = "面板置信度"
        high_dimensional_label = "高维结果范围"
        visual_label = "原图视觉核验"
        limit_label = "限制"
        classification_uncertainty_label = "图型分类不确定性"
        missing_label = "缺失或不可恢复"
        no_missing = "未登记影响当前解释的关键缺失项。"
        derived_label = "派生值审计"
        resolution_label = "处置"
        review_action_label = "复核动作"
        no_conflict = "在已纳入来源范围内未登记面板级冲突。"
        global_limitations_heading = "全局限制"
        review_required_text = "复核状态：需要人工复核。"
        review_not_required_text = "复核状态：当前无强制人工复核项；用于关键定量合并或临床判断前仍建议抽查原图。"
        global_review_heading = "全局复核"
    lines = [
        f"# {report_title}",
        "",
        _tr(language, f"- {paper_label}：{_md(projection['title'], language)}", f"- {paper_label}: {_md(projection['title'], language)}"),
    ]
    if projection["doi"]:
        lines.append(_tr(language, f"- DOI：{_md(projection['doi'], language)}", f"- DOI: {_md(projection['doi'], language)}"))
    lines.extend([
        _tr(language, f"- {extraction_label}：{_md(projection['run_status'], language)}", f"- {extraction_label}: {_md(projection['run_status'], language)}"),
        "",
        f"## {structured_section}",
        "",
    ])
    for panel in projection["panels"]:
        lines.extend([f"### {_md(panel['title'], language)}", ""])
        lines.extend(markdown_table(panel["headers"], panel["rows"], language))
        lines.extend(["", _tr(language, f"> {scope_label}：{_md(panel['scope'], language)}", f"> {scope_label}: {_md(panel['scope'], language)}"), ""])

    lines.extend([f"## {interpretation_section}", ""])
    for panel in projection["panels"]:
        lines.extend([
            f"### {_md(panel['title'], language)}",
            "",
            _tr(language, f"- {objective_label}：{_md(panel['objective'], language)}", f"- {objective_label}: {_md(panel['objective'], language)}"),
        ])
        lines.append(_tr(language, f"- {classification_label}：{_md(panel['classification'], language)}", f"- {classification_label}: {_md(panel['classification'], language)}"))
        if panel["conditions"]:
            joined = _tr(language, "；", "; ").join(panel["conditions"])
            lines.append(_tr(language, f"- {context_label}：{_md(joined, language)}", f"- {context_label}: {_md(joined, language)}"))
        else:
            lines.append(_tr(language, f"- {context_label}：{no_context}", f"- {context_label}: {no_context}"))
        for claim in panel["claims"]:
            lines.append(f"- {_md(claim, language)}")
        lines.append(_tr(language, f"- {confidence_label}：{_md(panel['confidence'], language)}", f"- {confidence_label}: {_md(panel['confidence'], language)}"))
        if panel["scope_mode"] in {"selected", "summary_only"}:
            lines.append(_tr(language, f"- {high_dimensional_label}：{_md(panel['scope'], language)}", f"- {high_dimensional_label}: {_md(panel['scope'], language)}"))
        lines.append("")

    lines.extend([
        f"## {location_section}",
        "",
    ])
    lines.extend(markdown_table(language_profile["location_table"]["columns"], [], language))
    for panel in projection["panels"]:
        lines.append("| " + " | ".join(_md(item, language) for item in panel["location"]) + " |")

    lines.extend(["", f"## {coverage_section}", ""])
    lines.extend(markdown_table(language_profile["source_table"]["columns"], projection["coverage"], language))

    lines.extend(["", f"## {uncertainty_section}", ""])
    for panel in projection["panels"]:
        confidence_line = _tr(language, f"- {confidence_label}：{_md(panel['confidence'], language)}", f"- {confidence_label}: {_md(panel['confidence'], language)}")
        lines.extend([f"### {_md(panel['title'], language)}", "", confidence_line])
        visual = _tr(language, f"{visual_label}：{panel['visual_status']}", f"{visual_label}: {panel['visual_status']}")
        if panel["visual_limit"]:
            visual += _tr(language, f"；{limit_label}：{panel['visual_limit']}", f"; {limit_label}: {panel['visual_limit']}")
        lines.append(f"- {_md(visual, language)}")
        if panel["classification_provisional"]:
            lines.append(_tr(language, f"- {classification_uncertainty_label}：{_md(panel['classification'], language)}", f"- {classification_uncertainty_label}: {_md(panel['classification'], language)}"))
        if panel["missing"]:
            for item in panel["missing"]:
                lines.append(_tr(language, f"- {missing_label}：{_md(item, language)}", f"- {missing_label}: {_md(item, language)}"))
        else:
            lines.append(_tr(language, f"- {missing_label}：{no_missing}", f"- {missing_label}: {no_missing}"))
        for item in panel["derived"]:
            lines.append(_tr(language, f"- {derived_label}：{_md(item, language)}", f"- {derived_label}: {_md(item, language)}"))
        if panel["conflicts"]:
            for conflict in panel["conflicts"]:
                if language == "en":
                    lines.append(
                        f"- {_md(conflict['kind'], language)}: {_md(conflict['statements'], language)}; "
                        f"{resolution_label}: {_md(conflict['resolution'], language)}; {review_action_label}: {_md(conflict['action'], language)}."
                    )
                else:
                    lines.append(
                        f"- {_md(conflict['kind'], language)}：{_md(conflict['statements'], language)}；"
                        f"{resolution_label}：{_md(conflict['resolution'], language)}；{review_action_label}：{_md(conflict['action'], language)}。"
                    )
        else:
            lines.append(_tr(language, f"- 来源冲突：{no_conflict}", f"- Source conflict: {no_conflict}"))
        lines.append("")
    if projection["global_limitations"] or projection["global_conflicts"]:
        lines.extend([f"### {global_limitations_heading}", ""])
        for limitation in projection["global_limitations"]:
            lines.append(f"- {_md(limitation, language)}")
        for conflict in projection["global_conflicts"]:
            if language == "en":
                lines.append(
                    f"- {_md(conflict['kind'], language)}: {_md(conflict['statements'], language)}; "
                    f"{resolution_label}: {_md(conflict['resolution'], language)}; {review_action_label}: {_md(conflict['action'], language)}."
                )
            else:
                lines.append(
                    f"- {_md(conflict['kind'], language)}：{_md(conflict['statements'], language)}；"
                    f"{resolution_label}：{_md(conflict['resolution'], language)}；{review_action_label}：{_md(conflict['action'], language)}。"
                )
        lines.append("")

    lines.extend([f"## {review_section}", ""])
    for panel in projection["panels"]:
        lines.extend([f"### {_md(panel['title'], language)}", ""])
        if panel["review_required"]:
            lines.append(f"- {review_required_text}")
            lines.append("")
            lines.extend(markdown_table(language_profile["review_table"]["columns"], _render_review_rows(panel["review_suggestions"], language), language))
        else:
            lines.append(f"- {review_not_required_text}")
        lines.append("")
    if projection["global_review_required"]:
        lines.extend([f"### {global_review_heading}", ""])
        lines.extend(markdown_table(language_profile["review_table"]["columns"], _render_review_rows(projection["global_review"], language), language))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        data = load_json(args.evidence)
        report = render(data)
        atomic_write_text(args.report, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"passed": True, "report": str(args.report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
