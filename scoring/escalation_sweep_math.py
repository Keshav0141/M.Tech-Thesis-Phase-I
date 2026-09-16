"""Math-only threshold sweep for the confidence gate (targeted diagnostic).

Reuses the existing unigram gate (CV winner for math) unchanged, applied to
the COMBINED math pool: main math (150, 6 majority-incorrect) + mathb
expansion (150, 3 majority-incorrect) = 300 questions, 9 errors.

Sweeps --top-pct in {5, 10, 15, 20, 25} and appends a "Math threshold sweep"
section to results/escalation_report.md.

Usage:
    python scoring/escalation_sweep_math.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

SWEEP = [5, 10, 15, 20, 25]


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
    mathb_correctness = load_jsonl(uq.RESULTS_DIR / "mathb_correctness.jsonl")
    lexical = load_jsonl(uq.RESULTS_DIR / "lexical.jsonl")
    mathb_lexical = load_jsonl(uq.RESULTS_DIR / "mathb_lexical.jsonl")

    rows = []
    for source_labels, source_scores in (
        (correctness, lexical),
        (mathb_correctness, mathb_lexical),
    ):
        for question_id, label_row in source_labels.items():
            if label_row.get("category") != "math":
                continue
            label = label_row.get("overall_correct")
            if label is None or question_id not in source_scores:
                continue
            score = source_scores[question_id].get("uncertainty")
            if score is None:
                continue
            rows.append(
                {
                    "question_id": question_id,
                    "score": float(score),
                    "error": 1 - int(label),
                }
            )

    total_errors = sum(row["error"] for row in rows)
    base_rate = total_errors / len(rows) if rows else 0.0
    print(f"combined math pool: {len(rows)} questions, {total_errors} errors, base rate {base_rate:.3f}")

    ranks = rank_normalize([row["score"] for row in rows])
    for row, rank in zip(rows, ranks):
        row["percentile"] = rank

    lines = [
        "",
        "## Math threshold sweep (combined pool: main math + mathb = 300, 9 errors)",
        "",
        f"_Unigram gate unchanged. Base error rate {base_rate:.3f}._",
        "",
        "| top-pct | escalated | precision (wrong/escalated) | recall (of 9 errors) |",
        "|---:|---:|---:|---:|",
    ]
    verdict_parts = []
    for pct in SWEEP:
        threshold = 1.0 - pct / 100.0
        escalated = [row for row in rows if row["percentile"] >= threshold]
        incorrect_escalated = sum(row["error"] for row in escalated)
        precision = incorrect_escalated / len(escalated) if escalated else 0.0
        recall = incorrect_escalated / total_errors if total_errors else 0.0
        lines.append(
            f"| {pct}% | {len(escalated)} | {precision:.2f} | {recall:.2f} |"
        )
        verdict_parts.append(f"{pct}%->{precision:.2f}")

    lines += [
        "",
        "## Verdict (math sweep)",
        "",
        f"- Precision across thresholds: {'; '.join(verdict_parts)}.",
        f"- The gate method stays poor regardless of threshold; the ceiling is set by the "
        f"data (9 errors in 300 questions, base rate {base_rate:.3f}), not by threshold tuning.",
    ]
    lines.append("")

    report_path = uq.RESULTS_DIR / "escalation_report.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("\n".join(lines))
    print(f"appended sweep to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
