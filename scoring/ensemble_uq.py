"""Ensemble UQ score: rank-average of the five uncertainty methods.

Variants:
    unweighted-5   mean of 5 rank-normalized scores (no fitting)
    weighted-5-CV  logistic regression weights, 5-fold CV (OOF predictions)
    unweighted-3   mean of tfidf + bigram + trigram ranks
    weighted-3-CV  logistic regression weights on those 3, 5-fold CV

Rank normalization is done per category so methods on different scales
combine fairly. Polarity is checked first (higher = more uncertain); inverted
methods are flipped before ranking.

Outputs:
    results/ensemble_scores.jsonl
    results/ensemble_report.md

Usage:
    python scoring/ensemble_uq.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import uq_common as uq

METHOD_SOURCES = {
    "tfidf": ("ngram_tfidf", "tfidf_uncertainty"),
    "bigram": ("ngram_tfidf", "bigram_uncertainty"),
    "trigram": ("ngram_tfidf", "trigram_uncertainty"),
    "unigram": ("lexical", "uncertainty"),
    "semantic": ("semantic", "semantic_entropy"),
}

VARIANT_5 = ["tfidf", "bigram", "trigram", "unigram", "semantic"]
VARIANT_3 = ["tfidf", "bigram", "trigram"]

CV_FOLDS = 5
CV_SEED = 42


def load_jsonl(path: Path) -> dict[str, dict]:
    rows = {}
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
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


def rank_normalize(values: list[float]) -> list[float]:
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    index = 0
    while index < n:
        end = index
        while end + 1 < n and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2.0
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return [rank / (n - 1) if n > 1 else 0.5 for rank in ranks]


def main() -> int:
    uq.enable_utf8_stdout()
    uq.ensure_results_dir()

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    sources = {
        "ngram_tfidf": load_jsonl(uq.RESULTS_DIR / "ngram_tfidf.jsonl"),
        "lexical": load_jsonl(uq.RESULTS_DIR / "lexical.jsonl"),
        "semantic": load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl"),
    }

    rows = []
    for question_id, label_row in correctness.items():
        label = label_row.get("overall_correct")
        if label is None:
            continue
        score_row = {}
        complete = True
        for method, (source, field) in METHOD_SOURCES.items():
            value = sources[source].get(question_id, {}).get(field)
            if value is None:
                complete = False
                break
            score_row[method] = float(value)
        if not complete:
            continue
        rows.append(
            {
                "question_id": question_id,
                "category": label_row["category"],
                "error": 1 - int(label),
                **score_row,
            }
        )

    print(f"joined {len(rows)} labeled questions with all 5 method scores")
    categories = ["factual", "math", "reasoning"]

    # polarity check per method (pooled): higher should mean higher uncertainty
    for method in METHOD_SOURCES:
        correct_mean = np.mean([r[method] for r in rows if r["error"] == 0])
        incorrect_mean = np.mean([r[method] for r in rows if r["error"] == 1])
        if incorrect_mean < correct_mean:
            print(f"[flip] {method}: incorrect mean {incorrect_mean:.4f} < correct mean {correct_mean:.4f} -> inverted, flipping")
            for row in rows:
                row[method] = -row[method]
        else:
            print(f"[ok] {method}: incorrect mean {incorrect_mean:.4f} >= correct mean {correct_mean:.4f}")

    # per-category rank normalization
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    for category, group in by_category.items():
        for method in METHOD_SOURCES:
            ranks = rank_normalize([row[method] for row in group])
            for row, rank in zip(group, ranks):
                row[f"{method}_rank"] = rank

    for row in rows:
        row["ensemble_5"] = float(np.mean([row[f"{m}_rank"] for m in VARIANT_5]))
        row["ensemble_3"] = float(np.mean([row[f"{m}_rank"] for m in VARIANT_3]))

    # logistic regression CV for weighted variants
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold

    labels = np.array([r["error"] for r in rows])
    oof_5 = np.full(len(rows), np.nan)
    oof_3 = np.full(len(rows), np.nan)
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=CV_SEED)
    for train_idx, test_idx in skf.split(rows, labels):
        for name, methods, oof in (("5", VARIANT_5, oof_5), ("3", VARIANT_3, oof_3)):
            X_train = np.array([[r[f"{m}_rank"] for m in methods] for r in rows])[train_idx]
            X_test = np.array([[r[f"{m}_rank"] for m in methods] for r in rows])[test_idx]
            model = LogisticRegression(max_iter=2000).fit(X_train, labels[train_idx])
            oof[test_idx] = model.predict_proba(X_test)[:, 1]
    for row, value_5, value_3 in zip(rows, oof_5, oof_3):
        row["ensemble_5_weighted"] = float(value_5)
        row["ensemble_3_weighted"] = float(value_3)

    uq.write_jsonl(uq.RESULTS_DIR / "ensemble_scores.jsonl", rows)

    def auc_of(field: str, category: str | None = None):
        subset = [r for r in rows if category is None or r["category"] == category]
        scores = [r[field] for r in subset]
        errs = [r["error"] for r in subset]
        auc, n_pos, n_neg = uq.roc_auc(errs, scores)
        return auc, n_pos, n_neg

    methods = {
        "tfidf (baseline)": "tfidf",
        "bigram (baseline)": "bigram",
        "trigram (baseline)": "trigram",
        "unigram (baseline)": "unigram",
        "semantic (baseline)": "semantic",
        "ensemble unweighted-5": "ensemble_5",
        "ensemble weighted-5 (5-fold CV)": "ensemble_5_weighted",
        "ensemble unweighted-3": "ensemble_3",
        "ensemble weighted-3 (5-fold CV)": "ensemble_3_weighted",
    }

    lines = [
        "# Ensemble UQ Report",
        "",
        "_Generated 2026-09-14. Labels: majority-vote incorrect vs correct "
        "(unresolved questions excluded). Scores rank-normalized per category "
        "before averaging; weighted variants use logistic regression with "
        f"5-fold stratified CV ({CV_FOLDS} folds, seed {CV_SEED}), reported on "
        "out-of-fold predictions only._",
        "",
        f"Questions in evaluation: **{len(rows)}**",
        "",
        "| Method | AUROC all | factual | math | reasoning |",
        "|---|---:|---:|---:|---:|",
    ]
    results_table = {}
    for label, field in methods.items():
        cells = []
        for category in ["all"] + categories:
            auc, n_pos, n_neg = auc_of(field, None if category == "all" else category)
            cells.append(f"{auc:.4f}" if auc is not None else "n/a")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
        results_table[label] = cells
    lines += [
        "",
        "## Verdict",
        "",
    ]

    baseline = auc_of("tfidf", None)[0]
    best_label, best_auc = None, 0.0
    for label in ("ensemble unweighted-5", "ensemble weighted-5 (5-fold CV)", "ensemble unweighted-3", "ensemble weighted-3 (5-fold CV)"):
        auc = auc_of(methods[label], None)[0]
        if auc > best_auc:
            best_label, best_auc = label, auc
    if best_auc > baseline:
        lines.append(
            f"- **Yes: {best_label} beats TF-IDF alone** (AUROC {best_auc:.4f} vs "
            f"{baseline:.4f}, +{(best_auc - baseline):.4f})."
        )
    else:
        lines.append(
            f"- No ensemble variant beats TF-IDF alone ({baseline:.4f}); best ensemble is "
            f"{best_label} at {best_auc:.4f}."
        )
    per_category = []
    for category in categories:
        tfidf_auc = auc_of("tfidf", category)[0]
        best_cat = max(
            ("ensemble unweighted-5", "ensemble weighted-5 (5-fold CV)", "ensemble unweighted-3", "ensemble weighted-3 (5-fold CV)"),
            key=lambda label: auc_of(methods[label], category)[0] or 0.0,
        )
        best_cat_auc = auc_of(methods[best_cat], category)[0] or 0.0
        per_category.append(f"{category}: tfidf {tfidf_auc:.4f} vs best ensemble {best_cat_auc:.4f}")
    lines.append("- Per category: " + "; ".join(per_category) + ".")
    lines.append("")
    (uq.RESULTS_DIR / "ensemble_report.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"report -> {uq.RESULTS_DIR / 'ensemble_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
