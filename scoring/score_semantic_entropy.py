"""Semantic entropy uncertainty via NLI-based semantic clustering.

Clusters the samples of each question into semantic equivalence classes using
bidirectional entailment from a local cross-encoder NLI model
(cross-encoder/nli-deberta-v3-base by default), then computes Shannon entropy
over the cluster distribution:

    H = -sum_c p_c * ln(p_c),   p_c = cluster_size / n_samples

Implementation note: sentence-transformers 5.5.1 crashes the interpreter on
import in this environment (access violation with transformers 5.3.0), so the
cross-encoder is run directly through transformers
(AutoModelForSequenceClassification). Same model, same NLI semantics.

Outputs:
    results/semantic_entropy.jsonl -- question_id, category, n_samples,
                                      n_clusters, cluster_sizes, entropy,
                                      normalized_entropy, pairwise entailment
                                      probabilities

Usage:
    python score_semantic_entropy.py
    python score_semantic_entropy.py --limit 20 --batch-size 32 --device cpu
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections import defaultdict

import uq_common as uq


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Semantic entropy via NLI clustering.")
    parser.add_argument("--model", help="only score samples from this model_name")
    parser.add_argument("--provider", help="only score samples from this provider")
    parser.add_argument("--limit", type=int, help="max questions to score")
    parser.add_argument("--min-samples", type=int, default=2)
    parser.add_argument("--nli-model", default="cross-encoder/nli-deberta-v3-base")
    parser.add_argument("--threshold", type=float, default=0.5, help="bidirectional entailment threshold")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--half", action="store_true", help="fp16 inference (faster on consumer GPUs)")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "semantic_entropy.jsonl"))
    args = parser.parse_args()

    uq.ensure_results_dir()
    questions = uq.load_questions()
    samples, counts = uq.load_samples()
    model_filter, provider_filter = uq.resolve_filters(args, counts)
    if model_filter or provider_filter:
        samples, _ = uq.load_samples(model=model_filter, provider=provider_filter)

    if args.limit:
        questions = questions[: args.limit]

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as error:
        print(f"missing dependency: {error}. Install with: pip install transformers torch")
        return 1

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"loading NLI model {args.nli_model} on {device} (first run downloads ~750MB)...", flush=True)
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.nli_model)
        nli_model = AutoModelForSequenceClassification.from_pretrained(args.nli_model)
        if args.half:
            nli_model = nli_model.half()
        nli_model.to(device)
        nli_model.eval()
    except Exception as error:
        print(f"could not load NLI model: {error}")
        return 1

    id2label = getattr(getattr(nli_model, "config", None), "id2label", {}) or {}
    entailment_index = 1
    for index, label in id2label.items():
        if "entail" in str(label).lower():
            entailment_index = int(index)
    print(f"NLI label mapping: {id2label} | entailment index: {entailment_index}")

    # Build all bidirectional pair inputs across questions.
    pair_plan: dict[str, list[tuple[int, int]]] = {}
    texts_by_question: dict[str, list[str]] = {}
    inputs: list[tuple[str, str]] = []
    for question in questions:
        question_id = question["question_id"]
        texts = [(r.get("response_text") or "").strip() for r in samples.get(question_id, [])]
        texts = [text for text in texts if text]
        if len(texts) < args.min_samples:
            continue
        texts_by_question[question_id] = texts
        pairs = list(itertools.combinations(range(len(texts)), 2))
        pair_plan[question_id] = pairs
        for i, j in pairs:
            inputs.append((texts[i], texts[j]))
            inputs.append((texts[j], texts[i]))

    print(f"scoring {len(pair_plan)} questions, {len(inputs) // 2} sample pairs (bidirectional)...", flush=True)
    probabilities: list[list[float]] = []
    with torch.no_grad():
        for start in range(0, len(inputs), args.batch_size):
            chunk = inputs[start : start + args.batch_size]
            premises = [premise for premise, _ in chunk]
            hypotheses = [hypothesis for _, hypothesis in chunk]
            encoded = tokenizer(
                premises,
                hypotheses,
                padding=True,
                truncation=True,
                max_length=args.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            logits = nli_model(**encoded).logits
            probabilities.extend(torch.softmax(logits, dim=-1).cpu().tolist())
            if (start // args.batch_size) % 20 == 0:
                print(f"  NLI batch {start // args.batch_size + 1}/{(len(inputs) + args.batch_size - 1) // args.batch_size}", flush=True)

    rows = []
    totals: dict[str, list[float]] = defaultdict(list)
    probability_position = 0
    for question in questions:
        question_id = question["question_id"]
        if question_id not in pair_plan:
            continue
        texts = texts_by_question[question_id]
        n = len(texts)
        union_find = UnionFind(n)
        pair_records = []
        for i, j in pair_plan[question_id]:
            probability_ij = probabilities[probability_position][entailment_index]
            probability_ji = probabilities[probability_position + 1][entailment_index]
            probability_position += 2
            bidirectional = probability_ij >= args.threshold and probability_ji >= args.threshold
            if bidirectional:
                union_find.union(i, j)
            pair_records.append(
                {
                    "i": i,
                    "j": j,
                    "p_ij": round(probability_ij, 6),
                    "p_ji": round(probability_ji, 6),
                    "equivalent": bidirectional,
                }
            )

        clusters: dict[int, list[int]] = defaultdict(list)
        for node in range(n):
            clusters[union_find.find(node)].append(node)
        cluster_sizes = sorted((len(members) for members in clusters.values()), reverse=True)
        distribution = [size / n for size in cluster_sizes]
        entropy = -sum(p * math.log(p) for p in distribution)
        normalized = entropy / math.log(n) if n > 1 else 0.0

        rows.append(
            {
                "question_id": question_id,
                "category": question["category"],
                "n_samples": n,
                "n_clusters": len(cluster_sizes),
                "cluster_sizes": cluster_sizes,
                "clusters": [
                    {
                        "sample_ids": [samples[question_id][index].get("sample_id") for index in members],
                        "text_preview": texts[members[0]][:120],
                    }
                    for members in sorted(clusters.values(), key=len, reverse=True)
                ],
                "semantic_entropy": round(entropy, 6),
                "normalized_entropy": round(normalized, 6),
                "nli_model": args.nli_model,
                "threshold": args.threshold,
                "pairwise": pair_records,
            }
        )
        totals[question["category"]].append(entropy)

    uq.write_jsonl(args.output, rows)
    print(f"scored {len(rows)} questions -> {args.output}")
    for category in ("factual", "math", "reasoning"):
        values = totals.get(category, [])
        if values:
            mean = sum(values) / len(values)
            print(f"{category:<10} n={len(values):>3} mean semantic entropy={mean:.4f} nats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
