"""Robustness of the framework results (no API calls): threshold sensitivity, bootstrap intervals,
breakdown of the accepted wrong answers, and the second-answer estimate for easy questions.
Step 1 uses one threshold per domain (percentile of that domain's reference-set scores).
Output: track2/outputs/docs_extras.json; also refreshes agree_by_domain in report_extras.json.
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
qs = {q["question_id"]: q for q in json.load(open(ROOT / "data/dataset.json"))}
W = {i: 1 - pc[i]["sample1_correct"] for i in ids}
cor = L(ROOT / "results/correctness.jsonl")
WO = {i: round(v["tfidf_uncertainty"], 9) for i, v in L(ROOT / "results/ngram_tfidf.jsonl").items() if i in W}
bz = np.load(OUT / "bank_emb.npz", allow_pickle=True); BE, BD = bz["emb"], bz["domain"]
tz = np.load(OUT / "question_emb.npz", allow_pickle=True); te = dict(zip(tz["ids"], tz["emb"]))
own = {}
for d in DOM:
    S = BE[BD == d] @ BE[BD == d].T; np.fill_diagonal(S, -1); own[d] = np.sort(S, 1)[:, -K:].mean(1)
X = np.stack([te[i] for i in ids]); TS = np.stack([np.sort(X @ BE[BD == d].T, 1)[:, -K:].mean(1) for d in DOM], 1)
pred = {i: DOM[int(TS[n].argmax())] for n, i in enumerate(ids)}; sc = {i: float(TS[n].max()) for n, i in enumerate(ids)}
bn = pd.read_csv(OUT / "bank_nll.csv")
nl = pd.read_csv(OUT / "question_nll.csv"); nl = nl[nl.ref_model == "Qwen/Qwen2.5-1.5B"].set_index("question_id").mean_nll.to_dict()


def nrm(x):
    if isinstance(x, (int, float)):
        return round(float(x), 4)
    t = re.sub(r"[^a-z0-9 ]", " ", str(x).lower()); t = re.sub(r"\b(the|a|an)\b", " ", t)
    return " ".join(t.split())


ans = {i: [nrm(p["extracted"]) if p["extracted"] not in (None, "") else None for p in cor[i]["per_sample"]] for i in ids}
agree = {i: None not in ans[i] and len(set(ans[i])) == 1 for i in ids}
acc = lambda s: round(100 * (1 - np.mean([W[i] for i in s])), 1)


def run(p1=2, q=0.5):
    thr = {d: float(np.percentile(own[d], p1)) for d in DOM}
    med = bn.groupby("domain").mean_nll.quantile(q).to_dict()
    ood = [i for i in ids if sc[i] < thr[pred[i]]]; ind = [i for i in ids if sc[i] >= thr[pred[i]]]
    easy = [i for i in ind if nl[i] <= med[pred[i]]]; hard = [i for i in ind if nl[i] > med[pred[i]]]
    dis = [i for i in hard if not agree[i]]
    return dict(thr=thr, ood=ood, easy=easy, hard=hard, dis=dis, held=ood + dis)


def summ(r):
    held = set(r["held"]); accd = [i for i in ids if i not in held]
    return {"thr": {d: round(v, 3) for d, v in r["thr"].items()}, "out": len(r["ood"]), "easy": len(r["easy"]), "hard": len(r["hard"]),
            "flag": len(held), "caught": sum(W[i] for i in held), "acc": acc(accd), "calls": len(r["easy"]) + 5 * len(r["hard"]),
            "acc_easy": acc(r["easy"]), "acc_hard": acc(r["hard"])}


B = run(); res = {"base": summ(B)}
res["sens_p1"] = {str(p): summ(run(p1=p)) for p in [1, 2, 5, 10]}
res["sens_q"] = {str(q): summ(run(q=q)) for q in [0.3, 0.4, 0.5, 0.6, 0.7]}

# bootstrap within each true domain (thresholds fixed); word overlap holds back the same number, ties shared
rng = np.random.default_rng(0); held = set(B["held"])
h = np.array([i in held for i in ids]); w = np.array([W[i] for i in ids]); v = np.array([WO[i] for i in ids])
strata = [np.array([n for n, i in enumerate(ids) if qs[i]["category"] == d]) for d in DOM]


def wo_caught(vv, ww, k):
    if k == 0:
        return 0.0
    cut = np.sort(vv)[::-1][k - 1]; ab, tie = vv > cut, vv == cut
    return ww[ab].sum() + (k - ab.sum()) / tie.sum() * ww[tie].sum()


rows = []
for _ in range(2000):
    ix = np.concatenate([rng.choice(s, len(s)) for s in strata]); hh, ww, vv = h[ix], w[ix], v[ix]
    k = int(hh.sum()); cf = ww[hh].sum(); cw = wo_caught(vv, ww, k); n = len(ix); nw = ww.sum()
    rows.append([cf - cw, 100 * (1 - (nw - cf) / (n - k)), 100 * (1 - nw / n), 100 * (1 - (nw - cw) / (n - k))])
R = np.array(rows); ci = lambda x: [round(float(a), 1) for a in np.percentile(x, [2.5, 97.5])]
res["boot"] = {"diff_caught_fw_minus_wo": ci(R[:, 0]), "p_fw_ge_wo": round(float((R[:, 0] >= 0).mean()), 2), "acc_fw": ci(R[:, 1]),
               "acc_nocheck": ci(R[:, 2]), "acc_wo": ci(R[:, 3]), "gain_fw_vs_nocheck": ci(R[:, 1] - R[:, 2])}

ha = [i for i in B["hard"] if agree[i]]
byd = lambda s: {d: sum(W[i] for i in s if pred[i] == d) for d in DOM}
res["missed"] = {"total": sum(W[i] for i in B["easy"] + ha), "easy": byd(B["easy"]), "hard_agree": byd(ha)}
ew = [i for i in B["easy"] if W[i]]
res["easy_wrong_examples"] = [[i, round(nl[i], 2), qs[i]["question_text"], cor[i]["per_sample"][0]["extracted"], qs[i]["ground_truth_answer"]] for i in ew if pred[i] == "factual"][:8]
res["easy_wrong_agree"] = [sum(agree[i] for i in ew), len(ew)]
two = [i for i in B["easy"] if ans[i][0] != ans[i][1] or ans[i][0] is None]
res["two_answer_easy"] = {"easy": len(B["easy"]), "flagged": len(two), "wrong_caught": sum(W[i] for i in two), "easy_wrong": len(ew), "extra_calls": len(B["easy"])}
res["ood"] = [[i, qs[i]["category"], pred[i], round(sc[i], 3), round(B["thr"][pred[i]], 3), bool(1 - W[i]), qs[i]["question_text"]] for i in B["ood"]]
json.dump(res, open(OUT / "docs_extras.json", "w"), indent=1)

X_ = json.load(open(OUT / "report_extras.json"))
X_["agree_by_domain"] = {d: (lambda hd: {"hard": len(hd), "agree": sum(agree[i] for i in hd), "acc_agree": acc([i for i in hd if agree[i]]),
                                         "disagree": sum(not agree[i] for i in hd), "acc_disagree": acc([i for i in hd if not agree[i]])})([i for i in B["hard"] if pred[i] == d]) for d in DOM}
X_["banking"]["note"] = "computed with the earlier single threshold 0.288"
json.dump(X_, open(OUT / "report_extras.json", "w"), indent=1)
print(json.dumps({k: res[k] for k in res if k != "easy_wrong_examples"}))
print(X_["agree_by_domain"])
