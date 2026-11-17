"""Track 2, Step 0: per-question % correct (out of 5 samples) from existing Track 1 labels.

Reads results/correctness.jsonl and results/mathb_correctness.jsonl (read-only).
Writes track2/outputs/pct_correct.jsonl and prints a summary.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"main": ROOT / "results/correctness.jsonl", "mathb_heldout": ROOT / "results/mathb_correctness.jsonl"}
OUT = ROOT / "track2/outputs/pct_correct.jsonl"

rows = []
for split, path in SOURCES.items():
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        labels = [s["label"] for s in sorted(r["per_sample"], key=lambda s: int(s["sample_id"]))]
        n_correct = sum(l == "correct" for l in labels)
        rows.append({
            "question_id": r["question_id"], "category": r["category"], "split": split,
            "n_samples": len(labels), "n_correct": n_correct,
            "pct_correct": round(100 * n_correct / len(labels), 1),
            "sample1_correct": int(labels[0] == "correct"),
            "majority_correct": int(r["overall_correct"]),
        })

OUT.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")

groups = defaultdict(list)
for x in rows:
    groups[(x["split"], x["category"])].append(x)
for (split, cat), xs in groups.items():
    dist = Counter(int(x["pct_correct"]) for x in xs)
    mean = sum(x["pct_correct"] for x in xs) / len(xs)
    s1 = sum(x["sample1_correct"] for x in xs) / len(xs)
    maj = sum(x["majority_correct"] for x in xs) / len(xs)
    print(f"{split:14s} {cat:9s} n={len(xs)} mean%={mean:5.1f} sample1_acc={s1:.3f} majority_acc={maj:.3f} "
          + " ".join(f"{k}%:{dist.get(k,0)}" for k in (0, 20, 40, 60, 80, 100)))
