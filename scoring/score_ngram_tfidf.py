"""Lexical uncertainty baselines: bigram, trigram, and TF-IDF.

Per question, over the N samples:
    bigram_uncertainty  = 1 - mean pairwise Jaccard over word-bigram sets
    trigram_uncertainty = 1 - mean pairwise Jaccard over word-trigram sets
    tfidf_uncertainty   = 1 - mean pairwise cosine similarity of TF-IDF vectors

TF-IDF uses a global IDF (smoothed log document frequency over all samples in
the generation log), L2-normalized vectors, computed in pure Python.

Outputs:
    results/ngram_tfidf.jsonl -- one row per question with >=2 samples

Usage:
    python scoring/score_ngram_tfidf.py
    python scoring/score_ngram_tfidf.py --limit 100
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq


def build_idf(all_samples: list[list[str]]) -> dict[str, float]:
    document_frequency: Counter = Counter()
    total_documents = 0
    for tokens in all_samples:
        if not tokens:
            continue
        total_documents += 1
        for token in set(tokens):
            document_frequency[token] += 1
    return {
        token: math.log((total_documents + 1) / (count + 1)) + 1.0
        for token, count in document_frequency.items()
    }


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    term_frequency = Counter(tokens)
    vector = {token: term_frequency[token] * idf[token] for token in term_frequency if idf.get(token, 0.0) > 0}
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return {}
    return {token: value / norm for token, value in vector.items()}


def cosine(vector_a: dict[str, float], vector_b: dict[str, float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    common = set(vector_a) & set(vector_b)
    if not common:
        return 0.0
    return sum(vector_a[token] * vector_b[token] for token in common)


def mean_pairwise(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Bigram / trigram / TF-IDF uncertainty baselines.")
    parser.add_argument("--model", help="only score samples from this model_name")
    parser.add_argument("--provider", help="only score samples from this provider")
    parser.add_argument("--limit", type=int, help="max questions to score")
    parser.add_argument("--min-samples", type=int, default=2)
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "ngram_tfidf.jsonl"))
    args = parser.parse_args()

    uq.ensure_results_dir()
    questions = uq.load_questions()
    samples, counts = uq.load_samples()
    model, provider = uq.resolve_filters(args, counts)
    if model or provider:
        samples, _ = uq.load_samples(model=model, provider=provider)

    if args.limit:
        questions = questions[: args.limit]

    all_token_lists: list[list[str]] = [
        uq.tokenize(record.get("response_text") or "")
        for records in samples.values()
        for record in records
    ]
    idf = build_idf(all_token_lists)
    print(f"global IDF built over {len(all_token_lists)} samples, {len(idf)} unique tokens")

    rows = []
    totals: dict[str, list[float]] = defaultdict(list)
    skipped = 0
    for question in questions:
        records = samples.get(question["question_id"], [])
        texts = [(r.get("response_text") or "").strip() for r in records]
        texts = [text for text in texts if text]
        if len(texts) < args.min_samples:
            skipped += 1
            continue

        token_lists = [uq.tokenize(text) for text in texts]
        bigrams = [uq.ngram_set(tokens, 2) for tokens in token_lists]
        trigrams = [uq.ngram_set(tokens, 3) for tokens in token_lists]
        vectors = [tfidf_vector(tokens, idf) for tokens in token_lists]

        bigram_sims = [uq.jaccard(a, b) for a, b in itertools.combinations(bigrams, 2)]
        trigram_sims = [uq.jaccard(a, b) for a, b in itertools.combinations(trigrams, 2)]
        tfidf_sims = [cosine(a, b) for a, b in itertools.combinations(vectors, 2)]

        bigram_uncertainty = 1.0 - mean_pairwise(bigram_sims)
        trigram_uncertainty = 1.0 - mean_pairwise(trigram_sims)
        tfidf_uncertainty = 1.0 - mean_pairwise(tfidf_sims)

        rows.append(
            {
                "question_id": question["question_id"],
                "category": question["category"],
                "n_samples": len(texts),
                "bigram_uncertainty": round(bigram_uncertainty, 6),
                "trigram_uncertainty": round(trigram_uncertainty, 6),
                "tfidf_uncertainty": round(tfidf_uncertainty, 6),
                "avg_bigram_similarity": round(mean_pairwise(bigram_sims), 6),
                "avg_trigram_similarity": round(mean_pairwise(trigram_sims), 6),
                "avg_tfidf_similarity": round(mean_pairwise(tfidf_sims), 6),
            }
        )
        totals[question["category"]].append((bigram_uncertainty, trigram_uncertainty, tfidf_uncertainty))

    uq.write_jsonl(args.output, rows)
    print(f"scored {len(rows)} questions (skipped {skipped} with <{args.min_samples} samples) -> {args.output}")
    for category in ("factual", "math", "reasoning"):
        values = totals.get(category, [])
        if values:
            n = len(values)
            bigram = sum(v[0] for v in values) / n
            trigram = sum(v[1] for v in values) / n
            tfidf = sum(v[2] for v in values) / n
            print(f"{category:<10} n={n:>3} mean bigram={bigram:.4f} trigram={trigram:.4f} tfidf={tfidf:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
