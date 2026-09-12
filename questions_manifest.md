# Questions Manifest

_Living document. Last regenerated: 2026-09-12 04:23 UTC (seed 42, target 150/category)._

## Dataset summary

Total active questions: **450** — factual: 150, math: 150, reasoning: 150

3 entries are retained in data/dataset.json with status `rejected` (manual spot-check findings) and are excluded from generation and validation counts.

| Category | Source | Inspected | Accepted | Rejected | Target met |
|---|---|---:|---:|---:|:---:|
| factual | TriviaQA (rc.nocontext) | 883 | 150 | 333 | yes |
| math | GSM8K (main) | 557 | 150 | 7 | yes |
| reasoning | StrategyQA | 550 | 150 | 0 | yes |

## Difficulty distribution (heuristic proxy)

| Category | easy | medium | hard |
|---|---:|---:|---:|
| factual | 49 | 64 | 37 |
| math | 57 | 71 | 22 |
| reasoning | 85 | 62 | 3 |

Difficulty flags are deterministic heuristics, not gold labels: factual = question word count (<=10 / <=16 / more), math = number of calculator steps in the solution (<=2 / <=4 / more), reasoning = number of supporting facts in the evidence (<=2 / <=4 / more).

## Validation criteria applied

- **Factual**: single unambiguous answer, verifiable from a Wikipedia entity, not time-sensitive, no multi-answer prompts.
- **Mathematical**: exactly one numeric final answer after the `####` marker, no multi-part questions, no unit ambiguity.
- **Reasoning**: multi-step inference, clear binary (yes/no) final answer, no arithmetic-heavy items (math overlap).

All questions were additionally required to be unique (exact and near-duplicate check at sequence ratio >= 0.90 across all categories).

## Excluded examples

Selected dropped candidates (full reasons in data/excluded_examples.json):

1. **factual_0037** (factual) — `December 12, 2003 saw the death of Keiko, an Orca whale, off the coast of Finland. Keiko achieved fame as a star in what movie series?`
   - Reason: manual spot-check: source question contains a factual error — Keiko the orca died in Taknes Bay, Halsa (Norway), not off the coast of Finland
2. **factual_0025** (factual) — `Who made his film debut playing Kasper Gutman in the 1941 film ‘Casablanca’?`
   - Reason: manual spot-check: source question conflates two films — Kasper Gutman is a character from The Maltese Falcon (1941), not Casablanca (1942)
3. **factual** — `In 2006, Michelle Bachelet became the first female president of which country?`
   - Reason: ambiguous answer (aliases refer to different answers)
4. **factual** — `Which post-war Prime Minister was MP for Warwick and Leamington?`
   - Reason: exact duplicate of factual_0035
5. **factual** — `This couple were iconic dance partners who made motion pictures together from 1933 - 1949. They made a total of 10 movies?`
   - Reason: answer too long to be atomic

Aggregate rejection counts by category:

- **factual**: 333 rejected
  - 323x ambiguous answer (aliases refer to different answers)
  - 4x question length outside 20-220 chars
  - 3x multiple questions in one item
  - 2x answer too long to be atomic
  - 1x exact duplicate of factual_0035
- **math**: 7 rejected
  - 6x question length outside 20-400 chars
  - 1x multiple questions in one item
- **reasoning**: 0 rejected

Manual spot-check rejections (source-data errors, not filtering misses):

- **factual_0037**: manual spot-check: source question contains a factual error — Keiko the orca died in Taknes Bay, Halsa (Norway), not off the coast of Finland
- **factual_0025**: manual spot-check: source question conflates two films — Kasper Gutman is a character from The Maltese Falcon (1941), not Casablanca (1942)

## Overlap / MECE note

The three categories are defined as: factual = single-hop lookup from parametric knowledge; mathematical = numeric computation on a word problem; reasoning = multi-hop logical inference over stated or world facts.
No inspected StrategyQA candidate reduced to arithmetic, so no mathematical-overlap item was dropped in this build; the filter still runs at build time.

