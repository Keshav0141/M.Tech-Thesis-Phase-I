"""Consistency check of every number shown in the deck (run after deck_data.py, before building the deck).

Every value in the deck comes from track2/outputs/deck_data.json. This script recomputes the key counts
from the raw files and checks that every table adds up: rows, columns, TP/FP/FN/TN and the accuracies.
It exits with an error if any check fails, so a deck with inconsistent numbers is never built.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "track2/outputs"
D = json.load(open(OUT / "deck_data.json"))
DOM = ["factual", "math", "reasoning"]
N = 450
fails, n_ok = [], 0


def check(name, cond, detail=""):
    global n_ok
    if cond:
        n_ok += 1
    else:
        fails.append(f"{name}: {detail}")


def close(a, b, tol=0.051):
    return abs(a - b) <= tol


# ---- labels, recomputed from the raw file -------------------------------------------------------
pc = [json.loads(l) for l in open(OUT / "pct_correct.jsonl")]
pc = [r for r in pc if r["split"] == "main"]
nw = sum(1 - r["sample1_correct"] for r in pc)
check("450 test questions", len(pc) == N, len(pc))
check("wrong first answers (raw file vs deck)", nw == D["n_wrong"], f"{nw} vs {D['n_wrong']}")
NW, NC = D["n_wrong"], N - D["n_wrong"]
check("no-check accuracy = correct / 450", close(D["base_acc"], round(100 * NC / N, 1)), D["base_acc"])
for dm in DOM:
    check(f"150 {dm} questions", sum(r["question_id"].startswith(dm) for r in pc) == 150)


# ---- four outcomes for every row of every comparison table --------------------------------------
def outcomes(name, r, k=None):
    TP, FP, FN = r["caught"], r["flagged"] - r["caught"], r["missed"]
    TN = N - r["flagged"] - FN
    check(f"{name}: held back + accepted = 450", r["flagged"] + r["accepted"] == N, r)
    check(f"{name}: TP + FP = held back", TP + FP == r["flagged"])
    check(f"{name}: FP as stored", FP == r["false"], f"{FP} vs {r['false']}")
    check(f"{name}: TP + FN = all wrong ({NW})", close(TP + FN, NW, 1e-6), TP + FN)
    check(f"{name}: FP + TN = all correct ({NC})", close(FP + TN, NC, 1e-6), FP + TN)
    check(f"{name}: TP+FP+FN+TN = 450", close(TP + FP + FN + TN, N, 1e-6))
    check(f"{name}: no negative cell", min(TP, FP, FN, TN) >= 0)
    check(f"{name}: accuracy = TN/(TN+FN)", close(r["acc"], round(100 * TN / (TN + FN), 1)), f"{r['acc']} vs {100 * TN / (TN + FN):.2f}")
    if k is not None:
        check(f"{name}: held back = {k}", r["flagged"] == k)
    return TP, FP, FN, TN


U = D["cum"]
for key in ["nocheck", "wo", "se", "ns", "kev", "s1", "s2", "s3", "s4"]:
    outcomes(f"cum.{key}", U[key])
for m in ["wo", "se", "ns", "kev"]:
    check(f"Phase 1 {m}: holds back {NW}", U[m]["flagged"] == NW)
for k, rows in D["cum_at"].items():
    for m, r in rows.items():
        outcomes(f"at {k} held back: {m}", r, int(k))
for s, k in [("s2", U["s2"]["flagged"]), ("s4", U["s4"]["flagged"])]:
    A = D["cum_at"][str(k)]
    for m, ref in [("wo", "ref_wo"), ("se", "ref_se"), ("ns", "ref_ns")]:
        check(f"{s}: {m} TP in growing table = same-number comparison", close(U[s][ref], A[m]["caught"], 1e-6), f"{U[s][ref]} vs {A[m]['caught']}")
check("Step 3 changes nothing (same row as Step 2)", all(U["s3"][x] == U["s2"][x] for x in ["flagged", "caught", "missed", "calls"]))

# ---- Step 1 --------------------------------------------------------------------------------------
S1 = D["step1"]; cm = S1["routing_confusion"]
for t in DOM:
    check(f"Step 1 routing row {t} sums to 150", sum(cm[t].values()) == 150)
check("Step 1 routing table sums to 450", sum(sum(r.values()) for r in cm.values()) == N)
diag = sum(cm[t][t] for t in DOM)
check("Step 1 routing accuracy = diagonal / 450", close(S1["routing_accuracy"], round(100 * diag / N, 1)))
OD = {t: {a: 0 for a in DOM} for t in DOM}
for x in S1["examples_out"]:
    OD[x["true"]][x["pred"]] += 1
    check(f"out of domain {x['q'][:30]}: score below threshold", x["score"] < x["thr"])
    check(f"out of domain {x['q'][:30]}: threshold of assigned domain", close(x["thr"], S1["thresholds"][x["pred"]], 0.0006))
check("out-of-domain list has all removed questions", len(S1["examples_out"]) == S1["removed"])
check("kept + removed = 450", S1["kept"] + S1["removed"] == N)
check("removed by domain sums to removed", sum(S1["removed_by_domain"].values()) == S1["removed"])
for a in DOM:
    check(f"removed assigned to {a}", sum(OD[t][a] for t in DOM) == S1["removed_by_domain"][a])
check("removed_wrong = TP after Step 1", S1["removed_wrong"] == U["s1"]["caught"])
check("Step 1 held back = removed", U["s1"]["flagged"] == S1["removed"])
inT = {t: {a: cm[t][a] - OD[t][a] for a in DOM} for t in DOM}
for t in DOM:
    check(f"slide 8 table row {t}: in-domain cells + out of domain = 150", sum(inT[t].values()) + sum(OD[t].values()) == 150)
check("slide 8 out-of-domain column sums to removed", sum(sum(OD[t].values()) for t in DOM) == S1["removed"])
inN = N - S1["removed"]; inOk = sum(inT[t][t] for t in DOM)
check("slide 8 in-domain table sums to kept", sum(sum(r.values()) for r in inT.values()) == inN)

# ---- Step 2 --------------------------------------------------------------------------------------
S2 = D["step2"]; B = S2["by_domain"]
for a in DOM:
    assigned_in = sum(inT[t][a] for t in DOM)
    check(f"Step 2 {a}: easy + hard = in-domain questions assigned to {a}", B[a]["easy"] + B[a]["hard"] == assigned_in, f"{B[a]['easy'] + B[a]['hard']} vs {assigned_in}")
check("Step 2 easy total = sum over domains", S2["easy"] == sum(B[a]["easy"] for a in DOM))
check("Step 2 hard total = sum over domains", S2["hard"] == sum(B[a]["hard"] for a in DOM))
check("easy + hard = kept", S2["easy"] + S2["hard"] == S1["kept"])
for g in ["easy", "hard"]:
    wavg = sum(B[a][g] * B[a]["acc_" + g] for a in DOM) / S2[g]
    check(f"Step 2 {g} accuracy = weighted domain accuracies", close(wavg, S2["acc_" + g], 0.15), f"{wavg:.2f} vs {S2['acc_' + g]}")
check("Step 2 held back = removed + hard", U["s2"]["flagged"] == S1["removed"] + S2["hard"])
check("Step 2 accepted = easy", U["s2"]["accepted"] == S2["easy"])
check("Step 2 accepted accuracy = easy accuracy", close(U["s2"]["acc"], S2["acc_easy"]))
check("Step 2 model calls = kept (one answer each)", U["s2"]["calls"] == S1["kept"])
wrong_easy = U["s2"]["missed"]; wrong_hard = U["s2"]["caught"] - S1["removed_wrong"]
check("Step 2 wrong easy = easy x (1 - accuracy)", close(wrong_easy, S2["easy"] * (1 - S2["acc_easy"] / 100), 0.5))
check("Step 2 wrong hard = hard x (1 - accuracy)", close(wrong_hard, S2["hard"] * (1 - S2["acc_hard"] / 100), 0.5))

# ---- Steps 3 to 5 ------------------------------------------------------------------------------
S3, S4, S5 = D["step3"], D["step4"], D["step5"]
check("Step 3 hard math = Step 2 math hard", S3["hard_math"] == B["math"]["hard"])
check("Step 3 checkable <= hard math", S3["checkable"] <= S3["hard_math"])
check("Step 4 agree + disagree = hard", S4["agree"] + S4["disagree"] == S2["hard"])
wa = round(S4["agree"] * (1 - S4["acc_agree"] / 100)); wd = round(S4["disagree"] * (1 - S4["acc_disagree"] / 100))
check("Step 4 wrong agree + wrong disagree = wrong hard", wa + wd == wrong_hard, f"{wa}+{wd} vs {wrong_hard}")
c = S5["cells"]
check("Step 5 easy cell", c["easy"] == [S2["easy"], S2["acc_easy"]])
check("Step 5 agree cell", c["hard_agree"] == [S4["agree"], S4["acc_agree"]])
check("Step 5 disagree cell", c["hard_disagree"] == [S4["disagree"], S4["acc_disagree"]])
check("Step 5 accepted = easy + agree", S5["accepted"] == S2["easy"] + S4["agree"])
check("Step 5 withheld = disagree", S5["flagged"] == S4["disagree"])
check("accepted + withheld + out of domain = 450", S5["accepted"] + S5["flagged"] + S1["removed"] == N)
acc5 = 100 * (S2["easy"] * S2["acc_easy"] + S4["agree"] * S4["acc_agree"]) / 100 / S5["accepted"]
check("Step 5 accepted accuracy = weighted", close(acc5, S5["acc_accepted"], 0.15), f"{acc5:.2f}")
check("final held back = withheld + out of domain", U["s4"]["flagged"] == S5["flagged"] + S1["removed"])
check("final TP = out-of-domain wrong + disagree wrong", U["s4"]["caught"] == S1["removed_wrong"] + wd)
check("final FN = wrong easy + wrong agree", U["s4"]["missed"] == wrong_easy + wa)
check("final model calls = easy x 1 + hard x 5", U["s4"]["calls"] == S2["easy"] + 5 * S2["hard"])
check("5-answer methods: 450 x 5 calls", U["wo"]["calls"] == 5 * N)
check("final accepted accuracy = Step 5", close(U["s4"]["acc"], S5["acc_accepted"]))

# ---- AUROC values ---------------------------------------------------------------------------------
for m, v in D["auroc"].items():
    check(f"AUROC {m} within 0 and 1", all(0 <= x <= 1 for x in v.values()))

# ---- independent recomputation from the raw score files (word overlap, verifier) ----------------
import numpy as np
L = lambda f: {json.loads(l)["question_id"]: json.loads(l) for l in open(f)}
lab = {r["question_id"]: 1 - r["sample1_correct"] for r in pc}
ids = sorted(lab)
raw = {"Word overlap (TF-IDF)": {i: v["tfidf_uncertainty"] for i, v in L(ROOT / "results/ngram_tfidf.jsonl").items()},
       "Kev": {i: 1 - v["p_yes"] for i, v in L(ROOT / "track2/kev/kev_scores.jsonl").items()}}
key = {"Word overlap (TF-IDF)": "wo", "Kev": "kev"}


def auroc(sc, y):
    w = [s for s, t in zip(sc, y) if t]; c = [s for s, t in zip(sc, y) if not t]
    return sum((a > b) + 0.5 * (a == b) for a in w for b in c) / (len(w) * len(c))


def tp_at(sc, y, k):
    sc, y = np.round(np.array(sc), 9), np.array(y); cut = np.sort(sc)[::-1][k - 1]; ab, tie = sc > cut, sc == cut
    return y[ab].sum() + (k - ab.sum()) / tie.sum() * y[tie].sum()


for m, sc in raw.items():
    for dm in DOM + ["all"]:
        q = [i for i in ids if dm == "all" or i.startswith(dm)]
        a = auroc([sc[i] for i in q], [lab[i] for i in q])
        check(f"AUROC {m} {dm} recomputed from raw scores", close(a, D["auroc"][m][dm], 0.006), f"{a:.3f} vs {D['auroc'][m][dm]}")
    for k, r in [(NW, U[key[m]])] + [(int(k), D["cum_at"][k][key[m]]) for k in D["cum_at"]]:
        t = tp_at([sc[i] for i in ids], [lab[i] for i in ids], k)
        check(f"{m} TP at {k} held back recomputed from raw scores", close(t, r["caught"], 0.51), f"{t:.2f} vs {r['caught']}")

# ---- Step 3 counts over all math answers ----------------------------------------------------------
_ar = [json.loads(l) for l in open(OUT / "arith_verify.jsonl")]
check("Step 3: 1,500 math answers = 300 questions x 5", D["arith_all"]["answers"] == len(_ar) == 1500)
check("Step 3: steps recounted", D["arith_all"]["steps"] == sum(r["n_steps_checked"] for r in _ar))
check("Step 3: wrong steps recounted", D["arith_all"]["wrong"] == sum(r["n_steps_wrong"] for r in _ar))
check("Step 3: hard-question steps <= all steps", D["step3"]["steps"] <= D["arith_all"]["steps"])

# ---- AUROC as pair counts (AUROC slides) ------------------------------------------------------------
for m, v in D["auroc_pairs"].items():
    for dm, x in v.items():
        check(f"AUROC pairs {m} {dm}: pairs = wrong x correct", x["pairs"] == x["wrong"] * x["correct"])
        check(f"AUROC pairs {m} {dm}: higher + tied <= pairs", x["higher"] + x["ties"] <= x["pairs"])
        check(f"AUROC pairs {m} {dm}: (higher + tied/2) / pairs = AUROC table", close((x["higher"] + 0.5 * x["ties"]) / x["pairs"], D["auroc"][m][dm], 0.0006))
    check(f"AUROC pairs {m}: wrong over domains = {NW}", sum(v[dm]["wrong"] for dm in DOM) == v["all"]["wrong"] == NW)
    check(f"AUROC pairs {m}: correct over domains = {NC}", sum(v[dm]["correct"] for dm in DOM) == v["all"]["correct"] == NC)
EX = D["auroc_example"]
for e in EX:
    check(f"AUROC example {e['id']}: label from raw file", e["wrong"] == bool(lab[e["id"]]))
    check(f"AUROC example {e['id']}: NumSets from raw file", e["numsets"] == json.loads([l for l in open(ROOT / "results/graph_methods.jsonl") if e["id"] in l][0])["num_sets"])
    check(f"AUROC example {e['id']}: group sizes sum to 5 and match NumSets", sum(e["group_sizes"]) == 5 and len(e["group_sizes"]) == e["numsets"])
    check(f"AUROC example {e['id']}: score from raw file", close(e["score"], abs(raw["Word overlap (TF-IDF)"][e["id"]]), 0.006))

# ---- pair-count example (how 29,292 etc. are obtained) ----------------------------------------------
for m, v in D["pair_count_example"].items():
    check(f"pair count {m}: sum over wrong answers = table value", v["sum_higher"] == D["auroc_pairs"][m]["all"]["higher"] and v["sum_ties"] == D["auroc_pairs"][m]["all"]["ties"])
    for e, p in v["examples"].items():
        check(f"pair count {m} {e}: higher + ties + lower = 347", p["higher"] + p["ties"] + p["lower"] == NC)
        check(f"pair count {m} {e}: listed higher-scoring correct answers", len(p["above"]) == min(3, p["lower"]) and all(lab[x[0]] == 0 for x in p["above"]))

# next-step column of the 450-to-66 slide
check("next-step column: 450 - removed = kept", N - S1["removed"] == S1["kept"])
check("next-step column: kept - easy = hard", S1["kept"] - S2["easy"] == S2["hard"])
check("next-step column: hard - agree = disagree", S2["hard"] - S4["agree"] == S4["disagree"])

print(f"{n_ok} checks passed, {len(fails)} failed")
for f in fails:
    print("FAIL", f)
sys.exit(1 if fails else 0)
