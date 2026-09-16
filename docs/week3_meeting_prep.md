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
and a first-pass confidence-gated escalation pipeline routes the top-15%
most-uncertain questions with 0.50 precision (2.3x error enrichment). We also
generated a 150-question GSM8K expansion to enlarge the math error pool and
diagnosed semantic entropy's numeric blindness on math. Details:
`docs/mid_review_draft.md`.

## 2. Decisions needed

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

### (b) Math error-pool scarcity — 9 errors in 300 questions

**Question:** GSM8K may be too easy for this model (98% majority accuracy);
accept small-n, or change the math source or signal?

**Evidence:** main math 6/150 + expansion 3/150 = 9 errors, base rate 0.03;
threshold sweep: best gate precision 0.13 (top 5-10%), recall plateaus at
0.44 — a data-volume problem, not a threshold-tuning problem.

**Options:**
- Accept small-n — no new work; math AUROC reported with an n=9 caveat.
- Switch to a harder math source (MATH dataset) — more errors; new sourcing + generation (~2-3 days).
- Build a numeric-aware signal (final-number disagreement) — targeted fix for the diagnosed NLI blindness; modest effort.

### (c) Escalation gate sign-off

**Question:** approve the gate design so the second-model call can be wired?

**Evidence:** top-15% escalation on the 433 labeled questions gives 0.50
precision, 0.35 recall (2.3x enrichment); factual precision 1.00; the
second-model call is currently stubbed pending (a).

**Options:**
- Approve now with a tier from (a) — pipeline completes; gate can be evaluated end-to-end.
- Keep stubbed — no second-model cost; metrics stay simulation-only.

## 3. Next step

If (a) picks a second tier and (b) picks a math fix, we wire the real
escalation call and re-run the math category; otherwise we finalize the
single-model write-up with small-n caveats.
