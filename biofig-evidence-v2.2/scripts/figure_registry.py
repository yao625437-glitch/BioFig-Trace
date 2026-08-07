#!/usr/bin/env python3
"""Load the canonical six-category figure registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schemas" / "figure_registry.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("figure registry root must be an object")
    return value


def panel_rule(panel_type: str) -> dict[str, str]:
    registry = load_registry()
    try:
        rule = registry["panel_types"][panel_type]
    except KeyError as exc:
        raise ValueError(f"unknown panel_type: {panel_type!r}") from exc
    return rule
