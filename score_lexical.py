"""Lexical uncertainty via pairwise Jaccard similarity over word n-grams.

For each question the n-gram sets of its samples are compared pairwise; the
uncertainty score is 1 - average pairwise Jaccard similarity. Pure Python,
no models required.

Outputs:
    results/lexical.jsonl -- question_id, category, n_samples, avg_similarity,
                             uncertainty, pairwise similarities

Usage:
    python score_lexical.py
    python score_lexical.py --ngram 1 --limit 50
"""

from __future__ import annotations

import argparse
import itertools
import sys
from collections import defaultdict

import uq_common as uq


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Lexical (n-gram Jaccard) uncertainty.")
    parser.add_argument("--model", help="only score samples from this model_name")
    parser.add_argument("--provider", help="only score samples from this provider")
    parser.add_argument("--limit", type=int, help="max questions to score")
    parser.add_argument("--ngram", type=int, default=2, help="word n-gram size (default 2)")
    parser.add_argument("--min-samples", type=int, default=2, help="skip questions with fewer samples")
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "lexical.jsonl"))
    args = parser.parse_args()

    uq.ensure_results_dir()
    questions = uq.load_questions()
    samples, counts = uq.load_samples()
    model, provider = uq.resolve_filters(args, counts)
    if model or provider:
        samples, _ = uq.load_samples(model=model, provider=provider)

    if args.limit:
        questions = questions[: args.limit]

    rows = []
    totals: dict[str, list[float]] = defaultdict(list)
    skipped = 0
    for question in questions:
        records = samples.get(question["question_id"], [])
        texts = [(r.get("response_text") or "").strip() for r in records]
        texts = [t for t in texts if t]
        if len(texts) < args.min_samples:
            skipped += 1
            continue

        sets = [uq.ngram_set(uq.tokenize(text), args.ngram) for text in texts]
        pair_sims = [uq.jaccard(a, b) for a, b in itertools.combinations(sets, 2)]
        average = sum(pair_sims) / len(pair_sims) if pair_sims else 0.0
        uncertainty = 1.0 - average
        rows.append(
            {
                "question_id": question["question_id"],
                "category": question["category"],
                "n_samples": len(texts),
                "ngram": args.ngram,
                "avg_similarity": round(average, 6),
                "uncertainty": round(uncertainty, 6),
                "pairwise_similarities": [round(value, 6) for value in pair_sims],
            }
        )
        totals[question["category"]].append(uncertainty)

    uq.write_jsonl(args.output, rows)
    print(f"scored {len(rows)} questions (skipped {skipped} with <{args.min_samples} samples) -> {args.output}")
    for category in ("factual", "math", "reasoning"):
        values = totals.get(category, [])
        if values:
            mean = sum(values) / len(values)
            print(f"{category:<10} n={len(values):>3} mean lexical uncertainty={mean:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
