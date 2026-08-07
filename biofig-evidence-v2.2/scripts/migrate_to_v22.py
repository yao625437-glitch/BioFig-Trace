#!/usr/bin/env python3
"""Migrate Biofig Evidence 2.0 or 2.1 data to the current 2.2 contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from migrate_v20_to_v21 import migrate as migrate_v20_to_v21
from migrate_v21_to_v22 import migrate as migrate_v21_to_v22


def migrate(data: dict) -> dict:
    version = data.get("schema_version")
    if version == "2.0":
        data = migrate_v20_to_v21(data)
    elif version != "2.1":
        raise ValueError("input must have schema_version 2.0 or 2.1")
    return migrate_v21_to_v22(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_json")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        migrated = migrate(data)
        Path(args.output_json).write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"MIGRATION FAILED: {exc}")
        return 1
    print(f"MIGRATED -> 2.2: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
