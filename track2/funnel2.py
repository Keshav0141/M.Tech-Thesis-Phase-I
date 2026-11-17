"""Track 2 framework v2: domain bank routing + bank-based difficulty thresholds.

Inputs (saved data, no API calls):
  track2/outputs/bank_emb.npz, bank_nll.csv        domain bank (questions outside the 450)
  track2/outputs/question_emb.npz, question_nll.csv the 450 test questions
  pct_correct, correctness, arith_verify, results/* (baselines), kev scores
Label everywhere: is the FIRST answer (the one a user receives) correct?
Output: track2/outputs/funnel2.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "track2/outputs"
sys.path.insert(0, str(ROOT / "scoring"))
from uq_common import roc_auc  # noqa: E402

K, KEEP_PCT, REF = 5, 2, "Qwen/Qwen2.5-1.5B"
DOM = ["factual", "math", "reasoning"]
L = lambda f: {json.loads(l)["question_id"]: json.loads(l) for l in open(f)}
pc = {k: v for k, v in L(OUT / "pct_correct.jsonl").items() if v["split"] == "main"}
ids = sorted(pc)
qs = {q["question_id"]: q for q in json.load(open(ROOT / "data/dataset.json"))}
cor = L(ROOT / "results/correctness.jsonl")
arith = {r["question_id"]: r for r in map(json.loads, open(OUT / "arith_verify.jsonl")) if r["sample_id"] == 0}
wrong = {i: 1 - pc[i]["sample1_correct"] for i in ids}
tf, se, gm = L(ROOT / "results/ngram_tfidf.jsonl"), L(ROOT / "results/semantic_entropy.jsonl"), L(ROOT / "results/graph_methods.jsonl")
kev = L(ROOT / "track2/kev/kev_scores.jsonl")
BASE = {"Word overlap (TF-IDF), 5 answers": {i: tf[i]["tfidf_uncertainty"] for i in ids},
        "Semantic Entropy, 5 answers": {i: se[i]["semantic_entropy"] for i in ids},
        "NumSets (Lin et al.), 5 answers": {i: gm[i]["num_sets"] for i in ids},
        "Kev verifier, 1 answer": {i: 1 - kev[i]["p_yes"] for i in ids}}
res = {"label": "first answer wrong = 1", "n": len(ids), "n_wrong": sum(wrong.values())}
acc = lambda s: round(100 * (1 - np.mean([wrong[i] for i in s])), 1) if s else None


def auroc(score, sub=None):
    sub = sub or ids
    return round(roc_auc([wrong[i] for i in sub], [score[i] for i in sub])[0], 3)


res["auroc_all"] = {m: {c: auroc(s, [i for i in ids if qs[i]["category"] == c]) for c in DOM} | {"all": auroc(s)} for m, s in BASE.items()}

# ---------------- Step 1: domain bank routing ----------------
bz = np.load(OUT / "bank_emb.npz", allow_pickle=True)
BE, BD = bz["emb"], bz["domain"]
tz = np.load(OUT / "question_emb.npz", allow_pickle=True)
te = dict(zip(tz["ids"], tz["emb"]))
X = np.stack([te[i] for i in ids])


def dom_scores(V, exclude_self=False):
    out = np.zeros((len(V), 3))
    for j, d in enumerate(DOM):
        S = V @ BE[BD == d].T
        if exclude_self:
            S = np.sort(S, 1)[:, :-1]  # drop the self-match (similarity 1)
        out[:, j] = np.sort(S, 1)[:, -K:].mean(1)
    return out


# threshold from the bank only: leave-one-out score of each bank question against its own domain
own = np.zeros(len(BE))
for j, d in enumerate(DOM):
    m = BD == d
    S = BE[m] @ BE[m].T
    np.fill_diagonal(S, -1)
    own[m] = np.sort(S, 1)[:, -K:].mean(1)
# one threshold per domain: the KEEP_PCT-th percentile of that domain's own leave-one-out scores
thr = {d: float(np.percentile(own[BD == d], KEEP_PCT)) for d in DOM}
thr_pooled = float(np.percentile(own, KEEP_PCT))
TS = dom_scores(X)
pred = {i: DOM[int(np.argmax(TS[n]))] for n, i in enumerate(ids)}
score = {i: float(TS[n].max()) for n, i in enumerate(ids)}
ind = [i for i in ids if score[i] >= thr[pred[i]]]
out = [i for i in ids if score[i] < thr[pred[i]]]
cm = {t: {p: sum(1 for i in ids if qs[i]["category"] == t and pred[i] == p) for p in DOM} for t in DOM}
ex = lambda lst: [{"q": qs[i]["question_text"], "true": qs[i]["category"], "pred": pred[i],
                   "score": round(score[i], 3), "thr": round(thr[pred[i]], 3), "first_correct": not wrong[i], "by_domain": dict(zip(DOM, np.round(TS[ids.index(i)], 3).tolist()))} for i in lst]
hi = sorted(ids, key=lambda i: -score[i])
res["step1"] = {"bank_size": {d: int((BD == d).sum()) for d in DOM}, "k": K, "thresholds": {d: round(v, 3) for d, v in thr.items()}, "threshold_pooled": round(thr_pooled, 3),
                "bank_score_median": {d: round(float(np.median(own[BD == d])), 3) for d in DOM},
                "threshold_rule": f"per domain: {KEEP_PCT}th percentile of that domain's bank leave-one-out scores (keeps {100 - KEEP_PCT}% of the domain)",
                "removed_by_domain": {d: sum(pred[i] == d for i in out) for d in DOM}, "removed_wrong": sum(wrong[i] for i in out),
                "kept": len(ind), "removed": len(out), "routing_confusion": cm,
                "routing_accuracy": round(100 * np.mean([pred[i] == qs[i]["category"] for i in ids]), 1),
                "examples_in": ex([next(i for i in hi if qs[i]["category"] == c) for c in DOM]),
                "examples_out": ex(sorted(out, key=lambda i: (pred[i], score[i]))),
                "misrouted": ex([i for i in ids if pred[i] != qs[i]["category"]][:6]),
                "acc_in": acc(ind), "acc_out": acc(out)}

# ---------------- Step 2: difficulty, threshold = median NLL of the bank per domain ----------------
bn = pd.read_csv(OUT / "bank_nll.csv")
dthr = bn.groupby("domain").mean_nll.median().to_dict()
tn = pd.read_csv(OUT / "question_nll.csv")
tn = tn[(tn.ref_model == REF)].set_index("question_id").mean_nll.to_dict()
easy = [i for i in ind if tn[i] <= dthr[pred[i]]]
hard = [i for i in ind if tn[i] > dthr[pred[i]]]
res["step2"] = {"thresholds": {d: round(v, 3) for d, v in dthr.items()}, "easy": len(easy), "hard": len(hard),
                "acc_easy": acc(easy), "acc_hard": acc(hard),
                "by_domain": {d: {"easy": sum(pred[i] == d for i in easy), "hard": sum(pred[i] == d for i in hard),
                                  "acc_easy": acc([i for i in easy if pred[i] == d]), "acc_hard": acc([i for i in hard if pred[i] == d])} for d in DOM},
                "nll_auroc": {d: auroc(tn, [i for i in ind if pred[i] == d]) for d in DOM},
                "examples": {d: {"easy": min(([qs[i]["question_text"], round(tn[i], 2), not wrong[i]] for i in easy if pred[i] == d and len(qs[i]["question_text"]) < 260), key=lambda r: r[1], default=None),
                                 "hard": max(([qs[i]["question_text"], round(tn[i], 2), not wrong[i]] for i in hard if pred[i] == d and len(qs[i]["question_text"]) < 260), key=lambda r: r[1], default=None)} for d in DOM}}

# ---------------- Step 3: arithmetic check on hard questions routed to math ----------------
hm = [i for i in hard if pred[i] == "math"]
chk = [i for i in hm if arith.get(i, {}).get("n_steps_checked", 0) > 0]
res["step3"] = {"hard_math": len(hm), "checkable": len(chk), "steps": sum(arith[i]["n_steps_checked"] for i in chk),
                "steps_wrong": sum(arith[i]["n_steps_wrong"] for i in chk)}


# ---------------- Step 4: agreement of 5 answers on hard questions ----------------
def nrm(x):
    if isinstance(x, (int, float)):
        return round(float(x), 4)
    s = re.sub(r"[^a-z0-9 ]", " ", str(x).lower()); s = re.sub(r"\b(the|a|an)\b", " ", s)
    return " ".join(s.split())


def agree(i):
    a = [nrm(p["extracted"]) for p in cor[i]["per_sample"] if p["extracted"] not in (None, "")]
    return len(a) == 5 and len(set(a)) == 1


ag = [i for i in hard if agree(i)]
dis = [i for i in hard if not agree(i)]
res["step4"] = {"agree": len(ag), "disagree": len(dis), "acc_agree": acc(ag), "acc_disagree": acc(dis)}

# ---------------- Step 5 + comparison tables (same number of flagged questions) ----------------
accepted = easy + ag
flag = dis


def cmat(flagged, pool):
    fl = set(flagged); acc_set = [i for i in pool if i not in fl]
    return {"flagged": len(fl), "caught_wrong": sum(wrong[i] for i in fl), "false_alarm": sum(1 - wrong[i] for i in fl),
            "missed_wrong": sum(wrong[i] for i in acc_set), "accepted_right": sum(1 - wrong[i] for i in acc_set),
            "accepted_accuracy": acc(acc_set)}


def compare(fw_flag, pool, fw_calls):
    rows = {"Framework": cmat(fw_flag, pool) | {"calls": fw_calls}}
    for m, s in BASE.items():
        top = sorted(pool, key=lambda i: -s[i])[:len(fw_flag)]
        rows[m] = cmat(top, pool) | {"calls": 5 * len(pool) if "5 answers" in m else len(pool)}
    rows["No check (trust all)"] = cmat([], pool) | {"calls": len(pool)}
    return rows


res["step5"] = {"accepted": len(accepted), "acc_accepted": acc(accepted), "flagged": len(flag), "acc_flagged": acc(flag),
                "cells": {"easy": [len(easy), acc(easy)], "hard_agree": [len(ag), acc(ag)], "hard_disagree": [len(dis), acc(dis)]}}
res["compare_step2"] = compare(hard, ind, len(ind))  # flag = hard questions, 1 call each
res["compare_final"] = compare(flag, ind, len(easy) + 5 * len(hard))
json.dump(res, open(OUT / "funnel2.json", "w"), indent=1)
print(json.dumps({k: res[k] for k in ["step1", "step2", "step3", "step4", "step5"]}, indent=1)[:6000])
print(json.dumps(res["compare_final"], indent=1))
