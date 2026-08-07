#!/usr/bin/env python3
"""Dependency-free validator for every JSON Schema keyword used by this skill.

The public validator also runs jsonschema.Draft202012Validator when the optional
dependency is installed. This module prevents a missing dependency from turning
validation into a no-op.
"""

from __future__ import annotations

import re
from typing import Any


def _resolve(root: dict[str, Any], pointer: str) -> dict[str, Any]:
    if not pointer.startswith("#/"):
        raise ValueError(f"only local JSON pointers are supported: {pointer}")
    value: Any = root
    for token in pointer[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    if not isinstance(value, dict):
        raise ValueError(f"reference does not resolve to a schema object: {pointer}")
    return value


def _is_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"unsupported JSON Schema type: {expected}")


def validate(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    root = schema if root is None else root
    if "$ref" in schema:
        return validate(instance, _resolve(root, schema["$ref"]), root, path)

    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} is not in the allowed enum")

    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(instance, item) for item in choices):
            errors.append(f"{path}: expected type {choices}, got {type(instance).__name__}")
            return errors

    if "allOf" in schema:
        for part in schema["allOf"]:
            errors.extend(validate(instance, part, root, path))
    if "anyOf" in schema and not any(not validate(instance, part, root, path) for part in schema["anyOf"]):
        errors.append(f"{path}: does not satisfy anyOf")
    if "oneOf" in schema:
        matches = sum(not validate(instance, part, root, path) for part in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: must satisfy exactly one oneOf branch (matched {matches})")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}.{key}: required property is missing")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(validate(value, properties[key], root, child_path))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{child_path}: additional property is not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(validate(value, schema["additionalProperties"], root, child_path))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: has more than {schema['maxItems']} item(s)")
        if schema.get("uniqueItems"):
            for index, item in enumerate(instance):
                if item in instance[:index]:
                    errors.append(f"{path}[{index}]: duplicate item")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{index}]"))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} is below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} exceeds maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: {instance} must exceed {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: {instance} must be below {schema['exclusiveMaximum']}")
    return errors