## Rejected entries (excluded from generation)

| question_id | reason |
|---|---|
| factual_0025 | manual spot-check: source question conflates two films — Kasper Gutman is a character from The Maltese Falcon (1941), not Casablanca (1942) |
| factual_0037 | manual spot-check: source question contains a factual error — Keiko the orca died in Taknes Bay, Halsa (Norway), not off the coast of Finland |
| factual_0152 | curation guard: time-sensitive wording ('recent London summer Olympics'); auto-replacement rejected during curation |

## Per-question metadata

| question_id | category | source | difficulty | status | words |
|---|---|---|---|---|---:|
| factual_0001 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0002 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0003 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0004 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0005 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 29 |
| factual_0006 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0007 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0008 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0009 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 23 |
| factual_0010 | factual | TriviaQA (rc.nocontext) | easy | spot_checked | 6 |
| factual_0011 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0012 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0013 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0014 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0015 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0016 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0017 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0018 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0019 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 17 |
| factual_0020 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 20 |
| factual_0021 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0022 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0023 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 17 |
| factual_0024 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0025 | factual | TriviaQA (rc.nocontext) | medium | rejected | 13 |
| factual_0026 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0027 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0028 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0029 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0030 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0031 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 23 |
| factual_0032 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0033 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0034 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0035 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0036 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 33 |
| factual_0037 | factual | TriviaQA (rc.nocontext) | hard | rejected | 26 |
| factual_0038 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0039 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 24 |
| factual_0040 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 32 |
| factual_0041 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0042 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0043 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 22 |
| factual_0044 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0045 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0046 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 32 |
| factual_0047 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0048 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0049 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0050 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0051 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0052 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 29 |
| factual_0053 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0054 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0055 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0056 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0057 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0058 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0059 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0060 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0061 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0062 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 22 |
| factual_0063 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0064 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0065 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0066 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 22 |
| factual_0067 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0068 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0069 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0070 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 20 |
| factual_0071 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0072 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 23 |
| factual_0073 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0074 | factual | TriviaQA (rc.nocontext) | medium | spot_checked | 14 |
| factual_0075 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0076 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0077 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0078 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0079 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 17 |
| factual_0080 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0081 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0082 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0083 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0084 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0085 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 26 |
| factual_0086 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0087 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0088 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 26 |
| factual_0089 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0090 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0091 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0092 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0093 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0094 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0095 | factual | TriviaQA (rc.nocontext) | hard | spot_checked | 21 |
| factual_0096 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 32 |
| factual_0097 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0098 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0099 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0100 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 22 |
| factual_0101 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0102 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0103 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 15 |
| factual_0104 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0105 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0106 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0107 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0108 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0109 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0110 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0111 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0112 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 22 |
| factual_0113 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 20 |
| factual_0114 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0115 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0116 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0117 | factual | TriviaQA (rc.nocontext) | medium | spot_checked | 16 |
| factual_0118 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0119 | factual | TriviaQA (rc.nocontext) | easy | spot_checked | 8 |
| factual_0120 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0121 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0122 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0123 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0124 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 29 |
| factual_0125 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 20 |
| factual_0126 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0127 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 13 |
| factual_0128 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 24 |
| factual_0129 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 26 |
| factual_0130 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 9 |
| factual_0131 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 18 |
| factual_0132 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0133 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 5 |
| factual_0134 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 17 |
| factual_0135 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 8 |
| factual_0136 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 10 |
| factual_0137 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0138 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 6 |
| factual_0139 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0140 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0141 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 20 |
| factual_0142 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0143 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 16 |
| factual_0144 | factual | TriviaQA (rc.nocontext) | easy | auto_validated | 7 |
| factual_0145 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0146 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0147 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| factual_0148 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 12 |
| factual_0149 | factual | TriviaQA (rc.nocontext) | hard | auto_validated | 23 |
| factual_0150 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0151 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 14 |
| factual_0152 | factual | TriviaQA (rc.nocontext) | medium | rejected | 15 |
| factual_0153 | factual | TriviaQA (rc.nocontext) | medium | auto_validated | 11 |
| math_0001 | math | GSM8K (main) | medium | auto_validated | 48 |
| math_0002 | math | GSM8K (main) | easy | auto_validated | 36 |
| math_0003 | math | GSM8K (main) | medium | auto_validated | 29 |
| math_0004 | math | GSM8K (main) | hard | auto_validated | 55 |
| math_0005 | math | GSM8K (main) | easy | spot_checked | 33 |
| math_0006 | math | GSM8K (main) | easy | auto_validated | 24 |
| math_0007 | math | GSM8K (main) | easy | auto_validated | 27 |
| math_0008 | math | GSM8K (main) | hard | auto_validated | 59 |
| math_0009 | math | GSM8K (main) | easy | auto_validated | 58 |
| math_0010 | math | GSM8K (main) | easy | auto_validated | 28 |
| math_0011 | math | GSM8K (main) | medium | auto_validated | 49 |
| math_0012 | math | GSM8K (main) | easy | auto_validated | 41 |
| math_0013 | math | GSM8K (main) | easy | auto_validated | 18 |
| math_0014 | math | GSM8K (main) | hard | auto_validated | 47 |
| math_0015 | math | GSM8K (main) | hard | auto_validated | 62 |
| math_0016 | math | GSM8K (main) | medium | auto_validated | 45 |
| math_0017 | math | GSM8K (main) | medium | auto_validated | 64 |
| math_0018 | math | GSM8K (main) | medium | auto_validated | 54 |
| math_0019 | math | GSM8K (main) | easy | auto_validated | 61 |
| math_0020 | math | GSM8K (main) | easy | auto_validated | 41 |
| math_0021 | math | GSM8K (main) | medium | auto_validated | 62 |
| math_0022 | math | GSM8K (main) | medium | auto_validated | 35 |
| math_0023 | math | GSM8K (main) | medium | auto_validated | 30 |
| math_0024 | math | GSM8K (main) | easy | auto_validated | 26 |
| math_0025 | math | GSM8K (main) | easy | auto_validated | 34 |
| math_0026 | math | GSM8K (main) | easy | auto_validated | 47 |
| math_0027 | math | GSM8K (main) | easy | auto_validated | 70 |
| math_0028 | math | GSM8K (main) | easy | auto_validated | 48 |
| math_0029 | math | GSM8K (main) | easy | auto_validated | 35 |
| math_0030 | math | GSM8K (main) | medium | auto_validated | 37 |
| math_0031 | math | GSM8K (main) | easy | auto_validated | 25 |
| math_0032 | math | GSM8K (main) | easy | auto_validated | 32 |
| math_0033 | math | GSM8K (main) | medium | auto_validated | 29 |
| math_0034 | math | GSM8K (main) | medium | auto_validated | 24 |
| math_0035 | math | GSM8K (main) | hard | auto_validated | 36 |
| math_0036 | math | GSM8K (main) | hard | auto_validated | 40 |
| math_0037 | math | GSM8K (main) | hard | auto_validated | 72 |
| math_0038 | math | GSM8K (main) | medium | auto_validated | 28 |
| math_0039 | math | GSM8K (main) | medium | auto_validated | 51 |
| math_0040 | math | GSM8K (main) | easy | auto_validated | 66 |
| math_0041 | math | GSM8K (main) | medium | auto_validated | 40 |
| math_0042 | math | GSM8K (main) | hard | auto_validated | 43 |
| math_0043 | math | GSM8K (main) | medium | auto_validated | 56 |
| math_0044 | math | GSM8K (main) | easy | auto_validated | 68 |
| math_0045 | math | GSM8K (main) | easy | auto_validated | 38 |
| math_0046 | math | GSM8K (main) | easy | auto_validated | 27 |
| math_0047 | math | GSM8K (main) | medium | auto_validated | 52 |
| math_0048 | math | GSM8K (main) | easy | auto_validated | 42 |
| math_0049 | math | GSM8K (main) | medium | auto_validated | 38 |
| math_0050 | math | GSM8K (main) | medium | auto_validated | 63 |
| math_0051 | math | GSM8K (main) | medium | auto_validated | 44 |
| math_0052 | math | GSM8K (main) | easy | auto_validated | 30 |
| math_0053 | math | GSM8K (main) | hard | auto_validated | 55 |
| math_0054 | math | GSM8K (main) | medium | auto_validated | 63 |
| math_0055 | math | GSM8K (main) | easy | auto_validated | 34 |
| math_0056 | math | GSM8K (main) | medium | auto_validated | 42 |
| math_0057 | math | GSM8K (main) | easy | auto_validated | 36 |
| math_0058 | math | GSM8K (main) | medium | auto_validated | 55 |
| math_0059 | math | GSM8K (main) | easy | auto_validated | 38 |
| math_0060 | math | GSM8K (main) | easy | auto_validated | 53 |
| math_0061 | math | GSM8K (main) | medium | auto_validated | 51 |
| math_0062 | math | GSM8K (main) | hard | auto_validated | 57 |
| math_0063 | math | GSM8K (main) | medium | auto_validated | 58 |
| math_0064 | math | GSM8K (main) | medium | auto_validated | 39 |
| math_0065 | math | GSM8K (main) | medium | auto_validated | 28 |
| math_0066 | math | GSM8K (main) | medium | auto_validated | 54 |
| math_0067 | math | GSM8K (main) | medium | auto_validated | 33 |
| math_0068 | math | GSM8K (main) | medium | auto_validated | 65 |
| math_0069 | math | GSM8K (main) | medium | auto_validated | 37 |
| math_0070 | math | GSM8K (main) | medium | auto_validated | 36 |
| math_0071 | math | GSM8K (main) | hard | auto_validated | 28 |
| math_0072 | math | GSM8K (main) | easy | auto_validated | 38 |
| math_0073 | math | GSM8K (main) | easy | auto_validated | 46 |
| math_0074 | math | GSM8K (main) | medium | auto_validated | 38 |
| math_0075 | math | GSM8K (main) | medium | auto_validated | 40 |
| math_0076 | math | GSM8K (main) | easy | auto_validated | 45 |
| math_0077 | math | GSM8K (main) | medium | auto_validated | 38 |
| math_0078 | math | GSM8K (main) | easy | auto_validated | 35 |
| math_0079 | math | GSM8K (main) | hard | auto_validated | 29 |
| math_0080 | math | GSM8K (main) | easy | auto_validated | 33 |
| math_0081 | math | GSM8K (main) | hard | auto_validated | 57 |
| math_0082 | math | GSM8K (main) | medium | auto_validated | 67 |
| math_0083 | math | GSM8K (main) | easy | auto_validated | 24 |
| math_0084 | math | GSM8K (main) | easy | auto_validated | 28 |
| math_0085 | math | GSM8K (main) | hard | auto_validated | 47 |
| math_0086 | math | GSM8K (main) | medium | auto_validated | 49 |
| math_0087 | math | GSM8K (main) | medium | auto_validated | 42 |
| math_0088 | math | GSM8K (main) | easy | auto_validated | 35 |
| math_0089 | math | GSM8K (main) | hard | auto_validated | 61 |
| math_0090 | math | GSM8K (main) | medium | auto_validated | 39 |
| math_0091 | math | GSM8K (main) | easy | auto_validated | 32 |
| math_0092 | math | GSM8K (main) | hard | auto_validated | 34 |
| math_0093 | math | GSM8K (main) | medium | auto_validated | 54 |
| math_0094 | math | GSM8K (main) | easy | auto_validated | 18 |
| math_0095 | math | GSM8K (main) | hard | auto_validated | 62 |
| math_0096 | math | GSM8K (main) | medium | spot_checked | 33 |
| math_0097 | math | GSM8K (main) | hard | auto_validated | 53 |
| math_0098 | math | GSM8K (main) | hard | auto_validated | 75 |
| math_0099 | math | GSM8K (main) | medium | auto_validated | 37 |
| math_0100 | math | GSM8K (main) | medium | auto_validated | 50 |
| math_0101 | math | GSM8K (main) | medium | auto_validated | 49 |
| math_0102 | math | GSM8K (main) | medium | auto_validated | 34 |
| math_0103 | math | GSM8K (main) | easy | auto_validated | 40 |
| math_0104 | math | GSM8K (main) | easy | auto_validated | 27 |
| math_0105 | math | GSM8K (main) | easy | auto_validated | 23 |
| math_0106 | math | GSM8K (main) | medium | auto_validated | 54 |
| math_0107 | math | GSM8K (main) | medium | auto_validated | 20 |
| math_0108 | math | GSM8K (main) | medium | auto_validated | 54 |
| math_0109 | math | GSM8K (main) | medium | auto_validated | 45 |
| math_0110 | math | GSM8K (main) | easy | auto_validated | 46 |
| math_0111 | math | GSM8K (main) | medium | spot_checked | 58 |
| math_0112 | math | GSM8K (main) | easy | auto_validated | 39 |
| math_0113 | math | GSM8K (main) | medium | auto_validated | 61 |
| math_0114 | math | GSM8K (main) | medium | auto_validated | 78 |
| math_0115 | math | GSM8K (main) | easy | auto_validated | 19 |
| math_0116 | math | GSM8K (main) | medium | auto_validated | 39 |
| math_0117 | math | GSM8K (main) | medium | auto_validated | 26 |
| math_0118 | math | GSM8K (main) | medium | auto_validated | 46 |
| math_0119 | math | GSM8K (main) | easy | auto_validated | 31 |
| math_0120 | math | GSM8K (main) | medium | auto_validated | 43 |
| math_0121 | math | GSM8K (main) | hard | auto_validated | 70 |
| math_0122 | math | GSM8K (main) | easy | auto_validated | 45 |
| math_0123 | math | GSM8K (main) | hard | auto_validated | 53 |
| math_0124 | math | GSM8K (main) | easy | auto_validated | 25 |
| math_0125 | math | GSM8K (main) | easy | auto_validated | 38 |
| math_0126 | math | GSM8K (main) | easy | auto_validated | 38 |
| math_0127 | math | GSM8K (main) | medium | auto_validated | 26 |
| math_0128 | math | GSM8K (main) | easy | spot_checked | 37 |
| math_0129 | math | GSM8K (main) | easy | auto_validated | 30 |
| math_0130 | math | GSM8K (main) | easy | auto_validated | 16 |
| math_0131 | math | GSM8K (main) | easy | auto_validated | 24 |
| math_0132 | math | GSM8K (main) | medium | spot_checked | 51 |
| math_0133 | math | GSM8K (main) | medium | auto_validated | 72 |
| math_0134 | math | GSM8K (main) | medium | auto_validated | 50 |
| math_0135 | math | GSM8K (main) | medium | auto_validated | 55 |
| math_0136 | math | GSM8K (main) | easy | auto_validated | 32 |
| math_0137 | math | GSM8K (main) | easy | auto_validated | 36 |
| math_0138 | math | GSM8K (main) | medium | auto_validated | 33 |
| math_0139 | math | GSM8K (main) | medium | auto_validated | 67 |
| math_0140 | math | GSM8K (main) | medium | auto_validated | 34 |
| math_0141 | math | GSM8K (main) | medium | spot_checked | 46 |
| math_0142 | math | GSM8K (main) | easy | auto_validated | 32 |
| math_0143 | math | GSM8K (main) | hard | auto_validated | 38 |
| math_0144 | math | GSM8K (main) | easy | auto_validated | 23 |
| math_0145 | math | GSM8K (main) | medium | auto_validated | 61 |
| math_0146 | math | GSM8K (main) | medium | auto_validated | 48 |
| math_0147 | math | GSM8K (main) | medium | auto_validated | 68 |
| math_0148 | math | GSM8K (main) | medium | spot_checked | 36 |
| math_0149 | math | GSM8K (main) | medium | auto_validated | 24 |
| math_0150 | math | GSM8K (main) | medium | auto_validated | 42 |
| reasoning_0001 | reasoning | StrategyQA | medium | auto_validated | 15 |
| reasoning_0002 | reasoning | StrategyQA | medium | auto_validated | 14 |
| reasoning_0003 | reasoning | StrategyQA | easy | auto_validated | 16 |
| reasoning_0004 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0005 | reasoning | StrategyQA | easy | auto_validated | 15 |
| reasoning_0006 | reasoning | StrategyQA | medium | auto_validated | 10 |
| reasoning_0007 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0008 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0009 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0010 | reasoning | StrategyQA | hard | auto_validated | 10 |
| reasoning_0011 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0012 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0013 | reasoning | StrategyQA | medium | auto_validated | 6 |
| reasoning_0014 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0015 | reasoning | StrategyQA | medium | spot_checked | 7 |
| reasoning_0016 | reasoning | StrategyQA | medium | auto_validated | 4 |
| reasoning_0017 | reasoning | StrategyQA | hard | auto_validated | 8 |
| reasoning_0018 | reasoning | StrategyQA | medium | auto_validated | 7 |
| reasoning_0019 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0020 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0021 | reasoning | StrategyQA | medium | auto_validated | 6 |
| reasoning_0022 | reasoning | StrategyQA | easy | auto_validated | 14 |
| reasoning_0023 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0024 | reasoning | StrategyQA | easy | auto_validated | 4 |
| reasoning_0025 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0026 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0027 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0028 | reasoning | StrategyQA | medium | spot_checked | 8 |
| reasoning_0029 | reasoning | StrategyQA | easy | auto_validated | 4 |
| reasoning_0030 | reasoning | StrategyQA | easy | auto_validated | 4 |
| reasoning_0031 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0032 | reasoning | StrategyQA | medium | spot_checked | 7 |
| reasoning_0033 | reasoning | StrategyQA | easy | auto_validated | 5 |
| reasoning_0034 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0035 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0036 | reasoning | StrategyQA | medium | auto_validated | 10 |
| reasoning_0037 | reasoning | StrategyQA | easy | auto_validated | 15 |
| reasoning_0038 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0039 | reasoning | StrategyQA | medium | auto_validated | 12 |
| reasoning_0040 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0041 | reasoning | StrategyQA | medium | auto_validated | 13 |
| reasoning_0042 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0043 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0044 | reasoning | StrategyQA | medium | auto_validated | 12 |
| reasoning_0045 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0046 | reasoning | StrategyQA | easy | spot_checked | 8 |
| reasoning_0047 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0048 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0049 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0050 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0051 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0052 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0053 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0054 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0055 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0056 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0057 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0058 | reasoning | StrategyQA | easy | auto_validated | 12 |
| reasoning_0059 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0060 | reasoning | StrategyQA | medium | auto_validated | 12 |
| reasoning_0061 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0062 | reasoning | StrategyQA | medium | auto_validated | 7 |
| reasoning_0063 | reasoning | StrategyQA | medium | auto_validated | 12 |
| reasoning_0064 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0065 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0066 | reasoning | StrategyQA | medium | auto_validated | 3 |
| reasoning_0067 | reasoning | StrategyQA | medium | auto_validated | 15 |
| reasoning_0068 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0069 | reasoning | StrategyQA | medium | auto_validated | 13 |
| reasoning_0070 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0071 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0072 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0073 | reasoning | StrategyQA | medium | auto_validated | 13 |
| reasoning_0074 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0075 | reasoning | StrategyQA | medium | auto_validated | 10 |
| reasoning_0076 | reasoning | StrategyQA | easy | auto_validated | 17 |
| reasoning_0077 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0078 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0079 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0080 | reasoning | StrategyQA | easy | auto_validated | 5 |
| reasoning_0081 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0082 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0083 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0084 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0085 | reasoning | StrategyQA | easy | auto_validated | 14 |
| reasoning_0086 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0087 | reasoning | StrategyQA | medium | auto_validated | 13 |
| reasoning_0088 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0089 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0090 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0091 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0092 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0093 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0094 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0095 | reasoning | StrategyQA | medium | auto_validated | 7 |
| reasoning_0096 | reasoning | StrategyQA | easy | auto_validated | 18 |
| reasoning_0097 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0098 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0099 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0100 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0101 | reasoning | StrategyQA | medium | spot_checked | 10 |
| reasoning_0102 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0103 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0104 | reasoning | StrategyQA | medium | auto_validated | 13 |
| reasoning_0105 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0106 | reasoning | StrategyQA | hard | auto_validated | 14 |
| reasoning_0107 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0108 | reasoning | StrategyQA | easy | auto_validated | 15 |
| reasoning_0109 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0110 | reasoning | StrategyQA | medium | auto_validated | 10 |
| reasoning_0111 | reasoning | StrategyQA | easy | auto_validated | 16 |
| reasoning_0112 | reasoning | StrategyQA | medium | spot_checked | 11 |
| reasoning_0113 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0114 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0115 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0116 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0117 | reasoning | StrategyQA | easy | auto_validated | 12 |
| reasoning_0118 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0119 | reasoning | StrategyQA | medium | auto_validated | 5 |
| reasoning_0120 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0121 | reasoning | StrategyQA | easy | auto_validated | 11 |
| reasoning_0122 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0123 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0124 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0125 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0126 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0127 | reasoning | StrategyQA | medium | auto_validated | 7 |
| reasoning_0128 | reasoning | StrategyQA | medium | auto_validated | 6 |
| reasoning_0129 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0130 | reasoning | StrategyQA | medium | auto_validated | 11 |
| reasoning_0131 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0132 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0133 | reasoning | StrategyQA | medium | auto_validated | 6 |
| reasoning_0134 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0135 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0136 | reasoning | StrategyQA | medium | auto_validated | 9 |
| reasoning_0137 | reasoning | StrategyQA | easy | auto_validated | 6 |
| reasoning_0138 | reasoning | StrategyQA | medium | auto_validated | 6 |
| reasoning_0139 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0140 | reasoning | StrategyQA | easy | auto_validated | 7 |
| reasoning_0141 | reasoning | StrategyQA | easy | auto_validated | 12 |
| reasoning_0142 | reasoning | StrategyQA | easy | auto_validated | 9 |
| reasoning_0143 | reasoning | StrategyQA | easy | auto_validated | 8 |
| reasoning_0144 | reasoning | StrategyQA | easy | auto_validated | 10 |
| reasoning_0145 | reasoning | StrategyQA | easy | auto_validated | 13 |
| reasoning_0146 | reasoning | StrategyQA | medium | auto_validated | 7 |
| reasoning_0147 | reasoning | StrategyQA | medium | auto_validated | 8 |
| reasoning_0148 | reasoning | StrategyQA | easy | auto_validated | 12 |
| reasoning_0149 | reasoning | StrategyQA | easy | auto_validated | 12 |
| reasoning_0150 | reasoning | StrategyQA | easy | auto_validated | 13 |
