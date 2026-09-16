"""Numeric-aware uncertainty signal for math questions.

For each math question, extract the final numeric answer from each of the 5
samples (reusing the extractor from the correctness scorer) and compute a
disagreement score:

    numeric_disagreement = 1 - (count of samples matching the majority number) / n_extracted

Also stores the coefficient of variation across extracted numbers (secondary).

Scores the combined math pool (main 150 + mathb 150 = 300) and evaluates:
    - AUROC (combined pool + main-only context vs the unigram baseline)
    - escalation gate at top-15%: precision / recall vs unigram

Outputs:
    results/math_numeric_signal.jsonl
    appends a "Numeric-aware math signal" section to results/escalation_report.md

Usage:
    python scoring/math_numeric_signal.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

import config as config_mod

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

    samples_by_q: dict[str, list[dict]] = defaultdict(list)
    with config_mod.GENERATIONS_PATH.open(encoding="utf-8") as handle:
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

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    mathb_correctness = load_jsonl(uq.RESULTS_DIR / "mathb_correctness.jsonl")

    rows = []
    for labels in (correctness, mathb_correctness):
        for question_id, label_row in labels.items():
            if label_row.get("category") != "math" or label_row.get("overall_correct") is None:
                continue
            records = samples_by_q.get(question_id, [])
            numbers = [uq.extract_number(r.get("response_text")) for r in records]
            extracted = [n for n in numbers if n is not None]
            if extracted:
                majority, count = Counter(extracted).most_common(1)[0]
                mode_fraction = count / len(extracted)
                disagreement = 1.0 - mode_fraction
            else:
                majority, mode_fraction, disagreement = None, 0.0, 0.0
            cv = 0.0
            if len(extracted) >= 2:
                mean = statistics.fmean(extracted)
                if mean != 0:
                    cv = statistics.pstdev(extracted) / abs(mean)
            rows.append(
                {
                    "question_id": question_id,
                    "category": "math",
                    "n_samples": len(records),
                    "n_extracted": len(extracted),
                    "extracted_numbers": extracted,
                    "majority_number": majority,
                    "mode_fraction": round(mode_fraction, 4),
                    "numeric_disagreement": round(disagreement, 4),
                    "cv": round(cv, 4),
                    "error": 1 - int(label_row["overall_correct"]),
                }
            )

    uq.write_jsonl(uq.RESULTS_DIR / "math_numeric_signal.jsonl", rows)
    print(f"scored {len(rows)} math questions -> {uq.RESULTS_DIR / 'math_numeric_signal.jsonl'}")
    none_extraction = sum(1 for r in rows if r["n_extracted"] == 0)
    print(f"questions with zero extracted numbers: {none_extraction}")

    # evaluation: combined pool (300) and main-only (150)
    lexical = load_jsonl(uq.RESULTS_DIR / "lexical.jsonl")
    mathb_lexical = load_jsonl(uq.RESULTS_DIR / "mathb_lexical.jsonl")
    unigram_by_q = {}
    for question_id, row in lexical.items():
        unigram_by_q[question_id] = row.get("uncertainty")
    for question_id, row in mathb_lexical.items():
        unigram_by_q[question_id] = row.get("uncertainty")

    for row in rows:
        row["unigram"] = unigram_by_q.get(row["question_id"])

    def evaluate(group: list[dict], label: str):
        labels = [r["error"] for r in group]
        numeric_auc, _, _ = uq.roc_auc(labels, [r["numeric_disagreement"] for r in group])
        unigram_auc, _, _ = uq.roc_auc(labels, [r["unigram"] for r in group])
        threshold = 1.0 - TOP_PCT / 100.0
        lines = []
        for name, field in (("numeric_disagreement", "numeric_disagreement"), ("unigram (baseline)", "unigram")):
            ranks = rank_normalize([r[field] for r in group])
            escalated = [r for r, rank in zip(group, ranks) if rank >= threshold]
            incorrect_total = sum(r["error"] for r in group)
            incorrect_escalated = sum(r["error"] for r in escalated)
            precision = incorrect_escalated / len(escalated) if escalated else 0.0
            recall = incorrect_escalated / incorrect_total if incorrect_total else 0.0
            lines.append((name, escalated, incorrect_escalated, precision, recall))
        print(f"\n[{label}] n={len(group)} errors={sum(labels)}")
        print(f"  AUROC numeric_disagreement: {numeric_auc:.4f} | unigram: {unigram_auc:.4f}")
        for name, escalated, incorrect_escalated, precision, recall in lines:
            print(f"  top-{TOP_PCT:g}% {name}: escalated {len(escalated)}, precision {precision:.2f}, recall {recall:.2f}")
        return numeric_auc, unigram_auc, lines

    combined_auc_numeric, combined_auc_unigram, combined_lines = evaluate(rows, "combined math pool (300)")
    main_rows = [r for r in rows if r["question_id"].startswith("math_")]
    main_auc_numeric, main_auc_unigram, main_lines = evaluate(main_rows, "main math only (150)")

    section = [
        "",
        "## Numeric-aware math signal (final-answer disagreement)",
        "",
        f"_numeric_disagreement = 1 - (samples matching the majority final number)/n_extracted; "
        f"scored on the combined math pool (300 questions, 9 errors). Unigram baseline recomputed "
        f"on the same pool. Escalation at top-{TOP_PCT:g}%._",
        "",
        "| Pool | Signal | AUROC | top-15% precision | top-15% recall |",
        "|---|---|---:|---:|---:|",
        f"| combined (300) | numeric_disagreement | {combined_auc_numeric:.4f} | "
        f"{combined_lines[0][3]:.2f} | {combined_lines[0][4]:.2f} |",
        f"| combined (300) | unigram (baseline) | {combined_auc_unigram:.4f} | "
        f"{combined_lines[1][3]:.2f} | {combined_lines[1][4]:.2f} |",
        f"| main only (150) | numeric_disagreement | {main_auc_numeric:.4f} | "
        f"{main_lines[0][3]:.2f} | {main_lines[0][4]:.2f} |",
        f"| main only (150) | unigram (baseline) | {main_auc_unigram:.4f} | "
        f"{main_lines[1][3]:.2f} | {main_lines[1][4]:.2f} |",
        "",
    ]
    report_path = uq.RESULTS_DIR / "escalation_report.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(section))
    print("\n".join(section))
    print(f"appended to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
