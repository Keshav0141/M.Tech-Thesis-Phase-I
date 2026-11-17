"""Track 2 funnel: all numbers for the framework deck, on the 450 main questions.

Uses saved data only (no API calls). Steps that need question_nll.csv / question_emb.npz
(from track2/kaggle/question_nll_embed.py) are skipped until those files exist.
Output: track2/outputs/funnel.json and a printed summary.
"""
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "track2/outputs"
REF_MODEL = "Qwen/Qwen2.5-1.5B"
import sys as _s
FEAT = _s.argv[1] if len(_s.argv) > 1 else "mean_nll"

pc = {r["question_id"]: r for r in map(json.loads, open(OUT / "pct_correct.jsonl")) if r["split"] == "main"}
qs = {q["question_id"]: q for q in json.load(open(ROOT / "data/dataset.json")) if q["question_id"] in pc}
cor = {r["question_id"]: r for r in map(json.loads, open(ROOT / "results/correctness.jsonl")) if r["question_id"] in pc}
arith = {}
for r in map(json.loads, open(OUT / "arith_verify.jsonl")):
    if r["question_id"] in pc and r["sample_id"] == 0:
        arith[r["question_id"]] = r
ids = sorted(pc)
CATS = ["factual", "math", "reasoning"]
res = {"n": len(ids)}


def acc(sub):  # single-pass (sample 1) accuracy in %
    return round(100 * np.mean([pc[i]["sample1_correct"] for i in sub]), 1) if sub else None


def norm(x):
    if isinstance(x, (int, float)):
        return round(float(x), 4)
    s = re.sub(r"[^a-z0-9 ]", " ", str(x).lower())
    s = re.sub(r"\b(the|a|an)\b", " ", s)
    return " ".join(s.split())


# ---- data table ----
res["data"] = {c: {"n": sum(qs[i]["category"] == c for i in ids),
                   "majority_correct": sum(pc[i]["majority_correct"] for i in ids if qs[i]["category"] == c),
                   "single_pass_acc": acc([i for i in ids if qs[i]["category"] == c])} for c in CATS}
res["data"]["all"] = {"n": len(ids), "majority_correct": sum(pc[i]["majority_correct"] for i in ids),
                      "single_pass_acc": acc(ids)}

# ---- step 1: domain check (embeddings + similarity threshold) ----
in_domain = set(ids)
emb_path = OUT / "question_emb.npz"
if emb_path.exists():
    z = np.load(emb_path, allow_pickle=True)
    e = dict(zip(z["ids"], z["emb"]))
    X = np.stack([e[i] for i in ids])
    S = X @ X.T
    np.fill_diagonal(S, -1)
    K = 5
    own = np.sort(S, axis=1)[:, -K:].mean(1)  # leave-one-out: mean sim to 5 nearest other questions
    ood = {}
    if "banking_test_emb" in z.files:
        B = z["banking_test_emb"]
        ood_sc = np.sort(B @ X.T, axis=1)[:, -K:].mean(1)
        thr = float(np.percentile(own, 2))  # keep 98% of our questions
        ood = {"banking77_n": len(B), "banking77_rejected": int((ood_sc < thr).sum()),
               "banking_kept_examples": [str(t) for t, s in zip(z["banking_test_text"], ood_sc) if s >= thr][:3],
               "banking_rejected_examples": [str(t) for t in z["banking_test_text"][np.argsort(ood_sc)[:3]]]}
    else:
        thr = float(np.percentile(own, 2))
    removed = [i for i, s in zip(ids, own) if s < thr]
    in_domain = set(ids) - set(removed)
    res["domain"] = {"threshold": round(thr, 3), "k": K, "kept": len(in_domain), "removed": len(removed),
                     "removed_ids": removed, "removed_examples": [qs[i]["question_text"] for i in removed[:3]],
                     "acc_kept": acc(sorted(in_domain)), "acc_removed": acc(removed), **ood}
else:
    res["domain"] = "pending: needs question_emb.npz"

