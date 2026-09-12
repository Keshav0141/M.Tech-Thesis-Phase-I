# Manual spot-check sample

Review these 20 questions against the dataset. For each one:
1. Confirm the question is unambiguous and self-contained.
2. Confirm the ground-truth answer is correct and verifiable.
3. If it passes, set `validation_status` to `spot_checked` in data/dataset.json.
   If it fails, set it to `rejected` and note the reason in research_log.md.

## Factual (7 sampled)

- **factual_0010** (easy): What was Kevin Kline's first movie?
  - Ground truth: `Sophie's Choice`
- **factual_0074** (medium): "In the monologue, ""Albert and The Lion"", what was the name of the lion?"
  - Ground truth: `WALLACE`
- **factual_0037** (hard): December 12, 2003 saw the death of Keiko, an Orca whale, off the coast of Finland. Keiko achieved fame as a star in what movie series?
  - Ground truth: `Free Willy`
- **factual_0119** (easy): Rothesay is the principal town of which island?
  - Ground truth: `Bute`
- **factual_0095** (hard): Suzette Charles of New Jersey became Miss America 1984 because of the resignation of the actual winner. Whom did she replace?
  - Ground truth: `Vanessa Williams`
- **factual_0025** (medium): Who made his film debut playing Kasper Gutman in the 1941 film ‘Casablanca’?
  - Ground truth: `SYDNEY GREENSTREET`
- **factual_0117** (medium): Released in 1989, 'Orange Crush' was the first UK top 40 hit for which rock group?
  - Ground truth: `'REM'`

## Math (7 sampled)

- **math_0128** (easy): Harly's animal shelter has 80 dogs. She adopts out 40% of them but then has to take back 5 because of personality conflicts with other dogs in their adopted homes. How many dogs does she have now?
  - Ground truth: `53`
- **math_0005** (easy): A portable battery charger can fully charge a smartphone in 26 minutes or a tablet in 53 minutes. Ana charged her tablet fully and her phone halfway. How many minutes did it take?
  - Ground truth: `66`
- **math_0132** (medium): John's neighbor tells him to walk his dog for 1 hour each day for a total of $10. He does this for April, save for the 4 Sundays in April. He later spent $50 on books and gave his sister Kaylee the same amount. How much money did John have left?
  - Ground truth: `160`
- **math_0111** (medium): John watches a TV show and they announce they are going to do 1 more season.  Each season is 22 episodes except for the last season which is 4 episodes longer.  There were 9 seasons before the announcement.  If each episode is .5 hours how long will it take to watch them all after the last season finishes?
  - Ground truth: `112`
- **math_0148** (medium): Trevor buys three bouquets of carnations. The first included 9 carnations, and the second included 14 carnations. If the average number of carnations in the bouquets is 12, how many carnations were in the third bouquet?
  - Ground truth: `13`
- **math_0096** (medium): Lars owns a bakeshop. She can bake 10 loaves of bread within an hour and 30 baguettes every 2 hours. If she bakes 6 hours a day, how many breads does she makes?
  - Ground truth: `150`
- **math_0141** (medium): It takes Polly 20 minutes to cook breakfast every day. She spends 5 minutes cooking lunch. She spends 10 minutes cooking dinner 4 days this week. The rest of the days she spends 30 minutes cooking dinner. How many minutes does Polly spend cooking this week?
  - Ground truth: `305`

## Reasoning (6 sampled)

- **reasoning_0112** (medium): Would a kindergarten teacher make a lesson of the New Testament?
  - Ground truth: `no`
- **reasoning_0101** (medium): Does the density of helium cause voices to sound deeper?
  - Ground truth: `no`
- **reasoning_0046** (easy): Is the Sea of Japan landlocked within Japan?
  - Ground truth: `no`
- **reasoning_0015** (medium): Did Julius Caesar read books on Pharmacology?
  - Ground truth: `no`
- **reasoning_0028** (medium): Can eating your weight in celery prevent diabetes?
  - Ground truth: `no`
- **reasoning_0032** (medium): Can children be hurt by jalapeno peppers?
  - Ground truth: `yes`
