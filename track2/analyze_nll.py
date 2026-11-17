"""Component (a) test: does question NLL separate correct vs incorrect answers?

Needs track2/outputs/question_nll.csv (from the Kaggle job) and pct_correct.jsonl (Step 0).
AUROC is for flagging an INCORRECT answer with a high score. AUROC < 0.5 means the low end flags errors.
Labels: sample-1 wrong (the real single-response case) and majority wrong (Track 1 label).
"""
import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scoring"))
from uq_common import roc_auc  # noqa: E402

nll = pd.read_csv(ROOT / "track2/outputs/question_nll.csv")
lab = pd.DataFrame([json.loads(l) for l in open(ROOT / "track2/outputs/pct_correct.jsonl")])
df = nll.merge(lab[["question_id", "pct_correct", "sample1_correct", "majority_correct"]], on="question_id")
FEATS = ["mean_nll", "sum_nll", "max_nll", "n_tokens"]  # n_tokens = length baseline

out = []
for (model, split), g in df.groupby(["ref_model", "split"]):
    for cat, h in [("all", g)] + list(g.groupby("category")):
        for f in FEATS:
            a1, p1, _ = roc_auc((1 - h.sample1_correct).tolist(), h[f].tolist())
            am, pm, _ = roc_auc((1 - h.majority_correct).tolist(), h[f].tolist())
            rho, p = spearmanr(h[f], h.pct_correct)
            out.append({"ref_model": model, "split": split, "category": cat, "feature": f, "n": len(h),
                        "wrong_s1": p1, "auroc_s1": a1, "wrong_maj": pm, "auroc_maj": am,
                        "spearman_vs_pct": rho, "spearman_p": p})
res = pd.DataFrame(out)
res.to_csv(ROOT / "track2/outputs/nll_auroc.csv", index=False)
pd.set_option("display.width", 200)
print(res.round(3).to_string(index=False))
