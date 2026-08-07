#!/usr/bin/env python3
"""Migrate a Biofig Evidence 2.0 output to the 2.1 contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ORIGIN_MAP = {
    "direct_measurement": ("direct_measurement", "direct_report"),
    "calculated": ("calculated", "calculated_from_evidence"),
    "author_reported": ("author_reported", "text_transcription"),
    "image_estimate": ("unknown", "image_estimate"),
    "unknown": ("unknown", "unknown"),
    "not_applicable": ("not_applicable", "not_applicable"),
}


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != "2.0":
        raise ValueError("input must have schema_version 2.0")

    migrated = json.loads(json.dumps(data))
    migrated["schema_version"] = "2.1"
    migrated["source_coverage"] = list(migrated.get("source_coverage") or [])

    for panel in migrated.get("panels", []):
        for measurement in panel.get("measurements", []):
            old_origin = measurement.get("origin", "unknown")
            try:
                new_origin, extraction_method = ORIGIN_MAP[old_origin]
            except KeyError as exc:
                raise ValueError(f"unsupported measurement.origin: {old_origin!r}") from exc
            measurement["origin"] = new_origin
            measurement["extraction_method"] = extraction_method

    covered_sources = {item.get("source_id") for item in migrated["source_coverage"] if isinstance(item, dict)}
    scope_map = {"results": "results", "methods": "experimental_conditions", "supplement": "other"}
    for source in migrated.get("sources", []):
        source_id = source.get("id")
        source_type = source.get("type")
        if source_type not in scope_map or source_id in covered_sources:
            continue
        migrated["source_coverage"].append({
            "id": f"migration_{source_id}",
            "source_id": source_id,
            "scope": scope_map[source_type],
            "fact_summary": f"Unmapped {source_type} facts carried over from the v2.0 output.",
            "status": "not_consumed",
            "field_paths": [],
            "reason": "v2.0 did not record source consumption; review this source and replace the migration placeholder.",
        })

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
    print(f"MIGRATED 2.0 -> 2.1: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
