# Week 3 Meeting Prep — Discussion Agenda

_Companion to `docs/mid_review_draft.md` (the formal write-up). All numbers
pulled from the results files; nothing recomputed here._

## 1. Since the last meeting

We finished the dataset (450 questions x 5 samples = 2,250 samples on Groq
`qwen3.8-27b`, temperature 0.7, 569k tokens, 0 duplicates), implemented all
nine black-box UQ methods from Lin et al. (TMLR 2024) including the four graph
measures (NumSets, Degree, EigV, Eccentricity), and completed the Week 1
evaluation: TF-IDF leads the single methods (AUROC 0.847); a CV-validated
per-category selector beats TF-IDF under identical CV (macro 0.804 vs 0.759);
and the confidence-gated escalation pipeline routes the top-15% most-uncertain
questions with 0.51 precision (2.3x error enrichment). We also generated a
150-question GSM8K expansion and built a numeric-aware uncertainty signal for
math. Details: `docs/mid_review_draft.md`.

## 2. Decision closed

### (a) Model tier — standardized on 27B → 120B escalation-only

**Decision:** keep Groq `qwen/qwen3.8-27b` as tier 1 and use Groq
`openai/gpt-oss-120b` as the tier-2 escalation model. **Scale:** selective
escalation only — no full second-dataset generation.

**Why:** the provider/model search covered Groq, Gemini, OpenCode Zen,
OpenRouter, Cerebras, and HuggingFace. HuggingFace’s current Inference
Providers router works, but it is credit-metered and offers the same model
class with no capability advantage over Groq, so it was not adopted.
The alternatives were therefore rejected for availability, quota/cost, or
capability reasons; `gpt-oss-120b` was the viable larger Groq tier.

**Evidence:** the 52-question tier-2 pilot moved accuracy on the escalated
subset from **0.31 to 0.58 (+0.27)**. Of 32 originally wrong answers,
gpt-oss-120b recovered **14 (44%)**; there were 4 regressions (**8%**), all
in reasoning (`results/tier2_pilot_results.md`). The pilot used the
pre-review 52-question gate; after manual review, the recommended escalation
set expands to 55 by adding `factual_0001`, `factual_0113`, and
`factual_0117`. Pilot statistics are unchanged because the only overlapping
reviewed question, `factual_0048`, retained its incorrect majority label.

**Options rejected:**
- Single 27B model — simplest, but loses the escalation story.
- Full second dataset on 120B — unnecessary for selective escalation and far
  more expensive in quota/time.
- Multi-size ensemble (20B/27B/120B) — richest comparison, but inconsistent
  with the thesis’s selective-escalation framing and quota constraints.

## 3. Decided and done (for information, no action requested)

### (b) Math error-pool scarcity — resolved with a numeric-aware signal

**Decision:** build a numeric-aware signal instead of switching to a harder
math dataset. **Why:** it is a targeted fix for the diagnosed numeric blindness
(and the NLI merge failure on `math_0009`) and requires no new data sourcing.

**Acted on:** `scoring/math_numeric_signal.py` is implemented and evaluated on
the combined math pool (300 questions, 9 errors; `numeric_disagreement` =
1 - fraction of samples matching the majority final number). Result vs the
unigram baseline: AUROC 0.651 vs 0.794 (standalone ranking is weaker), but
escalation precision at top-15% improves 0.09 -> 0.20 while recall moves
0.44 -> 0.33.

**Final math gate (decided):** the union (OR) of the two signals was tested
and rejected — it added no recall (4/9 either way) and diluted precision
(0.09 -> 0.08). Math uses the **numeric-disagreement signal alone** at
top-15% (~5% effective rate): 0.20 precision / 0.33 recall, ~5 calls per
caught error vs unigram's 0.09 / 0.44 and ~11 calls. Unigram remains the
documented recall-priority alternative if the second model turns out cheap.

### (c) Escalation gate — approved as designed

**Decision:** proceed with the validated gate (CV selector method per
category, configurable top-N% threshold). **Why:** on the 450 labeled
questions the top-15% gate reaches 0.51 precision, 0.36 recall, and 2.3x error
enrichment (factual precision 0.96).

**Acted on:** `scoring/escalate.py` produces per-question keep/escalate
decisions (`results/escalation_decisions.jsonl`) and the report. The tier-2
call to `openai/gpt-oss-120b` is wired in
`scoring/escalate.py:escalate_to_larger_model` and was executed by
`scoring/tier2_pilot.py` for the 52 escalated questions. The routine gate
itself spends no API calls.

## 4. Next step

With tier 2 closed, finalize the post-manual-review evaluation numbers, keep
the escalation-only design, and complete the single-model write-up with the
documented small-n caveats.
