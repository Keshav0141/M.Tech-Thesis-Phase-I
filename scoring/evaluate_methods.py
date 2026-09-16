"""Join correctness labels with uncertainty scores and compute AUROC.

Reads results/correctness.jsonl, results/lexical.jsonl and
results/semantic_entropy.jsonl (all produced by the scoring modules), then
reports AUROC of each uncertainty method for predicting incorrect answers,
overall and per category.

Outputs:
    results/week1_auroc_report.md
    results/auroc.json

Usage:
    python evaluate_methods.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import uq_common as uq

METHODS = {
    "bigram_jaccard": ("ngram_tfidf", "bigram_uncertainty"),
    "trigram_jaccard": ("ngram_tfidf", "trigram_uncertainty"),
    "tfidf_cosine": ("ngram_tfidf", "tfidf_uncertainty"),
    "unigram_jaccard": ("lexical", "uncertainty"),
    "semantic_entropy": ("semantic", "semantic_entropy"),
    "semantic_entropy_normalized": ("semantic", "normalized_entropy"),
    "num_sets": ("graph", "num_sets"),
    "degree_matrix": ("graph", "degree_matrix"),
    "eigv": ("graph", "eigv"),
    "eccentricity": ("graph", "eccentricity"),
    "numeric_disagreement": ("numeric", "numeric_disagreement"),
}


def load_jsonl(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows[row["question_id"]] = row
    return rows


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="AUROC evaluation for uncertainty methods.")
    parser.add_argument("--correctness", default=str(uq.RESULTS_DIR / "correctness.jsonl"))
    parser.add_argument("--lexical", default=str(uq.RESULTS_DIR / "lexical.jsonl"))
    parser.add_argument("--ngram-tfidf", default=str(uq.RESULTS_DIR / "ngram_tfidf.jsonl"))
    parser.add_argument("--semantic", default=str(uq.RESULTS_DIR / "semantic_entropy.jsonl"))
    parser.add_argument("--graph-methods", default=str(uq.RESULTS_DIR / "graph_methods.jsonl"))
    parser.add_argument("--numeric-signal", default=str(uq.RESULTS_DIR / "math_numeric_signal.jsonl"))
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "week1_auroc_report.md"))
    args = parser.parse_args()

    correctness = load_jsonl(Path(args.correctness))
    sources = {
        "lexical": load_jsonl(Path(args.lexical)),
        "ngram_tfidf": load_jsonl(Path(args.ngram_tfidf)),
        "semantic": load_jsonl(Path(args.semantic)),
        "graph": load_jsonl(Path(args.graph_methods)),
        "numeric": load_jsonl(Path(args.numeric_signal)),
    }
    questions = {q["question_id"]: q for q in uq.load_questions()}
    categories = ["factual", "math", "reasoning", "all"]

    results: dict[str, dict] = {}
    for method, (source, field) in METHODS.items():
        results[method] = {}
        for category in categories:
            labels: list[int] = []
            scores: list[float] = []
            score_errors: list[float] = []
            score_correct: list[float] = []
            for question_id, row in correctness.items():
                if category != "all" and row["category"] != category:
                    continue
                method_row = sources[source].get(question_id)
                if not method_row:
                    continue
                score = method_row.get(field)
                label = row.get("overall_correct")
                if score is None or label is None:
                    continue
                error_label = 1 - int(label)
                labels.append(error_label)
                scores.append(float(score))
                (score_errors if error_label == 1 else score_correct).append(float(score))
            auc, n_errors, n_correct = uq.roc_auc(labels, scores)
            results[method][category] = {
                "auroc": round(auc, 4) if auc is not None else None,
                "n_incorrect": n_errors,
                "n_correct": n_correct,
                "mean_score_incorrect": round(sum(score_errors) / len(score_errors), 4) if score_errors else None,
                "mean_score_correct": round(sum(score_correct) / len(score_correct), 4) if score_correct else None,
            }

    coverage: dict[str, dict] = {}
    for category in ["factual", "math", "reasoning"]:
        expected = sum(1 for q in questions.values() if q["category"] == category)
        with_correctness = sum(1 for row in correctness.values() if row["category"] == category)
        with_semantic = sum(
            1 for qid, row in correctness.items() if row["category"] == category and qid in sources["semantic"]
        )
        coverage[category] = {
            "dataset_questions": expected,
            "scored_questions": with_correctness,
            "with_semantic_entropy": with_semantic,
        }

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AUROC Report - uncertainty vs. incorrect answers",
        "",
        f"_Generated {generated} (full dataset: 450 questions x 5 samples)._",
        "",
        "Label: majority-vote incorrect (1) vs correct (0); unresolved/no-sample questions are excluded.",
        "AUROC > 0.5 means the uncertainty score is higher on incorrect answers.",
        "",
        "## Coverage",
        "",
        "| Category | Dataset questions | Scored | With semantic entropy |",
        "|---|---:|---:|---:|",
    ]
    for category, row in coverage.items():
        lines.append(
            f"| {category} | {row['dataset_questions']} | {row['scored_questions']} | {row['with_semantic_entropy']} |"
        )
    lines += [
        "",
        "## Results",
        "",
        "| Category | Method | AUROC | incorrect/correct | mean score (incorrect) | mean score (correct) |",
        "|---|---|---:|---|---:|---:|",
    ]
    for category in categories:
        for method in METHODS:
            row = results[method][category]
            auc = f"{row['auroc']:.4f}" if row["auroc"] is not None else "n/a"
            pair = f"{row['n_incorrect']}/{row['n_correct']}"
            mean_error = row["mean_score_incorrect"] if row["mean_score_incorrect"] is not None else "n/a"
            mean_ok = row["mean_score_correct"] if row["mean_score_correct"] is not None else "n/a"
            lines.append(f"| {category} | {method} | {auc} | {pair} | {mean_error} | {mean_ok} |")
    lines.append("")

    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    uq.RESULTS_DIR.joinpath("auroc.json").write_text(
        json.dumps({"generated_utc": generated, "coverage": coverage, "results": results}, indent=2),
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"report -> {args.output}")
    print(f"machine-readable -> {uq.RESULTS_DIR / 'auroc.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
