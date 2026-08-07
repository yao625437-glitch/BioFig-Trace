#!/usr/bin/env python3
"""Migrate a Biofig Evidence 2.1 output to the additive 2.2 contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from figure_registry import panel_rule


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != "2.1":
        raise ValueError("input must have schema_version 2.1")

    migrated = json.loads(json.dumps(data))
    migrated["schema_version"] = "2.2"
    for coverage in migrated.get("source_coverage", []):
        if coverage.get("status") == "not_applicable":
            coverage["status"] = "not_consumed"
            reason = str(coverage.get("reason") or "").strip()
            coverage["reason"] = f"与当前提取目标不相关。{reason}" if reason else "与当前提取目标不相关。"

    for panel in migrated.get("panels", []):
        rule = panel_rule(panel.get("panel_type", ""))
        panel["figure_category"] = rule["category"]
        panel["result_profile"] = rule["profile"]
        panel.setdefault("relationships", [])

        evidence_ids = [panel.get("location", {}).get("source_id")]
        for claim in panel.get("claims", []):
            evidence_ids.extend(claim.get("evidence_ids", []))
        limitations = [reason.get("detail", "") for reason in panel.get("review_reasons", []) if reason.get("detail")]
        panel["academic_summary"] = {
            "objective": None,
            "approach": panel.get("experiment", {}).get("protocol"),
            "key_finding": panel.get("chart_explanation") or "旧版输出未提供面板解释。",
            "critical_appraisal": panel.get("confidence_rationale") or "需回到原图与正文核对证据边界。",
            "limitations": limitations,
            "evidence_ids": _unique(evidence_ids),
        }

        for measurement in panel.get("measurements", []):
            for point in measurement.get("points", []):
                for coordinate in ("x", "y"):
                    point.get(coordinate, {}).setdefault("category", None)
        for step in panel.get("process_steps", []):
            step.setdefault("input", None)
            step.setdefault("output", None)
        record_count = sum(len(item.get("points", [])) + len(item.get("derived_values", [])) for item in panel.get("measurements", []))
        record_count += len(panel.get("qualitative_observations", [])) + len(panel.get("process_steps", [])) + len(panel.get("relationships", []))
        panel["reporting_scope"] = {
            "mode": "full", "displayed_count": record_count, "total_count": record_count, "selection_rule": None,
        }

    migrated["validation"] = {
        "schema_passed": False,
        "semantic_passed": False,
        "report_generated": False,
        "validator": "pending migration",
        "validated_at": None,
    }
    return migrated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    try:
        migrated = migrate(load(args.input_json))
        Path(args.output_json).write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"MIGRATION FAILED: {exc}")
        return 1
    print(f"MIGRATED 2.1 -> 2.2: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
