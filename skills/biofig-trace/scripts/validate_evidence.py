"""Validate the v3 JSON Schema and cross-field scientific evidence invariants."""

from __future__ import annotations

import argparse
import ast
import json
import math
import operator
from pathlib import Path
from typing import Any, Iterable

from common import SCHEMA_ROOT, content_digest, duplicate_values, load_json, pointer_get


SCHEMA_PATH = SCHEMA_ROOT / "evidence_schema_v3.json"
PRIORITY = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
ALLOWED_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _json_path(parts: Iterable[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def schema_errors(data: Any, schema_path: str | Path = SCHEMA_PATH) -> list[dict[str, str]]:
    schema = load_json(schema_path)
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        from schema_engine import validate

        return [_error("SCHEMA", item["path"], item["message"]) for item in validate(data, schema)]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        _error("SCHEMA", _json_path(item.absolute_path), item.message)
        for item in sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    ]


def _refs(errors: list[dict[str, str]], refs: Iterable[str], known: set[str], path: str, kind: str) -> None:
    for ref in refs:
        if ref not in known:
            errors.append(_error("BAD_REFERENCE", path, f"无法解析的 {kind}: {ref}"))


def _walk_data_values(value: Any, path: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if {"value", "unit", "state", "precision", "tolerance", "basis", "evidence_ids"}.issubset(value):
            yield path, value
        for key, child in value.items():
            yield from _walk_data_values(child, f"{path}/{key}" if path else f"/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_data_values(child, f"{path}/{index}" if path else f"/{index}")


def _walk_bboxes(value: Any, path: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if value.get("coordinate_system") == "normalized_page" and {"x", "y", "width", "height"}.issubset(value):
            yield path, value
        for key, child in value.items():
            yield from _walk_bboxes(child, f"{path}/{key}" if path else f"/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_bboxes(child, f"{path}/{index}" if path else f"/{index}")


def _safe_formula(expression: str, inputs: list[float]) -> float:
    names = {f"x{index}": float(value) for index, value in enumerate(inputs)}

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_BINARY:
            return float(ALLOWED_BINARY[type(node.op)](evaluate(node.left), evaluate(node.right)))
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_UNARY:
            return float(ALLOWED_UNARY[type(node.op)](evaluate(node.operand)))
        raise ValueError("公式仅允许 x0、x1…、数值、括号和 + - * / **")

    tree = ast.parse(expression, mode="eval")
    result = evaluate(tree)
    if not math.isfinite(result):
        raise ValueError("公式结果不是有限数")
    return result


def _confidence(errors: list[dict[str, str]], item: dict[str, Any], path: str) -> None:
    level, score = item.get("level"), item.get("score")
    if level == "unknown" and score is not None:
        errors.append(_error("CONFIDENCE_SCALE", path, "unknown confidence 必须使用 null score"))
    if level != "unknown" and score is None:
        errors.append(_error("CONFIDENCE_SCALE", path, "已分级 confidence 必须提供 0–1 score"))
    if isinstance(score, (int, float)):
        expected = "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
        if level != expected:
            errors.append(_error("CONFIDENCE_SCALE", path, f"score={score} 应映射为 {expected}"))


def semantic_errors(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if data.get("run", {}).get("status") == "failed":
        errors.append(
            _error(
                "RUN_FAILED",
                "/run/status",
                "失败运行只能写入独立 failure.json，不得发布为 evidence.json",
            )
        )
    if not isinstance(data, dict):
        return [_error("TYPE", "$", "顶层必须是对象")]

    sources = data.get("sources", [])
    activities = data.get("activities", [])
    figures = data.get("figures", [])
    panels = data.get("panels", [])
    evidence_items = data.get("evidence_items", [])
    source_ids = {item.get("source_id") for item in sources}
    figure_ids = {item.get("figure_id") for item in figures}
    panel_ids = {item.get("panel_id") for item in panels}
    evidence_ids = {item.get("evidence_id") for item in evidence_items}
    activity_ids = {item.get("activity_id") for item in activities}

    id_groups = {
        "source_id": [item.get("source_id") for item in sources],
        "figure_id": [item.get("figure_id") for item in figures],
        "panel_id": [item.get("panel_id") for item in panels],
        "evidence_id": [item.get("evidence_id") for item in evidence_items],
        "activity_id": [item.get("activity_id") for item in activities],
        "coverage_id": [item.get("coverage_id") for item in data.get("source_coverage", [])],
        "conflict_id": [item.get("conflict_id") for item in data.get("conflicts", [])],
    }
    for label, values in id_groups.items():
        for duplicate in duplicate_values(str(value) for value in values if value is not None):
            errors.append(_error("DUPLICATE_ID", "$", f"重复 {label}: {duplicate}"))

    source_by_id = {item.get("source_id"): item for item in sources}
    evidence_by_id = {item.get("evidence_id"): item for item in evidence_items}

    for index, source in enumerate(sources):
        inspection = source.get("visual_inspection", {})
        _confidence(errors, inspection.get("confidence", {}), f"/sources/{index}/visual_inspection/confidence") if "confidence" in inspection else None
        if source.get("availability") == "available" and not source.get("locator", {}).get("path") and not source.get("locator", {}).get("uri"):
            errors.append(_error("SOURCE_LOCATOR", f"/sources/{index}/locator", "可用来源必须提供 path 或 uri"))
        if source.get("availability") != "available" and inspection.get("status") == "completed":
            errors.append(_error("VISUAL_ACCESS", f"/sources/{index}/visual_inspection", "不可用来源不能标记为已完成视觉核验"))
        parent = source.get("parent_source_id")
        activity = source.get("generated_by_activity_id")
        if parent is not None and parent not in source_ids:
            errors.append(_error("BAD_REFERENCE", f"/sources/{index}/parent_source_id", "parent_source_id 不存在"))
        if activity is not None and activity not in activity_ids:
            errors.append(_error("BAD_REFERENCE", f"/sources/{index}/generated_by_activity_id", "generated_by_activity_id 不存在"))

    for index, activity in enumerate(activities):
        _refs(errors, activity.get("input_source_ids", []), source_ids, f"/activities/{index}/input_source_ids", "source_id")
        _refs(errors, activity.get("output_source_ids", []), source_ids, f"/activities/{index}/output_source_ids", "source_id")

    for index, evidence in enumerate(evidence_items):
        base = f"/evidence_items/{index}"
        if evidence.get("source_id") not in source_ids:
            errors.append(_error("BAD_REFERENCE", f"{base}/source_id", "evidence source_id 不存在"))
        _confidence(errors, evidence.get("confidence", {}), f"{base}/confidence")
        nature, method = evidence.get("nature"), evidence.get("capture_method")
        if nature == "inferred" and method not in {"calculation", "model_fit"}:
            errors.append(_error("EVIDENCE_BOUNDARY", f"{base}/capture_method", "inferred 锚点必须由 calculation 或 model_fit 产生"))
        if nature == "depicted" and method not in {"visual_observation", "ocr"}:
            errors.append(_error("EVIDENCE_BOUNDARY", f"{base}/capture_method", "depicted 关系必须来自视觉观察或 OCR 锚点"))
        if method == "visual_estimate" and nature != "observed":
            errors.append(_error("EVIDENCE_BOUNDARY", f"{base}/nature", "图像估读值应标为 observed；作者印刷数值应转录为 reported"))
        source = source_by_id.get(evidence.get("source_id"), {})
        if source and source.get("availability") != "available":
            errors.append(_error("SOURCE_UNAVAILABLE", f"{base}/source_id", "不可用或未取得的来源不得支撑科学事实"))
        status = source.get("visual_inspection", {}).get("status")
        if method in {"visual_observation", "visual_estimate", "ocr"} and status not in {"completed", "partial"}:
            errors.append(_error("VISUAL_ACCESS", base, "视觉证据引用的来源尚未完成或部分完成视觉检查"))
        for pointer in evidence.get("supports", []):
            try:
                pointer_get(data, pointer)
            except (KeyError, IndexError):
                errors.append(_error("BAD_FIELD_PATH", f"{base}/supports", f"字段路径不可解析: {pointer}"))
            if pointer.startswith(("/validation", "/source_coverage", "/evidence_items", "/review", "/activities")):
                errors.append(_error("BAD_FIELD_PATH", f"{base}/supports", "证据 supports 只能指向科学事实、条件、分类、定位或结论"))

    registry = load_json(SCHEMA_ROOT / "figure_registry_v3.json")
    figure_types = registry["figure_types"]
    all_record_ids: set[str] = set()
    record_paths: dict[str, str] = {}
    for panel_index, panel in enumerate(panels):
        base = f"/panels/{panel_index}"
        if panel.get("figure_id") not in figure_ids:
            errors.append(_error("BAD_REFERENCE", f"{base}/figure_id", "panel figure_id 不存在"))
        location = panel.get("location", {})
        if location.get("source_id") not in source_ids:
            errors.append(_error("BAD_REFERENCE", f"{base}/location/source_id", "定位 source_id 不存在"))
        visual = panel.get("visual_check", {})
        source_visual = source_by_id.get(location.get("source_id"), {}).get("visual_inspection", {}).get("status")
        if visual.get("status") in {"completed", "partial"} and source_visual not in {"completed", "partial"}:
            errors.append(_error("VISUAL_ACCESS", f"{base}/visual_check", "面板视觉核验状态与来源状态矛盾"))

        classification = panel.get("classification", {})
        _confidence(errors, classification.get("confidence", {}), f"{base}/classification/confidence")
        _refs(errors, classification.get("evidence_ids", []), evidence_ids, f"{base}/classification/evidence_ids", "evidence_id")
        figure_type = classification.get("figure_type")
        rule = figure_types.get(figure_type)
        if rule is None:
            errors.append(_error("UNKNOWN_FIGURE_TYPE", f"{base}/classification/figure_type", "figure_type 不在 v3 注册表"))
        else:
            if classification.get("function_category") not in rule["allowed_categories"]:
                errors.append(_error("CLASSIFICATION_MISMATCH", f"{base}/classification/function_category", "功能类别与注册表不一致"))
            if classification.get("result_template") not in rule["allowed_templates"]:
                errors.append(_error("CLASSIFICATION_MISMATCH", f"{base}/classification/result_template", "结果模板与注册表不一致"))
        if panel.get("results", {}).get("template") != classification.get("result_template"):
            errors.append(_error("TEMPLATE_MISMATCH", f"{base}/results/template", "results.template 与 classification.result_template 不一致"))
        if classification.get("status") == "provisional":
            if classification.get("confidence", {}).get("level") == "high":
                errors.append(_error("PROVISIONAL_CONFIDENCE", f"{base}/classification/confidence", "暂定分类不得使用 high confidence"))
            if not classification.get("alternatives"):
                errors.append(_error("PROVISIONAL_ALTERNATIVES", f"{base}/classification/alternatives", "暂定分类必须保留至少一个备选组合"))
            if not panel.get("review", {}).get("required"):
                errors.append(_error("PROVISIONAL_REVIEW", f"{base}/review", "暂定分类必须进入人工复核"))

        scope = panel.get("reporting_scope", {})
        mode, displayed, total = scope.get("mode"), scope.get("displayed_count"), scope.get("total_count")
        if mode in {"selected", "summary_only"}:
            if displayed is None or total is None or not scope.get("selection_rule"):
                errors.append(_error("SILENT_TRUNCATION", f"{base}/reporting_scope", "选取或汇总结果必须声明展示数、总数和筛选规则"))
            elif displayed > total:
                errors.append(_error("SCOPE_COUNT", f"{base}/reporting_scope", "displayed_count 不能大于 total_count"))
        if mode == "full" and displayed is not None and total is not None and displayed != total:
            errors.append(_error("SILENT_TRUNCATION", f"{base}/reporting_scope", "full scope 的展示数与总数必须一致"))
        if classification.get("function_category") == "omics_bioinformatics" and mode == "full" and total is not None and len(panel.get("results", {}).get("records", [])) < total:
            errors.append(_error("SILENT_TRUNCATION", f"{base}/reporting_scope", "组学 full scope 记录数少于声明总数"))

        for condition_index, condition in enumerate(panel.get("conditions", [])):
            cbase = f"{base}/conditions/{condition_index}"
            _refs(errors, condition.get("evidence_ids", []), evidence_ids, f"{cbase}/evidence_ids", "evidence_id")
            _confidence(errors, condition.get("confidence", {}), f"{cbase}/confidence")

        records = panel.get("results", {}).get("records", [])
        for record_index, record in enumerate(records):
            rbase = f"{base}/results/records/{record_index}"
            record_id = record.get("record_id")
            if record_id in all_record_ids:
                errors.append(_error("DUPLICATE_ID", f"{rbase}/record_id", f"重复 record_id: {record_id}"))
            all_record_ids.add(record_id)
            record_paths[record_id] = rbase
            _refs(errors, record.get("evidence_ids", []), evidence_ids, f"{rbase}/evidence_ids", "evidence_id")
            _confidence(errors, record.get("confidence", {}), f"{rbase}/confidence")
            if classification.get("result_template") == "mechanism_relation":
                if record.get("evidence_nature") != "depicted":
                    errors.append(_error("MECHANISM_EVIDENCE", f"{rbase}/evidence_nature", "机制图中的箭头关系必须首先标为 depicted"))
                if record.get("measurement_origin") != "not_applicable":
                    errors.append(_error("MECHANISM_EVIDENCE", f"{rbase}/measurement_origin", "图示关系不应伪装为测量值"))
                cited_natures = {evidence_by_id.get(item, {}).get("nature") for item in record.get("evidence_ids", [])}
                if "depicted" not in cited_natures:
                    errors.append(_error("MECHANISM_EVIDENCE", f"{rbase}/evidence_ids", "机制关系必须引用 depicted 原子证据"))
            if figure_type == "embedding_plot":
                joined = json.dumps(record, ensure_ascii=False).casefold()
                if any(token in joined for token in ["effect size", "效应量", "causes", "导致"]):
                    errors.append(_error("EMBEDDING_OVERCLAIM", rbase, "UMAP/t-SNE 距离或位置不得解释为效应量或因果关系"))
            if figure_type == "shap_plot":
                joined = json.dumps(record, ensure_ascii=False).casefold()
                if any(token in joined for token in ["causes", "导致", "因果"]):
                    errors.append(_error("SHAP_OVERCLAIM", rbase, "SHAP 重要性不得解释为因果关系"))

        if figure_type == "enrichment_plot":
            roles = {condition.get("role") for condition in panel.get("conditions", [])}
            missing = {"database", "background_set", "multiple_testing"} - roles
            if missing:
                errors.append(_error("ENRICHMENT_CONTEXT", f"{base}/conditions", "富集分析必须显式记录数据库、背景集和多重检验；缺少: " + ", ".join(sorted(missing))))

        for claim_index, claim in enumerate(panel.get("claims", [])):
            cbase = f"{base}/claims/{claim_index}"
            _refs(errors, claim.get("evidence_ids", []), evidence_ids, f"{cbase}/evidence_ids", "evidence_id")
            _confidence(errors, claim.get("confidence", {}), f"{cbase}/confidence")
            if claim.get("nature") == "inferred":
                if claim.get("confidence", {}).get("level") == "high":
                    errors.append(_error("INFERENCE_CONFIDENCE", f"{cbase}/confidence", "有限推断不得使用 high confidence"))
                if not claim.get("limitation"):
                    errors.append(_error("INFERENCE_LIMIT", f"{cbase}/limitation", "推断结论必须说明边界或限制"))
                if not claim.get("premise_ids") or not claim.get("inference_rule"):
                    errors.append(_error("INFERENCE_PREMISES", cbase, "inferred 结论必须记录 premise_ids 和 inference_rule"))
            elif claim.get("premise_ids") or claim.get("inference_rule") is not None:
                errors.append(_error("INFERENCE_PREMISES", cbase, "非 inferred 结论不得携带推断前提或规则"))
            if claim.get("nature") in {"depicted", "inferred"} and any(token in claim.get("text", "").casefold() for token in ["proves", "causes", "证明", "必然导致"]):
                errors.append(_error("CAUSAL_OVERCLAIM", f"{cbase}/text", "图示或有限推断不得使用证明性因果措辞"))

        for derived_index, derived in enumerate(panel.get("derived_values", [])):
            dbase = f"{base}/derived_values/{derived_index}"
            _refs(errors, derived.get("evidence_ids", []), evidence_ids, f"{dbase}/evidence_ids", "evidence_id")
            inputs = derived.get("inputs", [])
            for input_index, input_item in enumerate(inputs):
                try:
                    pointer_get(data, input_item.get("field_path", ""))
                except (KeyError, IndexError):
                    errors.append(_error("BAD_FIELD_PATH", f"{dbase}/inputs/{input_index}/field_path", "派生值输入路径不可解析"))
            try:
                calculated = _safe_formula(derived.get("formula", ""), [item["value"] for item in inputs])
                allowed = max(derived.get("absolute_tolerance", 0.0), abs(calculated) * derived.get("relative_tolerance", 0.0), 1e-12)
                if abs(calculated - derived.get("recalculated", math.nan)) > allowed:
                    errors.append(_error("DERIVED_RECALCULATION", f"{dbase}/recalculated", "recalculated 与公式复算不一致"))
                reported = derived.get("reported")
                expected = "not_evaluable" if reported is None else "consistent" if abs(reported - calculated) <= allowed else "conflict"
                if derived.get("comparison") != expected:
                    errors.append(_error("DERIVED_COMPARISON", f"{dbase}/comparison", f"comparison 应为 {expected}"))
                if expected == "conflict" and not derived.get("review_action"):
                    errors.append(_error("DERIVED_CONFLICT", f"{dbase}/review_action", "派生值冲突必须给出人工处置建议"))
            except (ValueError, ZeroDivisionError, OverflowError, KeyError, TypeError) as exc:
                errors.append(_error("DERIVED_FORMULA", f"{dbase}/formula", str(exc)))

        _confidence(errors, panel.get("confidence", {}), f"{base}/confidence")
        _review_consistency(errors, panel.get("review", {}), f"{base}/review")

    for path, value in _walk_data_values(data):
        state, precision = value.get("state"), value.get("precision")
        present_value = value.get("value")
        if state == "present" and present_value is None:
            errors.append(_error("MISSING_STATE", path, "state=present 时 value 不能为 null"))
        if state != "present" and present_value is not None:
            errors.append(_error("MISSING_STATE", path, "非 present 状态必须使用 null，不得把 null 当作零值"))
        if state == "present" and precision == "not_applicable":
            errors.append(_error("PRECISION_STATE", path, "present 值必须声明 exact、approximate 或 bounded"))
        if state != "present" and precision != "not_applicable":
            errors.append(_error("PRECISION_STATE", path, "缺失或不适用值的 precision 必须为 not_applicable"))
        if precision == "approximate" and (not isinstance(value.get("tolerance"), (int, float)) or not value.get("basis")):
            errors.append(_error("ESTIMATE_TOLERANCE", path, "估读值必须提供正容差和估读依据"))
        if precision == "exact" and value.get("tolerance") is not None:
            errors.append(_error("EXACT_TOLERANCE", path, "精确转录值不得伪装带估读容差"))
        if state == "present" and not value.get("evidence_ids"):
            errors.append(_error("MISSING_EVIDENCE", path, "每个 present 值必须引用原子证据"))
        if state in {"unknown", "not_recoverable"} and not value.get("basis"):
            errors.append(_error("MISSING_REASON", path, "unknown/not_recoverable 必须说明原因"))
        if state == "conflicted" and not value.get("conflict_id"):
            errors.append(_error("CONFLICT_STATE", path, "state=conflicted 必须引用 conflict_id"))
        if state != "conflicted" and value.get("conflict_id") is not None:
            errors.append(_error("CONFLICT_STATE", path, "只有 conflicted 值可以携带 conflict_id"))
        if value.get("conflict_id") is not None and value.get("conflict_id") not in {item.get("conflict_id") for item in data.get("conflicts", [])}:
            errors.append(_error("BAD_REFERENCE", f"{path}/conflict_id", "conflict_id 不存在"))
        uncertainty = value.get("scientific_uncertainty")
        if isinstance(uncertainty, dict):
            _refs(errors, uncertainty.get("evidence_ids", []), evidence_ids, f"{path}/scientific_uncertainty/evidence_ids", "evidence_id")
            lower, upper = uncertainty.get("lower"), uncertainty.get("upper")
            if lower is not None and upper is not None and lower > upper:
                errors.append(_error("UNCERTAINTY_INTERVAL", f"{path}/scientific_uncertainty", "科学区间 lower 不能大于 upper"))
            if uncertainty.get("kind") in {"ci", "credible_interval", "prediction_interval"} and uncertainty.get("level") is None:
                errors.append(_error("UNCERTAINTY_LEVEL", f"{path}/scientific_uncertainty/level", "区间必须声明置信或可信水平；未知时用 kind=unknown"))
        _refs(errors, value.get("evidence_ids", []), evidence_ids, f"{path}/evidence_ids", "evidence_id")

    for path, bbox in _walk_bboxes(data):
        if bbox.get("x", 0) + bbox.get("width", 0) > 1 + 1e-12 or bbox.get("y", 0) + bbox.get("height", 0) > 1 + 1e-12:
            errors.append(_error("BBOX_BOUNDS", path, "normalized_page bbox 必须完整位于 [0,1] 页面内"))

    known_premises = all_record_ids | {claim.get("claim_id") for panel in panels for claim in panel.get("claims", [])}
    for panel_index, panel in enumerate(panels):
        for claim_index, claim in enumerate(panel.get("claims", [])):
            _refs(errors, claim.get("premise_ids", []), known_premises, f"/panels/{panel_index}/claims/{claim_index}/premise_ids", "premise_id")

    for panel_index, panel in enumerate(panels):
        workflow_graph: dict[str, list[str]] = {}
        for record_index, record in enumerate(panel.get("results", {}).get("records", [])):
            if panel.get("results", {}).get("template") == "workflow_step":
                workflow_graph[record.get("record_id")] = list(record.get("predecessors", []))
                for predecessor in record.get("predecessors", []):
                    if predecessor not in all_record_ids:
                        errors.append(_error("BAD_REFERENCE", f"/panels/{panel_index}/results/records/{record_index}/predecessors", f"流程前置步骤不存在: {predecessor}"))
                    if predecessor == record.get("record_id"):
                        errors.append(_error("WORKFLOW_CYCLE", f"/panels/{panel_index}/results/records/{record_index}/predecessors", "流程步骤不得以自身为前置步骤"))
        if workflow_graph:
            for node, parents in workflow_graph.items():
                for parent in parents:
                    if parent not in workflow_graph:
                        errors.append(_error("BAD_REFERENCE", f"/panels/{panel_index}/results/records", f"流程前置步骤不在同一面板: {node} <- {parent}"))
            visiting: set[str] = set()
            visited: set[str] = set()

            def visit(node: str) -> bool:
                if node in visiting:
                    return True
                if node in visited or node not in workflow_graph:
                    return False
                visiting.add(node)
                cyclic = any(visit(parent) for parent in workflow_graph[node])
                visiting.remove(node)
                visited.add(node)
                return cyclic

            if any(visit(node) for node in workflow_graph):
                errors.append(_error("WORKFLOW_CYCLE", f"/panels/{panel_index}/results/records", "流程前置关系必须构成有向无环图"))

    for index, figure in enumerate(figures):
        _refs(errors, figure.get("evidence_ids", []), evidence_ids, f"/figures/{index}/evidence_ids", "evidence_id")

    for index, coverage in enumerate(data.get("source_coverage", [])):
        base = f"/source_coverage/{index}"
        if coverage.get("source_id") not in source_ids:
            errors.append(_error("BAD_REFERENCE", f"{base}/source_id", "coverage source_id 不存在"))
        status, paths = coverage.get("status"), coverage.get("field_paths", [])
        if status in {"consumed", "partially_consumed"} and not paths:
            errors.append(_error("COVERAGE_PATH", f"{base}/field_paths", "已使用或部分使用来源必须提供字段路径"))
        if status in {"not_consumed", "unavailable"} and paths:
            errors.append(_error("COVERAGE_PATH", f"{base}/field_paths", "未使用或不可用来源不得伪造字段路径"))
        if status in {"partially_consumed", "not_consumed", "unavailable"} and not coverage.get("reason"):
            errors.append(_error("COVERAGE_REASON", f"{base}/reason", "该来源状态必须说明限制或未使用原因"))
        for pointer in paths:
            try:
                pointer_get(data, pointer)
            except (KeyError, IndexError):
                errors.append(_error("BAD_FIELD_PATH", f"{base}/field_paths", f"字段路径不可解析: {pointer}"))
            if pointer.startswith(("/validation", "/source_coverage", "/review", "/activities")):
                errors.append(_error("COVERAGE_PATH", f"{base}/field_paths", "来源消费路径不得指向验证、覆盖、复核或活动审计字段"))

    for index, conflict in enumerate(data.get("conflicts", [])):
        base = f"/conflicts/{index}"
        _refs(errors, conflict.get("evidence_ids", []), evidence_ids, f"{base}/evidence_ids", "evidence_id")
        statement_sources = [item.get("source_id") for item in conflict.get("statements", [])]
        _refs(errors, statement_sources, source_ids, f"{base}/statements", "source_id")
        if len(set(statement_sources)) < 2 and conflict.get("kind") == "source_disagreement":
            errors.append(_error("CONFLICT_SOURCES", f"{base}/statements", "来源分歧必须至少涉及两个不同来源"))
        for pointer in conflict.get("field_paths", []):
            try:
                pointer_get(data, pointer)
            except (KeyError, IndexError):
                errors.append(_error("BAD_FIELD_PATH", f"{base}/field_paths", f"冲突字段路径不可解析: {pointer}"))

    _review_consistency(errors, data.get("review", {}), "/review")
    if data.get("conflicts") and not data.get("review", {}).get("required"):
        errors.append(_error("REVIEW_CONFLICT", "/review/required", "存在冲突时必须启用人工复核"))
    if any(panel.get("review", {}).get("required") for panel in panels) and not data.get("review", {}).get("required"):
        errors.append(_error("REVIEW_ROLLUP", "/review/required", "顶层复核状态必须覆盖面板复核状态"))

    validation = data.get("validation", {})
    flags = [validation.get("schema_passed"), validation.get("semantic_passed"), validation.get("report_passed")]
    if validation.get("state") == "unvalidated":
        if any(flags) or validation.get("validated_at") is not None or validation.get("content_sha256") is not None or validation.get("report_sha256") is not None:
            errors.append(_error("VALIDATION_STATE", "/validation", "unvalidated 状态不得含通过标志、时间或摘要"))
    elif validation.get("state") == "validated":
        if not all(flags) or not validation.get("validated_at") or not validation.get("content_sha256") or not validation.get("report_sha256"):
            errors.append(_error("VALIDATION_STATE", "/validation", "validated 状态必须含三个通过标志、时间和摘要"))
        elif validation.get("content_sha256") != content_digest(data):
            errors.append(_error("VALIDATION_DIGEST", "/validation/content_sha256", "内容摘要与当前证据不一致"))
    return errors


def _review_consistency(errors: list[dict[str, str]], review: dict[str, Any], path: str) -> None:
    suggestions = review.get("suggestions", [])
    required = review.get("required")
    highest = review.get("highest_priority")
    if not required and suggestions:
        errors.append(_error("REVIEW_STATE", path, "review.required=false 时 suggestions 必须为空"))
    if not required and highest != "none":
        errors.append(_error("REVIEW_STATE", path, "无需复核时 highest_priority 必须为 none"))
    if required and not suggestions:
        errors.append(_error("REVIEW_STATE", path, "需要复核时必须给出可执行建议"))
    if suggestions:
        expected = max((item.get("priority", "low") for item in suggestions), key=lambda item: PRIORITY.get(item, -1))
        if highest != expected:
            errors.append(_error("REVIEW_PRIORITY", f"{path}/highest_priority", f"highest_priority 应为 {expected}"))


def audit(data: dict[str, Any], *, require_validated: bool = False) -> list[dict[str, str]]:
    errors = schema_errors(data)
    if not errors:
        errors.extend(semantic_errors(data))
    if require_validated and data.get("validation", {}).get("state") != "validated":
        errors.append(_error("NOT_VALIDATED", "/validation/state", "最终交付必须处于 validated 状态"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--require-validated", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        data = load_json(args.evidence)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [_error("INPUT", "$", str(exc))]
    else:
        errors = schema_errors(data) if args.schema_only else audit(data, require_validated=args.require_validated)
    if args.as_json:
        print(json.dumps({"passed": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        for item in errors:
            print(f"[{item['code']}] {item['path']}: {item['message']}")
    else:
        print("BioFig Trace evidence validation passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
