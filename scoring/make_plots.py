"""Generate Week 1 evaluation figures from results/.

Outputs (results/figures/):
    auroc_bar.png             AUROC per method, overall and per category
    uncertainty_boxplots.png  uncertainty distribution: incorrect vs correct
                              (tfidf, bigram, trigram, semantic entropy)

Usage:
    python scoring/make_plots.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

FIGURES_DIR = uq.RESULTS_DIR / "figures"

METHOD_LABELS = {
    "bigram_jaccard": "Bigram Jaccard",
    "trigram_jaccard": "Trigram Jaccard",
    "tfidf_cosine": "TF-IDF cosine",
    "unigram_jaccard": "Unigram Jaccard",
    "semantic_entropy": "Semantic entropy",
    "semantic_entropy_normalized": "Semantic entropy (norm)",
}

PLOT_ORDER = ["bigram_jaccard", "trigram_jaccard", "tfidf_cosine", "unigram_jaccard", "semantic_entropy"]


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


def main() -> int:
    uq.enable_utf8_stdout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    auroc = json.loads((uq.RESULTS_DIR / "auroc.json").read_text(encoding="utf-8"))
    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    ngram_tfidf = load_jsonl(uq.RESULTS_DIR / "ngram_tfidf.jsonl")
    lexical = load_jsonl(uq.RESULTS_DIR / "lexical.jsonl")
    semantic = load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl")

    # ---- figure 1: AUROC bars ----
    categories = ["all", "factual", "math", "reasoning"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), sharey=True)
    for axis, category in zip(axes, categories):
        methods = []
        values = []
        for method in PLOT_ORDER:
            entry = auroc["results"].get(method, {}).get(category, {})
            auc = entry.get("auroc")
            if auc is None:
                continue
            methods.append(METHOD_LABELS[method])
            values.append(auc)
        bars = axis.bar(methods, values, color="#4c72b0", width=0.6)
        axis.axhline(0.5, color="grey", linestyle="--", linewidth=1)
        axis.set_title(f"{category} (n inc/corr: {auroc['results']['bigram_jaccard'][category]['n_incorrect']}/"
                       f"{auroc['results']['bigram_jaccard'][category]['n_correct']})")
        axis.set_ylim(0.45, 0.95)
        axis.tick_params(axis="x", rotation=40)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, value + 0.008, f"{value:.3f}", ha="center", fontsize=8)
    axes[0].set_ylabel("AUROC (uncertainty vs. error)")
    fig.suptitle("Week 1: AUROC of uncertainty methods for predicting incorrect answers", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "auroc_bar.png", dpi=150)
    plt.close(fig)

    # ---- figure 2: boxplots incorrect vs correct ----
    rows = []
    for question_id, row in correctness.items():
        label = row.get("overall_correct")
        if label is None:
            continue
        group = "correct" if label == 1 else "incorrect"
        entry = {
            "question_id": question_id,
            "group": group,
            "category": row["category"],
        }
        if question_id in ngram_tfidf:
            entry["tfidf"] = ngram_tfidf[question_id]["tfidf_uncertainty"]
            entry["bigram"] = ngram_tfidf[question_id]["bigram_uncertainty"]
            entry["trigram"] = ngram_tfidf[question_id]["trigram_uncertainty"]
        if question_id in semantic:
            entry["semantic"] = semantic[question_id]["semantic_entropy"]
        rows.append(entry)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for axis, (field, title) in zip(
        axes.flat,
        [
            ("tfidf", "TF-IDF cosine uncertainty"),
            ("bigram", "Bigram Jaccard uncertainty"),
            ("trigram", "Trigram Jaccard uncertainty"),
            ("semantic", "Semantic entropy (nats)"),
        ],
    ):
        correct = [row[field] for row in rows if row["group"] == "correct" and field in row]
        incorrect = [row[field] for row in rows if row["group"] == "incorrect" and field in row]
        axis.boxplot([incorrect, correct], labels=["incorrect", "correct"], patch_artist=True,
                     boxprops={"facecolor": "#ffb3b3"}, medianprops={"color": "black"})
        axis.set_title(title, fontsize=10)
        axis.set_ylabel("uncertainty")
    fig.suptitle("Uncertainty distribution by majority-vote correctness (all questions)", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "uncertainty_boxplots.png", dpi=150)
    plt.close(fig)

    print(f"figures -> {FIGURES_DIR}")
    for path in sorted(FIGURES_DIR.glob("*.png")):
        print(f"  {path.name} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
