"""Track 2, component (e): AUROC of Kev-0.8B P(yes) for detecting wrong answers (no LLM judge, laptop CPU run)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scoring"))
from uq_common import roc_auc  # noqa: E402

kev = {json.loads(l)["question_id"]: json.loads(l)["p_yes"] for l in (ROOT / "track2/kev/kev_scores.jsonl").open()}
rows = []
for l in (ROOT / "results/correctness.jsonl").open(encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        s0 = next(s for s in r["per_sample"] if int(s["sample_id"]) == 0)
        rows.append((r["category"], kev[r["question_id"]], int(s0["label"] == "correct"), int(r["majority_label"] == "correct"), r["n_correct"] / 5))
print(f"{'category':10s} {'n':>4s} {'wrong(s0)':>9s} {'AUROC s0':>9s} {'AUROC maj':>9s} {'meanP|right':>11s} {'meanP|wrong':>11s}")
for cat in ("factual", "math", "reasoning", "all"):
    xs = [x for x in rows if cat == "all" or x[0] == cat]
    a0 = roc_auc([1 - x[2] for x in xs], [1 - x[1] for x in xs])[0]
    am = roc_auc([1 - x[3] for x in xs], [1 - x[1] for x in xs])[0]
    pr = [x[1] for x in xs if x[2]]; pw = [x[1] for x in xs if not x[2]]
    print(f"{cat:10s} {len(xs):4d} {len(pw):9d} {a0:9.3f} {am:9.3f} {sum(pr)/len(pr):11.3f} {sum(pw)/max(1,len(pw)):11.3f}")
