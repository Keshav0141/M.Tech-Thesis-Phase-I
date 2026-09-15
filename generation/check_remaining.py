"""Report generation progress per category without reading the raw JSONL.

Usage:
    python check_remaining.py
    python check_remaining.py --category math
    python check_remaining.py --n 5 --model openai/gpt-oss-20b
    python check_remaining.py --json
    python check_remaining.py --list-gaps

Exit code is 0 when every active question has n samples, 1 otherwise, so it
can be used in a daily shell loop:
    python check_remaining.py || python generation/generate.py --category factual --n 5 --temperature 0.7
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


def iter_ok_records(model_filter: str | None):
    if not config.GENERATIONS_PATH.exists():
        return
    with config.GENERATIONS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") != "ok":
                continue
            if model_filter and record.get("model_name") != model_filter:
                continue
            yield record


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Show how many samples are still missing.")
    parser.add_argument("--n", type=int, default=config.N_SAMPLES_DEFAULT, help="samples expected per question")
    parser.add_argument("--category", choices=config.CATEGORIES, help="restrict to one category")
    parser.add_argument("--dataset", default=str(config.DATASET_PATH), help="dataset file to check (default: main dataset)")
    parser.add_argument("--model", help="count only samples from this model_name")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--list-gaps", action="store_true", help="print each question still missing samples")
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    categories = [args.category] if args.category else list(config.CATEGORIES)
    active = [
        question
        for question in dataset
        if question.get("validation_status") != "rejected" and question["category"] in categories
    ]
    active_ids = {question["question_id"] for question in active}

    have: dict[str, set[int]] = defaultdict(set)
    providers = Counter()
    for record in iter_ok_records(args.model):
        if record["question_id"] in active_ids:
            have[record["question_id"]].add(int(record["sample_id"]))
            providers[record.get("provider", "?")] += 1

    report: dict[str, dict] = {}
    total_missing = 0
    total_done = 0
    total_expected = 0
    for category in categories:
        items = [question for question in active if question["category"] == category]
        missing_samples = 0
        complete_questions = 0
        samples_done = 0
        gaps: list[tuple[str, list[int]]] = []
        for question in items:
            got = {sample for sample in have.get(question["question_id"], set()) if 0 <= sample < args.n}
            samples_done += len(got)
            absent = sorted(set(range(args.n)) - got)
            if absent:
                missing_samples += len(absent)
                gaps.append((question["question_id"], absent))
            else:
                complete_questions += 1
        expected = len(items) * args.n
        total_missing += missing_samples
        total_done += samples_done
        total_expected += expected
        report[category] = {
            "questions": len(items),
            "questions_complete": complete_questions,
            "samples_done": samples_done,
            "samples_expected": expected,
            "samples_missing": missing_samples,
            "gaps": gaps,
        }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if total_missing == 0 else 1

    header = f"Resume check (n={args.n}" + (f", model={args.model}" if args.model else "") + ")"
    print(header)
    print("=" * len(header))
    print(f"{'category':<10} {'questions':>14} {'samples':>16} {'missing':>8}")
    for category in categories:
        row = report[category]
        print(
            f"{category:<10} {row['questions_complete']:>6}/{row['questions']:<6} "
            f"{row['samples_done']:>7}/{row['samples_expected']:<7} {row['samples_missing']:>8}"
        )
    print(f"{'TOTAL':<10} {'':>14} {total_done:>7}/{total_expected:<7} {total_missing:>8}")
    if providers:
        print("logged samples by provider: " + ", ".join(f"{name}={count}" for name, count in providers.most_common()))

    if args.list_gaps:
        print()
        for category in categories:
            for question_id, absent in report[category]["gaps"]:
                print(f"  {question_id}: missing sample_ids {absent}")

    if total_missing == 0:
        print("\nAll categories complete.")
    else:
        print("\nNext (runs skip completed samples automatically):")
        for category in categories:
            if report[category]["samples_missing"]:
                print(
                    f"  python generation/generate.py --category {category} --n {args.n} --temperature 0.7 "
                    "--provider groq --model qwen/qwen3.8-27b --reasoning-effort none --sleep 22"
                )
    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
