"""Analyze high-confidence wrong answers (low-uncertainty incorrect questions).

Finds questions whose majority-vote label is "incorrect" but whose bigram or
trigram Jaccard uncertainty is low (the model was confidently wrong), and
characterizes the failure pattern.

Outputs:
    results/low_uncertainty_incorrect_cases.md

Usage:
    python scoring/analyze_low_uncertainty.py
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

import config as config_mod

BIGRAM_LOW = 0.4
TRIGRAM_LOW = 0.5


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
    uq.ensure_results_dir()

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    scores = load_jsonl(uq.RESULTS_DIR / "ngram_tfidf.jsonl")
    needs_review = load_jsonl(uq.RESULTS_DIR / "needs_review.jsonl")
    questions = {q["question_id"]: q for q in uq.load_questions()}

    samples_by_q: dict[str, list[dict]] = defaultdict(list)
    with config_mod.GENERATIONS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") == "ok":
                samples_by_q[record["question_id"]].append(record)
    for question_id in samples_by_q:
        samples_by_q[question_id].sort(key=lambda r: int(r.get("sample_id", -1)))

    cases = []
    for question_id, row in correctness.items():
        if row.get("majority_label") != "incorrect":
            continue
        score_row = scores.get(question_id)
        if not score_row:
            continue
        bigram = score_row.get("bigram_uncertainty")
        trigram = score_row.get("trigram_uncertainty")
        if bigram is None or trigram is None:
            continue
        if bigram >= BIGRAM_LOW and trigram >= TRIGRAM_LOW:
            continue

        question = questions[question_id]
        per_sample = row["per_sample"]
        extracted = [str(sample.get("extracted")) for sample in per_sample]
        labels = [sample.get("label") for sample in per_sample]
        unique_extracted = Counter(extracted)

        texts = [(r.get("response_text") or "").strip() for r in samples_by_q.get(question_id, [])]
        texts = [t for t in texts if t]
        bigram_sims = []
        if len(texts) >= 2:
            sets = [uq.ngram_set(uq.tokenize(t), 2) for t in texts]
            bigram_sims = [uq.jaccard(a, b) for a, b in itertools.combinations(sets, 2)]

        n_samples = len(per_sample)
        n_wrong = sum(1 for label in labels if label != "correct")
        top, top_count = unique_extracted.most_common(1)[0] if unique_extracted else ("", 0)
        if n_samples == top_count:
            pattern = "all samples same wrong answer"
        elif top_count >= 4:
            pattern = f"{top_count}/{n_samples} samples same wrong answer"
        elif bigram_sims and sum(bigram_sims) / len(bigram_sims) >= 0.6:
            pattern = "near-identical wrong text"
        else:
            pattern = "diverse wrong answers"

        cases.append(
            {
                "question_id": question_id,
                "category": question["category"],
                "question": question["question_text"],
                "ground_truth": question["ground_truth_answer"],
                "bigram": bigram,
                "trigram": trigram,
                "n_samples": n_samples,
                "n_wrong": n_wrong,
                "top_extracted": str(top),
                "top_count": top_count,
                "all_extracted": extracted,
                "pattern": pattern,
                "in_needs_review": question_id in needs_review,
            }
        )

    cases.sort(key=lambda c: min(c["bigram"], c["trigram"]))

    lines = [
        "# Low-uncertainty incorrect cases (confidently wrong)",
        "",
        f"_Generated 2026-09-14. Definition: majority vote = incorrect AND "
        f"(bigram Jaccard uncertainty < {BIGRAM_LOW} OR trigram < {TRIGRAM_LOW})._",
        "",
        f"Total cases: **{len(cases)}**",
        "",
        "| question_id | category | bigram | trigram | n_wrong/5 | pattern | GT | model answer(s) | review |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ]
    for case in cases:
        question_short = case["question"].replace("|", "/")[:80]
        gt = str(case["ground_truth"]).replace("|", "/")[:40]
        answers = " / ".join(dict.fromkeys(a[:40] for a in case["all_extracted"]))[:120]
        answers = answers.replace("|", "/")
        lines.append(
            f"| {case['question_id']} | {case['category']} | {case['bigram']:.3f} | {case['trigram']:.3f} | "
            f"{case['n_wrong']}/5 | {case['pattern']} | {gt} | {answers} | "
            f"{'yes' if case['in_needs_review'] else 'no'} |"
        )
    lines += [
        "",
        "## Pattern summary by category",
        "",
        "| category | cases | common pattern |",
        "|---|---:|---|",
    ]
    by_category: dict[str, list] = defaultdict(list)
    for case in cases:
        by_category[case["category"]].append(case)
    for category in ("factual", "math", "reasoning"):
        group = by_category.get(category, [])
        if not group:
            continue
        patterns = Counter(c["pattern"] for c in group)
        common = ", ".join(f"{p} (x{cnt})" for p, cnt in patterns.most_common(2))
        lines.append(f"| {category} | {len(group)} | {common} |")
    lines.append("")

    output = uq.RESULTS_DIR / "low_uncertainty_incorrect_cases.md"
    output.write_text("\n".join(lines), encoding="utf-8")

    print(f"cases: {len(cases)} -> {output}")
    for category in ("factual", "math", "reasoning"):
        group = by_category.get(category, [])
        if group:
            print(f"  {category}: {len(group)} cases")
    patterns = Counter(c["pattern"] for c in cases)
    print("patterns:", dict(patterns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
