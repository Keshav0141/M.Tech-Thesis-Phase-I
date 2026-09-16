"""Confidence-gated escalation pipeline (first pass).

Uses the CV-validated per-category method selector as the confidence gate:
for each question, the winning method's uncertainty score (per its category)
is ranked within the category; the most-uncertain top-N% are flagged for
escalation to a larger model.

The second-model call is STUBBED: the model tier is still pending professor
sign-off (8B/20B vs 27B/70B/120B). The plumbing logs what WOULD be escalated
and to which placeholder tier.

Outputs:
    results/escalation_decisions.jsonl  per-question keep/escalate decisions
    results/escalation_report.md        escalation rate + gate hit-rate

Usage:
    python scoring/escalate.py --top-pct 15
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

import config

METHOD_SOURCES = {
    "tfidf": ("ngram_tfidf", "tfidf_uncertainty"),
    "bigram": ("ngram_tfidf", "bigram_uncertainty"),
    "trigram": ("ngram_tfidf", "trigram_uncertainty"),
    "unigram": ("lexical", "uncertainty"),
    "semantic": ("semantic", "semantic_entropy"),
}

PLACEHOLDER_TIER = "larger model (TBD: 70B/120B on Groq)"

# Reasoning-proof cap (the qwen pipeline lesson): reasoning answers truncated
# at 512 and 1024; 1536 eliminated truncation. gpt-oss-120b is a reasoning
# model (even at effort=low it emits hidden reasoning), so all tier-2 calls
# use 1536 to avoid the same problem.
TIER2_MAX_TOKENS = 1536


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


def category_winner(selector_results: dict) -> dict[str, str]:
    """Most common fold winner per category (the CV-validated gate method)."""
    winners = {}
    for category, entry in selector_results["selector"].items():
        counts = Counter(fold["winner"] for fold in entry["folds"])
        winners[category] = counts.most_common(1)[0][0]
    return winners


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


def escalate_to_larger_model(question_text: str, category: str, temperature: float = 0.7) -> dict:
    """Real second-model call: openai/gpt-oss-120b on Groq (free plan, 200K TPD).

    Reuses the API-call logic from generation/generate.py (GroqProvider),
    including its rate-limit-safe client. NOTE: gpt-oss-120b only accepts
    reasoning_effort in {low, medium, high} (verified live 2026-09-16, 'none'
    is rejected), so 'low' is used as the closest instruct-mode setting.

    Pacing: waits max(22s, completion_tokens/900*60 + 2s) to stay under the
    Groq OTPM-style cap, matching the main pipeline's safeguards.
    """
    import time

    from generation.generate import GroqProvider

    provider = GroqProvider("openai/gpt-oss-120b", reasoning_effort="low")
    system = config.CATEGORY_INSTRUCTIONS[category]
    max_tokens = TIER2_MAX_TOKENS
    text, usage, finish_reason = provider.generate(question_text, system, temperature, max_tokens)
    completion_tokens = usage.get("completion_tokens") or 0
    sleep_seconds = max(config.DEFAULT_SLEEP_SECONDS, completion_tokens * 60.0 / config.GROQ_OTPM_TARGET + 2.0)
    time.sleep(sleep_seconds)
    return {
        "status": "ok",
        "model": "openai/gpt-oss-120b",
        "answer": text,
        "finish_reason": finish_reason,
        "token_usage": usage,
    }


def main() -> int:
    uq.enable_utf8_stdout()
    parser = argparse.ArgumentParser(description="Confidence-gated escalation decisions.")
    parser.add_argument("--top-pct", type=float, default=15.0, help="fraction of most-uncertain questions escalated")
    parser.add_argument("--selector-json", default=str(uq.RESULTS_DIR / "selector_cv_results.json"))
    parser.add_argument("--output", default=str(uq.RESULTS_DIR / "escalation_decisions.jsonl"))
    parser.add_argument("--report", default=str(uq.RESULTS_DIR / "escalation_report.md"))
    args = parser.parse_args()
    uq.ensure_results_dir()

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    sources = {
        "ngram_tfidf": load_jsonl(uq.RESULTS_DIR / "ngram_tfidf.jsonl"),
        "lexical": load_jsonl(uq.RESULTS_DIR / "lexical.jsonl"),
        "semantic": load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl"),
    }
    selector_results = json.loads(Path(args.selector_json).read_text(encoding="utf-8"))
    winners = category_winner(selector_results)

    rows = []
    for question_id, label_row in correctness.items():
        label = label_row.get("overall_correct")
        if label is None:
            continue
        category = label_row["category"]
        method = winners[category]
        source, field = METHOD_SOURCES[method]
        score = sources[source].get(question_id, {}).get(field)
        if score is None:
            continue
        rows.append(
            {
                "question_id": question_id,
                "category": category,
                "method": method,
                "score": float(score),
                "error": 1 - int(label),
            }
        )

    # rank within category (per-method scores are already the gate method's)
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    for category, group in by_category.items():
        ranks = rank_normalize([row["score"] for row in group])
        for row, rank in zip(group, ranks):
            row["percentile"] = round(rank, 4)

    threshold = 1.0 - args.top_pct / 100.0
    for row in rows:
        row["escalate"] = row["percentile"] >= threshold

    decisions = []
    for row in rows:
        decision = {
            "question_id": row["question_id"],
            "category": row["category"],
            "gate_method": row["method"],
            "uncertainty": row["score"],
            "percentile": row["percentile"],
            "decision": "escalate" if row["escalate"] else "keep",
            "was_incorrect": bool(row["error"]),
        }
        if row["escalate"]:
            decision["escalation_target"] = {
                "tier": "openai/gpt-oss-120b",
                "status": "handled by scoring/tier2_pilot.py (gate runs spend no API calls)",
            }
        decisions.append(decision)
    uq.write_jsonl(args.output, decisions)

    # report at 10 / default / 20 percent
    lines = [
        "# Confidence-gated escalation report (first pass)",
        "",
        f"_Gate method per category (CV selector fold winners): "
        + ", ".join(f"{c}={m}" for c, m in winners.items()) + "._",
        "",
        f"Thresholds evaluated: top 10% / {args.top_pct:g}% / 20% most-uncertain.",
        "Precision = incorrect / escalated; recall = escalated-incorrect / all-incorrect; "
        "escalation rate = escalated / labeled.",
        "",
        "| Category | pct | labeled | escalated (rate) | incorrect-escalated | precision | recall | error rate |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    summary_blocks = []
    for pct in (10.0, args.top_pct, 20.0):
        threshold_pct = 1.0 - pct / 100.0
        block = []
        for category in ("factual", "math", "reasoning"):
            group = by_category[category]
            escalated = [r for r in group if r["percentile"] >= threshold_pct]
            incorrect_total = sum(r["error"] for r in group)
            incorrect_escalated = sum(r["error"] for r in escalated)
            precision = incorrect_escalated / len(escalated) if escalated else 0.0
            recall = incorrect_escalated / incorrect_total if incorrect_total else 0.0
            error_rate = incorrect_total / len(group) if group else 0.0
            lines.append(
                f"| {category} | {pct:g}% | {len(group)} | {len(escalated)} ({100 * len(escalated) / len(group):.0f}%) "
                f"| {incorrect_escalated} | {precision:.2f} | {recall:.2f} | {error_rate:.2f} |"
            )
        # overall
        escalated = [r for r in rows if r["percentile"] >= threshold_pct]
        incorrect_total = sum(r["error"] for r in rows)
        incorrect_escalated = sum(r["error"] for r in escalated)
        precision = incorrect_escalated / len(escalated) if escalated else 0.0
        recall = incorrect_escalated / incorrect_total if incorrect_total else 0.0
        lines.append(
            f"| **all** | {pct:g}% | {len(rows)} | {len(escalated)} ({100 * len(escalated) / len(rows):.0f}%) "
            f"| {incorrect_escalated} | {precision:.2f} | {recall:.2f} | {incorrect_total / len(rows):.2f} |"
        )
        summary_blocks.append(
            f"top {pct:g}%: escalate {len(escalated)}/{len(rows)} ({100 * len(escalated) / len(rows):.0f}%), "
            f"precision {precision:.2f}, recall {recall:.2f}"
        )
    lines += [
        "",
        "## Summary",
        "",
    ]
    for block in summary_blocks:
        lines.append(f"- {block}")
    lines += [
        "",
        "## Second-model call",
        "",
        f"- The escalation call is wired (`openai/gpt-oss-120b`, reasoning_effort "
        f"low) in `scoring/escalate.py:escalate_to_larger_model`, but is executed "
        f"only by `scoring/tier2_pilot.py` for the ~52 escalated questions; the "
        f"gate itself never spends API calls.",
        "",
    ]
    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"decisions -> {args.output}")
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
