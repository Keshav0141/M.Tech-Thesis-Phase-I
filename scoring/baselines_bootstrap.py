"""Random-escalation baseline and bootstrap confidence intervals.

Read-only on all existing results; no API calls. Seed 42 everywhere.

Part 1  Random escalation baseline: draw the same number of questions per
        category as the final gate (results/tier2_escalated_questions.json),
        10,000 times, and compare precision/recall with the gate.
Part 2  Bootstrap 95% CIs (2,000 resamples, questions resampled with
        replacement within each category):
          (a) gate precision / recall (escalated set kept fixed)
          (b) TF-IDF AUROC overall and per category
          (c) CV selector vs TF-IDF macro-AUROC, using the SAME folds and
              fold winners as scoring/selector_cv.py. Each held-out fold is
              resampled on its own and fold AUROCs are averaged, exactly as
              the reported 0.804 / 0.759 are computed (avoids pooling scores
              from different methods on different scales).

Outputs:
    results/baselines_report.md
    results/baselines_bootstrap.json

Usage:
    python scoring/baselines_bootstrap.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uq_common as uq
from selector_cv import METHOD_SOURCES, METHOD_ORDER, CV_FOLDS, CV_SEED, load_jsonl

SEED = 42
N_RANDOM = 10_000
N_BOOT = 2_000
CATEGORIES = ["factual", "math", "reasoning"]


def auc(labels, scores):
    value, _, _ = uq.roc_auc(list(labels), list(scores))
    return value


def pct(values, lo=2.5, hi=97.5):
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    return float(np.percentile(arr, lo)), float(np.percentile(arr, hi)), int(arr.size)


def main() -> int:
    uq.enable_utf8_stdout()
    rng = np.random.default_rng(SEED)

    correctness = load_jsonl(uq.RESULTS_DIR / "correctness.jsonl")
    sources = {
        "ngram_tfidf": load_jsonl(uq.RESULTS_DIR / "ngram_tfidf.jsonl"),
        "lexical": load_jsonl(uq.RESULTS_DIR / "lexical.jsonl"),
        "semantic": load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl"),
        "graph": load_jsonl(uq.RESULTS_DIR / "graph_methods.jsonl"),
    }
    gate = json.loads((uq.RESULTS_DIR / "tier2_escalated_questions.json").read_text(encoding="utf-8"))
    escalated = {q["question_id"] for q in gate["questions"]}

    # Same row construction and order as selector_cv.py
    rows_by_category: dict[str, list[dict]] = defaultdict(list)
    for question_id, label_row in correctness.items():
        label = label_row.get("overall_correct")
        if label is None:
            continue
        row = {"question_id": question_id, "category": label_row["category"], "error": 1 - int(label)}
        complete = True
        for method, (source, field) in METHOD_SOURCES.items():
            value = sources[source].get(question_id, {}).get(field)
            if value is None:
                complete = False
                break
            row[method] = float(value)
        if complete:
            row["escalated"] = int(question_id in escalated)
            rows_by_category[label_row["category"]].append(row)

    all_rows = [r for c in CATEGORIES for r in rows_by_category[c]]
    total_wrong = sum(r["error"] for r in all_rows)
    out: dict = {"seed": SEED, "n_random": N_RANDOM, "n_boot": N_BOOT,
                 "n_questions": len(all_rows), "n_wrong": total_wrong}

    # ---------------- Part 1: random escalation baseline ----------------
    gate_stats = {}
    for c in CATEGORIES:
        g = rows_by_category[c]
        k = sum(r["escalated"] for r in g)
        hit = sum(r["escalated"] * r["error"] for r in g)
        wrong = sum(r["error"] for r in g)
        gate_stats[c] = {"escalated": k, "wrong_caught": hit, "wrong_total": wrong,
                         "precision": hit / k if k else None, "recall": hit / wrong if wrong else None}
    k_all = sum(s["escalated"] for s in gate_stats.values())
    hit_all = sum(s["wrong_caught"] for s in gate_stats.values())
    gate_stats["all"] = {"escalated": k_all, "wrong_caught": hit_all, "wrong_total": total_wrong,
                         "precision": hit_all / k_all, "recall": hit_all / total_wrong}

    errors = {c: np.array([r["error"] for r in rows_by_category[c]]) for c in CATEGORIES}
    rand_hits = {c: np.empty(N_RANDOM) for c in CATEGORIES}
    for i in range(N_RANDOM):
        for c in CATEGORIES:
            k = gate_stats[c]["escalated"]
            idx = rng.choice(len(errors[c]), size=k, replace=False)
            rand_hits[c][i] = errors[c][idx].sum()
    random_stats = {}
    for c in CATEGORIES:
        k = gate_stats[c]["escalated"]
        prec = rand_hits[c] / k
        rec = rand_hits[c] / max(1, gate_stats[c]["wrong_total"])
        random_stats[c] = {
            "precision_mean": float(prec.mean()), "precision_ci": [float(np.percentile(prec, 2.5)), float(np.percentile(prec, 97.5))],
            "recall_mean": float(rec.mean()), "recall_ci": [float(np.percentile(rec, 2.5)), float(np.percentile(rec, 97.5))],
            "p_value_precision": float((prec >= gate_stats[c]["precision"] - 1e-12).mean()),
        }
    hits_all = sum(rand_hits[c] for c in CATEGORIES)
    prec_all = hits_all / k_all
    rec_all = hits_all / total_wrong
    random_stats["all"] = {
        "precision_mean": float(prec_all.mean()), "precision_ci": [float(np.percentile(prec_all, 2.5)), float(np.percentile(prec_all, 97.5))],
        "recall_mean": float(rec_all.mean()), "recall_ci": [float(np.percentile(rec_all, 2.5)), float(np.percentile(rec_all, 97.5))],
        "p_value_precision": float((prec_all >= gate_stats["all"]["precision"] - 1e-12).mean()),
    }
    out["part1_random_baseline"] = {"gate": gate_stats, "random": random_stats}

    # ---------------- Part 2a/2b: stratified bootstrap of questions ----------------
    cat_arrays = {
        c: {
            "error": np.array([r["error"] for r in rows_by_category[c]]),
            "esc": np.array([r["escalated"] for r in rows_by_category[c]]),
            "tfidf": np.array([r["tfidf"] for r in rows_by_category[c]]),
        }
        for c in CATEGORIES
    }
    boot_prec, boot_rec = [], []
    boot_auc = {c: [] for c in CATEGORIES + ["all"]}
    for _ in range(N_BOOT):
        e_all, s_all = [], []
        hits = esc_n = wrong_n = 0
        for c in CATEGORIES:
            a = cat_arrays[c]
            idx = rng.integers(0, len(a["error"]), size=len(a["error"]))
            e, esc, s = a["error"][idx], a["esc"][idx], a["tfidf"][idx]
            hits += int((e * esc).sum()); esc_n += int(esc.sum()); wrong_n += int(e.sum())
            boot_auc[c].append(auc(e, s))
            e_all.append(e); s_all.append(s)
        boot_prec.append(hits / esc_n if esc_n else None)
        boot_rec.append(hits / wrong_n if wrong_n else None)
        boot_auc["all"].append(auc(np.concatenate(e_all), np.concatenate(s_all)))

    gate_ci = {
        "precision": gate_stats["all"]["precision"], "precision_ci": list(pct(boot_prec)[:2]),
        "recall": gate_stats["all"]["recall"], "recall_ci": list(pct(boot_rec)[:2]),
    }
    point_auc = {c: auc(cat_arrays[c]["error"], cat_arrays[c]["tfidf"]) for c in CATEGORIES}
    point_auc["all"] = auc(np.concatenate([cat_arrays[c]["error"] for c in CATEGORIES]),
                           np.concatenate([cat_arrays[c]["tfidf"] for c in CATEGORIES]))
    auc_ci = {}
    for c in CATEGORIES + ["all"]:
        lo, hi, n_ok = pct(boot_auc[c])
        auc_ci[c] = {"auroc": point_auc[c], "ci": [lo, hi], "valid_resamples": n_ok}
    out["part2a_gate_ci"] = gate_ci
    out["part2b_tfidf_auroc_ci"] = auc_ci

    # ---------------- Part 2c: selector vs TF-IDF (same folds as selector_cv.py) ----------------
    from sklearn.model_selection import StratifiedKFold

    folds_by_cat = {}
    for c in CATEGORIES:
        group = rows_by_category[c]
        labels = [r["error"] for r in group]
        skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=CV_SEED)
        folds = []
        for train_idx, test_idx in skf.split(group, labels):
            train_rows = [group[i] for i in train_idx]
            test_rows = [group[i] for i in test_idx]
            train_labels = [r["error"] for r in train_rows]
            train_aucs = {m: auc(train_labels, [r[m] for r in train_rows]) for m in METHOD_ORDER}
            winner = METHOD_ORDER[0]
            for m in METHOD_ORDER[1:]:
                if train_aucs[m] is not None and (train_aucs[winner] is None or train_aucs[m] > train_aucs[winner]):
                    winner = m
            folds.append({
                "winner": winner,
                "error": np.array([r["error"] for r in test_rows]),
                "sel": np.array([r[winner] for r in test_rows]),
                "tfidf": np.array([r["tfidf"] for r in test_rows]),
            })
        folds_by_cat[c] = folds

    def fold_avg(folds, key, idx_list=None):
        vals = []
        for f_i, f in enumerate(folds):
            if idx_list is None:
                e, s = f["error"], f[key]
            else:
                e, s = f["error"][idx_list[f_i]], f[key][idx_list[f_i]]
            v = auc(e, s)
            if v is not None:
                vals.append(v)
        return sum(vals) / len(vals) if vals else None

    point_sel = {c: fold_avg(folds_by_cat[c], "sel") for c in CATEGORIES}
    point_tf = {c: fold_avg(folds_by_cat[c], "tfidf") for c in CATEGORIES}
    point_macro_sel = sum(point_sel.values()) / 3
    point_macro_tf = sum(point_tf.values()) / 3

    diffs, macro_sel_b, macro_tf_b = [], [], []
    for _ in range(N_BOOT):
        sel_c, tf_c = [], []
        for c in CATEGORIES:
            idx_list = [rng.integers(0, len(f["error"]), size=len(f["error"])) for f in folds_by_cat[c]]
            sel_c.append(fold_avg(folds_by_cat[c], "sel", idx_list))
            tf_c.append(fold_avg(folds_by_cat[c], "tfidf", idx_list))
        if None in sel_c or None in tf_c:
            continue
        ms, mt = sum(sel_c) / 3, sum(tf_c) / 3
        macro_sel_b.append(ms); macro_tf_b.append(mt); diffs.append(ms - mt)
    diffs_arr = np.array(diffs)
    out["part2c_selector_vs_tfidf"] = {
        "fold_winners": {c: [f["winner"] for f in folds_by_cat[c]] for c in CATEGORIES},
        "selector_per_category": point_sel, "tfidf_per_category": point_tf,
        "selector_macro": point_macro_sel, "tfidf_macro": point_macro_tf,
        "difference": point_macro_sel - point_macro_tf,
        "difference_ci": [float(np.percentile(diffs_arr, 2.5)), float(np.percentile(diffs_arr, 97.5))],
        "selector_macro_ci": list(pct(macro_sel_b)[:2]), "tfidf_macro_ci": list(pct(macro_tf_b)[:2]),
        "fraction_difference_le_0": float((diffs_arr <= 0).mean()),
        "valid_resamples": int(diffs_arr.size),
    }

    (uq.RESULTS_DIR / "baselines_bootstrap.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # ---------------- Report ----------------
    f3 = lambda x: f"{x:.3f}"
    L = ["# Random-escalation baseline and bootstrap confidence intervals", "",
         f"_Generated by scoring/baselines_bootstrap.py. Seed {SEED}. {len(all_rows)} labeled questions, {total_wrong} wrong (base error rate {total_wrong/len(all_rows):.3f})._", "",
         "## Part 1 — Gate vs random escalation", "",
         f"Random baseline: the same number of questions per category as the final gate, picked at random, {N_RANDOM:,} times.", "",
         "| Category | Escalated | Gate precision | Random precision (mean, 95% range) | p (random ≥ gate) | Gate recall | Random recall (mean, 95% range) |",
         "|---|---:|---:|---|---:|---:|---|"]
    for c in CATEGORIES + ["all"]:
        g, r = gate_stats[c], random_stats[c]
        L.append(f"| {c} | {g['escalated']} | {f3(g['precision'])} ({g['wrong_caught']}/{g['escalated']}) | {f3(r['precision_mean'])} ({f3(r['precision_ci'][0])}–{f3(r['precision_ci'][1])}) | {r['p_value_precision']:.4f} | {f3(g['recall'])} | {f3(r['recall_mean'])} ({f3(r['recall_ci'][0])}–{f3(r['recall_ci'][1])}) |")
    ra = random_stats["all"]; ga = gate_stats["all"]
    pv_text = "none" if ra["p_value_precision"] == 0 else "a share of {:.4f}".format(ra["p_value_precision"])
    L += ["", f"**Verdict:** the gate's precision ({f3(ga['precision'])}) is far above random ({f3(ra['precision_mean'])}, 95% range {f3(ra['precision_ci'][0])}–{f3(ra['precision_ci'][1])}); "
          f"{pv_text} of the {N_RANDOM:,} random draws matched it. "
          "Per category: " + "; ".join(
              "{}: p = {:.3f} ({})".format(c, random_stats[c]["p_value_precision"],
                                          "clearly better than random" if random_stats[c]["p_value_precision"] < 0.01
                                          else "better than random at the 5% level" if random_stats[c]["p_value_precision"] < 0.05
                                          else "NOT clearly better than random")
              for c in CATEGORIES) + ". Overall strength comes mostly from factual; math has only 6 wrong answers.", ""]

    L += ["## Part 2a — Gate precision and recall, 95% bootstrap CI", "",
          f"{N_BOOT:,} resamples of questions (within each category), escalated set kept fixed.", "",
          "| Metric | Value | 95% CI |", "|---|---:|---|",
          f"| Precision | {f3(gate_ci['precision'])} | {f3(gate_ci['precision_ci'][0])}–{f3(gate_ci['precision_ci'][1])} |",
          f"| Recall | {f3(gate_ci['recall'])} | {f3(gate_ci['recall_ci'][0])}–{f3(gate_ci['recall_ci'][1])} |", "",
          f"**Verdict:** even the low end of the precision interval ({f3(gate_ci['precision_ci'][0])}) is well above the random level (~{f3(ra['precision_mean'])}).", ""]

    L += ["## Part 2b — TF-IDF AUROC, 95% bootstrap CI", "",
          "| Category | AUROC | 95% CI |", "|---|---:|---|"]
    for c in CATEGORIES + ["all"]:
        a = auc_ci[c]
        L.append(f"| {c} | {f3(a['auroc'])} | {f3(a['ci'][0])}–{f3(a['ci'][1])} |")
    L += ["", "**Verdict:** factual and overall intervals are tight and far above 0.5. Math is wide because only 6 math answers are wrong. Reasoning stays clearly above 0.5 but is the weakest.", ""]

    s = out["part2c_selector_vs_tfidf"]
    L += ["## Part 2c — CV selector vs TF-IDF (same folds as selector_cv.py)", "",
          "Each held-out fold is resampled on its own and fold AUROCs are averaged, the same way the reported numbers are computed.", "",
          "| | Selector | TF-IDF |", "|---|---:|---:|"]
    for c in CATEGORIES:
        L.append(f"| {c} | {f3(s['selector_per_category'][c])} | {f3(s['tfidf_per_category'][c])} |")
    L += [f"| **macro** | **{f3(s['selector_macro'])}** ({f3(s['selector_macro_ci'][0])}–{f3(s['selector_macro_ci'][1])}) | **{f3(s['tfidf_macro'])}** ({f3(s['tfidf_macro_ci'][0])}–{f3(s['tfidf_macro_ci'][1])}) |", "",
          f"- Difference: **{s['difference']:+.3f}**, 95% CI {s['difference_ci'][0]:+.3f} to {s['difference_ci'][1]:+.3f}",
          f"- Share of resamples where the selector is not better (difference ≤ 0): {s['fraction_difference_le_0']:.3f}",
          f"- Valid resamples: {s['valid_resamples']} of {N_BOOT} (a resample is skipped if a held-out fold ends up with no wrong answers)",
          f"- Fold winners: " + "; ".join(f"{c}: {', '.join(w)}" for c, w in s['fold_winners'].items()), ""]
    lo = s["difference_ci"][0]
    verdict = ("the +{:.3f} gain is reliably above zero".format(s["difference"]) if lo > 0
               else "the +{:.3f} gain is NOT reliably above zero — the interval includes 0".format(s["difference"]))
    L += [f"**Verdict:** {verdict}. Almost all of the gain comes from math, where only 6 answers are wrong, so treat it as promising but not proven.", ""]

    (uq.RESULTS_DIR / "baselines_report.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
