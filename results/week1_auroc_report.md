# AUROC Report - uncertainty vs. incorrect answers

_Generated 2026-09-12 12:03 UTC (partial data; final run once generation completes)._

Label: majority-vote incorrect (1) vs correct (0); unresolved/no-sample questions are excluded.
AUROC > 0.5 means the uncertainty score is higher on incorrect answers.

## Coverage

| Category | Dataset questions | Scored | With semantic entropy |
|---|---:|---:|---:|
| factual | 150 | 150 | 29 |
| math | 150 | 150 | 0 |
| reasoning | 150 | 150 | 0 |

## Results

| Category | Method | AUROC | incorrect/correct | mean score (incorrect) | mean score (correct) |
|---|---|---:|---|---:|---:|
| factual | lexical_uncertainty | 0.8375 | 10/16 | 0.7912 | 0.5391 |
| factual | semantic_entropy | 0.7250 | 10/16 | 1.0445 | 0.6298 |
| factual | semantic_entropy_normalized | 0.7250 | 10/16 | 0.649 | 0.3913 |
| math | lexical_uncertainty | n/a | 0/0 | n/a | n/a |
| math | semantic_entropy | n/a | 0/0 | n/a | n/a |
| math | semantic_entropy_normalized | n/a | 0/0 | n/a | n/a |
| reasoning | lexical_uncertainty | n/a | 0/0 | n/a | n/a |
| reasoning | semantic_entropy | n/a | 0/0 | n/a | n/a |
| reasoning | semantic_entropy_normalized | n/a | 0/0 | n/a | n/a |
| all | lexical_uncertainty | 0.8375 | 10/16 | 0.7912 | 0.5391 |
| all | semantic_entropy | 0.7250 | 10/16 | 1.0445 | 0.6298 |
| all | semantic_entropy_normalized | 0.7250 | 10/16 | 0.649 | 0.3913 |
