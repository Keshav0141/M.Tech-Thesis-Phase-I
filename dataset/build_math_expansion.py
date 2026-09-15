"""Build a math expansion set (set B): ~150 fresh GSM8K questions.

Reuses the original validation logic from build_dataset.py (check_math,
Deduper). Questions are deduplicated against the locked 450-question dataset
AND within the expansion set. Written to data/math_expansion.json with
question ids mathb_0001.. so they can never collide with the main dataset.

Not merged into data/dataset.json; the main pipeline is untouched.

Usage:
    python dataset/build_math_expansion.py --target 150 --seed 100
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_dataset
import config


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the GSM8K math expansion set.")
    parser.add_argument("--target", type=int, default=150)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--max-candidates", type=int, default=2000)
    parser.add_argument("--output", default=str(config.DATA_DIR / "math_expansion.json"))
    args = parser.parse_args()

    deduper = build_dataset.Deduper()
    locked = json.loads(config.DATASET_PATH.read_text(encoding="utf-8"))
    for entry in locked:
        deduper.check(entry["question_text"], entry["category"], entry["question_id"])
    print(f"deduper seeded with {len(locked)} locked questions")

    accepted = []
    reasons: Counter = Counter()
    inspected = 0
    for item in build_dataset.iter_candidates("math", args.seed, args.max_candidates):
        if len(accepted) >= args.target:
            break
        inspected += 1
        record, reason = build_dataset.check_math(item)
        if reason:
            reasons[reason] += 1
            continue
        question_id = f"mathb_{len(accepted) + 1:04d}"
        if deduper.check(record["question_text"], "math", question_id):
            reasons["duplicate (exact/near)"] += 1
            continue
        record.update(
            {
                "question_id": question_id,
                "category": "math",
                "source_dataset": "GSM8K (main) - expansion set B",
                "validation_status": "auto_validated",
            }
        )
        accepted.append(record)

    if len(accepted) < args.target:
        print(f"WARNING: only found {len(accepted)}/{args.target} after inspecting {inspected}")
    Path(args.output).write_text(json.dumps(accepted, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"math expansion -> {args.output}: {len(accepted)} questions")
    print(f"inspected {inspected}, rejected {sum(reasons.values())}: {dict(reasons.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
