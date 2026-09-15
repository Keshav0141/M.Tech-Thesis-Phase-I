# Ensemble UQ Report

_Generated 2026-09-14. Labels: majority-vote incorrect vs correct (unresolved questions excluded). Scores rank-normalized per category before averaging; weighted variants use logistic regression with 5-fold stratified CV (5 folds, seed 42), reported on out-of-fold predictions only._

Questions in evaluation: **433**

| Method | AUROC all | factual | math | reasoning |
|---|---:|---:|---:|---:|
| tfidf (baseline) | 0.8449 | 0.9093 | 0.7558 | 0.6299 |
| bigram (baseline) | 0.8195 | 0.8398 | 0.8171 | 0.6772 |
| trigram (baseline) | 0.8168 | 0.8478 | 0.8137 | 0.6728 |
| unigram (baseline) | 0.8247 | 0.8350 | 0.8449 | 0.6453 |
| semantic (baseline) | 0.7063 | 0.6588 | 0.5150 | 0.6332 |
| ensemble unweighted-5 | 0.7469 | 0.8587 | 0.8021 | 0.6786 |
| ensemble weighted-5 (5-fold CV) | 0.7447 | 0.8698 | 0.7986 | 0.6647 |
| ensemble unweighted-3 | 0.7514 | 0.8822 | 0.8079 | 0.6679 |
| ensemble weighted-3 (5-fold CV) | 0.7482 | 0.8841 | 0.8137 | 0.6574 |

## Verdict

- No ensemble variant beats TF-IDF alone (0.8449); best ensemble is ensemble unweighted-3 at 0.7514.
- Per category: factual: tfidf 0.9093 vs best ensemble 0.8841; math: tfidf 0.7558 vs best ensemble 0.8137; reasoning: tfidf 0.6299 vs best ensemble 0.6786.
