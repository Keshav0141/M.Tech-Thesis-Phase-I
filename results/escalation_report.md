# Confidence-gated escalation report (first pass)

_Gate method per category (CV selector fold winners): factual=tfidf, math=unigram, reasoning=bigram._

Thresholds evaluated: top 10% / 15% / 20% most-uncertain.
Precision = incorrect / escalated; recall = escalated-incorrect / all-incorrect; escalation rate = escalated / labeled.

| Category | pct | labeled | escalated (rate) | incorrect-escalated | precision | recall | error rate |
|---|---|---:|---:|---:|---:|---:|---:|
| factual | 10% | 150 | 15 (10%) | 15 | 1.00 | 0.30 | 0.33 |
| math | 10% | 150 | 15 (10%) | 3 | 0.20 | 0.50 | 0.04 |
| reasoning | 10% | 150 | 15 (10%) | 9 | 0.60 | 0.21 | 0.28 |
| **all** | 10% | 450 | 45 (10%) | 27 | 0.60 | 0.28 | 0.22 |
| factual | 15% | 150 | 23 (15%) | 22 | 0.96 | 0.44 | 0.33 |
| math | 15% | 150 | 23 (15%) | 3 | 0.13 | 0.50 | 0.04 |
| reasoning | 15% | 150 | 23 (15%) | 10 | 0.43 | 0.24 | 0.28 |
| **all** | 15% | 450 | 69 (15%) | 35 | 0.51 | 0.36 | 0.22 |
| factual | 20% | 150 | 30 (20%) | 27 | 0.90 | 0.54 | 0.33 |
| math | 20% | 150 | 30 (20%) | 3 | 0.10 | 0.50 | 0.04 |
| reasoning | 20% | 150 | 30 (20%) | 14 | 0.47 | 0.33 | 0.28 |
| **all** | 20% | 450 | 90 (20%) | 44 | 0.49 | 0.45 | 0.22 |

## Summary

- top 10%: escalate 45/450 (10%), precision 0.60, recall 0.28
- top 15%: escalate 69/450 (15%), precision 0.51, recall 0.36
- top 20%: escalate 90/450 (20%), precision 0.49, recall 0.45

## Second-model call

- The escalation call is wired (`openai/gpt-oss-120b`, reasoning_effort low) in `scoring/escalate.py:escalate_to_larger_model`, but is executed only by `scoring/tier2_pilot.py` for the ~52 escalated questions; the gate itself never spends API calls.

## Math threshold sweep (combined pool: main math + mathb = 300, 9 errors)

_Unigram gate unchanged. Base error rate 0.030._

| top-pct | escalated | precision (wrong/escalated) | recall (of 9 errors) |
|---:|---:|---:|---:|
| 5% | 15 | 0.13 | 0.22 |
| 10% | 30 | 0.13 | 0.44 |
| 15% | 45 | 0.09 | 0.44 |
| 20% | 60 | 0.07 | 0.44 |
| 25% | 75 | 0.07 | 0.56 |

## Verdict (math sweep)

- Precision across thresholds: 5%->0.13; 10%->0.13; 15%->0.09; 20%->0.07; 25%->0.07.
- **Best precision is 0.13** (top 5-10%), which is ~4.3x the 0.03 base rate,
  but absolute precision stays low and DEGRADES as the threshold widens.
- Recall plateaus at 0.44 for 10-20% (only 4 of 9 errors caught) and reaches
  0.56 only at 25% -- the remaining errors have LOW unigram uncertainty and
  no threshold can surface them.
- Conclusion: this is primarily a **data-volume problem** (9 positives in 300),
  not a threshold-tuning problem. Tuning cannot rescue the math gate; a
  better math uncertainty signal (or a harder math source) is needed.

## Numeric-aware math signal (final-answer disagreement)

_numeric_disagreement = 1 - (samples matching the majority final number)/n_extracted; scored on the combined math pool (300 questions, 9 errors). Unigram baseline recomputed on the same pool. Escalation at top-15%._

| Pool | Signal | AUROC | top-15% precision | top-15% recall |
|---|---|---:|---:|---:|
| combined (300) | numeric_disagreement | 0.6510 | 0.20 | 0.33 |
| combined (300) | unigram (baseline) | 0.7942 | 0.09 | 0.44 |
| main only (150) | numeric_disagreement | 0.6487 | 0.22 | 0.33 |
| main only (150) | unigram (baseline) | 0.8449 | 0.13 | 0.50 |

## Combined math gate (union of unigram OR numeric-disagreement)

_Escalate if in the top-15% by EITHER signal (union, not intersection). Ties in the numeric signal make its top-15% set smaller in practice._

| Pool | Gate | escalated (rate) | precision | recall | errors caught |
|---|---|---:|---:|---:|---:|
| combined (300) | unigram alone | 45 (15%) | 0.09 | 0.44 | 4/9 |
| combined (300) | numeric alone | 15 (5%) | 0.20 | 0.33 | 3/9 |
| combined (300) | union (OR) | 49 (16%) | 0.08 | 0.44 | 4/9 |
| combined (300) | overlap (unigram ∩ numeric) | 11 | - | - | - |
| main only (150) | unigram alone | 23 (15%) | 0.13 | 0.50 | 3/6 |
| main only (150) | numeric alone | 9 (6%) | 0.22 | 0.33 | 2/6 |
| main only (150) | union (OR) | 26 (17%) | 0.12 | 0.50 | 3/6 |
| main only (150) | overlap (unigram ∩ numeric) | 6 | - | - | - |
