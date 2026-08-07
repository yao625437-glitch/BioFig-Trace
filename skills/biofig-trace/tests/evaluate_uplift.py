"""Independent field-level scorer for paired Skill/baseline evaluations.

This module intentionally imports only the Python standard library.  It does
not call BioFig Trace's schema, semantic, report, or finalization validators;
the evaluator must remain an independent measurement component.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import unicodedata
from pathlib import Path
from typing import Any


SCORER_VERSION = "1.0"
EXPECTED_RUNS_PER_TASK = 3


class ScoringError(ValueError):
    """Raised when a gold or run document violates the scorer contract."""


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _normalize_space(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _normalize_key_value(value: Any) -> Any:
    """Normalize scientific-key values without weakening scientific values."""

    if isinstance(value, str):
        return _normalize_space(value).casefold()
    if value is None or isinstance(value, bool):
        return value
    if _is_finite_number(value):
        number = float(value)
        return int(number) if number.is_integer() else number
    if isinstance(value, list):
        return [_normalize_key_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(field): _normalize_key_value(item)
            for field, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    raise ScoringError(f"scientific key contains unsupported value: {value!r}")


def scientific_key(atom: dict[str, Any]) -> str:
    """Return an order-independent identity for one atomic scientific fact."""

    key = atom.get("key")
    if not isinstance(key, dict) or not key:
        raise ScoringError("every atom requires a non-empty object at 'key'")
    normalized = _normalize_key_value(key)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalize_unit(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ScoringError("unit must be a string or null")
    # NFKC makes the micro sign and Greek mu comparable while preserving case,
    # which is scientifically important for units such as mM and mm.
    return _normalize_space(value)


def _nonnegative_tolerance(match: dict[str, Any], name: str) -> float:
    value = match.get(name, 0.0)
    if not _is_finite_number(value) or float(value) < 0:
        raise ScoringError(f"{name} must be a finite non-negative number")
    return float(value)


def _atoms_match(gold: dict[str, Any], prediction: dict[str, Any]) -> bool:
    match = gold.get("match", {})
    if not isinstance(match, dict):
        raise ScoringError("gold atom 'match' must be an object")

    gold_value = gold.get("value")
    mode = match.get("type")
    if mode is None:
        mode = "numeric" if _is_finite_number(gold_value) else "exact"

    if mode == "numeric":
        predicted_value = prediction.get("value")
        if not _is_finite_number(gold_value):
            raise ScoringError("numeric gold atom requires a finite numeric value")
        if not _is_finite_number(predicted_value):
            return False
        if "unit" in gold:
            try:
                if _normalize_unit(prediction.get("unit")) != _normalize_unit(gold.get("unit")):
                    return False
            except ScoringError:
                return False
        absolute = _nonnegative_tolerance(match, "abs_tol")
        relative = _nonnegative_tolerance(match, "rel_tol") * abs(float(gold_value))
        digitization = _nonnegative_tolerance(match, "digitization_tol")
        tolerance = max(absolute, relative, digitization)
        return abs(float(predicted_value) - float(gold_value)) <= tolerance

    if mode == "normalized_text":
        predicted_value = prediction.get("value")
        if not isinstance(gold_value, str) or not isinstance(predicted_value, str):
            return False
        return _normalize_space(predicted_value).casefold() == _normalize_space(gold_value).casefold()

    if mode == "exact":
        if "value" not in prediction:
            return False
        predicted_value = prediction["value"]
        # Avoid Python's surprising True == 1 behavior for JSON scalar values.
        if isinstance(gold_value, bool) or isinstance(predicted_value, bool):
            return type(gold_value) is type(predicted_value) and gold_value == predicted_value
        return predicted_value == gold_value

    raise ScoringError(f"unsupported match type: {mode!r}")


def _group_atoms(atoms: Any, label: str) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(atoms, list):
        raise ScoringError(f"{label} atoms must be an array")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            raise ScoringError(f"{label} atom {index} must be an object")
        grouped.setdefault(scientific_key(atom), []).append(atom)
    return grouped


def score_run(gold_task: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Score one run using gold atoms and unsupported-extra-fact penalties."""

    gold_groups = _group_atoms(gold_task.get("atoms"), "gold")
    if not gold_groups:
        raise ScoringError("a gold task must contain at least one atom")
    duplicate_gold = [token for token, atoms in gold_groups.items() if len(atoms) != 1]
    if duplicate_gold:
        raise ScoringError("gold scientific keys must be unique")

    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ScoringError("every run requires a non-empty run_id")
    status = run.get("status", "completed")
    if status not in {"completed", "failed", "timeout"}:
        raise ScoringError(f"unsupported run status: {status!r}")

    gold_count = len(gold_groups)
    if status != "completed":
        return {
            "run_id": run_id,
            "status": status,
            "score": 0.0,
            "matched_atoms": 0,
            "gold_atoms": gold_count,
            "unsupported_extra_atoms": 0,
            "denominator": gold_count,
            "missed_keys": [atoms[0]["key"] for atoms in gold_groups.values()],
            "extra_keys": [],
            "duplicate_predictions": 0,
        }

    predicted_groups = _group_atoms(run.get("atoms"), "prediction")
    matched = 0
    duplicates = 0
    missed_keys: list[dict[str, Any]] = []
    extra_keys: list[dict[str, Any]] = []

    for token, gold_atoms in gold_groups.items():
        candidates = predicted_groups.get(token, [])
        if any(_atoms_match(gold_atoms[0], candidate) for candidate in candidates):
            matched += 1
        else:
            missed_keys.append(gold_atoms[0]["key"])
        if len(candidates) > 1:
            duplicates += len(candidates) - 1

    unseen_predictions = 0
    for token, candidates in predicted_groups.items():
        if token not in gold_groups:
            unseen_predictions += len(candidates)
            extra_keys.append({"key": candidates[0]["key"], "count": len(candidates)})

    unsupported_extra = unseen_predictions + duplicates
    denominator = gold_count + unsupported_extra
    return {
        "run_id": run_id,
        "status": status,
        "score": matched / denominator,
        "matched_atoms": matched,
        "gold_atoms": gold_count,
        "unsupported_extra_atoms": unsupported_extra,
        "denominator": denominator,
        "missed_keys": missed_keys,
        "extra_keys": extra_keys,
        "duplicate_predictions": duplicates,
    }


