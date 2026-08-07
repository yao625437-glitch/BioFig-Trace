"""Small strict validator for the JSON Schema features used by this Skill.

The evidence contract remains a standard Draft 2020-12 JSON Schema. This
fallback keeps the submission runnable in offline sandboxes where the optional
``jsonschema`` package is absent; when that package is present, the public
validator uses the standards implementation instead.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any

from common import pointer_get


def _path(parent: str, token: str | int) -> str:
    return f"{parent}[{token}]" if isinstance(token, int) else f"{parent}.{token}"


def _is_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _resolve(root: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#"):
        raise ValueError(f"fallback validator 只支持本地 $ref: {reference}")
    return pointer_get(root, reference[1:])


def _date_time(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return "T" in value


def validate(instance: Any, schema: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    def add(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    def check(value: Any, rule: Any, path: str) -> None:
        if rule is True:
            return
        if rule is False:
            add(path, "值被 boolean schema 拒绝")
            return
        if not isinstance(rule, dict):
            add(path, "内部 Schema 规则必须是对象或布尔值")
            return
        if "$ref" in rule:
            check(value, _resolve(schema, rule["$ref"]), path)
            siblings = {key: item for key, item in rule.items() if key != "$ref"}
            if siblings:
                check(value, siblings, path)
            return
        if "allOf" in rule:
            for item in rule["allOf"]:
                check(value, item, path)
        if "oneOf" in rule:
            candidates: list[list[dict[str, str]]] = []
            for item in rule["oneOf"]:
                start = len(errors)
                check(value, item, path)
                candidates.append(errors[start:])
                del errors[start:]
            passing = sum(not candidate for candidate in candidates)
            if passing != 1:
                add(path, f"oneOf 必须恰有一个分支通过，实际为 {passing}")
                if passing == 0 and candidates:
                    errors.extend(min(candidates, key=len)[:8])
                return
        if "const" in rule and value != rule["const"]:
            add(path, f"必须等于 {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            add(path, f"不在允许枚举中: {value!r}")

        expected = rule.get("type")
        if expected is not None:
            expected_types = [expected] if isinstance(expected, str) else expected
            if not any(_is_type(value, item) for item in expected_types):
                add(path, f"类型应为 {expected_types}，实际为 {type(value).__name__}")
                return

        if isinstance(value, dict):
            required = rule.get("required", [])
            for key in required:
                if key not in value:
                    add(path, f"缺少必填字段 {key!r}")
            properties = rule.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    check(item, properties[key], _path(path, key))
                elif rule.get("additionalProperties") is False:
                    add(_path(path, key), "不允许额外字段")
                elif isinstance(rule.get("additionalProperties"), dict):
                    check(item, rule["additionalProperties"], _path(path, key))

        if isinstance(value, list):
            if "minItems" in rule and len(value) < rule["minItems"]:
                add(path, f"数组项数不能少于 {rule['minItems']}")
            if "maxItems" in rule and len(value) > rule["maxItems"]:
                add(path, f"数组项数不能多于 {rule['maxItems']}")
            if rule.get("uniqueItems"):
                serialized = [json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False) for item in value]
                if len(serialized) != len(set(serialized)):
                    add(path, "数组项必须唯一")
            if "items" in rule:
                for index, item in enumerate(value):
                    check(item, rule["items"], _path(path, index))

        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                add(path, f"字符串长度不能小于 {rule['minLength']}")
            if "maxLength" in rule and len(value) > rule["maxLength"]:
                add(path, f"字符串长度不能大于 {rule['maxLength']}")
            if "pattern" in rule and re.search(rule["pattern"], value) is None:
                add(path, f"字符串不匹配模式 {rule['pattern']!r}")
            if rule.get("format") == "date-time" and not _date_time(value):
                add(path, "不是合法 RFC 3339 date-time")

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric = float(value)
            if not math.isfinite(numeric):
                add(path, "数值必须有限")
                return
            if "minimum" in rule and numeric < rule["minimum"]:
                add(path, f"数值不能小于 {rule['minimum']}")
            if "maximum" in rule and numeric > rule["maximum"]:
                add(path, f"数值不能大于 {rule['maximum']}")
            if "exclusiveMinimum" in rule and numeric <= rule["exclusiveMinimum"]:
                add(path, f"数值必须大于 {rule['exclusiveMinimum']}")
            if "exclusiveMaximum" in rule and numeric >= rule["exclusiveMaximum"]:
                add(path, f"数值必须小于 {rule['exclusiveMaximum']}")

    check(instance, schema, "$")
    return errors