# ---- step 2: hard vs easy (question NLL, threshold = median of in-domain) ----
nll_path = OUT / "question_nll.csv"
easy, hard = None, None
if nll_path.exists():
    import pandas as pd
    nl = pd.read_csv(nll_path)
    nl = nl[(nl.ref_model == REF_MODEL) & nl.question_id.isin(in_domain)].set_index("question_id")
    cat_thr = nl.groupby("category")[FEAT].median()  # one cut-off per category (a single cut-off just splits categories)
    nl = nl[FEAT]
    easy = sorted(i for i in nl.index if nl[i] <= cat_thr[qs[i]["category"]])
    hard = sorted(i for i in nl.index if nl[i] > cat_thr[qs[i]["category"]])
    res["difficulty"] = {"feature": f"{FEAT} of question under {REF_MODEL}", "threshold_per_category": cat_thr.round(3).to_dict(),
                         "easy": len(easy), "hard": len(hard), "acc_easy": acc(easy), "acc_hard": acc(hard),
                         "by_cat": {c: {"easy": sum(qs[i]["category"] == c for i in easy),
                                        "hard": sum(qs[i]["category"] == c for i in hard),
                                        "acc_easy": acc([i for i in easy if qs[i]["category"] == c]),
                                        "acc_hard": acc([i for i in hard if qs[i]["category"] == c])} for c in CATS},
                         "easy_example": qs[easy[np.argmin([nl[i] for i in easy])]]["question_text"],
                         "hard_example": qs[hard[np.argmax([nl[i] for i in hard])]]["question_text"]}
else:
    res["difficulty"] = "pending: needs question_nll.csv"

# ---- step 3: math checkable (first answer has >=1 'expr = number' step) ----
pool = hard if hard is not None else sorted(in_domain)
math_ids = [i for i in pool if qs[i]["category"] == "math"]
chk = [i for i in math_ids if arith.get(i, {}).get("n_steps_checked", 0) > 0]
res["math_check"] = {"pool": "hard" if hard is not None else "all in-domain", "math_questions": len(math_ids),
                     "checkable": len(chk), "not_checkable": len(math_ids) - len(chk),
                     "steps_checked": sum(arith[i]["n_steps_checked"] for i in chk),
                     "steps_wrong": sum(arith[i]["n_steps_wrong"] for i in chk),
                     "acc_checkable": acc(chk), "acc_not_checkable": acc([i for i in math_ids if i not in chk])}

# ---- step 4: regenerate (5 saved answers) and check agreement ----
def agree(i):
    ans = [norm(p["extracted"]) for p in cor[i]["per_sample"] if p["extracted"] not in (None, "")]
    if len(ans) < 5:
        return False, 0
    top = Counter(ans).most_common(1)[0][1]
    return top == 5, top


regen_pool = hard if hard is not None else sorted(in_domain)
co = {i: agree(i) for i in regen_pool}
coh = [i for i in regen_pool if co[i][0]]
inc = [i for i in regen_pool if not co[i][0]]
res["agreement"] = {"pool": "hard" if hard is not None else "all in-domain", "n": len(regen_pool),
                    "coherent_5of5": len(coh), "not_coherent": len(inc),
                    "coherent_and_correct": sum(pc[i]["majority_correct"] for i in coh),
                    "acc_coherent": acc(coh), "acc_not_coherent": acc(inc),
                    "by_cat": {c: {"coherent": sum(qs[i]["category"] == c for i in coh),
                                   "not": sum(qs[i]["category"] == c for i in inc),
                                   "acc_coherent": acc([i for i in coh if qs[i]["category"] == c]),
                                   "acc_not": acc([i for i in inc if qs[i]["category"] == c])} for c in CATS},
                    "coherent_but_wrong_examples": [i for i in coh if not pc[i]["majority_correct"]][:5]}

# ---- step 5: 2x2 decision (only once difficulty exists) ----
if easy is not None:
    allco = {i: agree(i)[0] for i in in_domain}
    cells = {"easy_agree (accept)": [i for i in easy if allco[i]],
             "easy_disagree (verify)": [i for i in easy if not allco[i]],
             "hard_agree (verify)": [i for i in hard if allco[i]],
             "hard_disagree (refuse)": [i for i in hard if not allco[i]]}
    res["decision_2x2"] = {k: {"n": len(v), "acc": acc(v)} for k, v in cells.items()}
else:
    res["decision_2x2"] = "pending: needs difficulty split"

json.dump(res, open(OUT / "funnel.json", "w"), indent=1)
print(json.dumps(res, indent=1))
