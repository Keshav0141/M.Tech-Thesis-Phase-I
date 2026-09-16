# Confidence-gated escalation report (first pass)

_Gate method per category (CV selector fold winners): factual=tfidf, math=unigram, reasoning=bigram._

Thresholds evaluated: top 10% / 15% / 20% most-uncertain.
Precision = incorrect / escalated; recall = escalated-incorrect / all-incorrect; escalation rate = escalated / labeled.

| Category | pct | labeled | escalated (rate) | incorrect-escalated | precision | recall | error rate |
|---|---|---:|---:|---:|---:|---:|---:|
| factual | 10% | 133 | 14 (11%) | 14 | 1.00 | 0.30 | 0.35 |
| math | 10% | 150 | 15 (10%) | 3 | 0.20 | 0.50 | 0.04 |
| reasoning | 10% | 150 | 15 (10%) | 9 | 0.60 | 0.21 | 0.28 |
| **all** | 10% | 433 | 44 (10%) | 26 | 0.59 | 0.28 | 0.22 |
| factual | 15% | 133 | 20 (15%) | 20 | 1.00 | 0.43 | 0.35 |
| math | 15% | 150 | 23 (15%) | 3 | 0.13 | 0.50 | 0.04 |
| reasoning | 15% | 150 | 23 (15%) | 10 | 0.43 | 0.24 | 0.28 |
| **all** | 15% | 433 | 66 (15%) | 33 | 0.50 | 0.35 | 0.22 |
| factual | 20% | 133 | 27 (20%) | 25 | 0.93 | 0.54 | 0.35 |
| math | 20% | 150 | 30 (20%) | 3 | 0.10 | 0.50 | 0.04 |
| reasoning | 20% | 150 | 30 (20%) | 14 | 0.47 | 0.33 | 0.28 |
| **all** | 20% | 433 | 87 (20%) | 42 | 0.48 | 0.45 | 0.22 |

## Summary

- top 10%: escalate 44/433 (10%), precision 0.59, recall 0.28
- top 15%: escalate 66/433 (15%), precision 0.50, recall 0.35
- top 20%: escalate 87/433 (20%), precision 0.48, recall 0.45

## Second-model call

- The escalation target is currently a STUB (`larger model (TBD: 70B/120B on Groq)`); no second model is called. The call site is marked TODO in `scoring/escalate.py:escalate_to_larger_model`.
