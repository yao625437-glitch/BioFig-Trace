#!/usr/bin/env python3
"""Cross-field scientific and provenance checks for Biofig Evidence 2.2."""

from __future__ import annotations

import ast
import itertools
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from figure_registry import load_registry
from migrate_v21_to_v22 import migrate as migrate_v21_to_v22


TEXT_TYPES = {"caption", "results", "methods", "supplement", "metadata", "user"}

REPLICATE_EVIDENCE_TERMS = {
    "biological": ("biological replicate", "biological replicates", "independent sample", "independent samples"),
    "technical": ("technical replicate", "technical replicates"),
    "independent_experiment": ("independent experiment", "independent experiments"),
    "field": ("field replicate", "field replicates", "field sample", "field samples"),
    "device": ("device measurement", "device measurements", "device replicate", "device replicates"),
    "specimen": ("specimen", "specimens"),
}


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def _safe_eval(expression: str, values: dict[str, float]) -> float:
    operators = {
        ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
        ast.Pow: lambda a, b: a**b,
    }

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in values:
            return float(values[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError(f"unsupported formula element: {ast.dump(node, include_attributes=False)}")

    return visit(ast.parse(expression, mode="eval"))


def _source_text(source_ids: list[str], sources: dict[str, dict[str, Any]]) -> str:
    chunks: list[str] = []
    for source_id in source_ids:
        source = sources.get(source_id, {})
        chunks.extend(str(source.get(key) or "") for key in ("quote", "locator"))
    return " ".join(chunks).lower()


def _resolve_output_path(data: dict[str, Any], field_path: str) -> Any:
    """Resolve the restricted JSON-like paths used by source_coverage."""
    if not field_path.startswith("$."):
        raise ValueError("path must begin with '$.'")
    current: Any = data
    position = 1
    token_re = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")
    while position < len(field_path):
        match = token_re.match(field_path, position)
        if not match:
            raise ValueError("unsupported path syntax")
        key, index = match.groups()
        if key is not None:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(key)
            current = current[key]
        else:
            item_index = int(index)
            if not isinstance(current, list) or item_index >= len(current):
                raise IndexError(item_index)
            current = current[item_index]
        position = match.end()
    return current


def _check_all_evidence_refs(value: Any, source_types: dict[str, str], path: str, errors: list[str]) -> None:
    """Recursively validate every evidence_ids/source_ids collection."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"evidence_ids", "source_ids"} and isinstance(child, list):
                _check_refs(child, source_types, child_path, errors)
            else:
                _check_all_evidence_refs(child, source_types, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_all_evidence_refs(child, source_types, f"{path}[{index}]", errors)


def _check_source_coverage(data: dict[str, Any], source_types: dict[str, str], errors: list[str]) -> None:
    """Require an explicit consume/exclude decision for methods/results sources."""
    coverage = data.get("source_coverage", [])
    if coverage is None:
        coverage = []
    if not isinstance(coverage, list):
        _add(errors, "$.source_coverage", "must be an array when present")
        return

    coverage_ids: set[str] = set()
    covered_sources: set[str] = set()
    for index, item in enumerate(coverage):
        path = f"$.source_coverage[{index}]"
        if not isinstance(item, dict):
            _add(errors, path, "must be an object")
            continue
        item_id = item.get("id")
        if item_id in coverage_ids:
            _add(errors, f"{path}.id", "coverage IDs must be unique")
        coverage_ids.add(item_id)
        source_id = item.get("source_id")
        if source_id not in source_types:
            _add(errors, f"{path}.source_id", f"unknown source id {source_id!r}")
        else:
            covered_sources.add(source_id)
        status = item.get("status")
        field_paths = item.get("field_paths", [])
        if not isinstance(field_paths, list):
            _add(errors, f"{path}.field_paths", "must be an array")
            field_paths = []
        if status in {"consumed", "partially_consumed"} and not field_paths:
            _add(errors, f"{path}.field_paths", f"required when status is {status!r}")
        if status in {"not_consumed", "unavailable"} and field_paths:
            _add(errors, f"{path}.field_paths", f"must be empty when status is {status!r}")
        for field_index, field_path in enumerate(field_paths):
            if not isinstance(field_path, str) or not field_path.startswith("$."):
                _add(errors, f"{path}.field_paths[{field_index}]", "must be a JSON-like path beginning with '$.'")
                continue
            try:
                _resolve_output_path(data, field_path)
            except (ValueError, KeyError, IndexError):
                _add(errors, f"{path}.field_paths[{field_index}]", "must resolve to an existing field in the output")

    required_types = {"methods", "results", "supplement"}
    for source_id, source_type in source_types.items():
        if source_type in required_types and source_id not in covered_sources:
            _add(errors, "$.source_coverage", f"source {source_id!r} ({source_type}) requires a consumed/not-consumed coverage record")


def _check_rounding_interval(derived: dict[str, Any], d_path: str, values: dict[str, float], errors: list[str]) -> None:
    """Validate the explicit rounding audit for a reported derived conflict."""
    if derived.get("reported") is None or derived.get("comparison_status") != "conflict":
        return
    check = derived.get("rounding_interval_check")
    if not isinstance(check, dict):
        _add(errors, f"{d_path}.rounding_interval_check", "required for reported calculation conflicts")
        return
    status = check.get("status")
    if status == "not_evaluable":
        if check.get("input_intervals"):
            _add(errors, f"{d_path}.rounding_interval_check.input_intervals", "must be empty when the rounding interval is not evaluable")
        if check.get("calculated_interval") is not None:
            _add(errors, f"{d_path}.rounding_interval_check.calculated_interval", "must be null when the rounding interval is not evaluable")
        if check.get("reported_inside_interval") is not None:
            _add(errors, f"{d_path}.rounding_interval_check.reported_inside_interval", "must be null when the rounding interval is not evaluable")
        if not str(check.get("notes") or "").strip():
            _add(errors, f"{d_path}.rounding_interval_check.notes", "must explain why the interval cannot be evaluated")
        return
    if status != "evaluated":
        _add(errors, f"{d_path}.rounding_interval_check.status", "must be evaluated or not_evaluable for a reported calculation conflict")
        return
    intervals = check.get("input_intervals", [])
    if not intervals:
        _add(errors, f"{d_path}.rounding_interval_check.input_intervals", "must list every rounded formula input")
        return
    interval_values: dict[str, tuple[float, float]] = {}
    for index, item in enumerate(intervals):
        symbol = item.get("symbol")
        lower, upper = item.get("lower"), item.get("upper")
        if symbol not in values:
            _add(errors, f"{d_path}.rounding_interval_check.input_intervals[{index}].symbol", "must match a formula input")
            continue
        if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)) or lower > upper:
            _add(errors, f"{d_path}.rounding_interval_check.input_intervals[{index}]", "must contain ordered numeric bounds")
            continue
        interval_values[symbol] = (float(lower), float(upper))
    if set(interval_values) != set(values):
        _add(errors, f"{d_path}.rounding_interval_check.input_intervals", "must cover exactly the formula input symbols")
        return
    try:
        combinations = itertools.product(*[interval_values[name] for name in values])
        calculated_values = [_safe_eval(derived["formula"], dict(zip(values, combo))) for combo in combinations]
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
        _add(errors, f"{d_path}.rounding_interval_check", f"cannot evaluate interval safely: {exc}")
        return
    expected_lower, expected_upper = min(calculated_values), max(calculated_values)
    calculated_interval = check.get("calculated_interval") or {}
    if not math.isclose(calculated_interval.get("lower", float("nan")), expected_lower, rel_tol=1e-9, abs_tol=1e-9):
        _add(errors, f"{d_path}.rounding_interval_check.calculated_interval.lower", f"must equal {expected_lower:.12g}")
    if not math.isclose(calculated_interval.get("upper", float("nan")), expected_upper, rel_tol=1e-9, abs_tol=1e-9):
        _add(errors, f"{d_path}.rounding_interval_check.calculated_interval.upper", f"must equal {expected_upper:.12g}")
    reported_inside = expected_lower <= float(derived["reported"]) <= expected_upper
    if check.get("reported_inside_interval") is not reported_inside:
        _add(errors, f"{d_path}.rounding_interval_check.reported_inside_interval", f"must be {reported_inside}")
    notes = str(check.get("notes") or "")
    if not notes.strip():
        _add(errors, f"{d_path}.rounding_interval_check.notes", "must explain the interval conclusion")


def _add(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _check_refs(refs: list[str], source_types: dict[str, str], path: str, errors: list[str]) -> set[str]:
    found: set[str] = set()
    for ref in refs:
        if ref not in source_types:
            _add(errors, path, f"unknown source id {ref!r}")
        else:
            found.add(source_types[ref])
    return found


def audit(data: dict[str, Any]) -> list[str]:
    if data.get("schema_version") == "2.1":
        try:
            data = migrate_v21_to_v22(data)
        except ValueError as exc:
            return [f"$.schema_version: legacy migration failed: {exc}"]
    elif data.get("schema_version") != "2.2":
        return ["$.schema_version: must be 2.1 or 2.2"]
    errors: list[str] = []
    sources = data.get("sources", [])
    source_ids = [item.get("id") for item in sources]
    if len(source_ids) != len(set(source_ids)):
        _add(errors, "$.sources", "source IDs must be unique")
    source_types = {item["id"]: item["type"] for item in sources if isinstance(item, dict) and item.get("id")}
    source_objects = {item["id"]: item for item in sources if isinstance(item, dict) and item.get("id")}
    _check_all_evidence_refs(data, source_types, "$", errors)
    _check_source_coverage(data, source_types, errors)

    registry = load_registry()
    registered_types = registry.get("panel_types", {})

    panel_ids: set[str] = set()
    conflict_paths = {path for conflict in data.get("conflicts", []) for path in conflict.get("field_paths", [])}
    any_panel_review = False
    major_or_critical = any(reason.get("severity") in {"major", "critical"} for reason in data.get("review_reasons", []))

    for p_index, panel in enumerate(data.get("panels", [])):
        base = f"$.panels[{p_index}]"
        panel_id = panel.get("panel_id")
        if panel_id in panel_ids:
            _add(errors, f"{base}.panel_id", "panel ID must be unique")
        panel_ids.add(panel_id)
        if panel.get("location", {}).get("source_id") not in source_types:
            _add(errors, f"{base}.location.source_id", "must resolve to a source")
        panel_type = panel.get("panel_type")
        rule = registered_types.get(panel_type)
        if not rule:
            _add(errors, f"{base}.panel_type", f"unregistered panel type {panel_type!r}")
        else:
            if panel.get("figure_category") != rule.get("category"):
                _add(errors, f"{base}.figure_category", f"must be {rule.get('category')!r} for panel_type {panel_type!r}")
            if panel.get("result_profile") != rule.get("profile"):
                _add(errors, f"{base}.result_profile", f"must be {rule.get('profile')!r} for panel_type {panel_type!r}")

        summary = panel.get("academic_summary", {})
        if isinstance(summary, dict):
            if str(summary.get("key_finding") or "").strip() == str(summary.get("critical_appraisal") or "").strip():
                _add(errors, f"{base}.academic_summary.critical_appraisal", "must appraise the evidence boundary rather than repeat the key finding")
        reporting_scope = panel.get("reporting_scope", {})
        actual_records = sum(len(item.get("points", [])) + len(item.get("derived_values", [])) for item in panel.get("measurements", []))
        actual_records += len(panel.get("qualitative_observations", [])) + len(panel.get("process_steps", [])) + len(panel.get("relationships", []))
        if reporting_scope.get("displayed_count") is not None and reporting_scope.get("displayed_count") != actual_records:
            _add(errors, f"{base}.reporting_scope.displayed_count", f"must equal the {actual_records} structured records present")
        if reporting_scope.get("mode") == "full":
            if reporting_scope.get("selection_rule") is not None:
                _add(errors, f"{base}.reporting_scope.selection_rule", "must be null when mode is full")
            if reporting_scope.get("total_count") is not None and reporting_scope.get("total_count") != actual_records:
                _add(errors, f"{base}.reporting_scope.total_count", f"must equal {actual_records} when mode is full")
        else:
            if not str(reporting_scope.get("selection_rule") or "").strip():
                _add(errors, f"{base}.reporting_scope.selection_rule", "must explain selection or summarization")
            if reporting_scope.get("total_count") is not None and reporting_scope.get("total_count") < actual_records:
                _add(errors, f"{base}.reporting_scope.total_count", "cannot be smaller than displayed_count")

        axes = panel.get("axes", [])
        axis_ids = [item.get("id") for item in axes]
        if len(axis_ids) != len(set(axis_ids)):
            _add(errors, f"{base}.axes", "axis IDs must be unique within a panel")
        series = panel.get("series", [])
        series_ids = [item.get("id") for item in series]
        if len(series_ids) != len(set(series_ids)):
            _add(errors, f"{base}.series", "series IDs must be unique within a panel")
        for s_index, item in enumerate(series):
            for axis_id in item.get("axis_ids", []):
                if axis_id not in axis_ids:
                    _add(errors, f"{base}.series[{s_index}].axis_ids", f"unknown axis id {axis_id!r}")
            _check_refs(item.get("evidence_ids", []), source_types, f"{base}.series[{s_index}].evidence_ids", errors)

        measurement_ids: set[str] = set()
        point_ids: set[str] = set()
        for m_index, measurement in enumerate(panel.get("measurements", [])):
            m_path = f"{base}.measurements[{m_index}]"
            measurement_id = measurement.get("id")
            if measurement_id in measurement_ids:
                _add(errors, f"{m_path}.id", "measurement ID must be unique within a panel")
            measurement_ids.add(measurement_id)
            axis_id = measurement.get("axis_id")
            if axis_id is not None and axis_id not in axis_ids:
                _add(errors, f"{m_path}.axis_id", f"unknown axis id {axis_id!r}")
            axis_unit = next((axis.get("unit") for axis in axes if axis.get("id") == axis_id), None)
            if axis_unit and measurement.get("unit") and axis_unit != measurement.get("unit"):
                _add(errors, f"{m_path}.unit", f"does not match mapped axis unit {axis_unit!r}")

            for point_index, point in enumerate(measurement.get("points", [])):
                point_path = f"{m_path}.points[{point_index}]"
                point_id = point.get("id")
                if point_id in point_ids:
                    _add(errors, f"{point_path}.id", "point ID must be unique within a panel")
                point_ids.add(point_id)
                if point.get("series_id") is not None and point.get("series_id") not in series_ids:
                    _add(errors, f"{point_path}.series_id", "must resolve to a panel series")
                for coordinate in ("x", "y"):
                    value = point.get(coordinate, {})
                    status, numeric, tolerance = value.get("status"), value.get("numeric"), value.get("tolerance")
                    category = value.get("category")
                    if status == "exact" and numeric is None and not str(category or "").strip():
                        _add(errors, f"{point_path}.{coordinate}", "exact values require a numeric or categorical value")
                    if status == "approximate" and numeric is None:
                        _add(errors, f"{point_path}.{coordinate}.numeric", "approximate values require one scalar numeric value")
                    if status == "approximate" and (tolerance is None or tolerance <= 0):
                        _add(errors, f"{point_path}.{coordinate}.tolerance", "approximate values require a positive tolerance")
                    if status in {"not_recoverable", "not_applicable"} and (numeric is not None or category is not None):
                        _add(errors, f"{point_path}.{coordinate}", f"numeric and category must be null when status is {status}")
                y_unit = point.get("y", {}).get("unit")
                if measurement.get("unit") and y_unit and y_unit != measurement.get("unit"):
                    _add(errors, f"{point_path}.y.unit", f"does not match measurement unit {measurement.get('unit')!r}")
                _check_refs(point.get("evidence_ids", []), source_types, f"{point_path}.evidence_ids", errors)

            for d_index, derived in enumerate(measurement.get("derived_values", [])):
                d_path = f"{m_path}.derived_values[{d_index}]"
                values = {item["symbol"]: item["value"] for item in derived.get("inputs", [])}
                try:
                    calculated = _safe_eval(derived.get("formula", ""), values)
                except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
                    _add(errors, f"{d_path}.formula", f"cannot evaluate safely: {exc}")
                    continue
                stored = derived.get("calculated")
                if stored is None or not math.isclose(stored, calculated, rel_tol=1e-9, abs_tol=1e-9):
                    _add(errors, f"{d_path}.calculated", f"must equal formula result {calculated:.12g}")
                reported = derived.get("reported")
                if reported is not None:
                    difference = abs(calculated - reported)
                    relative = difference / abs(reported) if reported != 0 else difference
                    expected = "consistent" if difference <= derived.get("tolerance", 0) else "conflict"
                    if derived.get("comparison_status") != expected:
                        _add(errors, f"{d_path}.comparison_status", f"must be {expected!r} for the stated tolerance")
                    if derived.get("relative_difference") is None or not math.isclose(derived["relative_difference"], relative, rel_tol=1e-6, abs_tol=1e-9):
                        _add(errors, f"{d_path}.relative_difference", f"must equal {relative:.9g}")
                    if expected == "conflict" and d_path not in conflict_paths:
                        _add(errors, d_path, "calculation conflict must be referenced by a top-level conflict.field_paths entry")
                _check_rounding_interval(derived, d_path, values, errors)
                _check_refs(derived.get("evidence_ids", []), source_types, f"{d_path}.evidence_ids", errors)

        steps = panel.get("process_steps", [])
        step_ids = {step.get("id") for step in steps}
        for step_index, step in enumerate(steps):
            for predecessor in step.get("predecessor_ids", []):
                if predecessor not in step_ids:
                    _add(errors, f"{base}.process_steps[{step_index}].predecessor_ids", f"unknown step {predecessor!r}")

        relationships = panel.get("relationships", [])
        relationship_ids = [item.get("id") for item in relationships]
        if len(relationship_ids) != len(set(relationship_ids)):
            _add(errors, f"{base}.relationships", "relationship IDs must be unique within a panel")
        for relation_index, relationship in enumerate(relationships):
            r_path = f"{base}.relationships[{relation_index}]"
            evidence_types = _check_refs(relationship.get("evidence_ids", []), source_types, f"{r_path}.evidence_ids", errors)
            epistemic_status = relationship.get("epistemic_status")
            if epistemic_status in {"depicted", "observed"} and "image" not in evidence_types:
                _add(errors, r_path, f"{epistemic_status} relationship must cite image evidence")
            if epistemic_status == "reported" and not evidence_types.intersection(TEXT_TYPES):
                _add(errors, r_path, "reported relationship must cite text evidence")
            if epistemic_status == "inferred" and relationship.get("confidence") == "high":
                _add(errors, r_path, "inferred relationship cannot use high confidence")

        profile = panel.get("result_profile")
        if profile == "workflow_flow":
            if not steps:
                _add(errors, f"{base}.process_steps", "workflow profile requires at least one process step")
            if panel.get("statistics", {}).get("error_bar", {}).get("kind") != "none":
                _add(errors, f"{base}.statistics.error_bar.kind", "workflow profile cannot declare variance or error bars")
        elif profile == "mechanism_relationship" and not relationships:
            _add(errors, f"{base}.relationships", "mechanism profile requires at least one explicit relationship")
        elif profile in {"image_observation", "band_lane", "cytometry_gate"}:
            if not panel.get("qualitative_observations") and not panel.get("measurements"):
                _add(errors, base, f"{profile} requires an observation or measurement")
        elif profile not in {"mixed", "workflow_flow", "mechanism_relationship"}:
            if not panel.get("measurements") and not panel.get("qualitative_observations"):
                _add(errors, base, f"{profile} requires a measurement or observation")

        claims = panel.get("claims", [])
        for c_index, claim in enumerate(claims):
            c_path = f"{base}.claims[{c_index}]"
            types = _check_refs(claim.get("evidence_ids", []), source_types, f"{c_path}.evidence_ids", errors)
            if claim.get("epistemic_status") == "observed" and "image" not in types:
                _add(errors, c_path, "observed claim must cite image evidence")
            if claim.get("epistemic_status") == "reported" and not types.intersection(TEXT_TYPES):
                _add(errors, c_path, "reported claim must cite text evidence")
            if claim.get("epistemic_status") == "inferred" and claim.get("confidence") == "high":
                _add(errors, c_path, "inferred claim cannot use high confidence")

        for s_index, sample in enumerate(panel.get("statistics", {}).get("sample_sizes", [])):
            s_path = f"{base}.statistics.sample_sizes[{s_index}]"
            replicate_type = sample.get("replicate_type")
            if replicate_type in REPLICATE_EVIDENCE_TERMS:
                evidence_text = " ".join([
                    str(sample.get("raw") or ""),
                    str(sample.get("scope") or ""),
                    _source_text(sample.get("evidence_ids", []), source_objects),
                ]).lower()
                terms = REPLICATE_EVIDENCE_TERMS[replicate_type]
                if not any(re.search(rf"\b{re.escape(term)}\b", evidence_text) for term in terms):
                    _add(errors, f"{s_path}.replicate_type", f"{replicate_type!r} requires explicit supporting replicate wording in raw text or cited sources")
            if replicate_type == "technical" and sample.get("independent_experiments") not in (None, 0):
                _add(errors, f"{s_path}", "technical replicates cannot simultaneously declare independent_experiments")

        reason_codes = {reason.get("code") for reason in panel.get("review_reasons", [])}
        stats = panel.get("statistics", {})
        if "MISSING_STATISTICS" in reason_codes and stats.get("scope") != "inferential" and not any(claim.get("claim_type") == "significance" for claim in claims):
            _add(errors, f"{base}.review_reasons", "MISSING_STATISTICS is only valid for inferential/significance claims")
        if stats.get("error_propagation", {}).get("status") == "not_reported" and "UNSPECIFIED_ERROR_PROPAGATION" not in reason_codes:
            _add(errors, f"{base}.review_reasons", "not_reported error propagation requires UNSPECIFIED_ERROR_PROPAGATION")
        has_calculated_measurement = any(item.get("origin") == "calculated" for item in panel.get("measurements", []))
        has_displayed_error = stats.get("error_bar", {}).get("kind") not in {None, "none"}
        propagation_status = stats.get("error_propagation", {}).get("status")
        if has_calculated_measurement and has_displayed_error and propagation_status == "not_applicable":
            _add(errors, f"{base}.statistics.error_propagation.status", "calculated measurements with displayed error bars cannot use not_applicable")
        if has_calculated_measurement and has_displayed_error and propagation_status == "not_reported" and "UNSPECIFIED_ERROR_PROPAGATION" not in reason_codes:
            _add(errors, f"{base}.review_reasons", "calculated measurements with unreported propagation require UNSPECIFIED_ERROR_PROPAGATION")

        for m_index, measurement in enumerate(panel.get("measurements", [])):
            m_path = f"{base}.measurements[{m_index}]"
            origin = measurement.get("origin")
            extraction_method = measurement.get("extraction_method")
            if extraction_method == "image_estimate" and origin == "direct_measurement":
                _add(errors, f"{m_path}.extraction_method", "image_estimate cannot be paired with direct_measurement origin")
            if extraction_method == "calculated_from_evidence" and origin != "calculated":
                _add(errors, f"{m_path}.extraction_method", "calculated_from_evidence requires calculated origin")
            if extraction_method == "direct_report" and origin not in {"direct_measurement", "author_reported"}:
                _add(errors, f"{m_path}.extraction_method", "direct_report requires direct_measurement or author_reported origin")
            if extraction_method == "text_transcription" and origin != "author_reported":
                _add(errors, f"{m_path}.extraction_method", "text_transcription requires author_reported origin")
            if origin == "unknown" and extraction_method not in {"image_estimate", "unknown"}:
                _add(errors, f"{m_path}.extraction_method", "unknown origin requires image_estimate or unknown extraction method")
            if origin == "not_applicable" and extraction_method != "not_applicable":
                _add(errors, f"{m_path}.extraction_method", "not_applicable origin requires not_applicable extraction method")
            if origin == "direct_measurement":
                for point_index, point in enumerate(measurement.get("points", [])):
                    statuses = [point.get(axis, {}).get("status") for axis in ("x", "y")]
                    if any(status in {"approximate", "bounded", "not_recoverable"} for status in statuses):
                        _add(errors, f"{m_path}.points[{point_index}]", "direct_measurement cannot contain approximate, bounded, or not_recoverable coordinates; use image_estimate or unknown")

        reasons = panel.get("review_reasons", [])
        needs_review = any(reason.get("severity") in {"major", "critical"} for reason in reasons)
        if needs_review and not panel.get("review_required"):
            _add(errors, f"{base}.review_required", "must be true for major/critical panel reasons")
        if panel.get("review_required") and not reasons:
            _add(errors, f"{base}.review_reasons", "must explain why panel review is required")
        any_panel_review = any_panel_review or bool(panel.get("review_required"))
        major_or_critical = major_or_critical or needs_review
        for r_index, reason in enumerate(reasons):
            _check_refs(reason.get("evidence_ids", []), source_types, f"{base}.review_reasons[{r_index}].evidence_ids", errors)

    for c_index, conflict in enumerate(data.get("conflicts", [])):
        _check_refs(conflict.get("source_ids", []), source_types, f"$.conflicts[{c_index}].source_ids", errors)
        if conflict.get("resolution") in {"unresolved", "reported_with_caveat"}:
            major_or_critical = True

    must_review = bool(major_or_critical or any_panel_review)
    if must_review and not data.get("review_required"):
        _add(errors, "$.review_required", "must be true for unresolved conflicts or panel review requirements")
    if data.get("review_required") and not (data.get("review_reasons") or any_panel_review or data.get("conflicts")):
        _add(errors, "$.review_required", "requires a root/panel review reason or unresolved conflict")
    return list(dict.fromkeys(errors))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: semantic_check.py <evidence.json>", file=sys.stderr)
        return 2
    try:
        errors = audit(load(sys.argv[1]))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"SEMANTIC INVALID: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"SEMANTIC INVALID: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("SEMANTIC VALID: references, scalar points, axes, statistics, reviews, and derived values are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
