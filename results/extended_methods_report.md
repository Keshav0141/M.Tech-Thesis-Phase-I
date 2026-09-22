# AUROC Report - uncertainty vs. incorrect answers

_Generated 2026-09-22 21:58 UTC (full dataset: 450 questions x 5 samples)._

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
| factual | bigram_jaccard | 0.8397 | 50/100 | 0.8095 | 0.5157 |
| factual | trigram_jaccard | 0.8502 | 50/100 | 0.8772 | 0.5877 |
| factual | tfidf_cosine | 0.9108 | 50/100 | 0.6549 | 0.2265 |
| factual | unigram_jaccard | 0.8345 | 50/100 | 0.7081 | 0.4122 |
| factual | semantic_entropy | 0.6560 | 50/100 | 0.9171 | 0.6096 |
| factual | semantic_entropy_normalized | 0.6560 | 50/100 | 0.5698 | 0.3788 |
| factual | num_sets | 0.6734 | 50/100 | 3.06 | 2.25 |
| factual | degree_matrix | 0.2826 | 50/100 | 5.2 | 9.98 |
| factual | eigv | 0.2826 | 50/100 | 5.2 | 9.98 |
| factual | eccentricity | 0.5059 | 50/100 | 1.18 | 1.18 |
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
| all | bigram_jaccard | 0.8200 | 98/352 | 0.8125 | 0.5879 |
| all | trigram_jaccard | 0.8188 | 98/352 | 0.8812 | 0.6784 |
| all | tfidf_cosine | 0.8474 | 98/352 | 0.5758 | 0.2445 |
| all | unigram_jaccard | 0.8254 | 98/352 | 0.6673 | 0.4115 |
| all | semantic_entropy | 0.7036 | 98/352 | 1.0681 | 0.6326 |
| all | semantic_entropy_normalized | 0.7036 | 98/352 | 0.6637 | 0.393 |
| all | num_sets | 0.7079 | 98/352 | 3.4592 | 2.3835 |
| all | degree_matrix | 0.2676 | 98/352 | 3.9796 | 9.4148 |
| all | eigv | 0.2676 | 98/352 | 3.9796 | 9.4148 |
| all | eccentricity | 0.4163 | 98/352 | 1.0102 | 1.2557 |
| all | numeric_disagreement | 0.6487 | 6/144 | 0.2 | 0.0139 |
