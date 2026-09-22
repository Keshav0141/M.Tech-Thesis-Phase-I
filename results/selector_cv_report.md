# Cross-validated per-category method selector

_Generated 2026-09-14. 5-fold stratified CV (seed 42) per category; the winner is chosen on the training split only, then evaluated on the held-out fold. n = 450 labeled questions._

## Per-category fold log (winner stability)

### factual (n=150, incorrect=50)

| fold | winner | winner train AUC | winner held-out AUC | runner-up note |
|---|---|---|---:|---|
| 1 | tfidf | 0.9369 | 0.81 | tfidf 0.937, trigram 0.862, bigram 0.848 |
| 2 | tfidf | 0.9025 | 0.95 | tfidf 0.902, trigram 0.851, bigram 0.840 |
| 3 | tfidf | 0.9034 | 0.94 | tfidf 0.903, trigram 0.843, bigram 0.834 |
| 4 | tfidf | 0.91 | 0.91 | tfidf 0.910, trigram 0.855, bigram 0.851 |
| 5 | tfidf | 0.9006 | 0.935 | tfidf 0.901, trigram 0.842, bigram 0.828 |

Selector CV AUROC (factual): **0.909**

### math (n=150, incorrect=6)

| fold | winner | winner train AUC | winner held-out AUC | runner-up note |
|---|---|---|---:|---|
| 1 | unigram | 0.8557 | 0.8276 | unigram 0.856, trigram 0.842, bigram 0.838 |
| 2 | unigram | 0.8504 | 0.931 | unigram 0.850, trigram 0.807, bigram 0.798 |
| 3 | unigram | 0.8157 | 0.9655 | unigram 0.816, bigram 0.786, trigram 0.779 |
| 4 | unigram | 0.873 | 0.6897 | unigram 0.873, bigram 0.828, trigram 0.823 |
| 5 | bigram | 0.8341 | 0.7679 | bigram 0.834, unigram 0.832, trigram 0.821 |

Selector CV AUROC (math): **0.8363**

### reasoning (n=150, incorrect=42)

| fold | winner | winner train AUC | winner held-out AUC | runner-up note |
|---|---|---|---:|---|
| 1 | bigram | 0.6768 | 0.6508 | bigram 0.677, trigram 0.665, numsets 0.656 |
| 2 | trigram | 0.6628 | 0.709 | trigram 0.663, bigram 0.662, tfidf 0.631 |
| 3 | bigram | 0.6601 | 0.7386 | bigram 0.660, trigram 0.658, unigram 0.636 |
| 4 | bigram | 0.7127 | 0.5682 | bigram 0.713, trigram 0.712, semantic 0.671 |
| 5 | bigram | 0.6737 | 0.6705 | bigram 0.674, trigram 0.666, unigram 0.657 |

Selector CV AUROC (reasoning): **0.6674**

## Same-fold CV AUROC for every single method (identical protocol)

| Method | factual | math | reasoning |
|---|---:|---:|---:|
| tfidf | 0.9090 | 0.7395 | 0.6289 |
| unigram | 0.8380 | 0.8578 | 0.6334 |
| bigram | 0.8490 | 0.8087 | 0.6738 |
| trigram | 0.8505 | 0.8195 | 0.6716 |
| semantic | 0.6580 | 0.5538 | 0.6225 |
| numsets | 0.6765 | 0.5573 | 0.6248 |
| degree | 0.2810 | 0.2675 | 0.3703 |
| eigv | 0.2810 | 0.2675 | 0.3703 |
| eccentricity | 0.5035 | 0.7038 | 0.3956 |

## Aggregate selector numbers

- Macro-average of per-category selector CV AUCs: **0.8042**
- Pooled OOF AUROC (ranks within category, then pooled across categories): **0.7671** (98 incorrect / 352 correct)

## Comparison with previous baselines (full-data protocol)

| Method | AUROC all | factual | math | reasoning |
|---|---:|---:|---:|---:|
| TF-IDF alone (full-data) | 0.8474 | 0.9108 | 0.7558 | 0.6299 |
| ensemble unweighted-3 (full-data) | 0.7571 | 0.8810 | 0.8079 | 0.6679 |
| CV selector (macro-avg) | 0.8042 | 0.909 | 0.8363 | 0.6674 |
| CV selector (pooled OOF rank) | 0.7671 | - | - | - |

## Verdict

- Selection is **stable**: factual picks tfidf 5/5 folds; math picks unigram 4/5 (one bigram flip); reasoning picks bigram 4/5 (one trigram flip).
- Under the identical CV protocol the selector beats TF-IDF on **math (0.8363 vs 0.7395)** and **reasoning (0.6674 vs 0.6289)**, and ties on factual (0.909 vs 0.9090).
- Macro-average over categories: selector **0.8042** vs TF-IDF 0.7591 (+0.0451).
- Pooled OOF-rank aggregate: **0.7671** -- does NOT beat the full-data TF-IDF headline (0.8474), but that headline is in-sample; TF-IDF's own CV macro (0.7591) is the comparable number, and the selector's pooling gains vanish because per-category ranking discards TF-IDF's cross-category scale advantage on factual, where most errors are.
- Math caution: with only 6 incorrect questions, held-out fold AUCs swing 0.69-0.97; the category's selection is indicative, not conclusive.
