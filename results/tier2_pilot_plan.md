# Tier-2 Escalation Pilot Plan (openai/gpt-oss-120b)

_Planning only — awaiting go-ahead. No API calls spent yet (one validation
probe was used to check `reasoning_effort`)._

## 1. Exact scope (from the decided gates)

Escalated set exported by `scoring/export_escalated.py` ->
`results/tier2_escalated_questions.json`:

| Category | Gate | Escalated |
|---|---|---:|
| factual | TF-IDF top-15% | 20 |
| reasoning | bigram top-15% | 23 |
| math | numeric-disagreement top-15% | 9 |
| **Total** | | **52** |

Note: the brief estimated 55 (23 factual); the actual gate escalates **20**
factual (top-15% of the 133 labeled questions; the 17 unresolved have no
label and are not escalated). Math gate ~5% effective rate confirms 9.

## 2. Model & call settings

- Target: `openai/gpt-oss-120b` on Groq (free plan confirmed: 30 RPM /
  1K RPD / 8K TPM / 200K TPD; no card).
- **`reasoning_effort="none"` is rejected by gpt-oss-120b** (verified live:
  only `low|medium|high` accepted). The pilot uses **`low`** (minimal
  thinking, closest to instruct mode).
- 1 sample per question, temperature 0.7 (the dataset's locked temperature).
- Call logic reused from `generation/generate.py` (`GroqProvider`), including
  the OTPM-style pacing safeguard (`max(22s, completion/900*60 + 2s)`).
- Answers logged to `logs/tier2_generations.jsonl` (separate from the main
  dataset log).

## 3. Request / token / time budget

| Metric | Value | vs daily quota |
|---|---:|---:|
| Requests | **52** | 5.2% of 1,000 RPD |
| Tokens (est) | ~21K (52 x ~400; range 13-31K) | ~10% of 200K TPD |
| Generation time (est) | **~24 min** (52 x ~28s) | trivial |

Comfortably inside one day's free-tier budget — no risk of hitting the wall.

## 4. What gets reported after the run

- Generation time taken (vs the ~24 min estimate).
- Error recovery: of the escalated questions where qwen was wrong, how many
  did gpt-oss-120b answer correctly (the system's whole point).
- Regressions (qwen right -> gpt-oss wrong), kept-right, final accuracy on
  the escalated set.

## 5. Files

- `scoring/escalate.py` — real `escalate_to_larger_model()` wired (gate runs
  never spend calls; only `tier2_pilot.py` invokes it).
- `scoring/tier2_pilot.py` — the runner (`--dry-run` for plan; resumable).
- `scoring/export_escalated.py` + `results/tier2_escalated_questions.json`.
- Output: `logs/tier2_generations.jsonl`, `results/tier2_pilot_results.md`.