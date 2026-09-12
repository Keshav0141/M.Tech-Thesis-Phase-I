"""Validate the generated dataset before it is locked for experiments.

Checks:
    - JSON parses and every entry has all required fields of the right type
    - question_id is unique and follows the <category>_NNNN pattern
    - no exact duplicate questions (normalized text)
    - no near-duplicate questions (sequence ratio >= threshold)
    - ground truth format matches the category (text / number / yes-no)
    - category balance and difficulty spread
    - optional: generation-log coverage per model (--check-logs)

Usage:
    python validate_dataset.py
    python validate_dataset.py --check-logs --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import config

REQUIRED_FIELDS = {
    "question_id": str,
    "category": str,
    "question_text": str,
    "ground_truth_answer": str,
    "source_dataset": str,
    "difficulty_flag": str,
    "validation_status": str,
}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_STATUS = {"auto_validated", "spot_checked", "rejected"}
ID_RE = re.compile(r"^(factual|math|reasoning)_\d{4}$")
NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_entries(dataset: list) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(dataset, list):
        return ["dataset.json must contain a JSON array"], warnings

    ids = Counter()
    texts: dict[str, str] = {}
    near_pairs: list[tuple[str, str, float]] = []
    seen_normalized: list[tuple[str, str]] = []

    for index, entry in enumerate(dataset):
        where = f"entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{where}: not a JSON object")
            continue
        for field, field_type in REQUIRED_FIELDS.items():
            if field not in entry:
                errors.append(f"{where}: missing field '{field}'")
            elif not isinstance(entry[field], field_type):
                errors.append(f"{where}: field '{field}' should be {field_type.__name__}")
        if errors and any(where in e for e in errors[-len(REQUIRED_FIELDS):]):
            continue

        qid = entry["question_id"]
        ids[qid] += 1
        if not ID_RE.match(qid):
            errors.append(f"{qid}: malformed question_id")
        if entry["category"] not in config.CATEGORIES:
            errors.append(f"{qid}: unknown category '{entry['category']}'")
        if entry["difficulty_flag"] not in VALID_DIFFICULTY:
            errors.append(f"{qid}: unknown difficulty '{entry['difficulty_flag']}'")
        if entry["validation_status"] not in VALID_STATUS:
            errors.append(f"{qid}: unknown validation_status '{entry['validation_status']}'")
        if not entry["question_text"].strip():
            errors.append(f"{qid}: empty question_text")
        if not entry["ground_truth_answer"].strip():
            errors.append(f"{qid}: empty ground_truth_answer")

        category = entry["category"]
        answer = entry["ground_truth_answer"].strip()
        if category == "math" and not NUMERIC_RE.match(answer):
            errors.append(f"{qid}: math ground truth is not numeric: {answer!r}")
        if category == "reasoning" and answer.lower() not in {"yes", "no"}:
            errors.append(f"{qid}: reasoning ground truth is not yes/no: {answer!r}")

        norm = normalize(entry["question_text"])
        if entry["validation_status"] == "rejected":
            continue
        if norm in texts:
            errors.append(f"{qid}: exact duplicate of {texts[norm]}")
        texts[norm] = qid
        for other_norm, other_id in seen_normalized:
            ratio_floor = min(len(norm), len(other_norm)) / max(len(norm), len(other_norm))
            if ratio_floor < 0.6:
                continue
            ratio = SequenceMatcher(None, norm, other_norm).ratio()
            if ratio >= config.NEAR_DUPLICATE_THRESHOLD:
                near_pairs.append((qid, other_id, round(ratio, 3)))
        seen_normalized.append((norm, qid))

    duplicate_ids = [qid for qid, count in ids.items() if count > 1]
    for qid in duplicate_ids:
        errors.append(f"duplicate question_id: {qid}")
    for qid, other_id, ratio in near_pairs[:20]:
        warnings.append(f"near duplicate: {qid} ~ {other_id} (ratio {ratio})")

    return errors, warnings


def coverage_report(dataset: list) -> str:
    if not config.GENERATIONS_PATH.exists():
        return "generations.jsonl not found (nothing generated yet)"
    per_model: dict[tuple[str, str], set] = defaultdict(set)
    samples: Counter = Counter()
    with config.GENERATIONS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") != "ok":
                continue
            key = (record.get("provider", "?"), record.get("model_name", "?"))
            per_model[key].add((record["question_id"], record["sample_id"]))
            samples[key] += 1

    total = len([e for e in dataset if e.get("validation_status") != "rejected"])
    lines = ["Generation coverage:"]
    for (provider, model), pairs in sorted(per_model.items()):
        questions = {qid for qid, _ in pairs}
        lines.append(
            f"  {provider}/{model}: {len(questions)}/{total} questions, {samples[(provider, model)]} successful samples"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate data/dataset.json")
    parser.add_argument("--dataset", default=str(config.DATASET_PATH))
    parser.add_argument("--check-logs", action="store_true", help="also report generation-log coverage")
    parser.add_argument("--write", action="store_true", help="write report to logs/validation_report.txt")
    args = parser.parse_args()

    try:
        dataset = json.loads(open(args.dataset, encoding="utf-8").read())
    except FileNotFoundError:
        print(f"FAIL: dataset not found at {args.dataset}")
        return 1
    except json.JSONDecodeError as error:
        print(f"FAIL: dataset is not valid JSON: {error}")
        return 1

    errors, warnings = validate_entries(dataset)
    active = [e for e in dataset if isinstance(e, dict) and e.get("validation_status") != "rejected"]
    rejected = [e for e in dataset if isinstance(e, dict) and e.get("validation_status") == "rejected"]
    counts = Counter(entry["category"] for entry in active)
    difficulties = Counter(entry.get("difficulty_flag") for entry in active)
    statuses = Counter(entry.get("validation_status") for entry in dataset if isinstance(entry, dict))

    lines = []
    lines.append("Dataset validation report")
    lines.append("=" * 60)
    lines.append(f"Active questions: {len(active)} (rejected entries retained: {len(rejected)})")
    lines.append("Category counts : " + ", ".join(f"{c}={counts.get(c, 0)}" for c in config.CATEGORIES))
    if counts:
        spread = max(counts.values()) - min(counts.values())
        lines.append(f"Balance spread  : {spread} (max-min); imbalance = {spread / max(counts.values()):.1%}")
    lines.append("Difficulty      : " + ", ".join(f"{k}={v}" for k, v in sorted(difficulties.items())))
    lines.append("Statuses        : " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    lines.append("")

    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        lines.extend(f"  FAIL: {error}" for error in errors)
    else:
        lines.append("All structural checks passed.")

    if warnings:
        lines.append("")
        lines.append(f"WARNINGS ({len(warnings)}):")
        lines.extend(f"  warn: {warning}" for warning in warnings)
    else:
        lines.append("No duplicate/near-duplicate warnings.")

    if args.check_logs:
        lines.append("")
        lines.append(coverage_report(dataset))

    report = "\n".join(lines)
    print(report)
    if args.write:
        config.LOGS_DIR.joinpath("validation_report.txt").write_text(report, encoding="utf-8")
        print(f"\nReport written to {config.LOGS_DIR / 'validation_report.txt'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
