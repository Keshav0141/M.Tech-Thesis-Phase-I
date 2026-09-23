"""Isolated uncertainty scoring for 1B experiment.

Computes unigram Jaccard and TF-IDF/bigram/trigram exactly like the main
pipeline, but reads/writes only inside experiments/kaggle_1b/.

Reads:  experiments/kaggle_1b/logs/generations_1b.jsonl
Writes: experiments/kaggle_1b/results/lexical_1b.jsonl
        experiments/kaggle_1b/results/ngram_tfidf_1b.jsonl

Usage:
    python score_uncertainty_1b.py
    python score_uncertainty_1b.py --generations logs/generations_1b.jsonl
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_GENERATIONS = HERE / "logs" / "generations_1b.jsonl"
DEFAULT_DATASET = PROJECT_ROOT / "data" / "dataset.json"
DEFAULT_LEXICAL = HERE / "results" / "lexical_1b.jsonl"
DEFAULT_NGRAM = HERE / "results" / "ngram_tfidf_1b.jsonl"

sys.path.insert(0, str(PROJECT_ROOT / "scoring"))
import uq_common as uq  # noqa: E402


def load_questions(dataset_path: Path) -> list[dict]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [q for q in dataset if q.get("validation_status") != "rejected"]


def load_samples(generations_path: Path) -> dict[str, list[dict]]:
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


def build_idf(all_samples: list[list[str]]) -> dict[str, float]:
    df: Counter = Counter()
    total = 0
    for tokens in all_samples:
        if not tokens:
            continue
        total += 1
        for tok in set(tokens):
            df[tok] += 1
    return {tok: math.log((total + 1) / (c + 1)) + 1.0 for tok, c in df.items()}


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    vec = {tok: tf[tok] * idf[tok] for tok in tf if idf.get(tok, 0) > 0}
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    if not common:
        return 0.0
    return sum(a[t] * b[t] for t in common)


def mean_pairwise(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Isolated 1B uncertainty scoring.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS))
    parser.add_argument("--lexical-output", default=str(DEFAULT_LEXICAL))
    parser.add_argument("--ngram-output", default=str(DEFAULT_NGRAM))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-samples", type=int, default=2)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    generations_path = Path(args.generations)
    lexical_path = Path(args.lexical_output)
    ngram_path = Path(args.ngram_output)
    lexical_path.parent.mkdir(parents=True, exist_ok=True)
    ngram_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(dataset_path)
    samples = load_samples(generations_path)
    if args.limit:
        questions = questions[: args.limit]

    # IDF over all samples
    all_token_lists = [uq.tokenize(r.get("response_text") or "") for recs in samples.values() for r in recs]
    idf = build_idf(all_token_lists)
    print(f"IDF built over {len(all_token_lists)} samples, {len(idf)} tokens")

    lexical_rows = []
    ngram_rows = []
    skipped = 0
    for q in questions:
        recs = samples.get(q["question_id"], [])
        texts = [(r.get("response_text") or "").strip() for r in recs]
        texts = [t for t in texts if t]
        if len(texts) < args.min_samples:
            skipped += 1
            continue
        token_lists = [uq.tokenize(t) for t in texts]
        # lexical unigram (n=1)
        sets_1 = [uq.ngram_set(toks, 1) for toks in token_lists]
        sims_1 = [uq.jaccard(a, b) for a, b in itertools.combinations(sets_1, 2)]
        avg_1 = mean_pairwise(sims_1)
        # ngram
        bigrams = [uq.ngram_set(toks, 2) for toks in token_lists]
        trigrams = [uq.ngram_set(toks, 3) for toks in token_lists]
        vecs = [tfidf_vector(toks, idf) for toks in token_lists]
        sims_bi = [uq.jaccard(a, b) for a, b in itertools.combinations(bigrams, 2)]
        sims_tri = [uq.jaccard(a, b) for a, b in itertools.combinations(trigrams, 2)]
        sims_tfidf = [cosine(a, b) for a, b in itertools.combinations(vecs, 2)]

        lexical_rows.append({
            "question_id": q["question_id"],
            "category": q["category"],
            "n_samples": len(texts),
            "ngram": 1,
            "avg_similarity": round(avg_1, 6),
            "uncertainty": round(1.0 - avg_1, 6),
            "pairwise_similarities": [round(v, 6) for v in sims_1],
        })
        ngram_rows.append({
            "question_id": q["question_id"],
            "category": q["category"],
            "n_samples": len(texts),
            "bigram_uncertainty": round(1.0 - mean_pairwise(sims_bi), 6),
            "trigram_uncertainty": round(1.0 - mean_pairwise(sims_tri), 6),
            "tfidf_uncertainty": round(1.0 - mean_pairwise(sims_tfidf), 6),
            "avg_bigram_similarity": round(mean_pairwise(sims_bi), 6),
            "avg_trigram_similarity": round(mean_pairwise(sims_tri), 6),
            "avg_tfidf_similarity": round(mean_pairwise(sims_tfidf), 6),
        })

    with lexical_path.open("w", encoding="utf-8") as h:
        for r in lexical_rows:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")
    with ngram_path.open("w", encoding="utf-8") as h:
        for r in ngram_rows:
            h.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"lexical -> {lexical_path} ({len(lexical_rows)} rows, skipped {skipped})")
    print(f"ngram_tfidf -> {ngram_path} ({len(ngram_rows)} rows)")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
