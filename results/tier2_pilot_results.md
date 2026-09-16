# Tier-2 Escalation Pilot Results (openai/gpt-oss-120b)

_Executed 2026-09-16, 18:38 IST. 52 escalated questions, 1 sample each,
temperature 0.7, reasoning_effort=low, max_tokens=1536._

## Budget vs actual

| Metric | Estimate | Actual |
|---|---:|---:|
| Requests | 52 | 52 |
| Tokens | ~21K | **13,414** (~258/sample) |
| Generation time | ~24 min | **20.5 min** |
| Truncated responses | n/a | **0** (all `finish_reason=stop`) |

## Escalation outcome matrix (qwen -> gpt-oss-120b)

| Outcome | Count | Meaning |
|---|---:|---|
| qwen wrong -> gpt-oss-120b right | **14** | RECOVERY (escalation fixed the error) |
| qwen wrong -> still wrong | 18 | no improvement |
| qwen right -> kept right | 16 | no harm |
| qwen right -> regressed | 4 | escalation broke a previously-correct answer |

## Did escalation actually improve final accuracy?

- qwen accuracy on the escalated subset: **16/52 = 0.31**
- Final accuracy after escalation: **30/52 = 0.58**
- **+0.27 absolute improvement** on the escalated questions.
- Of the 32 originally-wrong escalated questions, gpt-oss-120b fixed **14
  (44%)** and left 18 wrong.
- The gate did its job: it selected a low-accuracy subset (qwen 31% vs its
  78% overall), and escalation lifted it to 58%.

## Caveats

- 4 regressions (qwen right -> gpt-oss wrong) are worth inspecting: the
  bigger model is not uniformly better on these 52 questions.
- Final accuracy on the escalated set (58%) is still well below qwen's overall
  accuracy (78%), so escalation helps but does not fully close the gap.

## Files

- `logs/tier2_generations.jsonl` — raw tier-2 responses (finish_reason,
  token_usage, tier-2 labels).
- `results/tier2_escalated_questions.json` — the escalated set.