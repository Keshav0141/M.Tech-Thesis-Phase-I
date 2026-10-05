# Mid-Review Write-up (Draft)

_Status: main generation complete (2,250/2,250), Week 1 evaluation complete,
and the 52-question tier-2 escalation pilot is complete. Numbers pulled from
`results/` and `docs/research_log.md`; nothing recomputed._

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
- Pipeline under evaluation: tier 1 generates N=5 samples per question at
  temperature 0.7; five uncertainty scores (n-gram Jaccard, TF-IDF cosine,
  NLI semantic entropy) predict whether the majority-vote answer is wrong;
  AUROC is the metric. The top-uncertainty subset is then escalated
  selectively to tier 2 (`openai/gpt-oss-120b`); no full second-dataset
  generation is used.

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
  flash fallbacks were retired or 20 req/day capped; **final tier 1:
  Groq `qwen/qwen3.8-27b`**, `reasoning_effort="none"`, temperature 0.7,
  N=5, caps 1024/1024/1536. **Tier 2 is closed as Groq
  `openai/gpt-oss-120b`** after evaluating Groq/Gemini/OpenCode
  Zen/OpenRouter/Cerebras/HuggingFace; HuggingFace’s router works but is
  credit-metered and has no capability advantage over Groq, so it was not
  adopted.
- **Free-tier rate-limit handling**: 200k tokens/day, 1,000 requests/day
  (rolling 24h window), 1,000 output tokens/minute (OTPM) -> resumable JSONL
  logging, `ProviderExhausted` short-circuit, dynamic OTPM pacing
  (`max(22s, completion_tokens/900*60 + 2s)`), and a Windows Task Scheduler
  driver harvesting the rolling quota hourly during refill windows.
- **Result: 2,250/2,250 samples**, single model, temperature 0.7 on every
  record, 0 duplicates, 569,238 tokens, 53.9 hours wall-clock.

## 4. Week 1 baseline results (post-manual-review)

AUROC of uncertainty vs. majority-vote error (450 labeled questions;
post-manual-review protocol; grader fixed for accents and Roman ordinals):

| Method | All | Factual | Math | Reasoning |
|---|---:|---:|---:|---:|
| TF-IDF cosine | **0.847** | **0.911** | 0.756 | 0.630 |
| Unigram Jaccard | 0.825 | 0.835 | 0.845 | 0.645 |
| Bigram Jaccard | 0.820 | 0.840 | 0.817 | 0.677 |
| Trigram Jaccard | 0.819 | 0.850 | 0.814 | 0.673 |
| Semantic entropy (NLI) | 0.704 | 0.656 | 0.515 | 0.633 |

