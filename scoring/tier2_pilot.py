"""Tier-2 escalation pilot: run the real second-model call for the escalated set.

Calls openai/gpt-oss-120b (via scoring/escalate.escalate_to_larger_model) for
each of the ~52 escalated questions, 1 sample each (temperature 0.7), logs to
logs/tier2_generations.jsonl, then scores correctness of the tier-2 answer
against the original qwen correctness and reports error recovery.

Dry-run/plan mode: python scoring/tier2_pilot.py --dry-run

Actual run: python scoring/tier2_pilot.py  (awaits explicit go-ahead)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uq_common as uq

import config as config_mod

from escalate import escalate_to_larger_model

TIER2_LOG = config_mod.LOGS_DIR / "tier2_generations.jsonl"


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
    parser = argparse.ArgumentParser(description="Tier-2 (gpt-oss-120b) escalation pilot.")
    parser.add_argument("--escalated", default=str(uq.RESULTS_DIR / "tier2_escalated_questions.json"))
    parser.add_argument("--limit", type=int, help="max questions to process")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without calling the API")
    args = parser.parse_args()

    payload = json.loads(Path(args.escalated).read_text(encoding="utf-8"))
    escalated = payload["questions"]
    if args.limit:
        escalated = escalated[: args.limit]

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")

    def score_answer(question: dict, text: str):
        category = question["category"]
        ground_truth = question["ground_truth_answer"]
        if category == "factual":
            answer = uq.extract_final(text) or text
            label = uq.classify_factual(answer, ground_truth)
            return label, answer[:200]
        if category == "math":
            label, extracted = uq.classify_math(text, ground_truth)
            return label, extracted
        label, extracted = uq.classify_reasoning(text, ground_truth)
        return label, extracted

    if args.dry_run:
        print(f"[dry-run] {len(escalated)} escalated questions to call "
              f"openai/gpt-oss-120b (1 sample each, temp 0.7, reasoning_effort low):")
        print(f"[dry-run] tokens ~ {len(escalated) * 400:,} est | requests {len(escalated)} "
              f"| ETA ~ {len(escalated) * 28 / 60:.0f} min")
        from collections import Counter

        print("[dry-run] by category:", dict(Counter(q["category"] for q in escalated)))
        return 0

    done = set()
    if TIER2_LOG.exists():
        done = {row["question_id"] for row in load_jsonl(TIER2_LOG).values()}

    records = []
    start = time.time()
    for index, question in enumerate(escalated, 1):
        question_id = question["question_id"]
        if question_id in done:
            print(f"[{index}/{len(escalated)}] {question_id}: already done, skipping")
            continue
        call_start = time.time()
        try:
            result = escalate_to_larger_model(question["question_text"], question["category"])
        except Exception as error:
            print(f"[{index}/{len(escalated)}] {question_id}: FAILED {str(error)[:160]}")
            continue
        latency = time.time() - call_start
        record = {
            "run_id": uuid.uuid4().hex[:12],
            "status": "ok",
            "question_id": question_id,
            "category": question["category"],
            "provider": "groq",
            "model_name": "openai/gpt-oss-120b",
            "sample_id": 0,
            "response_text": result["answer"],
            "finish_reason": result.get("finish_reason"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token_usage": result.get("token_usage"),
            "parameters": {"temperature": 0.7, "reasoning_effort": "low"},
            "latency_s": round(latency, 2),
        }
        label, extracted = score_answer(question, result["answer"])
        record["tier2_label"] = label
        record["tier2_extracted"] = extracted
        original = correctness.get(question_id, {}).get("overall_correct")
        record["original_correct"] = original
        records.append(record)
        print(
            f"[{index}/{len(escalated)}] {question_id} ({question['category']}): "
            f"{label} | qwen_correct={original} | {latency:.1f}s"
        )
        with TIER2_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    elapsed = time.time() - start
    print(f"\n[tier2] completed in {elapsed / 60:.1f} min")

    # report recovery
    rows = []
    if TIER2_LOG.exists():
        rows = list(load_jsonl(TIER2_LOG).values())
    n_escalated = len(rows)
    recovery = sum(1 for r in rows if r.get("original_correct") == 0 and r.get("tier2_label") == "correct")
    still_wrong = sum(1 for r in rows if r.get("original_correct") == 0 and r.get("tier2_label") != "correct")
    regressed = sum(1 for r in rows if r.get("original_correct") == 1 and r.get("tier2_label") != "correct")
    kept_right = sum(1 for r in rows if r.get("original_correct") == 1 and r.get("tier2_label") == "correct")
    print(f"escalated answered: {n_escalated}")
    print(f"qwen wrong -> gpt-oss-120b right (RECOVERY): {recovery}")
    print(f"qwen wrong -> still wrong: {still_wrong}")
    print(f"qwen right -> kept right: {kept_right}")
    print(f"qwen right -> regressed: {regressed}")
    print(f"final accuracy on escalated set: {(recovery + kept_right) / max(1, n_escalated):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())