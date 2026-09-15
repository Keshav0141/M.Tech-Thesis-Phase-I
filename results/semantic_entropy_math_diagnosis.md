# Math semantic-entropy diagnosis: does NLI merge different numeric answers?

_Generated 2026-09-14. Bottom quartile by semantic entropy (n=37, entropy <= -0.0000)._

Low-entropy math questions with **different extracted final numbers** across samples: **2 / 37** (5% of the confident set).

## Pairwise NLI evidence (pairs whose final numbers differ)

### math_0009 (sample 0 vs sample 3)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 0: `To find the total number of recorded new coronavirus cases after the three weeks, we need to calculate the number of cases for each week and then sum them up.

` ... final = **12000**
- sample 3: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **7000**
- NLI p(i->j)=0.994 p(j->i)=0.934 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0009 (sample 0 vs sample 4)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 0: `To find the total number of recorded new coronavirus cases after the three weeks, we need to calculate the number of cases for each week and then sum them up.

` ... final = **12000**
- sample 4: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **2000**
- NLI p(i->j)=0.995 p(j->i)=0.965 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0009 (sample 1 vs sample 3)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 1: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **12000**
- sample 3: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **7000**
- NLI p(i->j)=0.034 p(j->i)=0.509 -> bidirectional equivalent: **False** (threshold 0.5, entropy -0.000)

### math_0009 (sample 1 vs sample 4)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 1: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **12000**
- sample 4: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **2000**
- NLI p(i->j)=0.057 p(j->i)=0.387 -> bidirectional equivalent: **False** (threshold 0.5, entropy -0.000)

### math_0009 (sample 2 vs sample 3)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 2: `To find the total number of recorded new coronavirus cases after the three weeks, we need to calculate the number of cases for each week and then sum them up.

` ... final = **12000**
- sample 3: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **7000**
- NLI p(i->j)=0.154 p(j->i)=0.857 -> bidirectional equivalent: **False** (threshold 0.5, entropy -0.000)

### math_0009 (sample 2 vs sample 4)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 2: `To find the total number of recorded new coronavirus cases after the three weeks, we need to calculate the number of cases for each week and then sum them up.

` ... final = **12000**
- sample 4: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **2000**
- NLI p(i->j)=0.934 p(j->i)=0.897 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0009 (sample 3 vs sample 4)
Question: New York recorded 5000 new coronavirus cases on a particular week. In the second week, half as many new coronaviruses cases as the first week was recorded by the state. In the third week, 2000 more cases were recorded in the state. What is the total number of recorded new coronaviruses in the state after the three weeks?

- sample 3: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **7000**
- sample 4: `To find the total number of recorded new coronavirus cases after three weeks, we need to calculate the number of cases for each week and then sum them up.

**St` ... final = **2000**
- NLI p(i->j)=0.995 p(j->i)=0.994 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0032 (sample 0 vs sample 1)
Question: Every 4 weeks, Helen hand washes her silk pillowcases.  It takes 30 minutes to hand wash all of them.  In 1 year, how much time does Helen spend hand washing her pillowcases?

- sample 0: `To determine how much time Helen spends hand washing her pillowcases in one year, we need to calculate the total number of times she washes them and then multip` ... final = **6.5**
- sample 1: `To determine how much time Helen spends hand washing her pillowcases in 1 year, we need to calculate the total number of times she washes them and then multiply` ... final = **390**
- NLI p(i->j)=0.991 p(j->i)=0.988 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0032 (sample 0 vs sample 2)
Question: Every 4 weeks, Helen hand washes her silk pillowcases.  It takes 30 minutes to hand wash all of them.  In 1 year, how much time does Helen spend hand washing her pillowcases?

- sample 0: `To determine how much time Helen spends hand washing her pillowcases in one year, we need to calculate the total number of times she washes them and then multip` ... final = **6.5**
- sample 2: `To find out how much time Helen spends hand washing her pillowcases in one year, we need to determine how many times she washes them and then multiply that by t` ... final = **390**
- NLI p(i->j)=0.987 p(j->i)=0.982 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0032 (sample 0 vs sample 3)
Question: Every 4 weeks, Helen hand washes her silk pillowcases.  It takes 30 minutes to hand wash all of them.  In 1 year, how much time does Helen spend hand washing her pillowcases?

- sample 0: `To determine how much time Helen spends hand washing her pillowcases in one year, we need to calculate the total number of times she washes them and then multip` ... final = **6.5**
- sample 3: `To determine how much time Helen spends hand washing her pillowcases in one year, we need to calculate the total number of times she washes them and then multip` ... final = **390**
- NLI p(i->j)=0.969 p(j->i)=0.991 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

### math_0032 (sample 0 vs sample 4)
Question: Every 4 weeks, Helen hand washes her silk pillowcases.  It takes 30 minutes to hand wash all of them.  In 1 year, how much time does Helen spend hand washing her pillowcases?

- sample 0: `To determine how much time Helen spends hand washing her pillowcases in one year, we need to calculate the total number of times she washes them and then multip` ... final = **6.5**
- sample 4: `To find the total time Helen spends hand washing her pillowcases in one year, we need to determine two things:
1. How many times she washes the pillowcases in a` ... final = **390**
- NLI p(i->j)=0.986 p(j->i)=0.988 -> bidirectional equivalent: **True** (threshold 0.5, entropy -0.000)

Across all flagged questions: 11 pairwise comparisons had different final numbers; **8 of them (73%) were marked semantically equivalent by bidirectional entailment**.

## Caveat: one flagged question is a unit-equivalence artifact, not an NLI failure
- `math_0032`: sample 0 ends `Final answer: 6.5 hours` while the others end
  `390 minutes` -- the same value in different units (390 min = 6.5 h), so the
  NLI was arguably right to merge them. The numeric extractor compares 6.5 to
  390 and flags them as different.
- Excluding math_0032, the genuine case is `math_0009` (12000 vs 7000 vs 2000):
  **4 of its 7 differing-number pairs were merged by bidirectional entailment
  (p up to 0.995)** -- e.g., "total = 12000" vs "total = 2000" marked
  equivalent. That is direct evidence for the hypothesis.

## Verdict
- Hypothesis **CONFIRMED, but incidence is small**: in the bottom quartile of
  math semantic entropy (37 confident questions), only ~1 question
  (`math_0009`, ~3%) shows NLI merging genuinely different numeric answers.
  Most confident math questions genuinely agree on the final number.
- The NLI failure mode is exactly as hypothesized: nearly identical reasoning
  text with different final numbers scores p(entailment) ~0.99 in both
  directions, so the samples collapse into one cluster and entropy stays 0.

Note: a bidirectional-equivalent pair with different final numbers is direct evidence that NLI merged numerically different answers; the 'confident' (low entropy) label on that question is then an artifact.