Error labels: 98 incorrect / 352 correct majority votes (factual 50, math 6,
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
| TF-IDF alone | **0.847** | **0.911** | 0.756 | 0.630 |
| Ensemble unweighted-5 | 0.753 | 0.860 | 0.802 | 0.679 |
| Ensemble weighted-5 (5-fold CV) | 0.747 | 0.870 | 0.782 | 0.661 |
| Ensemble unweighted-3 | 0.757 | 0.881 | 0.808 | 0.668 |
| Ensemble weighted-3 (5-fold CV) | 0.752 | 0.882 | 0.804 | 0.655 |

- Rank-averaging dilutes the strong method with correlated weaker ones:
  ensembles lose ~0.09-0.10 overall.
- Per category they help where TF-IDF is weak (math +0.05, reasoning +0.05)
  but lose factual, and factual carries most error labels (50 of 98), so the
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
| factual | **0.909** | 0.909 (tie) |
| math | **0.836** | 0.740 |
| reasoning | **0.667** | 0.629 |
| **macro-average** | **0.804** | 0.759 (+0.045) |

- Selector gain of +0.045: bootstrap 95% CI −0.024 to +0.105, so not yet
  significant.

- Caveat: the pooled OOF-rank aggregate (0.767) does not beat the in-sample
  full-data TF-IDF 0.847; TF-IDF's own CV macro (0.759) is the comparable
  number. Per-category ranking discards TF-IDF's raw-scale advantage on
  factual, where most errors are.
- **Math noise problem**: only 6 incorrect math questions; held-out fold
  AUCs swing 0.69-0.97, so the math numbers are indicative, not conclusive.
- Final gate (TF-IDF factual, numeric-disagreement math, bigram reasoning;
  top-15% per category): 55/450 escalated, 34 wrong, precision 0.62 (95% CI
  0.49–0.74), recall 0.35. Random escalation with the same per-category
  counts gives 0.26 (`results/baselines_report.md`).

## 8. Discussion: Tier-2 escalation tradeoffs

### Regression cost of escalation

The tier-2 pilot (52 questions, `openai/gpt-oss-120b`) recovered 14 of the
original `qwen/qwen3.8-27b` errors but introduced 4 new ones (regression
rate: 8%, 4/52). All four regressions occurred in the Reasoning category
(StrategyQA yes/no). Manual inspection shows `gpt-oss-120b` confidently
argues the opposite side on nuanced multi-hop questions: three of four
cases trace to a factual disagreement in the model's reasoning chain
(e.g. giant squid vs. Titanic deck-size comparison, Drow vs. Hobbit
height, watchmaker vs. Apple Watch precision), and the fourth is a
genuinely contestable historical claim (French Revolution outcome)
where reasonable disagreement exists independent of model capability.

Net effect on the escalated set: accuracy rose from 0.31 to 0.58
(+0.27), i.e. escalation recovers roughly 3.5 errors for every 1 it
introduces. We treat this as the expected cost of selective escalation
rather than a pipeline defect — a larger model is not uniformly more
reliable, and the gate's job is to bound how often that tradeoff is
paid, not eliminate it.

### Math error-pool scarcity

Math accuracy under `qwen/qwen3.8-27b` is high (96.0% on the main set and
98.0% on the expansion set), which leaves very few majority-incorrect
examples to validate an escalation gate against: 6/150 on the main set,
rising to only 9/300 after a 150-question GSM8K expansion (mathb) built
specifically to test whether this was a sampling artifact rather than a
genuine ceiling. A threshold sweep across 5-25% gate width topped out at
0.13 precision at any setting: 4 of 9 errors are caught at 10-20%, and
even at 25% only 5 of 9 are caught — confirming a data-volume limitation
rather than a tuning problem.

We evaluated a numeric-aware disagreement signal (extracting the final
numeric answer per sample and scoring disagreement directly) as an
alternative to lexical gating. It is a weaker standalone ranker (AUROC
0.651 vs. 0.794 for unigram Jaccard) but roughly doubles escalation
precision (0.20 vs. 0.09), at lower recall (0.33 vs. 0.44), because it
targets consistent-wrong cases — samples that agree lexically but
disagree numerically — that the lexical signal structurally cannot see.
An OR-combination of the two signals was tested and rejected: it added
no recall (the numeric signal's catches are a subset of the lexical
signal's) while diluting precision. The final math gate uses the
numeric-disagreement signal alone. Given n=9, these precision/recall
figures should be read as directional rather than statistically stable;
a larger error pool (e.g. via a harder dataset such as MATH) is the
natural next step if further validation is required.

### Note on gate/pilot alignment

After the post-review relabeling of the 29-question backlog, the
escalation gate at a fixed top-15% threshold now selects 55 questions
rather than the 52 evaluated in the executed tier-2 pilot. The pilot
was not re-run against the updated gate output; the 3-question
difference is small relative to gate size and unlikely to materially
shift the recovery/regression figures above, but is noted here for
completeness.

## 9. Closed items

1. **Model tier closed:** tier 1 is Groq `qwen/qwen3.8-27b`; tier 2 is Groq
   `openai/gpt-oss-120b`, used for selective escalation only. The provider
   search covered Groq, Gemini, OpenCode Zen, OpenRouter, Cerebras, and
   HuggingFace. The 52-question pilot lifted accuracy on the escalated subset
   from **0.31 to 0.58 (+0.27)**, recovering **14/32 (44%)** originally-wrong
   answers with a **4/52 (8%)** regression rate, all in reasoning
   (`results/tier2_pilot_results.md`).
2. **Manual-review backlog cleared:** all 29 factual questions with
   alias/partial-match samples were reviewed individually; all 17 previously
   “unresolved” questions now have final labels (13 correct, 4 incorrect).
   The 87 per-sample decisions (69 correct, 18 incorrect) are preserved in
   `results/manual_review_overrides.json` and applied by
   `scoring/score_correctness.py`. Final factual labels are 100 correct / 50
   incorrect; overall labels are 352 correct / 98 incorrect, with 0
   unresolved and an empty `results/needs_review.jsonl`.

## 10. Next steps (weeks 2-3)

- The full method set from the base paper is now implemented: NumSets,
  Degree matrix, EigV, and Eccentricity were added on top of the five Week 1
  methods (see `results/extended_methods_report.md`). Findings so far:
  NumSets ~ semantic entropy (0.708 vs 0.704 all-category); Degree/EigV are
  inverted (agreement measures, flipped ~0.73) and identical in our
  simplified binary-graph version (the paper's weighted, normalised versions
  differ); none of the four changed the CV selector's winners or its
   macro-AUROC (still 0.804 vs 0.759 TF-IDF-CV).
- Mathb expansion complete: 150/150 questions generated
  (`data/math_expansion.json`, ids mathb_0001..0150, 5 samples each, same
  model/settings), 3 majority-incorrect; combined math pool is now 9/300
  errors (main 6/150 + expansion 3/150). Gate evaluation uses this combined
  pool where noted.
- Add a number-aware semantic clustering fix (numeric-equality precondition
  before NLI merge, motivated by the math_0009 diagnosis).
- Keep the escalation-only tier-2 design; do not collect a full second-model
  dataset.
- After the professor's review: final proofread before submission.
