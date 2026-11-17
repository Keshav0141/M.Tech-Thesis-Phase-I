"""Collect every number used in the v6 deck into track2/outputs/deck_data.json (run after funnel2.py)."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "track2/outputs"
f = json.load(open(OUT / "funnel2.json"))
p1 = json.load(open(OUT / "phase1_confusion.json"))
DOM = ["factual", "math", "reasoning"]
ren = {"Word overlap (TF-IDF), 5 answers": "Word overlap (TF-IDF)", "Semantic Entropy, 5 answers": "Semantic Entropy",
       "NumSets (Lin et al.), 5 answers": "NumSets", "Kev verifier, 1 answer": "Kev"}
d = {"auroc": {ren[k]: v for k, v in f["auroc_all"].items()}, "phase1_cm": p1,
     "base_acc": round(100 * (1 - f["n_wrong"] / f["n"]), 1), "n_wrong": f["n_wrong"],
     "bank_total": sum(f["step1"]["bank_size"].values()), "bank_per": f["step1"]["bank_size"]["factual"]}
for k in ["step1", "step2", "step3", "step4", "step5", "compare_step2", "compare_final"]:
    d[k] = f[k]

# Step 1 worked example: domain scores and nearest bank question for one test question
bz = np.load(OUT / "bank_emb.npz", allow_pickle=True)
BE, BD = bz["emb"], bz["domain"]
bq = [json.loads(l)["question_text"] for l in open(OUT / "bank_questions.jsonl")]
tz = np.load(OUT / "question_emb.npz", allow_pickle=True)
te = dict(zip(tz["ids"], tz["emb"]))
qs = {q["question_id"]: q for q in json.load(open(ROOT / "data/dataset.json"))}
ex = {}
for qid in ["factual_0110", "math_0009", "reasoning_0061"]:
    v = te[qid]; row = {"q": qs[qid]["question_text"], "true": qs[qid]["category"], "scores": {}, "nearest": {}}
    for dm in DOM:
        idx = np.where(BD == dm)[0]; s = BE[idx] @ v; o = np.argsort(-s)[:5]
        row["scores"][dm] = round(float(s[o].mean()), 2)
        row["nearest"][dm] = [bq[idx[o[0]]], round(float(s[o[0]]), 2)]
    ex[qid] = row
d["s1_examples"] = ex
# Step 2 examples: questions whose assigned and true domain match, near the 25th (easy) / 75th (hard) percentile
nll = {r.split(",")[0]: r for r in []}
import pandas as pd
nl = pd.read_csv(OUT / "question_nll.csv"); nl = nl[nl.ref_model == "Qwen/Qwen2.5-1.5B"].set_index("question_id").mean_nll
pc = {json.loads(l)["question_id"]: json.loads(l) for l in open(OUT / "pct_correct.jsonl")}
pick = {"factual": ("factual_0133", "factual_0048"), "math": ("math_0102", "math_0124"), "reasoning": ("reasoning_0071", "reasoning_0074")}
d["step2"]["examples"] = {dm: {k: [qs[i]["question_text"], round(float(nl[i]), 2), bool(pc[i]["sample1_correct"])] for k, i in zip(["easy", "hard"], ids)} for dm, ids in pick.items()}
json.dump(d, open(OUT / "deck_data.json", "w"), indent=1)
print("wrote deck_data.json")

# cumulative comparison table (run track2/cumulative.py first)
_c = json.load(open(OUT / "cumulative.json")); d["cum"], d["cum_at"] = _c["rows"], _c["at"]
json.dump(d, open(OUT / "deck_data.json", "w"), indent=1)

# arithmetic check over all math answers (Step 3 slide)
_ar = [json.loads(l) for l in open(OUT / "arith_verify.jsonl")]
d["arith_all"] = {"answers": len(_ar), "steps": sum(r["n_steps_checked"] for r in _ar), "wrong": sum(r["n_steps_wrong"] for r in _ar)}
json.dump(d, open(OUT / "deck_data.json", "w"), indent=1)

# AUROC as pair counts (slides on AUROC): every (wrong, correct) pair, wrong scored higher / tied
_L = lambda f: {json.loads(l)["question_id"]: json.loads(l) for l in open(f)}
_tf, _se, _gm = _L(ROOT / "results/ngram_tfidf.jsonl"), _L(ROOT / "results/semantic_entropy.jsonl"), _L(ROOT / "results/graph_methods.jsonl")
_kev = _L(ROOT / "track2/kev/kev_scores.jsonl")
_ids = sorted(k for k, v in pc.items() if v["split"] == "main")
_W = {i: 1 - pc[i]["sample1_correct"] for i in _ids}
_SC = {"Word overlap (TF-IDF)": {i: _tf[i]["tfidf_uncertainty"] for i in _ids}, "Semantic Entropy": {i: _se[i]["semantic_entropy"] for i in _ids},
       "NumSets": {i: _gm[i]["num_sets"] for i in _ids}, "Kev": {i: 1 - _kev[i]["p_yes"] for i in _ids}}
d["auroc_pairs"] = {}
for m, sc in _SC.items():
    d["auroc_pairs"][m] = {}
    for dm in DOM + ["all"]:
        q = [i for i in _ids if dm == "all" or qs[i]["category"] == dm]
        w = [round(sc[i], 9) for i in q if _W[i]]; c = [round(sc[i], 9) for i in q if not _W[i]]
        hi = sum(a > b for a in w for b in c); ti = sum(a == b for a in w for b in c)
        d["auroc_pairs"][m][dm] = {"wrong": len(w), "correct": len(c), "pairs": len(w) * len(c), "higher": hi, "ties": ti,
                                   "auroc": round((hi + 0.5 * ti) / (len(w) * len(c)), 3)}
# real worked example: 3 wrong and 3 correct test questions with their word-overlap scores
_ex = ["factual_0097", "factual_0010", "factual_0044", "factual_0110", "factual_0133", "factual_0068"]
_cor = _L(ROOT / "results/correctness.jsonl")
d["auroc_example"] = [{"id": i, "q": qs[i]["question_text"], "score": round(abs(_SC["Word overlap (TF-IDF)"][i]), 2), "wrong": bool(_W[i]),
                       "answers": [p["extracted"] for p in _cor[i]["per_sample"]], "truth": qs[i]["ground_truth_answer"], "numsets": int(_SC["NumSets"][i]), "group_sizes": _se[i]["cluster_sizes"]} for i in _ex]
json.dump(d, open(OUT / "deck_data.json", "w"), indent=1)

# how a pair count is obtained: per wrong answer, count the correct answers it beats / ties (word overlap and NumSets)
d["pair_count_example"] = {}
for m in ["Word overlap (TF-IDF)", "NumSets"]:
    sc = _SC[m]; cw = [round(sc[i], 9) for i in _ids if not _W[i]]; ww = sorted([i for i in _ids if _W[i]], key=lambda i: -sc[i])
    per = [{"id": i, "score": round(sc[i], 2), "higher": sum(round(sc[i], 9) > c for c in cw), "ties": sum(round(sc[i], 9) == c for c in cw), "lower": sum(round(sc[i], 9) < c for c in cw), "above": [[j, round(sc[j], 2), qs[j]["question_text"], len({str(p["extracted"]).lower() for p in _cor[j]["per_sample"]})] for j in sorted([j for j in _ids if not _W[j] and round(sc[j], 9) > round(sc[i], 9)], key=lambda j: -sc[j])][:3]} for i in ww]
    d["pair_count_example"][m] = {"n_wrong": len(ww), "n_correct": len(cw), "sum_higher": sum(p["higher"] for p in per), "sum_ties": sum(p["ties"] for p in per),
                                  "examples": {e: next(p for p in per if p["id"] == e) for e in _ex if _W[e]}}
json.dump(d, open(OUT / "deck_data.json", "w"), indent=1)
