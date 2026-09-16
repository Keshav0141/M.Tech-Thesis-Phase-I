# Tier-2 / Tier-3 Generation Timeline Estimate

_Planning estimate only — no generation started. Limits checked against
https://console.groq.com/docs/rate-limits and a live header probe on
2026-09-16._

## 0. Limit check (corrections to the brief)

- Groq free plan, checked today: **30 RPM, 1,000 RPD, 8K TPM, 200K TPD** for
  `openai/gpt-oss-120b` (and the same for gpt-oss-20b and qwen3.8-27b).
  The brief's assumed **100K TPD is not current — the free-plan TPD is 200K**.
- **`llama-3.3-70b-versatile` is retired/unavailable**: a live call returns
  `404 model_not_found` and it is absent from the current model/limits table.
  Tier-2 as named cannot be generated. The available escalation targets are:
  `openai/gpt-oss-120b` (larger tier) and `openai/gpt-oss-20b` /
  `qwen/qwen3.6-27b` (same size class as the current 27B).
- Live header probe (gpt-oss-120b): 1,000 RPD, 8K TPM confirmed.

## 1. Token-per-sample average (from the existing run)

- 569,238 tokens / 2,250 samples = **253 tokens/sample** (all categories,
  qwen3.8-27b, reasoning_effort=none).
- Caveat: gpt-oss-120b is a reasoning model (no `none` effort; hidden
  reasoning counts as tokens), so real usage will be **higher**. Sensitivity
  below uses 253 / 400 / 600 tokens per sample.

## 2. Samples per day at 200K TPD (per model)

| tokens/sample | samples/day (TPD-bound) | notes |
|---:|---:|---|
| 253 | **~790** | TPD binds; RPD 1,000 not binding; 30 RPM fine at our ~25s pacing |
| 400 | ~500 | if 120B reasoning uses ~1.6x tokens |
| 600 | ~333 | pessimistic reasoning-heavy case |

At ~25-30s per sample of pacing, ~790 samples/day is also ~5.5-6.5h of
wall-clock, so wall time is not the constraint — TPD is.

## 3. (a) Full second dataset — 450 questions x 5 samples = 2,250 samples

| scenario | tokens/sample | samples/day | days |
|---|---:|---:|---:|
| optimistic (same as qwen) | 253 | 790 | **~3 days** |
| mid (reasoning overhead) | 400 | 500 | ~5 days |
| pessimistic | 600 | 333 | ~7 days |

## 4. (b) Escalation-only generation (the decided gate)

Escalated questions under the current gate (from
`results/escalation_decisions.jsonl` and the combined math gate):

- factual (TF-IDF, top-15%): 20 of 133 labeled -> ~23 of 150
- reasoning (bigram, top-15%): 23 of 150
- math (numeric-disagreement, ~5% effective): 9 of 150

Total: **~55 questions -> ~275 samples at N=5**.

| scenario | tokens/sample | samples/day | days |
|---|---:|---:|---:|
| optimistic | 253 | 790 | **<1 day (~0.35)** |
| mid | 400 | 500 | ~1 day (0.55) |
| pessimistic | 600 | 333 | ~1 day (0.83) |

With N=1 per escalated question (single second-model answer instead of 5),
it is ~55 samples — comfortably inside a single daily budget.

## 5. Bottom line for the professor

- Escalation-only tier-2/3 generation is **~1 day** (one daily free-tier
  budget), versus **~3 days (best case) to ~7 days** for a full second
  dataset of 450 questions.
- `llama-3.3-70b-versatile` no longer exists; the realistic larger tier is
  `openai/gpt-oss-120b` (200K TPD free plan).
- The escalation-only route therefore makes the gate experiment affordable on
  the free tier; the full second dataset is also feasible but ~3-7x the cost.
