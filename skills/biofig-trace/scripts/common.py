"""Shared, dependency-free helpers for the BioFig Trace v3 toolchain."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = SKILL_ROOT / "schemas"


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON 不允许非有限数值常量: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 对象包含重复键: {key}")
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def initial_validation() -> dict[str, Any]:
    return {
        "state": "unvalidated",
        "schema_passed": False,
        "semantic_passed": False,
        "report_passed": False,
        "validator": "biofig-trace-finalizer/3.0",
        "validated_at": None,
        "content_sha256": None,
        "report_sha256": None,
    }


def content_digest(data: dict[str, Any]) -> str:
    payload = copy.deepcopy(data)
    payload["validation"] = initial_validation()
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def atomic_write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def pointer_escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def pointer_get(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise KeyError("JSON Pointer must be empty or start with '/'")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if token == "-" or not token.isdigit():
                raise KeyError(pointer)
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise KeyError(pointer)
    return current


def duplicate_values(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def source_display(source: dict[str, Any]) -> str:
    locator = source.get("locator", {})
    label = locator.get("citation") or locator.get("uri") or locator.get("path") or source.get("kind", "来源")
    detail = locator.get("detail")
    return f"{label}（{detail}）" if detail else str(label)
