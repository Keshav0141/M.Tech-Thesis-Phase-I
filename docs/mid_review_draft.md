# Mid-Review Write-up (Draft)

_Status: generation complete (2,250/2,250), Week 1 evaluation complete.
Numbers pulled from `results/` and `docs/research_log.md`; nothing recomputed._

---

## 1. Problem & system design

- Goal: reliable LLM answers via **escalation gates** — a cheap uncertainty
  signal decides whether to accept the model's answer or escalate (retry,
  abstain, or call a stronger model).
- Framing and base paper: **Zhen Lin, Shubhendu Trivedi, and Jimeng Sun,
  "Generating with Confidence: Uncertainty Quantification for Black-box Large
  Language Models", Transactions on Machine Learning Research (TMLR), May
  2024, arXiv:2305.19187 (code: github.com/zlin7/UQ-NLG).** The paper studies
  black-box UQ for selective NLG — the same escalation-gate setting used here
  (an uncertainty/confidence measure decides whether a generation is accepted
  or escalated for further assessment).
- Pipeline under evaluation: one model generates N=5 samples per question at
  temperature 0.7; five uncertainty scores (n-gram Jaccard, TF-IDF cosine,
  NLI semantic entropy) predict whether the majority-vote answer is wrong;
  AUROC is the metric.

## 2. Dataset

- **450 questions, 3 categories (MECE)**: 150 factual (TriviaQA
  rc.nocontext), 150 math (GSM8K), 150 reasoning (StrategyQA).
- Per-category validation criteria; exact/near-duplicate removal; alias
  ambiguity filter (323 factual candidates dropped).
- Manual spot-check: 20 questions reviewed; **4 rejected entries retained**
  for provenance — two source-data errors fixed and replaced:
  - `factual_0025` conflated The Maltese Falcon with Casablanca
  - `factual_0037` mislocated Keiko's death (Finland vs Norway)
  - plus two time-sensitive wording rejects (`factual_0152`, `reasoning_0106`)
- Final: 450 active (432 auto_validated + 18 spot_checked) + 4 rejected;
  validated 150/150/150 with 0 duplicates and 0 structural errors.

## 3. Generation pipeline

- **Model journey**: original plan (Llama-3.2-1B / Llama-3.1-8B) retired
  mid-project; gpt-oss-20b pilot hit empty-response/thinking issues; Gemini
  flash fallbacks were retired or 20 req/day capped; **final single model:
  Groq `qwen/qwen3.8-27b`**, `reasoning_effort="none"`, temperature 0.7,
  N=5, caps 1024/1024/1536.
- **Free-tier rate-limit handling**: 200k tokens/day, 1,000 requests/day
  (rolling 24h window), 1,000 output tokens/minute (OTPM) -> resumable JSONL
  logging, `ProviderExhausted` short-circuit, dynamic OTPM pacing
  (`max(22s, completion_tokens/900*60 + 2s)`), and a Windows Task Scheduler
  driver harvesting the rolling quota hourly during refill windows.
- **Result: 2,250/2,250 samples**, single model, temperature 0.7 on every
  record, 0 duplicates, 569,238 tokens, 53.9 hours wall-clock.

## 4. Week 1 baseline results (post-grader-fix)

AUROC of uncertainty vs. majority-vote error (433 labeled questions;
full-data protocol; grader fixed for accents and Roman ordinals):

| Method | All | Factual | Math | Reasoning |
|---|---:|---:|---:|---:|
| TF-IDF cosine | **0.845** | **0.909** | 0.756 | 0.630 |
| Unigram Jaccard | 0.825 | 0.835 | 0.845 | 0.645 |
| Bigram Jaccard | 0.820 | 0.840 | 0.817 | 0.677 |
| Trigram Jaccard | 0.817 | 0.848 | 0.814 | 0.673 |
| Semantic entropy (NLI) | 0.706 | 0.659 | 0.515 | 0.633 |

Error labels: 94 incorrect / 339 correct majority votes (factual 46, math 6,
reasoning 42).

## 5. Diagnostic finding — semantic entropy's numeric blindness

- Bottom-quartile math entropy (37 "confident" questions, entropy ~0): only 2
  have different extracted final numbers; one is a unit-equivalence artifact
  of our extractor (6.5 h vs 390 min).
