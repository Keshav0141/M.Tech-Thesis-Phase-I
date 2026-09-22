# Ensemble UQ Report

_Generated 2026-09-14. Labels: majority-vote incorrect vs correct (unresolved questions excluded). Scores rank-normalized per category before averaging; weighted variants use logistic regression with 5-fold stratified CV (5 folds, seed 42), reported on out-of-fold predictions only._

Questions in evaluation: **450**

| Method | AUROC all | factual | math | reasoning |
|---|---:|---:|---:|---:|
| tfidf (baseline) | 0.8474 | 0.9108 | 0.7558 | 0.6299 |
| bigram (baseline) | 0.8200 | 0.8397 | 0.8171 | 0.6772 |
| trigram (baseline) | 0.8188 | 0.8502 | 0.8137 | 0.6728 |
| unigram (baseline) | 0.8254 | 0.8345 | 0.8449 | 0.6453 |
| semantic (baseline) | 0.7036 | 0.6560 | 0.5150 | 0.6332 |
| ensemble unweighted-5 | 0.7532 | 0.8601 | 0.8021 | 0.6786 |
| ensemble weighted-5 (5-fold CV) | 0.7471 | 0.8700 | 0.7824 | 0.6614 |
| ensemble unweighted-3 | 0.7571 | 0.8810 | 0.8079 | 0.6679 |
| ensemble weighted-3 (5-fold CV) | 0.7524 | 0.8822 | 0.8044 | 0.6554 |

## Verdict

- No ensemble variant beats TF-IDF alone (0.8474); best ensemble is ensemble unweighted-3 at 0.7571.
- Per category: factual: tfidf 0.9108 vs best ensemble 0.8822; math: tfidf 0.7558 vs best ensemble 0.8079; reasoning: tfidf 0.6299 vs best ensemble 0.6786.
