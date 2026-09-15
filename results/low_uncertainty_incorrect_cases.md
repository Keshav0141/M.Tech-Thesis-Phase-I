# Low-uncertainty incorrect cases (confidently wrong)

_Generated 2026-09-14. Definition: majority vote = incorrect AND (bigram Jaccard uncertainty < 0.4 OR trigram < 0.5)._

Total cases: **2**

| question_id | category | bigram | trigram | n_wrong/5 | pattern | GT | model answer(s) | review |
|---|---|---|---:|---:|---|---|---|---|
| factual_0059 | factual | 0.267 | 0.400 | 4/5 | 4/5 samples same wrong answer | Robin | Nightwing / Robin | no |
| factual_0081 | factual | 0.300 | 0.400 | 5/5 | 4/5 samples same wrong answer | Charlie Brown | Snoopy / Peppermint Patty | no |

## Pattern summary by category

| category | cases | common pattern |
|---|---:|---|
| factual | 2 | 4/5 samples same wrong answer (x2) |
