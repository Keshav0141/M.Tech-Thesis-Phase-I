# 7B AUROC Report (Qwen2.5-7B-Instruct, isolated)

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
| factual | tfidf_cosine | 0.8175 | 67/68 |
| factual | unigram_jaccard | 0.8154 | 67/68 |
| factual | bigram_jaccard | 0.8155 | 67/68 |
| factual | trigram_jaccard | 0.8107 | 67/68 |
| math | tfidf_cosine | 0.6993 | 7/143 |
| math | unigram_jaccard | 0.7732 | 7/143 |
| math | bigram_jaccard | 0.7772 | 7/143 |
| math | trigram_jaccard | 0.7842 | 7/143 |
| reasoning | tfidf_cosine | 0.5827 | 44/106 |
| reasoning | unigram_jaccard | 0.5827 | 44/106 |
| reasoning | bigram_jaccard | 0.6032 | 44/106 |
| reasoning | trigram_jaccard | 0.6062 | 44/106 |
| all | tfidf_cosine | 0.7129 | 118/317 |
| all | unigram_jaccard | 0.6954 | 118/317 |
| all | bigram_jaccard | 0.6439 | 118/317 |
| all | trigram_jaccard | 0.5978 | 118/317 |
