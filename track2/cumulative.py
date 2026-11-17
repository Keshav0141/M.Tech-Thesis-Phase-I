"""Cumulative comparison table for the deck and report (all 450 test questions, label = first answer wrong).

Rows: no check, the Phase 1 methods and the verifier (each flagging as many questions as there are wrong
first answers), then the framework after each step at its own operating point. For every framework row the
table also gives the number of wrong answers a 5-answer method catches when it flags the same number of
questions. Ties in a score are broken in expectation (not by question order).
Output: track2/outputs/cumulative.json
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "track2/outputs"
DOM, K = ["factual", "math", "reasoning"], 5
L = lambda f: {json.loads(l)["question_id"]: json.loads(l) for l in open(f)}
pc = {k: v for k, v in L(OUT / "pct_correct.jsonl").items() if v["split"] == "main"}
ids = sorted(pc)
W = {i: 1 - pc[i]["sample1_correct"] for i in ids}
NW = sum(W.values())
cor = L(ROOT / "results/correctness.jsonl")
tf, se, gm = L(ROOT / "results/ngram_tfidf.jsonl"), L(ROOT / "results/semantic_entropy.jsonl"), L(ROOT / "results/graph_methods.jsonl")
kev = L(ROOT / "track2/kev/kev_scores.jsonl")
SC = {"wo": {i: tf[i]["tfidf_uncertainty"] for i in ids}, "se": {i: se[i]["semantic_entropy"] for i in ids},
      "ns": {i: gm[i]["num_sets"] for i in ids}, "kev": {i: 1 - kev[i]["p_yes"] for i in ids}}


def caught_at(score, k):
    """Expected number of wrong answers among the k highest-scoring questions (ties shared equally)."""
    if k == 0:
        return 0.0
    v = np.array([round(score[i], 9) for i in ids]); w = np.array([W[i] for i in ids])
    cut = np.sort(v)[::-1][k - 1]
    above, tie = v > cut, v == cut
    return float(w[above].sum() + (k - above.sum()) / tie.sum() * w[tie].sum())


def row(label, calls, flagged, caught, ref=True):
    caught = int(round(caught)); fa = flagged - caught; missed = NW - caught; acc_n = len(ids) - flagged
    r = {"label": label, "calls": calls, "flagged": flagged, "accepted": acc_n, "caught": caught, "false": fa, "missed": missed,
         "acc": round(100 * (acc_n - missed) / acc_n, 1)}
    if ref:
        for m in ["wo", "se", "ns"]:
            r["ref_" + m] = int(round(caught_at(SC[m], flagged)))
    return r


# ---- framework sets (same definitions as funnel2.py) ----
bz = np.load(OUT / "bank_emb.npz", allow_pickle=True); BE, BD = bz["emb"], bz["domain"]
tz = np.load(OUT / "question_emb.npz", allow_pickle=True); te = dict(zip(tz["ids"], tz["emb"]))
own = np.zeros(len(BE))
for d in DOM:
    m = BD == d; S = BE[m] @ BE[m].T; np.fill_diagonal(S, -1); own[m] = np.sort(S, 1)[:, -K:].mean(1)
thr = {d: np.percentile(own[BD == d], 2) for d in DOM}  # one threshold per domain
X = np.stack([te[i] for i in ids]); TS = np.stack([np.sort(X @ BE[BD == d].T, 1)[:, -K:].mean(1) for d in DOM], 1)
pred = {i: DOM[int(TS[n].argmax())] for n, i in enumerate(ids)}; sc = {i: float(TS[n].max()) for n, i in enumerate(ids)}
ood = [i for i in ids if sc[i] < thr[pred[i]]]; ind = [i for i in ids if sc[i] >= thr[pred[i]]]
med = pd.read_csv(OUT / "bank_nll.csv").groupby("domain").mean_nll.median()
nl = pd.read_csv(OUT / "question_nll.csv"); nl = nl[nl.ref_model == "Qwen/Qwen2.5-1.5B"].set_index("question_id").mean_nll
easy = [i for i in ind if nl[i] <= med[pred[i]]]; hard = [i for i in ind if nl[i] > med[pred[i]]]


def nrm(x):
    if isinstance(x, (int, float)):
        return round(float(x), 4)
    t = re.sub(r"[^a-z0-9 ]", " ", str(x).lower()); t = re.sub(r"\b(the|a|an)\b", " ", t)
    return " ".join(t.split())


def agree(i):
    a = [nrm(p["extracted"]) for p in cor[i]["per_sample"] if p["extracted"] not in (None, "")]
    return len(a) == 5 and len(set(a)) == 1


dis = [i for i in hard if not agree(i)]
wr = lambda s: sum(W[i] for i in s)
N = len(ids)
R = {
    "nocheck": row("No check (every answer accepted)", N, 0, 0, ref=False),
    "wo": row("Word overlap, TF-IDF (5 answers)", 5 * N, NW, caught_at(SC["wo"], NW), ref=False),
    "se": row("Semantic Entropy (5 answers)", 5 * N, NW, caught_at(SC["se"], NW), ref=False),
    "ns": row("NumSets (5 answers)", 5 * N, NW, caught_at(SC["ns"], NW), ref=False),
    "kev": row("Kev verifier (1 answer)", N, NW, caught_at(SC["kev"], NW)),
    "s1": row("Framework: Step 1", len(ind), len(ood), wr(ood)),
    "s2": row("Framework: Steps 1 to 2", len(ind), len(ood) + len(hard), wr(ood) + wr(hard)),
    "s3": row("Framework: Steps 1 to 3", len(ind), len(ood) + len(hard), wr(ood) + wr(hard)),
    "s4": row("Framework: Steps 1 to 5", len(easy) + 5 * len(hard), len(ood) + len(dis), wr(ood) + wr(dis)),
}
AT = {str(k): {m: row(m, 0, k, caught_at(SC[m], k), ref=False) for m in SC} for k in {R["s2"]["flagged"], R["s4"]["flagged"]}}
json.dump({"n": N, "n_wrong": NW, "rows": R, "at": AT}, open(OUT / "cumulative.json", "w"), indent=1)
for k, r in R.items():
    print(k, r)
