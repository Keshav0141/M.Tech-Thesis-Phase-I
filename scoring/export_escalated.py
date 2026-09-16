"""Compute the exact escalated-question set for the tier-2 pilot.

factual/reasoning: top-15% gate from results/escalation_decisions.jsonl
(TF-IDF / bigram, the decided gates).
math: numeric-disagreement top-15% on the main 150 (the decided math gate).

Writes results/tier2_escalated_questions.json.

Usage:
    python scoring/export_escalated.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

TOP_PCT = 15.0


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

    decisions = load_jsonl(uq.RESULTS_DIR / "escalation_decisions.jsonl")
    numeric = load_jsonl(uq.RESULTS_DIR / "math_numeric_signal.jsonl")
    questions = {q["question_id"]: q for q in uq.load_questions()}

    escalated = []
    for question_id, row in decisions.items():
        if row["decision"] == "escalate" and row["category"] in ("factual", "reasoning"):
            escalated.append(
                {
                    "question_id": question_id,
                    "category": row["category"],
                    "gate_method": row["gate_method"],
                    "uncertainty": row["uncertainty"],
                }
            )

    # math: numeric-disagreement top-15% on the main pool
    main_math = [row for row in numeric.values() if row["question_id"].startswith("math_")]
    ranks = rank_normalize([row["numeric_disagreement"] for row in main_math])
    threshold = 1.0 - TOP_PCT / 100.0
    for row, rank in zip(main_math, ranks):
        if rank >= threshold:
            escalated.append(
                {
                    "question_id": row["question_id"],
                    "category": "math",
                    "gate_method": "numeric_disagreement",
                    "uncertainty": row["numeric_disagreement"],
                }
            )

    escalated.sort(key=lambda r: (r["category"], r["question_id"]))
    for entry in escalated:
        question = questions.get(entry["question_id"])
        entry["question_text"] = question["question_text"] if question else ""
        entry["ground_truth_answer"] = question["ground_truth_answer"] if question else ""
        entry["original_correct"] = None

    from collections import Counter

    counts = Counter(entry["category"] for entry in escalated)
    print(f"total escalated: {len(escalated)} | by category: {dict(counts)}")

    (uq.RESULTS_DIR / "tier2_escalated_questions.json").write_text(
        json.dumps({"top_pct": TOP_PCT, "counts": dict(counts), "questions": escalated}, indent=2),
        encoding="utf-8",
    )
    print(f"-> {uq.RESULTS_DIR / 'tier2_escalated_questions.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())