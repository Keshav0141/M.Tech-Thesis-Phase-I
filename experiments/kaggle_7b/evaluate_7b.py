"""Isolated AUROC evaluation for 7B experiment.

Joins experiments/kaggle_7B/results/correctness_7b.jsonl with
lexical_7b + ngram_tfidf_7b and computes AUROC per method, fully isolated.

Writes only to experiments/kaggle_7B/results/auroc_7b.json (and a markdown report).

Usage:
    python evaluate_7B.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scoring"))
import uq_common as uq  # noqa: E402

CORRECTNESS = HERE / "results" / "correctness_7b.jsonl"
LEXICAL = HERE / "results" / "lexical_7b.jsonl"
NGRAM = HERE / "results" / "ngram_tfidf_7b.jsonl"
OUTPUT_JSON = HERE / "results" / "auroc_7b.json"
OUTPUT_MD = HERE / "results" / "auroc_7b_report.md"


def load_jsonl(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as h:
        for line in h:
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
    correctness = load_jsonl(CORRECTNESS)
    lexical = load_jsonl(LEXICAL)
    ngram = load_jsonl(NGRAM)

    # question meta
    dataset = json.loads((PROJECT_ROOT / "data" / "dataset.json").read_text(encoding="utf-8"))
    qmeta = {q["question_id"]: q for q in dataset if q.get("validation_status") != "rejected"}

    methods = {
        "tfidf_cosine": ("ngram", "tfidf_uncertainty"),
        "unigram_jaccard": ("lexical", "uncertainty"),
        "bigram_jaccard": ("ngram", "bigram_uncertainty"),
        "trigram_jaccard": ("ngram", "trigram_uncertainty"),
    }
    sources = {"lexical": lexical, "ngram": ngram}
    categories = ["factual", "math", "reasoning", "all"]
    results: dict[str, dict] = {}
    for method, (src, field) in methods.items():
        results[method] = {}
        for cat in categories:
            labels: list[int] = []
            scores: list[float] = []
            for qid, row in correctness.items():
                if cat != "all" and row["category"] != cat:
                    continue
                src_row = sources[src].get(qid)
                if not src_row:
                    continue
                score = src_row.get(field)
                label = row.get("overall_correct")
                if score is None or label is None:
                    continue
                labels.append(1 - int(label))  # 1=incorrect
                scores.append(float(score))
            auc, n_pos, n_neg = uq.roc_auc(labels, scores)
            results[method][cat] = {"auroc": round(auc, 4) if auc is not None else None, "n_incorrect": n_pos, "n_correct": n_neg}

    # coverage
    coverage = {}
    for cat in ["factual", "math", "reasoning"]:
        exp = sum(1 for q in qmeta.values() if q["category"] == cat)
        scored = sum(1 for r in correctness.values() if r["category"] == cat)
        coverage[cat] = {"dataset_questions": exp, "scored_questions": scored}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps({"coverage": coverage, "results": results}, indent=2), encoding="utf-8")

    # markdown report
    lines = [
        "# 7B AUROC Report (Qwen2.5-7B-Instruct, isolated)",
        "",
        "Label: majority-vote incorrect (1) vs correct (0); unresolved excluded.",
        "",
        "## Coverage",
        "",
        "| Category | Dataset | Scored |",
        "|---|---:|---:|",
    ]
    for cat in ["factual", "math", "reasoning"]:
        lines.append(f"| {cat} | {coverage[cat]['dataset_questions']} | {coverage[cat]['scored_questions']} |")
    lines += ["", "## AUROC", "", "| Category | Method | AUROC | incorrect/correct |", "|---|---|---:|---|"]
    for cat in categories:
        for method in methods:
            row = results[method][cat]
            auc = f"{row['auroc']:.4f}" if row["auroc"] is not None else "n/a"
            pair = f"{row['n_incorrect']}/{row['n_correct']}"
            lines.append(f"| {cat} | {method} | {auc} | {pair} |")
    lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"-> {OUTPUT_JSON}")
    print(f"-> {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

