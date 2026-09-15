"""Per-sample and majority-vote correctness labels for generated samples.

Category rules:
    factual   -- normalized exact match against the ground-truth string;
                 partial/alias-like matches are flagged `needs_review`
    math      -- final numeric answer extracted from the sample, compared
                 numerically (tolerance 1e-6)
    reasoning -- final yes/no extracted from the sample, compared directly

Outputs:
    results/correctness.jsonl    one row per question with per-sample labels
    results/needs_review.jsonl   questions with at least one needs_review sample

Usage:
    python score_correctness.py
    python score_correctness.py --limit 20 --model qwen/qwen3.8-27b
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

import uq_common as uq


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
        per_sample.append(
            {
                "sample_id": record.get("sample_id"),
                "label": label,
                "extracted": extracted,
                "finish_reason": record.get("finish_reason"),
            }
        )

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
    parser = argparse.ArgumentParser(description="Label sample correctness.")
    parser.add_argument("--model", help="only score samples from this model_name")
    parser.add_argument("--provider", help="only score samples from this provider")
    parser.add_argument("--dataset", default=None, help="dataset file to score (default: main dataset)")
    parser.add_argument("--limit", type=int, help="max questions to score")
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "correctness.jsonl"))
    args = parser.parse_args()

    uq.ensure_results_dir()
    questions = uq.load_questions(args.dataset)
    samples, counts = uq.load_samples()
    model, provider = uq.resolve_filters(args, counts)
    if model or provider:
        samples, _ = uq.load_samples(model=model, provider=provider)

    if args.limit:
        questions = questions[: args.limit]

    rows = []
    for question in questions:
        rows.append(score_question(question, samples.get(question["question_id"], [])))

    uq.write_jsonl(uq.RESULTS_DIR / "needs_review.jsonl", [r for r in rows if r["n_needs_review"] > 0])
    uq.write_jsonl(args.output, rows)

    print(f"scored {len(rows)} questions -> {args.output}")
    for category in ("factual", "math", "reasoning"):
        group = [r for r in rows if r["category"] == category]
        if not group:
            continue
        majority = Counter(r["majority_label"] for r in group)
        sample_labels = Counter()
        for row in group:
            for sample in row["per_sample"]:
                sample_labels[sample["label"]] += 1
        print(f"{category:<10} questions={len(group):>3} majority={dict(majority)}")
        print(f"{'':<10} sample labels={dict(sample_labels)}")
    unresolved = sum(1 for r in rows if r["majority_label"] == "unresolved")
    print(f"unresolved questions (excluded from AUROC): {unresolved}")
    print(f"questions with any needs_review sample: {sum(1 for r in rows if r['n_needs_review'] > 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