- Genuine case `math_0009` (12000 vs 7000 vs 2000): **4/7 differing-number
  pairs marked equivalent by bidirectional NLI** (p up to 0.995).
- **Honest caveat**: incidence is ~1/37 (~3%) of confident math questions.
  The failure mode is real and matches prediction, but the effect size is
  small; it explains only part of semantic entropy's weak math AUROC
  (0.515, n=6 incorrect).

## 6. Ensemble result — negative in aggregate, positive per-category

| Variant | AUROC all | factual | math | reasoning |
|---|---:|---:|---:|---:|
| TF-IDF alone | **0.845** | **0.909** | 0.756 | 0.630 |
| Ensemble unweighted-5 | 0.747 | 0.859 | 0.802 | 0.679 |
| Ensemble weighted-5 (5-fold CV) | 0.745 | 0.870 | 0.799 | 0.665 |
| Ensemble unweighted-3 | 0.751 | 0.882 | 0.808 | 0.668 |
| Ensemble weighted-3 (5-fold CV) | 0.748 | 0.884 | 0.814 | 0.657 |

- Rank-averaging dilutes the strong method with correlated weaker ones:
  ensembles lose ~0.09-0.10 overall.
- Per category they help where TF-IDF is weak (math +0.06, reasoning +0.05)
  but lose factual, and factual carries most error labels (46 of 94), so the
  aggregate is negative. Logistic weights add nothing (methods highly
  correlated; weighted vs unweighted differ by <0.005).

## 7. CV-validated selector — the positive result

- Per category, 5-fold stratified CV: winner chosen on the training split
  only, evaluated on the held-out fold (leakage-free).
- Fold winners: factual tfidf 5/5; math unigram 4/5 (one bigram flip);
  reasoning bigram 4/5 (one trigram flip). Selection is stable.
- Results (same-fold protocol):

| | selector (CV) | TF-IDF (same-fold CV) |
|---|---:|---:|
| factual | **0.910** | 0.910 (tie) |
| math | **0.836** | 0.740 |
| reasoning | **0.667** | 0.629 |
| **macro-average** | **0.805** | 0.760 (+0.045) |

- Caveat: the pooled OOF-rank aggregate (0.760) does not beat the in-sample
  full-data TF-IDF 0.845; TF-IDF's own CV macro (0.760) is the comparable
  number. Per-category ranking discards TF-IDF's raw-scale advantage on
  factual, where most errors are.
- **Math noise problem**: only 6 incorrect math questions; held-out fold
  AUCs swing 0.69-0.97, so the math numbers are indicative, not conclusive.

## 8. Open items for the professor

1. **Model-tier mismatch**: the original plan was a small-model tier
   (1B/8B/20B) with escalation to larger tiers; Groq's catalog changes forced
   a single 27B model (qwen3.8-27b). An ensemble across model sizes
   (27B/70B/120B) is not yet collected — decide whether the gate design
   needs a second tier.
2. **Manual-review backlog**: `results/needs_review.jsonl` holds 29 factual
   questions with alias/partial-match samples; 17 factual questions are
   "unresolved" and currently excluded from AUROC. These need a review pass
   (or an approved alias list) before the final evaluation numbers.

## 9. Next steps (weeks 2-3)

- Shrink the math noise problem: collect more math error signal (or accept
  the small-n caveat and report per-category numbers with n).
- The full method set from the base paper is now implemented: NumSets,
  Degree matrix, EigV, and Eccentricity were added on top of the five Week 1
  methods (see `results/extended_methods_report.md`). Findings so far:
  NumSets ~ semantic entropy (0.710 vs 0.706 all-category); Degree/EigV are
  inverted (agreement measures, flipped ~0.735) and identical by
  construction; none of the four changed the CV selector's winners or its
  macro-AUROC (still 0.805 vs 0.760 TF-IDF-CV).
- Math noise expansion in progress: 150 fresh GSM8K questions
  (`data/math_expansion.json`, ids mathb_0001..0150) are being generated
  (5 samples each, same model/settings) to enlarge the 6-question incorrect
  pool. Generation is underway via the scheduled quota harvester; the
  incorrect-count report is pending — no results yet.
- Add a number-aware semantic clustering fix (numeric-equality precondition
  before NLI merge, motivated by the math_0009 diagnosis).
- Decide the second model tier (if any) and run the same pipeline on it.
- After the professor's review: final proofread before submission.
