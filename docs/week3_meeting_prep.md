# Week 3 Meeting Prep — Discussion Agenda

_Companion to `docs/mid_review_draft.md` (the formal write-up). All numbers
pulled from the results files; nothing recomputed here._

## 1. Since the last meeting

We finished the dataset (450 questions x 5 samples = 2,250 samples on Groq
`qwen3.8-27b`, temperature 0.7, 569k tokens, 0 duplicates), implemented all
nine black-box UQ methods from Lin et al. (TMLR 2024) including the four graph
measures (NumSets, Degree, EigV, Eccentricity), and completed the Week 1
evaluation: TF-IDF leads the single methods (AUROC 0.845); a CV-validated
per-category selector beats TF-IDF under identical CV (macro 0.805 vs 0.760);
and the confidence-gated escalation pipeline routes the top-15% most-uncertain
questions with 0.50 precision (2.3x error enrichment). We also generated a
150-question GSM8K expansion and built a numeric-aware uncertainty signal for
math. Details: `docs/mid_review_draft.md`.

## 2. Decision needed

### (a) Model tier — 1B/8B/20B plan vs. what Groq actually serves

**Question:** does the escalation design need a second, larger tier, or should
the thesis commit to a single 27B model?

**Evidence:** the original plan targeted 1B/8B/20B with escalation to a bigger
model; Groq's catalog now offers qwen3.x-27B, gpt-oss-20B/120B (Llama retired),
and all 2,250 current samples are from qwen3.8-27b.

**Options:**
- Single 27B model — simplest, matches existing data; loses the escalation story.
- 27B -> 120B escalation — keeps the gate design; needs a second sample set (~2-3 days free-tier).
- Multi-size ensemble (20B/27B/120B) — richest UQ comparison; most generation time.

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
0.44 -> 0.33. Kept as a precision-oriented gate component; a combined
numeric+unigram gate is the natural follow-up if the professor wants it.

### (c) Escalation gate — approved as designed

**Decision:** proceed with the validated gate (CV selector method per
category, configurable top-N% threshold). **Why:** on the 433 labeled
questions the top-15% gate reaches 0.50 precision and 2.3x error enrichment
(factual precision 1.00).

**Acted on:** `scoring/escalate.py` produces per-question keep/escalate
decisions (`results/escalation_decisions.jsonl`) and the report; the
second-model call is stubbed and marked TODO, blocked only on decision (a).

## 4. Next step

If (a) selects a second tier, we wire the real escalation call and re-run the
math category with the combined numeric+unigram gate; otherwise we finalize
the single-model write-up with small-n caveats.
