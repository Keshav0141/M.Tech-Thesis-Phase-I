# Week 3 Meeting Prep — Discussion Agenda

_Short talking-points doc for the meeting. Full detail: `docs/mid_review_draft.md`.
All numbers below are pulled from `results/` (no recomputation)._

## Since the last meeting

Generation is complete (2,250/2,250 samples, single model `qwen/qwen3.8-27b`,
temp 0.7, 0 duplicates, 569k tokens), and the Week 1 evaluation is done:
TF-IDF is the strongest single method (AUROC 0.845 overall, 0.909 factual),
the full 9-method Lin et al. set is implemented (NumSets 0.710; Degree/EigV
inverted agreement measures), and a cross-validated per-category selector
picks stable winners (TF-IDF / unigram / bigram) for a macro-AUROC of 0.805
vs 0.760 for TF-IDF-CV. The math-specific noise problem was investigated and
an expansion pool was generated (mathb, 750/750). A first-pass
confidence-gated escalation pipeline is built and validated (details below).

## Decisions needed

### (a) Model-tier mismatch — how should the escalation tiers be defined?

- **Question:** the original plan assumed a small tier (1B/8B/20B) escalating
  to a larger one; Groq retired the Llama models and only 27B-class and larger
  are available now. What should the two tiers be?
- **Evidence:** all 2,250 samples were generated with `qwen/qwen3.8-27b`
  (27B). Groq's current free-tier catalog also offers `openai/gpt-oss-120b`
  (200k tokens/day, same limits we already handle).
- **Options:**
  1. Keep 27B as the working tier, escalate to `gpt-oss-120b` — free-tier
     only, but the tier gap is large (no 70B middle).
  2. Regenerate the base set on a smaller model (e.g., `gpt-oss-20b`) so the
     small→big escalation matches the original design — costs ~2-3 extra
     days of quota-limited generation.
  3. Stay single-tier and reframe the thesis as gate validation only — zero
     extra cost, but drops the escalation story.

### (b) Math error-pool scarcity — what is the math benchmark for the final study?

- **Question:** math has only 9 incorrect majority-vote questions in 300
  (3%), which makes per-category math AUROC and the math gate unreliable.
  Do we accept this, or change the math source/signal?
- **Evidence:** GSM8K is too easy for this model (98% majority accuracy on
  the expansion set); the math gate sweep caps at 0.13 precision (best, top
  5-10%) and recall plateaus at 0.44 — a data-volume problem, not threshold
  tuning. The NLI math diagnosis (math_0009: 4/7 differing-number pairs
  merged, p up to 0.995) shows a separate numeric-blindness issue at ~3%
  incidence.
- **Options:**
  1. Accept small-n — no extra work; math numbers stay noisy and must be
     reported with n=9 caveats.
  2. Switch math to the harder MATH dataset — larger error pool expected;
     costs a new dataset build + ~2-3 days regeneration, and changes the
     benchmark from the original plan.
  3. Build a numeric-aware signal (compare final numbers before NLI merge) —
     cheap and fixes the diagnosed failure mode, but does not enlarge the
     9-error pool, so math AUROC noise remains.

### (c) Escalation gate — approve routing to a second model?

- **Question:** the confidence gate is validated; may we wire the real
  second-model call (tier per decision (a))?
- **Evidence:** top-15% escalation on the 433 labeled questions gives
  precision 0.50 and recall 0.35 vs a 0.22 base error rate (2.3x enrichment);
  factual is excellent (precision 1.00); math is weak (0.13, see (b)).
  The call is currently a stub, so nothing routes anywhere yet.
- **Options:**
  1. Wire the real call once (a) is decided — completes the pipeline;
     consumes free-tier quota only (~66 calls per 15% escalation run).
  2. Keep the stub — no cost, but no end-to-end escalation result.
  3. Start with a factual-only gate — highest precision, but ignores
     math/reasoning routing.

## Next step depending on (a) and (b)

If the professor approves `gpt-oss-120b` as the escalation tier and either
accepts the math small-n or moves to MATH, I will wire the second-model call
and re-run the gate on the chosen pool; otherwise the pipeline stays stubbed
and the thesis reports gate validation only.
