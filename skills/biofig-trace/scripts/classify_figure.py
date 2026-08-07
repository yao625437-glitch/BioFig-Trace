"""Return auditable figure-type candidates without silently guessing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import SCHEMA_ROOT, load_json


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    return load_json(path or (SCHEMA_ROOT / "figure_registry_v3.json"))


def _keyword_occurrences(text: str, keyword: str) -> int:
    folded = keyword.casefold().strip()
    if not folded:
        return 0
    if re.fullmatch(r"[a-z0-9+_.% -]+", folded):
        pattern = rf"(?<![a-z0-9]){re.escape(folded)}(?![a-z0-9])"
    else:
        pattern = re.escape(folded)
    return len(re.findall(pattern, text))


def _keyword_weight(keyword: str) -> int:
    # Specific multi-word scientific phrases must outrank a generic token.
    # Example: "scale bar" is microscopy evidence, not a bar-chart label.
    return min(3, 1 + keyword.strip().count(" "))


def classify(description: str, explicit_type: str | None = None, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    rules = registry["figure_types"]
    if explicit_type:
        if explicit_type not in rules:
            return {"status": "unresolved", "needs_review": True, "reason": f"未知 figure_type: {explicit_type}", "candidates": []}
        rule = rules[explicit_type]
        return {
            "status": "resolved",
            "figure_type": explicit_type,
            "function_category": rule["allowed_categories"][0],
            "result_template": rule["allowed_templates"][0],
            "confidence": 1.0,
            "needs_review": False,
            "reason": "使用调用方提供并在注册表中验证的明确图型。",
            "candidates": [{"figure_type": explicit_type, "score": 1.0}],
        }

    haystack = re.sub(r"\s+", " ", description.casefold())
    scored: list[tuple[str, int, list[str]]] = []
    for figure_type, rule in rules.items():
        occurrences = [(keyword, _keyword_occurrences(haystack, keyword)) for keyword in rule.get("keywords", [])]
        hits = [keyword for keyword, count in occurrences if count]
        score = sum(count * _keyword_weight(keyword) for keyword, count in occurrences)
        if score:
            scored.append((figure_type, score, hits))
    scored.sort(key=lambda item: (-item[1], item[0]))
    candidates = [
        {
            "figure_type": name,
            "function_category": rules[name]["allowed_categories"][0],
            "result_template": rules[name]["allowed_templates"][0],
            "score": score,
            "matched_keywords": hits,
        }
        for name, score, hits in scored[:5]
    ]
    if not candidates:
        return {
            "status": "unresolved",
            "figure_type": None,
            "function_category": None,
            "result_template": None,
            "confidence": 0.0,
            "needs_review": True,
            "reason": "没有足够的用途或语义线索；不得根据几何形状静默猜测。",
            "candidates": [],
        }
    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0
    margin = top["score"] - second_score
    confidence = min(0.95, 0.45 + 0.1 * top["score"] + 0.08 * margin)
    needs_review = top["score"] < 2 or margin < 1
    return {
        "status": "provisional" if needs_review else "resolved",
        "figure_type": top["figure_type"],
        "function_category": top["function_category"],
        "result_template": top["result_template"],
        "confidence": round(confidence, 2),
        "needs_review": needs_review,
        "reason": "候选接近或线索不足，需人工确认。" if needs_review else "依据用途关键词与专门图型线索分类。",
        "candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("description", help="图注、轴标签或对图的忠实描述")
    parser.add_argument("--type", dest="explicit_type", help="已人工确认的注册表 figure_type")
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    result = classify(args.description, args.explicit_type, load_registry(args.registry))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "resolved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
