# AUROC Report - uncertainty vs. incorrect answers

_Generated 2026-09-15 07:48 UTC (full dataset: 450 questions x 5 samples)._

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
| factual | bigram_jaccard | 0.8398 | 46/87 | 0.8113 | 0.5307 |
| factual | trigram_jaccard | 0.8478 | 46/87 | 0.8763 | 0.601 |
| factual | tfidf_cosine | 0.9093 | 46/87 | 0.6573 | 0.2346 |
| factual | unigram_jaccard | 0.8350 | 46/87 | 0.7122 | 0.4257 |
| factual | semantic_entropy | 0.6588 | 46/87 | 0.9255 | 0.6136 |
| factual | semantic_entropy_normalized | 0.6588 | 46/87 | 0.575 | 0.3812 |
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
| all | bigram_jaccard | 0.8195 | 94/339 | 0.8135 | 0.5945 |
| all | trigram_jaccard | 0.8168 | 94/339 | 0.881 | 0.6853 |
| all | tfidf_cosine | 0.8449 | 94/339 | 0.5737 | 0.2473 |
| all | unigram_jaccard | 0.8247 | 94/339 | 0.6676 | 0.4149 |
| all | semantic_entropy | 0.7063 | 94/339 | 1.0786 | 0.6344 |
| all | semantic_entropy_normalized | 0.7063 | 94/339 | 0.6702 | 0.3942 |
