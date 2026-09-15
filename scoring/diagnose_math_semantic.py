"""Diagnose whether NLI semantic entropy merges numerically-different math answers.

Hypothesis under test: NLI clustering treats "the answer is 42" and "the
answer is 44" as semantically equivalent because the surrounding reasoning
text is similar, so semantically-wrong-but-lexically-close samples collapse
into one cluster and entropy stays low.

Outputs:
    results/semantic_entropy_math_diagnosis.md

Usage:
    python scoring/diagnose_math_semantic.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

import config as config_mod

BOTTOM_QUARTILE = 0.25


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

    semantic = load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl")
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

    math_rows = [row for row in semantic.values() if row["category"] == "math"]
    math_rows.sort(key=lambda r: r["semantic_entropy"])
    cutoff = max(1, int(len(math_rows) * BOTTOM_QUARTILE))
    low_entropy = math_rows[:cutoff]
    print(f"math questions with semantic entropy: {len(math_rows)} | bottom quartile (n={cutoff}, "
          f"entropy <= {low_entropy[-1]['semantic_entropy']:.4f})")

    flagged = []
    for row in low_entropy:
        question_id = row["question_id"]
        records = samples_by_q.get(question_id, [])
        texts = [(r.get("response_text") or "").strip() for r in records]
        numbers = [uq.extract_number(text) for text in texts]
        distinct = sorted({n for n in numbers if n is not None})
        if len(distinct) > 1:
            flagged.append((row, records, texts, numbers, distinct))

    print(f"flagged (low entropy but different final numbers): {len(flagged)} / {len(low_entropy)}")

    lines = [
        "# Math semantic-entropy diagnosis: does NLI merge different numeric answers?",
        "",
        f"_Generated 2026-09-14. Bottom quartile by semantic entropy (n={len(low_entropy)}, "
        f"entropy <= {low_entropy[-1]['semantic_entropy']:.4f})._",
        "",
        f"Low-entropy math questions with **different extracted final numbers** across samples: "
        f"**{len(flagged)} / {len(low_entropy)}** "
        f"({100 * len(flagged) / len(low_entropy):.0f}% of the confident set).",
        "",
    ]

    if flagged:
        lines.append("## Pairwise NLI evidence (pairs whose final numbers differ)")
        lines.append("")
        shown = 0
        total_differing_pairs = 0
        equivalent_differing_pairs = 0
        for row, records, texts, numbers, distinct in flagged:
            question_id = row["question_id"]
            question = questions[question_id]
            pairwise = row.get("pairwise", [])
            for pair in pairwise:
                i, j = pair["i"], pair["j"]
                if i >= len(numbers) or j >= len(numbers):
                    continue
                number_i, number_j = numbers[i], numbers[j]
                if number_i is None or number_j is None or number_i == number_j:
                    continue
                total_differing_pairs += 1
                if pair.get("equivalent"):
                    equivalent_differing_pairs += 1
                if shown < 15:
                    lines.append(f"### {question_id} (sample {i} vs sample {j})")
                    lines.append(f"Question: {question['question_text']}")
                    lines.append("")
                    lines.append(f"- sample {i}: `{texts[i][:160]}` ... final = **{number_i:g}**")
                    lines.append(f"- sample {j}: `{texts[j][:160]}` ... final = **{number_j:g}**")
                    lines.append(
                        f"- NLI p(i->j)={pair['p_ij']:.3f} p(j->i)={pair['p_ji']:.3f} "
                        f"-> bidirectional equivalent: **{pair['equivalent']}** "
                        f"(threshold 0.5, entropy {row['semantic_entropy']:.3f})"
                    )
                    lines.append("")
                    shown += 1
        lines.append(
            f"Across all flagged questions: {total_differing_pairs} pairwise comparisons had different "
            f"final numbers; **{equivalent_differing_pairs} of them ({100 * equivalent_differing_pairs / max(1, total_differing_pairs):.0f}%) "
            f"were marked semantically equivalent by bidirectional entailment**."
        )
        lines.append("")
        if shown > 0:
            lines.append(
                "Note: a bidirectional-equivalent pair with different final numbers is direct "
                "evidence that NLI merged numerically different answers; the 'confident' (low "
                "entropy) label on that question is then an artifact."
            )
    else:
        lines.append("No low-entropy math question had different final numbers across samples — hypothesis not supported.")
    lines.append("")

    output = uq.RESULTS_DIR / "semantic_entropy_math_diagnosis.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"diagnosis -> {output}")

    if flagged:
        ratio = 100 * equivalent_differing_pairs / max(1, total_differing_pairs)
        print(f"differing-number pairs total: {total_differing_pairs} | marked equivalent: {equivalent_differing_pairs} ({ratio:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
