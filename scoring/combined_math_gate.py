"""Combined math escalation gate: union of unigram OR numeric-disagreement.

Escalates a question if it falls in the top-15% by EITHER signal (union of the
two escalation sets). Evaluated on both math pools (main 150, combined 300),
side by side with each signal alone.

Appends a section to results/escalation_report.md.

Usage:
    python scoring/combined_math_gate.py
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


def metrics(group: list[dict], escalated_indices: set[int]):
    escalated = [group[i] for i in escalated_indices]
    incorrect_total = sum(r["error"] for r in group)
    incorrect_escalated = sum(r["error"] for r in escalated)
    precision = incorrect_escalated / len(escalated) if escalated else 0.0
    recall = incorrect_escalated / incorrect_total if incorrect_total else 0.0
    return len(escalated), precision, recall, incorrect_escalated, incorrect_total


def main() -> int:
    uq.enable_utf8_stdout()
    uq.ensure_results_dir()

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    mathb_correctness = load_jsonl(uq.RESULTS_DIR / "mathb_correctness.jsonl")
    lexical = load_jsonl(uq.RESULTS_DIR / "lexical.jsonl")
    mathb_lexical = load_jsonl(uq.RESULTS_DIR / "mathb_lexical.jsonl")
    numeric = load_jsonl(uq.RESULTS_DIR / "math_numeric_signal.jsonl")

    rows = []
    for labels, scores in ((correctness, lexical), (mathb_correctness, mathb_lexical)):
        for question_id, label_row in labels.items():
            if label_row.get("category") != "math" or label_row.get("overall_correct") is None:
                continue
            unigram = scores.get(question_id, {}).get("uncertainty")
            disagreement = numeric.get(question_id, {}).get("numeric_disagreement")
            if unigram is None or disagreement is None:
                continue
            rows.append(
                {
                    "question_id": question_id,
                    "error": 1 - int(label_row["overall_correct"]),
                    "unigram": float(unigram),
                    "numeric": float(disagreement),
                }
            )

    pools = {
        "combined (300)": rows,
        "main only (150)": [r for r in rows if r["question_id"].startswith("math_")],
    }
    threshold = 1.0 - TOP_PCT / 100.0

    lines = [
        "",
        "## Combined math gate (union of unigram OR numeric-disagreement)",
        "",
        f"_Escalate if in the top-{TOP_PCT:g}% by EITHER signal (union, not intersection). "
        "Ties in the numeric signal make its top-15% set smaller in practice._",
        "",
        "| Pool | Gate | escalated (rate) | precision | recall | errors caught |",
        "|---|---|---:|---:|---:|---:|",
    ]
    summary = {}
    for pool_name, group in pools.items():
        unigram_ranks = rank_normalize([r["unigram"] for r in group])
        numeric_ranks = rank_normalize([r["numeric"] for r in group])
        unigram_set = {i for i, rank in enumerate(unigram_ranks) if rank >= threshold}
        numeric_set = {i for i, rank in enumerate(numeric_ranks) if rank >= threshold}
        union_set = unigram_set | numeric_set

        for gate_name, gate_set in (
            ("unigram alone", unigram_set),
            ("numeric alone", numeric_set),
            ("union (OR)", union_set),
        ):
            count, precision, recall, caught, total = metrics(group, gate_set)
            lines.append(
                f"| {pool_name} | {gate_name} | {count} ({100 * count / len(group):.0f}%) | "
                f"{precision:.2f} | {recall:.2f} | {caught}/{total} |"
            )
            summary[(pool_name, gate_name)] = (count, precision, recall, caught, total)
        lines.append(
            f"| {pool_name} | overlap (unigram ∩ numeric) | "
            f"{len(unigram_set & numeric_set)} | - | - | - |"
        )
    lines.append("")

    report_path = uq.RESULTS_DIR / "escalation_report.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("\n".join(lines))

    for key, value in summary.items():
        print(key, "->", value)
    print(f"appended to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
