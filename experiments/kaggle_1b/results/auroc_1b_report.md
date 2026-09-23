# 1B AUROC Report (Qwen2.5-1.5B-Instruct, isolated)

Label: majority-vote incorrect (1) vs correct (0); unresolved excluded.

## Coverage

| Category | Dataset | Scored |
|---|---:|---:|
| factual | 150 | 150 |
| math | 150 | 150 |
| reasoning | 150 | 150 |

## AUROC

| Category | Method | AUROC | incorrect/correct |
|---|---|---:|---|
| factual | tfidf_cosine | 0.8390 | 106/29 |
| factual | unigram_jaccard | 0.8414 | 106/29 |
| factual | bigram_jaccard | 0.8452 | 106/29 |
| factual | trigram_jaccard | 0.8487 | 106/29 |
| math | tfidf_cosine | 0.6291 | 28/122 |
| math | unigram_jaccard | 0.6127 | 28/122 |
| math | bigram_jaccard | 0.6259 | 28/122 |
| math | trigram_jaccard | 0.6303 | 28/122 |
| reasoning | tfidf_cosine | 0.5123 | 59/91 |
| reasoning | unigram_jaccard | 0.5373 | 59/91 |
| reasoning | bigram_jaccard | 0.5243 | 59/91 |
| reasoning | trigram_jaccard | 0.5289 | 59/91 |
| all | tfidf_cosine | 0.6682 | 193/242 |
| all | unigram_jaccard | 0.6345 | 193/242 |
| all | bigram_jaccard | 0.5814 | 193/242 |
| all | trigram_jaccard | 0.5440 | 193/242 |