def _task_map(document: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ScoringError(f"{label} document requires a non-empty tasks array")
    mapped: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ScoringError(f"{label} task must be an object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ScoringError(f"{label} task requires a non-empty task_id")
        if task_id in mapped:
            raise ScoringError(f"duplicate {label} task_id: {task_id}")
        mapped[task_id] = task
    return mapped


def _score_three_runs(gold_task: dict[str, Any], run_task: dict[str, Any]) -> list[dict[str, Any]]:
    runs = run_task.get("runs")
    if not isinstance(runs, list) or len(runs) != EXPECTED_RUNS_PER_TASK:
        raise ScoringError(
            f"task {gold_task['task_id']} requires exactly {EXPECTED_RUNS_PER_TASK} runs"
        )
    if any(not isinstance(run, dict) for run in runs):
        raise ScoringError(f"task {gold_task['task_id']} runs must be objects")
    run_ids = [run.get("run_id") for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise ScoringError(f"task {gold_task['task_id']} contains duplicate run_id values")
    return [score_run(gold_task, run) for run in runs]


def evaluate_uplift(
    gold_document: dict[str, Any],
    skill_document: dict[str, Any],
    baseline_document: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate paired three-run Skill and baseline documents."""

    gold_tasks = _task_map(gold_document, "gold")
    skill_tasks = _task_map(skill_document, "skill")
    baseline_tasks = _task_map(baseline_document, "baseline")
    expected_ids = set(gold_tasks)
    if set(skill_tasks) != expected_ids or set(baseline_tasks) != expected_ids:
        raise ScoringError("gold, Skill, and baseline task_id sets must be identical")

    per_task: list[dict[str, Any]] = []
    category_buckets: dict[str, list[dict[str, Any]]] = {}
    for task_id in sorted(expected_ids):
        gold_task = gold_tasks[task_id]
        skill_runs = _score_three_runs(gold_task, skill_tasks[task_id])
        baseline_runs = _score_three_runs(gold_task, baseline_tasks[task_id])
        skill_median = statistics.median(run["score"] for run in skill_runs)
        baseline_median = statistics.median(run["score"] for run in baseline_runs)
        category = gold_task.get("category", "uncategorized")
        if not isinstance(category, str) or not category:
            raise ScoringError(f"task {task_id} category must be a non-empty string")
        result = {
            "task_id": task_id,
            "category": category,
            "skill_runs": skill_runs,
            "baseline_runs": baseline_runs,
            "skill_median": skill_median,
            "baseline_median": baseline_median,
            "uplift": skill_median - baseline_median,
        }
        per_task.append(result)
        category_buckets.setdefault(category, []).append(result)

    categories: dict[str, dict[str, Any]] = {}
    for category, results in sorted(category_buckets.items()):
        skill_score = statistics.fmean(item["skill_median"] for item in results)
        baseline_score = statistics.fmean(item["baseline_median"] for item in results)
        categories[category] = {
            "task_count": len(results),
            "skill_score": skill_score,
            "baseline_score": baseline_score,
            "uplift": skill_score - baseline_score,
        }

    skill_macro = statistics.fmean(item["skill_median"] for item in per_task)
    baseline_macro = statistics.fmean(item["baseline_median"] for item in per_task)
    return {
        "scorer_version": SCORER_VERSION,
        "runs_per_task": EXPECTED_RUNS_PER_TASK,
        "tasks": per_task,
        "categories": categories,
        "summary": {
            "task_count": len(per_task),
            "skill_macro_score": skill_macro,
            "baseline_macro_score": baseline_macro,
            "macro_uplift": skill_macro - baseline_macro,
        },
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ScoringError(f"{path} must contain a JSON object")
    return document


def evaluate_files(gold_path: Path, skill_path: Path, baseline_path: Path) -> dict[str, Any]:
    return evaluate_uplift(
        _load_json(gold_path),
        _load_json(skill_path),
        _load_json(baseline_path),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score three paired Skill/baseline runs using independent scientific atoms."
    )
    parser.add_argument("--gold", type=Path, required=True, help="Gold task JSON document")
    parser.add_argument("--skill-runs", type=Path, required=True, help="Three-run Skill JSON document")
    parser.add_argument(
        "--baseline-runs", type=Path, required=True, help="Three-run no-Skill baseline JSON document"
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = evaluate_files(args.gold, args.skill_runs, args.baseline_runs)
    except (OSError, json.JSONDecodeError, ScoringError) as error:
        print(f"evaluation failed: {error}", file=sys.stderr)
        return 2
    indent = None if args.compact else 2
    print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
