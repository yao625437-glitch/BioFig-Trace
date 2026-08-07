#!/usr/bin/env python3
"""Validate evidence JSON against the matching 2.1 or 2.2 contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from schema_engine import validate


def load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    return value


def schema_path(version: str) -> Path:
    schemas = Path(__file__).resolve().parents[1] / "schemas"
    if version == "2.1":
        return schemas / "output_schema_v2.1.json"
    if version == "2.2":
        return schemas / "output_schema.json"
    raise ValueError(f"unsupported schema_version: {version!r}; migrate the output to 2.2")


def audit(data: dict[str, Any], require_standard: bool = False) -> tuple[list[str], str]:
    schema = load(schema_path(str(data.get("schema_version"))))
    errors = validate(data, schema)
    engine = "built-in-complete-keyword-engine"
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        if require_standard:
            errors.append("$: jsonschema dependency is unavailable; install requirements.txt")
    else:
        standard_errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path))
        errors.extend(f"jsonschema:{'.'.join(map(str, item.path)) or '$'}: {item.message}" for item in standard_errors)
        engine += "+jsonschema-draft2020-12"
    return sorted(set(errors)), engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    parser.add_argument("--require-standard", action="store_true")
    args = parser.parse_args()
    try:
        data = load(args.json_file)
        errors, engine = audit(data, args.require_standard)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"SCHEMA INVALID: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"SCHEMA INVALID: {len(errors)} issue(s) [{engine}]")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"SCHEMA VALID: Biofig Evidence {data.get('schema_version', 'unknown')} [{engine}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
