# AUROC Report - uncertainty vs. incorrect answers

_Generated 2026-09-16 12:31 UTC (full dataset: 450 questions x 5 samples)._

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
| factual | num_sets | 0.6728 | 46/87 | 3.087 | 2.2644 |
| factual | degree_matrix | 0.2796 | 46/87 | 5.1304 | 9.908 |
| factual | eigv | 0.2796 | 46/87 | 5.1304 | 9.908 |
| factual | eccentricity | 0.4959 | 46/87 | 1.1522 | 1.1724 |
| factual | numeric_disagreement | n/a | 0/0 | n/a | n/a |
| math | bigram_jaccard | 0.8171 | 6/144 | 0.6584 | 0.5023 |
| math | trigram_jaccard | 0.8137 | 6/144 | 0.7593 | 0.6137 |
| math | tfidf_cosine | 0.7558 | 6/144 | 0.1423 | 0.0845 |
| math | unigram_jaccard | 0.8449 | 6/144 | 0.4243 | 0.2808 |
| math | semantic_entropy | 0.5150 | 6/144 | 0.3804 | 0.293 |
| math | semantic_entropy_normalized | 0.5150 | 6/144 | 0.2364 | 0.1821 |
| math | num_sets | 0.5168 | 6/144 | 1.8333 | 1.6111 |
| math | degree_matrix | 0.3177 | 6/144 | 9.3333 | 13.3056 |
| math | eigv | 0.3177 | 6/144 | 9.3333 | 13.3056 |
| math | eccentricity | 0.6655 | 6/144 | 2.0 | 1.4931 |
| math | numeric_disagreement | 0.6487 | 6/144 | 0.2 | 0.0139 |
| reasoning | bigram_jaccard | 0.6772 | 42/108 | 0.838 | 0.7689 |
| reasoning | trigram_jaccard | 0.6728 | 42/108 | 0.9035 | 0.8487 |
| reasoning | tfidf_cosine | 0.6299 | 42/108 | 0.5436 | 0.4745 |
| reasoning | unigram_jaccard | 0.6453 | 42/108 | 0.6535 | 0.5852 |
| reasoning | semantic_entropy | 0.6332 | 42/108 | 1.3461 | 1.1065 |
| reasoning | semantic_entropy_normalized | 0.6332 | 42/108 | 0.8364 | 0.6875 |
| reasoning | num_sets | 0.6334 | 42/108 | 4.1667 | 3.537 |
| reasoning | degree_matrix | 0.3617 | 42/108 | 1.7619 | 3.7037 |
| reasoning | eigv | 0.3617 | 42/108 | 1.7619 | 3.7037 |
| reasoning | eccentricity | 0.3920 | 42/108 | 0.6667 | 1.0093 |
| reasoning | numeric_disagreement | n/a | 0/0 | n/a | n/a |
| all | bigram_jaccard | 0.8195 | 94/339 | 0.8135 | 0.5945 |
| all | trigram_jaccard | 0.8168 | 94/339 | 0.881 | 0.6853 |
| all | tfidf_cosine | 0.8449 | 94/339 | 0.5737 | 0.2473 |
| all | unigram_jaccard | 0.8247 | 94/339 | 0.6676 | 0.4149 |
| all | semantic_entropy | 0.7063 | 94/339 | 1.0786 | 0.6344 |
| all | semantic_entropy_normalized | 0.7063 | 94/339 | 0.6702 | 0.3942 |
| all | num_sets | 0.7096 | 94/339 | 3.4894 | 2.3923 |
| all | degree_matrix | 0.2650 | 94/339 | 3.8936 | 9.3746 |
| all | eigv | 0.2650 | 94/339 | 3.8936 | 9.3746 |
| all | eccentricity | 0.4084 | 94/339 | 0.9894 | 1.2566 |
| all | numeric_disagreement | 0.6487 | 6/144 | 0.2 | 0.0139 |
