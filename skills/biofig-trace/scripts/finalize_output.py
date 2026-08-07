"""Validate, render, stamp, revalidate and atomically publish one v3 output directory."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import atomic_write_json, atomic_write_text, content_digest, initial_validation, load_json
from render_report import render
from validate_evidence import schema_errors, semantic_errors
from verify_report import verify


class FinalizationError(RuntimeError):
    def __init__(self, phase: str, message: str, details: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.phase = phase
        self.details = details or []


def _require_clean_draft(data: dict[str, Any]) -> None:
    if data.get("validation") != initial_validation():
        raise FinalizationError("semantic", "finalizer 只接受 validation.state=unvalidated 且无通过戳的 draft")


def _raise_validation(phase: str, errors: list[dict[str, str]]) -> None:
    if errors:
        raise FinalizationError(phase, f"{phase} 阶段发现 {len(errors)} 个问题", errors)


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _stamp(data: dict[str, Any], report: str) -> dict[str, Any]:
    stamped = copy.deepcopy(data)
    stamped["validation"] = {
        "state": "validated",
        "schema_passed": True,
        "semantic_passed": True,
        "report_passed": True,
        "validator": "biofig-trace-finalizer/3.0",
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "content_sha256": content_digest(data),
        "report_sha256": hashlib.sha256(report.encode("utf-8")).hexdigest(),
    }
    return stamped


def finalize(draft_path: str | Path, output_dir: str | Path) -> dict[str, str]:
    draft = Path(draft_path).resolve(strict=True)
    output = Path(output_dir).resolve(strict=False)
    if output.exists() or output.is_symlink():
        raise FinalizationError("publish", f"输出目录必须不存在，拒绝覆盖: {output}")
    if output == draft or output in draft.parents:
        raise FinalizationError("publish", "输出目录不能是 draft 文件或其父目录")

    data = load_json(draft)
    if not isinstance(data, dict):
        raise FinalizationError("schema", "draft 顶层必须是 JSON 对象")

    # Fixed gate: Schema -> semantics -> render -> report check -> stamp -> full recheck.
    _raise_validation("schema", schema_errors(data))
    _raise_validation("semantic", semantic_errors(data))
    _require_clean_draft(data)

    report = render(data)
    _raise_validation("report", verify(data, report))

    stamped = _stamp(data, report)
    _raise_validation("final-schema", schema_errors(stamped))
    _raise_validation("final-semantic", semantic_errors(stamped))
    _raise_validation("final-report", verify(stamped, report))
    if render(stamped) != report:
        raise FinalizationError("final-report", "写入验证戳后公共报告投影发生变化")

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    published = False
    try:
        atomic_write_json(stage / "evidence.json", stamped)
        atomic_write_text(stage / "report.md", report)

        # Verify the exact staged bytes before the directory becomes visible.
        staged_data = load_json(stage / "evidence.json")
        staged_report = (stage / "report.md").read_text(encoding="utf-8")
        _raise_validation("staged-schema", schema_errors(staged_data))
        _raise_validation("staged-semantic", semantic_errors(staged_data))
        _raise_validation("staged-report", verify(staged_data, staged_report))
        _fsync_directory(stage)

        if output.exists() or output.is_symlink():
            raise FinalizationError("publish", f"发布前发现输出目录已存在，拒绝覆盖: {output}")
        os.rename(stage, output)
        published = True
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    return {"output_dir": str(output), "evidence": str(output / "evidence.json"), "report": str(output / "report.md")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="未验证 evidence draft")
    parser.add_argument("output_dir", type=Path, help="必须尚不存在；成功后包含 evidence.json 和 report.md")
    args = parser.parse_args()
    try:
        result = finalize(args.draft, args.output_dir)
    except Exception as exc:  # CLI boundary: diagnostics without an implementation traceback.
        if isinstance(exc, FinalizationError):
            payload: dict[str, Any] = {"passed": False, "phase": exc.phase, "error": str(exc), "details": exc.details}
        else:
            payload = {"passed": False, "phase": "input-or-io", "error": str(exc), "details": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"passed": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
