# AUROC Report - uncertainty vs. incorrect answers

_Generated 2026-09-14 19:42 UTC (full dataset: 450 questions x 5 samples)._

Label: majority-vote incorrect (1) vs correct (0); unresolved/no-sample questions are excluded.
AUROC > 0.5 means the uncertainty score is higher on incorrect answers.

## Coverage

| Category | Dataset questions | Scored | With semantic entropy |
|---|---:|---:|---:|
| factual | 150 | 150 | 150 |
| math | 150 | 150 | 150 |
| reasoning | 150 | 150 | 150 |

## Results

| Category | Method | AUROC | incorrect/correct | mean score (incorrect) | mean score (correct) |
|---|---|---:|---|---:|---:|
| factual | bigram_jaccard | 0.8125 | 48/85 | 0.7918 | 0.5351 |
| factual | trigram_jaccard | 0.8199 | 48/85 | 0.8572 | 0.6053 |
| factual | tfidf_cosine | 0.8841 | 48/85 | 0.6351 | 0.2372 |
| factual | unigram_jaccard | 0.8077 | 48/85 | 0.6928 | 0.4299 |
| factual | semantic_entropy | 0.6385 | 48/85 | 0.8974 | 0.6221 |
| factual | semantic_entropy_normalized | 0.6385 | 48/85 | 0.5576 | 0.3865 |
| math | bigram_jaccard | 0.8171 | 6/144 | 0.6584 | 0.5023 |
| math | trigram_jaccard | 0.8137 | 6/144 | 0.7593 | 0.6137 |
| math | tfidf_cosine | 0.7558 | 6/144 | 0.1423 | 0.0845 |
| math | unigram_jaccard | 0.8449 | 6/144 | 0.4243 | 0.2808 |
| math | semantic_entropy | 0.5150 | 6/144 | 0.3804 | 0.293 |
| math | semantic_entropy_normalized | 0.5150 | 6/144 | 0.2364 | 0.1821 |
| reasoning | bigram_jaccard | 0.6772 | 42/108 | 0.838 | 0.7689 |
| reasoning | trigram_jaccard | 0.6728 | 42/108 | 0.9035 | 0.8487 |
| reasoning | tfidf_cosine | 0.6299 | 42/108 | 0.5436 | 0.4745 |
| reasoning | unigram_jaccard | 0.6453 | 42/108 | 0.6535 | 0.5852 |
| reasoning | semantic_entropy | 0.6332 | 42/108 | 1.3461 | 1.1065 |
| reasoning | semantic_entropy_normalized | 0.6332 | 42/108 | 0.8364 | 0.6875 |
| all | bigram_jaccard | 0.8041 | 96/337 | 0.8037 | 0.596 |
| all | trigram_jaccard | 0.8011 | 96/337 | 0.8713 | 0.6869 |
| all | tfidf_cosine | 0.8352 | 96/337 | 0.5643 | 0.248 |
| all | unigram_jaccard | 0.8121 | 96/337 | 0.6588 | 0.4159 |
| all | semantic_entropy | 0.6973 | 96/337 | 1.0614 | 0.6367 |
| all | semantic_entropy_normalized | 0.6973 | 96/337 | 0.6595 | 0.3956 |
