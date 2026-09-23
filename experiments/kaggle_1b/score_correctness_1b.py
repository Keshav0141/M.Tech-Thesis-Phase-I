"""Isolated correctness scoring for 1B experiment.

Reads from data/dataset.json (read-only) and experiments/kaggle_1b/logs/generations_1b.jsonl,
writes only to experiments/kaggle_1b/results/correctness_1b.jsonl.

This is a copy-adapt of scoring/score_correctness.py, adapted to take
--generations / --dataset / --output so it can run isolated without
touching the main pipeline's config.GENERATIONS_PATH.

Usage:
    python score_correctness_1b.py --generations logs/generations_1b.jsonl --output results/correctness_1b.jsonl
    python score_correctness_1b.py --dataset data/dataset.json --generations logs/generations_1b.jsonl --output results/correctness_1b.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset.json"
DEFAULT_GENERATIONS = HERE / "logs" / "generations_1b.jsonl"
DEFAULT_OUTPUT = HERE / "results" / "correctness_1b.jsonl"

# Import shared helpers without pulling config.GENERATIONS_PATH
sys.path.insert(0, str(PROJECT_ROOT / "scoring"))
import uq_common as uq  # noqa: E402


def load_questions(dataset_path: Path) -> list[dict]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [q for q in dataset if q.get("validation_status") != "rejected"]


def load_samples_1b(generations_path: Path) -> dict[str, list[dict]]:
    samples: dict[str, list[dict]] = defaultdict(list)
    if not generations_path.exists():
        return samples
    with generations_path.open("r", encoding="utf-8") as handle:
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
            samples[record["question_id"]].append(record)
    for qid in samples:
        samples[qid].sort(key=lambda r: int(r.get("sample_id", -1)))
    return samples


def score_question(question: dict, samples: list[dict]) -> dict:
    category = question["category"]
    ground_truth = question["ground_truth_answer"]
    per_sample = []
    counts: Counter = Counter()
    for record in samples:
        text = record.get("response_text") or ""
        if category == "factual":
            answer = uq.extract_final(text) or text
            label = uq.classify_factual(answer, ground_truth)
            extracted = answer.strip()[:200] if answer else None
        elif category == "math":
            label, extracted = uq.classify_math(text, ground_truth)
        else:
            label, extracted = uq.classify_reasoning(text, ground_truth)
        counts[label] += 1
        per_sample.append({
            "sample_id": record.get("sample_id"),
            "label": label,
            "extracted": extracted,
        })
    n = len(samples)
    n_correct = counts["correct"]
    n_incorrect = counts["incorrect"]
    n_needs_review = counts["needs_review"]
    n_no_extraction = counts["no_extraction"]
    if n == 0:
        majority, overall = "no_samples", None
    elif n_correct > max(n_incorrect, n_needs_review + n_no_extraction):
        majority, overall = "correct", 1
    elif n_incorrect > max(n_correct, n_needs_review + n_no_extraction):
        majority, overall = "incorrect", 0
    else:
        majority, overall = "unresolved", None
    return {
        "question_id": question["question_id"],
        "category": category,
        "ground_truth": ground_truth,
        "n_samples": n,
        "n_correct": n_correct,
        "n_incorrect": n_incorrect,
        "n_needs_review": n_needs_review,
        "n_no_extraction": n_no_extraction,
        "majority_label": majority,
        "overall_correct": overall,
        "per_sample": per_sample,
    }


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Isolated 1B correctness scoring.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="dataset json (read-only)")
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS), help="1B generations jsonl")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="output correctness jsonl")
    parser.add_argument("--limit", type=int, help="max questions to score")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    generations_path = Path(args.generations)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(dataset_path)
    samples = load_samples_1b(generations_path)
    if args.limit:
        questions = questions[: args.limit]

    rows = [score_question(q, samples.get(q["question_id"], [])) for q in questions]
    # write output
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    # also write needs_review subset inside isolated results
    needs = [r for r in rows if r["n_needs_review"] > 0]
    with (output_path.parent / "needs_review_1b.jsonl").open("w", encoding="utf-8") as handle:
        for row in needs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"scored {len(rows)} questions -> {output_path}")
    for category in ("factual", "math", "reasoning"):
        group = [r for r in rows if r["category"] == category]
        if not group:
            continue
        majority = Counter(r["majority_label"] for r in group)
        sample_labels = Counter()
        for row in group:
            for s in row["per_sample"]:
                sample_labels[s["label"]] += 1
        print(f"{category:<10} questions={len(group):>3} majority={dict(majority)}")
        print(f"{'':<10} sample labels={dict(sample_labels)}")
    unresolved = sum(1 for r in rows if r["majority_label"] == "unresolved")
    print(f"unresolved (excluded from AUROC): {unresolved}")
    print(f"needs_review: {len(needs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
