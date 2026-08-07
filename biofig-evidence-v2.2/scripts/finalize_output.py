#!/usr/bin/env python3
"""Validate, render, verify, stamp, and atomically publish both deliverables."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(script_dir: Path, script: str, *args: str) -> None:
    completed = subprocess.run([sys.executable, str(script_dir / script), *args], check=False)
    if completed.returncode:
        raise RuntimeError(f"{script} failed with exit code {completed.returncode}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: finalize_output.py <evidence.json> <report.md>", file=sys.stderr)
        return 2
    evidence = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2]).resolve()
    temporary_evidence = evidence.with_name(evidence.name + ".biofig.tmp")
    temporary_report = report.with_name(report.name + ".biofig.tmp")
    scripts = Path(__file__).resolve().parent
    try:
        run(scripts, "validate_output.py", str(evidence))
        run(scripts, "semantic_check.py", str(evidence))
        run(scripts, "render_report.py", str(evidence), str(temporary_report))
        run(scripts, "verify_report.py", str(evidence), str(temporary_report))
        data = json.loads(evidence.read_text(encoding="utf-8"))
        data["validation"] = {
            "schema_passed": True,
            "semantic_passed": True,
            "report_generated": True,
            "validator": "validate_output.py + semantic_check.py + verify_report.py",
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary_evidence.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(scripts, "validate_output.py", str(temporary_evidence))
        run(scripts, "semantic_check.py", str(temporary_evidence))
        run(scripts, "verify_report.py", str(temporary_evidence), str(temporary_report))
        temporary_evidence.replace(evidence)
        temporary_report.replace(report)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        temporary_evidence.unlink(missing_ok=True)
        temporary_report.unlink(missing_ok=True)
        print(f"FINALIZATION FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"FINALIZED: {evidence} + {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
