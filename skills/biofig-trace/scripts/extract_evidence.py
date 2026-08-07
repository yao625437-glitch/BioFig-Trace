"""Create a v3 evidence draft from a source manifest; extraction remains evidence-led."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import atomic_write_json, initial_validation, load_json


def draft_from_manifest(
    manifest: dict[str, Any],
    *,
    title: str | None = None,
    doi: str | None = None,
    figure_label: str = "待定位图",
    language: str = "zh-CN",
) -> dict[str, Any]:
    return {
        "schema_id": "https://biofig-trace.local/schema/evidence/3.0",
        "schema_version": "3.0.0",
        "run": {
            "run_id": "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "status": "partial",
            "report_language": language,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "limitations": ["尚未完成面板级视觉检查和证据抽取。"],
        },
        "paper": {
            "title": title,
            "doi": doi,
            "identifiers": [],
            "public_access_confirmed": any(source.get("access_basis") == "public" for source in manifest.get("sources", [])),
        },
        "sources": manifest.get("sources", []),
        "activities": [],
        "figures": [{"figure_id": "fig-1", "label": figure_label, "caption": None, "evidence_ids": []}],
        "panels": [],
        "evidence_items": [],
        "source_coverage": [],
        "conflicts": [],
        "review": {
            "required": True,
            "highest_priority": "critical",
            "suggestions": [{"code": "INCOMPLETE_EXTRACTION", "priority": "critical", "panel_ids": [], "reason": "尚未完成面板级抽取。", "action": "检查原图、图注、结果和方法后补全证据。", "evidence_ids": []}],
        },
        "validation": initial_validation(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--doi")
    parser.add_argument("--figure-label", default="待定位图")
    parser.add_argument("--language", default="zh-CN")
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    if manifest.get("manifest_version") != "3.0.0" or not isinstance(manifest.get("sources"), list):
        parser.error("manifest 必须由 ingest_sources.py 生成且版本为 3.0.0。")
    draft = draft_from_manifest(manifest, title=args.title, doi=args.doi, figure_label=args.figure_label, language=args.language)
    atomic_write_json(args.output, draft)
    print(json.dumps({"output": str(args.output), "state": "unvalidated", "next": "完成面板分割和证据抽取后运行 finalize_output.py"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
