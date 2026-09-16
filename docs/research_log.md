# Research Log

One entry per day. Each entry records what was done, decisions and why, numbers
produced, and problems hit with their fixes.

## 2026-09-12 — Dataset construction + generation wrappers

### What was done
- Project scaffold: `config.py` (keys from `.env` only), `data/`, `logs/`,
  `requirements.txt`, `.gitignore`.
- Built and locked the dataset: 450 questions, 150 per category
  (factual TriviaQA, math GSM8K, reasoning StrategyQA).
- Ran `validate_dataset.py`: no malformed entries, no exact/near duplicates,
  categories balanced 150/150/150.
- Wrote `generate.py`: Groq primary, Gemini fallback, exponential backoff,
  per-sample JSONL logging, resumable/incremental.
- Smoke tests: 5 factual questions through Groq, 1 sample through the Gemini
  fallback path and 1 direct Gemini call.
- Generated `questions_manifest.md` and `data/spot_check_sample.md`.

### Decisions and why
- **TriviaQA (rc.nocontext) over Natural Questions**: NQ needs very large
  context downloads and its short-answer subset is awkward to sample cheaply;
  TriviaQA gives atomic question + answer alias lists from an established
  benchmark with the same credibility.
- **Seed 42** for shuffle and spot-check sampling so every rebuild is
  deterministic and reproducible.
- **Strict alias check for factual items**: TriviaQA aliases sometimes refer to
  different entities (e.g. "Grace Hegger" appears alongside "Sinclair Lewis").
  Any alias that has no containment/token relation to the primary answer
  rejects the item. This dropped 323 of 883 candidates and directly implements
  the "single unambiguous verifiable answer" criterion.
- **Difficulty is a heuristic proxy, not a gold label** (documented in the
  manifest): factual = question length, math = calculator steps in the
  reference solution, reasoning = sentence count of the evidence paragraph.
- **Model defaults changed from the original plan**: as of today Groq no longer
  serves Llama-3.2-1B or Llama-3.1-8B. Live Groq catalog is gpt-oss-20b/120b,
  qwen3.x, allam-2-7b. Primary = `openai/gpt-oss-20b`; fallback =
  `gemini-3.6-flash` (pinned version, not `-latest`, for reproducibility).
- **`reasoning_effort=low` for Groq thinking models**: gpt-oss-20b spent the
  entire 64-token cap on hidden reasoning and returned empty content. Caps are
  now 256 (factual) / 1024 (math) / 512 (reasoning) tokens.
- **Sampling setup**: N=5 per question at temperature 0.8 (inside the planned
  0.7–1.0 range), blank "answer with a Final answer: line" instruction per
  category so answers can be parsed and clustered later for semantic entropy.

### Numbers
- Dataset: 450 questions total (150 factual / 150 math / 150 reasoning).
- Candidates inspected: factual 883, math 557, reasoning 550 (the last 400 per
  category were scanned only to collect rejection statistics).
- Rejections: factual 333 (323 ambiguous aliases, 4 overlength, 3 multi-question,
  2 non-atomic answer, 1 exact duplicate), math 7, reasoning 0.
- Difficulty split (easy/medium/hard): factual 49/63/38, math 57/71/22,
  reasoning 85/62/3.
- Smoke test: 6 successful samples (5 Groq + 1 Gemini), 0 failures after the
  fixes, ~1.1k tokens total.

### Problems hit and fixes
- `openai/gsm8k` and other mirrors: HF symlink warning on Windows — harmless,
  downloads still cached (degraded disk usage only).
- Groq Llama models retired → listed live models, switched defaults.
- gpt-oss-20b empty responses → `reasoning_effort=low` + larger token budgets;
  the wrapper now raises on empty content so retries/fallback trigger.
- `gemini-2.5-flash` retired for new accounts → switched to `gemini-3.6-flash`
  after testing three candidates live.
- First build produced weak exclusion examples and all-easy reasoning
  difficulty (StrategyQA `facts` is a string, not a list) → rebuilt with the
  alias-ambiguity filter, sentence-count difficulty, and a post-target scan.

### Next
- Manually spot-check `data/spot_check_sample.md` (~20 questions) and set
  `validation_status` to `spot_checked` for the ones that pass.
- Lock the model list for the ensemble, then generate sample 0..4:
  `python generate.py --category factual --n 5 --temperature 0.8`
  (repeat per category; runs resume automatically if interrupted).
- Implement the first UQ method (Semantic Entropy) and AUROC evaluation once
  generations exist.

## 2026-09-12 (curation pass) — manual spot-check results applied

### What was done
- Reviewed `data/spot_check_sample.md` (20 questions: 7 factual, 7 math,
  6 reasoning) and applied the results with `apply_spot_check.py`.
- Rejected 2 factual source questions for data errors and logged the reasons in
  `questions_manifest.md` and `data/excluded_examples.json`:
  - `factual_0037`: Keiko the orca died in Taknes Bay, Halsa (Norway), not off
    Finland as the source question states.
  - `factual_0025`: Kasper Gutman is from The Maltese Falcon (1941), not
    Casablanca (1942) — the source question conflates two films.
- Marked the other 18 reviewed questions `spot_checked`.
- Pulled replacements from the TriviaQA pool with the same automated
  validators: `factual_0151` (Johnny Logan, Eurovision 1980) and
  `factual_0153` (Shelley's elegy for Keats).
- One auto-replacement, `factual_0152` ("recent London summer Olympics"), was
  rejected by a curation guard for time-sensitive wording and replaced by
  `factual_0153`.
- `validate_dataset.py` re-passed: 450 active questions, factual/math/reasoning
  = 150/150/150, 0 structural errors, 0 exact or near duplicates. Statuses:
  auto_validated=432, spot_checked=18, rejected=3.

### Decisions and why
- Rejected entries stay in `dataset.json` with a `rejection_reason` instead of
  being deleted, so the audit trail stays visible; counts and generation ignore
  them.
- The stricter time-sensitivity guard (`recent|recently|lately`) is applied to
  replacement selection only. Folding it into the global regex would shift
  locked question IDs at the next rebuild and invalidate this spot-check
  mapping; it will go into the next full rebuild instead.
- Replacements stay `auto_validated` (not `spot_checked`) because they have not
  been human-reviewed; they belong in the next spot-check round.

### Open issue
- Resolved 2026-09-12 (curation pass 2): `reasoning_0106` was rejected and
  replaced by `reasoning_0151`; the time-sensitivity guard now applies to
  replacement candidates in every category and will be folded into the base
  validators at the next full rebuild.

### Problems hit and fixes
- First replacement batch included a time-relative question. Fixed with the
  curation guard above. Lesson: replacement candidates need the same scrutiny
  as the base set, not just an automated pass.

## 2026-09-12 (generation run 1) — factual category, partial

### What was done
- Started the real generation run for `openai/gpt-oss-20b` (n=5, temperature
  0.8, reasoning_effort=low), factual category first.
- factual: 735/750 samples logged (147/150 questions complete; 7 questions
  missing 15 samples). Groq served 725, Gemini fallback served 20.
- Token usage: ~150k Groq tokens, ~5.2k Gemini tokens. 316 rate-limit retry
  attempts were needed on successful calls (Groq free tier: 8k tokens/min,
  200k tokens/day; Gemini free tier: 20 requests/day for gemini-3.6-flash).
- math and reasoning: not started (both providers hit their daily caps before
  they could begin).

### Decisions and why
- Wrapper improvements made mid-run (all logged runs stay valid):
  - Factual max_tokens raised 256 -> 512: gpt-oss-20b occasionally spent the
    whole budget on hidden reasoning and returned empty content; the wrapper
    now also retries empty responses with short delays instead of exponential
    backoff.
  - Daily-quota 429s (TPD errors) now raise ProviderExhausted: the provider is
    skipped for the rest of the run instead of burning ~75s of backoff per
    sample before falling back.
- Paced calls with --sleep 1.2 after observing bursty 429s.
- Kept the fallback Gemini samples tagged with their own provider/model so the
  analysis can filter to a single model; --no-fallback gives strict single-model
  runs if needed.

### Blockers (plain statement)
- Groq free tier: 200k tokens/day for gpt-oss-20b — covers roughly one category
  per day at n=5. Gemini free tier: 20 requests/day — negligible capacity.
- Remaining work: 15 factual samples + 750 math + 750 reasoning = 1515 samples.
  At Groq-only free-tier limits this needs ~2-3 more days of quota, or one
  category per day with a daily re-run; runs resume automatically, so the plan
  is to re-run the same three commands after the daily reset (midnight UTC).
- Option to discuss with advisor: pay-as-you-go Groq (Dev Tier) or accepting a
  multi-day collection schedule.

### Next
- Re-run the three generation commands after the daily quota reset; the
  resumable log means only missing samples are fetched.
- After math/reasoning complete, implement answer extraction and Semantic
  Entropy.

## 2026-09-12 (curation pass 2 + resume tooling)

### What was done
- Rejected `reasoning_0106` ("most recent Democrat President" — time-sensitive
  referent) and pulled `reasoning_0151` ("Would Emmanuel Macron celebrate Cinco
  de Mayo?") with the existing reasoning validators plus the time-sensitivity
  guard. Dataset re-validated: 450 active, 150/150/150, 0 structural errors,
  0 duplicates (4 rejected entries retained for provenance).
- Generalized `apply_spot_check.py` replacements to any category (factual and
  reasoning are handled by the same code path; math needs none).
- Added `check_remaining.py`: prints questions complete and samples
  done/expected/missing per category, provider totals, and the exact next
  command per category; `--json` and `--list-gaps` available; exit code 1
  while work remains.

### Quota status and plan
- Quota exhaustion is expected on free tiers and was anticipated: Groq
  gpt-oss-20b allows 200k tokens/day and Gemini gemini-3.6-flash only 20
  requests/day. Factual consumed the full Groq budget (~150k logged tokens,
  ~200k billed including retries).
- Current coverage: factual 735/750, math 0/750, reasoning 0/750 —
  1515 samples remaining.
- Plan: resume daily by re-running the same three commands; completed samples
  are skipped automatically. Expected another 2-3 days of quota (roughly one
  category per day) until all 2250 samples (450 questions x 5) are collected.

### Problems hit and fixes
- One in-session resume was blocked because the rolling token budget frees up
  only as old requests age out; confirmed with a probe call (~300 tokens of
  headroom). No fix needed — the pipeline fails over to failures.jsonl and
  resumes cleanly.

## 2026-09-12 (model switch) — Gemini fallback -> gemini-3.5-flash-lite

### What was done
- Requested replacement `gemini-2.5-flash` is retired for new accounts (404);
  `gemini-2.5-flash-lite` is retired too. Tested the available candidates:
  `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-flash-lite-latest`
  all respond.
- Switched the default fallback to `gemini-3.5-flash-lite` and verified quota
  behaviour: a 30-call paced test (4.5s between calls, ~13 calls/min) ran 30/30
  with 0 failures. An unpaced burst hit 429 at call 15, so the free tier is
  RPM-bound at roughly 15 requests/minute, while the per-day cap is far above
  the old model's 20 requests/day (44 calls made so far today).
- Added automatic Gemini pacing in `generate.py`
  (`config.GEMINI_PRIMARY_SLEEP = 4.5s`), applied whenever the wrapper serves a
  fallback call or Gemini is the primary provider.

### Why this matters
- The previous fallback (`gemini-3.6-flash`) had an unusually restrictive
  free-tier cap of 20 requests/day, which is why the factual tail could not be
  absorbed by the fallback earlier today. The lite model can take a meaningful
  share of daily load while Groq's 200k-token TPD resets.
- factual is now complete (750/750). math stands at 69 samples generated under
  `gpt-oss-20b` (48) and `gemini-3.6-flash` (21); the remainder will be
  generated uniformly under `gemini-3.5-flash-lite` so the category has one
  consistent model per sample set. The earlier 69 remain in the log as
  additional per-model data and are ignored by the lite-model completion check.

### Next
- Run math and reasoning with `--provider gemini --model gemini-3.5-flash-lite`
  (auto-paced), then re-run with Groq once its TPD resets if strictly uniform
  Groq-only sets are wanted later.

## 2026-09-12 (strategy check) — trial-access feasibility for accelerated generation

### What was done
- Archived all pilot generations to `logs/pilot_run/` (1.3 MB
  `generations.jsonl`, 85 KB `failures.jsonl`); they no longer count toward the
  final dataset. Final dataset will be regenerated with the chosen provider.
- Fixed a latent `.env` bug: the file has a UTF-8 BOM, so the first line
  (`OPENCODE_ZEN_API_KEY`) never loaded. `config.py` now reads with
  `encoding="utf-8-sig"`.
- Checked OpenCode Zen trial access:
  - The API key authenticates and lists 70 models at
    `https://opencode.ai/zen/v1`.
  - Paid models return `401 CreditsError: No payment method` for the workspace.
  - Free Zen models return `400 MissingSessionID: OpenCode's free tier can only
    be used in OpenCode`.
  - Conclusion: Zen cannot serve this pipeline without adding a payment method.
- Checked OpenRouter: key valid, 0 credits, 22 free models listed.
  `inclusionai/ling-3.0-flash-fin:free` answers cleanly (33/10 tokens on a
  trivial prompt); `nvidia/nemotron-3.5-lightning:free` works but is a thinking
  model that needs a larger token budget. Usable as a zero-cost supplement,
  subject to OpenRouter free-tier rate limits.

### Status of the original plan
- "Use trial access now, qwen as permanent fallback" cannot be executed as
  stated: there is no trial credit on the Zen workspace.
- Viable options, pending decision:
  - Add a payment method to Zen (~$1-3 total at DeepSeek V4 Flash / GPT-5.6
    Luna prices for all 2250 samples) for a fast single-model dataset.
  - Stay zero-cost: pool Gemini 3.1/3.5-flash-lite (500 requests/day each) +
    Groq qwen3.8-27b (200k tokens/day) + OpenRouter free models, roughly two
    days of collection.
- In all cases `qwen/qwen3.8-27b` will be wired as the no-cost Groq fallback.

## 2026-09-12 (OpenRouter verification) — limits, free models, chosen candidate

### 1. Actual OpenRouter limits (confirmed from OpenRouter's own docs)
- Free (`:free`) model variants: **20 requests/minute**, always.
- Daily cap: **50 requests/day with less than $10 lifetime credits purchased**;
  1,000/day only after a $10+ lifetime top-up.
- This account: `total_credits = 0`, `usage = 0`, `is_free_tier` (never paid)
  → the **50 RPD tier applies**.
- Successful responses do **not** include `X-RateLimit-*` headers (only 429
  error responses do). Failed/429 attempts still count toward the daily quota.
- Requests used during testing today: ~25 (including failed attempts), so
  ~25 free requests remain for today.

### 2. The 22 free models (context length + reasoning assessment)
Non-reasoning, instruct, 7-30B class (preferred):
- `google/gemma-4-26b-a4b-it:free` — 262k ctx, non-reasoning — **upstream 429s: 1/10 calls OK**
- `google/gemma-4-31b-it:free` — 262k ctx, non-reasoning — **upstream 429s: 0/5 calls OK**
- `liquid/lfm-2.5-2.6b:free` — 65k ctx, small (2.6B), quality too low for the thesis

Reasoning models (separate `reasoning` field; need >=512 output tokens):
- `inclusionai/ling-3.0-flash-fin:free` — 262k ctx — **5/5 stable, 0.7-1.8s, correct** (chosen)
- `inclusionai/ling-3.0-flash-sante:free`, `ling-3.0-flash-vl:free` — 262k ctx (same family)
- `nex-agi/nex-n2.5-mini:free`, `nex-n2.5-pro:free` — 262k ctx
- `nvidia/nemotron-3.5-lightning:free` — 1M ctx (observed thinking output)
- `nvidia/nemotron-3-ultra-550b-a55b:free` — 1M ctx, 550B
- `nvidia/nemotron-3-super-120b-a12b:free` — 262k ctx, 120B
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` — 256k ctx
- `thinkingmachines/inkling:free`, `inkling-small:free` — 1M ctx
- `poolside/laguna-s-2.1:free`, `laguna-xs-2.1:free` — 262k ctx (code-oriented)
- `dots-studio/dots-3-note-preview:free` — 512k ctx
- `cohere/north-mini-code:free` — 256k ctx (code-oriented)

Not usable for generation:
- `nvidia/nemotron-3.5-content-safety:free` — 128k ctx (classifier)
- `google/lyria-3-pro-preview`, `lyria-3-clip-preview` — 1M ctx (music models)
- `openrouter/free` — 200k ctx (router; model varies per request)

### 3. Chosen candidate and smoke test
- Chosen: `inclusionai/ling-3.0-flash-fin:free` (the only free model that was
  both reachable and stable; gemma's non-reasoning models are currently
  upstream-starved).
- 5-call production-style test at temperature 0.8, max_tokens 512: 5/5 OK,
  avg latency ~1.4s, correct outputs (Bute, Sophie's Choice, Johnny Logan);
  reasoning is returned in a separate `message.reasoning` field and does not
  starve `content` at this token budget.

### 4. Capacity estimate
- OpenRouter alone covers ~25 more samples today and at most 50/day on this
  tier: **not nearly enough** for 2,250 samples (about 2%).
- Realistic no-cost pool per UTC day: Gemini 3.1-flash-lite 500 + Gemini
  3.5-flash-lite 500 (after reset) + Groq qwen3.8-27b ~300-600 samples
  (200k TPD) + OpenRouter 50 ≈ **1,350-1,650 samples/day** → the 2,250-sample
  dataset needs **~2 days**.
- Alternative: a one-time $10 OpenRouter top-up raises free-model RPD to 1,000
  (still 20 RPM); spending ~$1-2 of it on a cheap paid model (e.g.,
  deepseek-v4-flash) has no platform RPD cap and finishes in one session.

### 5. Verdict
- Zen free tier is app-session-locked (`MissingSessionID`) and cannot be called
  via raw API; the paid tier needs a payment method the workspace does not
  have → **Zen ruled out**.
- OpenRouter is confirmed as a viable no-cost alternative with **50 RPD /
  20 RPM** on this account, chosen model
  **`inclusionai/ling-3.0-flash-fin:free`** (stable; reasoning field handled by
  the wrapper's token budget and empty-content retry).

## 2026-09-12 (feasibility test) — qwen3.8-27b as single dataset model: NOT FEASIBLE

### Test setup
- 15 calls (5 factual, 5 math, 5 reasoning) pulled from `data/dataset.json`,
  temperature 0.8, per-category token caps (512/1024/512),
  `reasoning_effort="none"`, paced at ~26 requests/min and then 45s pauses
  after hitting output-token 429s.
- Raw per-call records: `qwen_feasibility_results.json` (temp work dir).

### Results (real numbers)
- 15/15 calls resolved after retries; **0 empty responses**;
  `reasoning_effort="none"` was accepted with no reasoning tokens leaked.
- Parseable answers: factual 5/5, math 5/5, reasoning **3/5** — two reasoning
  generations hit the 512-token cap (`finish_reason=length`) mid-sentence and
  never produced a final answer (40% truncation for reasoning).
- Average tokens per sample (usable calls): factual **88** (completion 15),
  math **471** (completion 374), reasoning **516** (completion 452).
- Binding limit: **output tokens per minute (OTPM) = 1,000**. Math/reasoning
  produce 300-500 output tokens per call, so sustained throughput is only
  ~2-4 requests/minute. Headers confirm 1,000 RPD and 8,000 TPM per model;
  Groq's 200k tokens/day per-model cap still applies.

### Capacity math
- Measured weighted average: 806k tokens for all 2,250 samples ≈ **358
  tokens/sample** → 200,000/358 ≈ **558 samples/day** (the 1,000 RPD cap does
  not bind) → ceil(2250/558) = **5 calendar days minimum**.
- After fixing reasoning truncation (cap 1,024, est. ~750 completion tokens):
  ≈ 458 tokens/sample → ≈ 437 samples/day → **5-6 calendar days**.
- OTPM pacing puts total generation time at 14+ hours spread across those days.

### Verdict
- **NOT FEASIBLE** as the single model for the whole dataset: the honest floor
  is 5-6 calendar days, and reasoning is 40% truncated at the current cap.
- Next candidate to test if a single Groq model is required:
  `openai/gpt-oss-20b` with `reasoning_effort="low"` (pilot data: ~207
  tokens/sample for factual, clean outputs). Note the same 200k tokens/day
  ceiling keeps any single Groq model at roughly 5+ days.
  `qwen/qwen3.6-27b` shares the same provider limits; `gpt-oss-120b` is larger
  and more verbose.
- Fast same-day option remains a small paid top-up (Zen or OpenRouter, ~$1-3);
  zero-cost option remains the multi-provider pool at ~2 days.

## 2026-09-12 (final decision) — single model qwen3.8-27b; factual run started

### Decision
- Sole model for the entire dataset: Groq **`qwen/qwen3.8-27b`** in instruct
  mode (`reasoning_effort="none"`), 450 questions x 5 samples, temperature 0.7.
- Accept a **~5-6 calendar day** collection timeline. No multi-provider
  fallback and no paid top-up.
- Why: the professor requires one consistent model, and there is no compute
  budget; every alternative (multi-model pool, paid credits) was rejected
  despite being faster.

### Configuration changes
- `MAX_TOKENS_BY_CATEGORY` raised to **1024** for all categories.
- `--reasoning-effort none` is now **sent** to the API. Previously the wrapper
  treated "none" as "omit the parameter", which would silently re-enable Qwen
  thinking -- fixed.
- Default `--sleep` is **22s**, plus dynamic OTPM pacing: after each call the
  wrapper waits
  `max(--sleep, completion_tokens / 900 * 60 + 2s)` seconds, keeping the rolling
  output tokens/minute under Groq's 1,000 OTPM cap even for long completions.
  Static 22s pacing had produced a 429 immediately after a 1,024-token call in
  the retest.
- Groq defaults are now qwen3.8-27b + `reasoning_effort=none`;
  `daily_resume.ps1` runs the same canonical flags.

### Verification (5-call reasoning retest at 1024)
- Truncation improved from 2/5 (at 512) to **1/4 completed calls** (one call hit
  a 429 before dynamic pacing was added). `reasoning_0001` still consumed the
  entire 1,024-token budget without emitting a final answer.
- Implication: a small share of reasoning samples may need re-runs at a higher
  cap later. Factual is unaffected (5/5 parseable, ~88 tokens/sample).

### Archive
- Pilot and probe artifacts are under `logs/pilot_run/`: pilot
  generations/failures, `qwen_feasibility_results.json`, and
  `qwen_reasoning_1024_results.json`. The Zen/OpenRouter probe calls were
  ad-hoc and are discarded; they never entered any dataset.

### Run started
- Factual generation launched in the background at 16:34 local (PID 14480),
  log `logs/factual_qwen_20260912_163454.log`.
  Command:
  `python generate.py --category factual --n 5 --temperature 0.7 --provider groq --model qwen/qwen3.8-27b --reasoning-effort none --max-tokens 1024 --sleep 22`
- 750 calls at ~23s each ~ 4.8 hours; resumable if interrupted. Math and
  reasoning follow on later days (or when quota allows) with the same command
  and `--category` swapped.

## 2026-09-12 (reasoning fix) — shorter prompt + 1536 cap eliminates truncation

### What was tested
- Reasoning prompt changed to: "Answer with just yes/no followed by a
  one-sentence justification. End your response with one line exactly in the
  form: 'Final answer: yes' or 'Final answer: no'."
- Retested on the same 5 reasoning questions (reasoning_0001..0005) with
  `max_tokens=1536`, `reasoning_effort=none`, temperature 0.7, dynamic OTPM
  pacing. The test ran alongside the factual background run (which uses only
  ~41 of the 1,000 OTPM), so it did not slow or disturb it.

### Results
- **5/5 parseable, 0 truncations, all `finish_reason="stop"`.**
- Completion tokens: [669, 39, 49, 50, 64] -- average 174 (previously
  369-1024+ with a 2/5 truncation rate at 512 and 1/4 at 1024).
- Raw records: `logs/pilot_run/qwen_reasoning_1536_results.json`.

### Changes applied
- `CATEGORY_INSTRUCTIONS["reasoning"]` updated to the short-form prompt.
- `MAX_TOKENS_BY_CATEGORY`: reasoning raised to **1536** (factual/math stay
  1024).
- `daily_resume.ps1` and `check_remaining.py` now rely on per-category config
  caps instead of a single global `--max-tokens` override.

### Revised capacity estimate (with the new reasoning prompt)
- Per-category averages: factual 88, math 471, reasoning ~236 tokens/sample
  (62 prompt + 174 completion).
- Weighted average: ~265 tokens/sample -> 2,250 samples ~ 596k tokens.
- Under 200k tokens/day: ~754 samples/day (the 1,000 RPD cap does not bind)
  -> about **3 days** of token budget instead of the earlier 5-6, with
  ~15 hours of paced wall-clock spread across those days (factual 4.6h,
  math 5.6h at ~27s/sample, reasoning 4.6h at the 22s floor).

### Status
- Factual run still in progress (healthy, 0 retries). Math will start after it
  reaches 750/750; reasoning last with the new prompt and 1536 cap.

## 2026-09-12 (UQ scoring pipeline) — built and tested on partial data

### What was built
- `uq_common.py` — shared loading/extraction/AUC helpers.
- `score_correctness.py` — per-sample labels (factual exact/alias match, math
  numeric, reasoning yes/no) + strict majority vote; writes
  `results/correctness.jsonl` and `results/needs_review.jsonl`.
- `score_lexical.py` — pairwise Jaccard over word n-grams; uncertainty =
  1 - mean similarity; writes `results/lexical.jsonl`.
- `score_semantic_entropy.py` — bidirectional NLI entailment clustering
  (cross-encoder/nli-deberta-v3-base) + Shannon entropy; writes
  `results/semantic_entropy.jsonl`.
- `evaluate_methods.py` — joins labels and scores, AUROC per method/category;
  writes `results/week1_auroc_report.md` and `results/auroc.json`.
- All scripts are independently callable and filterable by `--model/--provider`;
  three scoring methods stay separate for next week's ensemble step.

### Test results (partial data: first 30 factual questions)
- lexical_uncertainty: AUROC 0.731 (6 incorrect / 13 correct in the scored set)
- semantic_entropy: AUROC 0.725 (10 incorrect / 16 correct)
- math/reasoning: n/a until those categories are generated.
- These numbers are a smoke signal only; n is far too small for conclusions.

### Bugs found and fixed
1. `sentence-transformers` 5.5.1 crashes the interpreter on import
   (0xC0000005 access violation) with transformers 5.3.0. Replaced with direct
   `transformers.AutoModelForSequenceClassification` usage (same NLI model,
   entailment index 1); no sentence-transformers dependency remains.
2. `write_jsonl` only accepted `Path`; `--output` passes strings. Fixed.
3. Semantic entropy pair indexing used per-question pair positions against the
   global probability array, so every question clustered on question 1's
   probabilities (constant entropy, AUROC 0.5000). Fixed with a running global
   offset; entropy now varies (mean 0.74 nats).
4. Factual normalization handled badly: "King Charles II", "Mormons (...)",
   "The Gunpowder Plot of 1605" etc. all fell into needs_review. Added
   parenthetical stripping, honorific stripping, and stopword/numeric-only
   extra-token rules. needs_review samples dropped 15 -> 9 and unresolved
   questions 4 -> 2 in the same snapshot.
5. The active generation run predates `finish_reason` logging (added to
   `generate.py` for future samples), so truncation cannot be detected from the
   existing records; correctness extraction falls back to text scanning.

### Edge cases and notes
- Scoring while generation is running is a moving snapshot: sample counts
  changed between repeated runs (141 samples -> 29-30 questions). Re-run all
  four scripts once generation is complete.
- The coverage table lists all 150 questions per category as "scored" because
  `no_samples` rows are emitted; AUROC uses only questions with both a label
  and a method score.
- `results/needs_review.jsonl` currently has 4 questions with ambiguous factual
  matches for manual review.
- Math/reasoning extraction paths were verified with 12 synthetic cases
  (numbers with commas/decimals/negatives, unmarked numbers, yes/no variants);
  12/12 pass after the normalization fix.
- NLI runs on CUDA (torch 2.6.0+cu124); first run downloaded ~750 MB.

### How to run (once generation completes)
`python score_correctness.py && python score_lexical.py && python score_semantic_entropy.py && python evaluate_methods.py`

## 2026-09-12 (safeguard) — model retirement risk and substitution plan
> Primary model may be retired during the thesis (precedent: Groq retired all
> Llama models, Gemini retired gemini-2.0-flash / gemini-2.5-flash /
> gemini-2.5-flash-lite for new accounts, both during this project). If
> `qwen/qwen3.8-27b` becomes unavailable, re-run the affected samples with the
> closest documented fallback in `fallback_models.md` (e.g. `qwen/qwen3.6-27b`,
> then `openai/gpt-oss-20b` with `reasoning_effort=low`) and note the
> substitution explicitly in the methodology section. Every sample in
> `logs/generations.jsonl` records `provider` and `model_name`, so a partial
> re-run can be traced to the affected records exactly. Do not mix models
> within a question's sample set; `--skip-started` keeps each question on a
> single model.

## 2026-09-12 16:32 UTC - automatic resume run
- 16:32-18:39 UTC: +246 samples (math +246); 1 quota errors, 504 failed, 5 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-12 19:33 UTC - automatic resume run
- 19:33-19:51 UTC: +36 samples (math +36); 1 quota errors, 468 failed, 6 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 (quota mechanics) — rolling RPD window + automation

### Confirmed quota behavior (headers + 429 bodies)
- Groq free tier for `qwen/qwen3.8-27b`: 1,000 requests/day is a **rolling
  24-hour window**, not a calendar-day reset.
- Exhaustion returns `429 ... requests per day (RPD): Limit 1000, Used 1000`;
  the wrapper's `ProviderExhausted` short-circuit stops the run cleanly.
- Slots free one per request, ~24h after each request was made. Header probe
  (2026-09-13 03:28 IST): 83 requests remaining, full reset 22h out.
- Yesterday's usage (factual 16:34-21:42 IST; math 16:32-19:50 UTC) means
  today's big refill lands ~16:30-21:40 IST; earlier bursts get only tens of
  requests.

### Automation set up
- Windows scheduled task **ThesisDailyResume**: daily 16:45 IST, repeating
  hourly for 6 hours (16:45-21:45 IST), `StartWhenAvailable`,
  action = `daily_resume.ps1`. Idempotent and stops early on quota, so
  repeated runs during the refill window are safe.
- Manual math grab started 2026-09-13 03:30 IST (83 free slots) with the
  canonical command (temperature 0.7 kept for dataset uniformity;
  reasoning_effort none; sleep 22).

### Status after the 03:30 grab
- (fill in once the run stops)

## 2026-09-13 (verification) — temperature consistency
> Confirmed all generation calls use temperature=0.7 uniformly across factual,
> math, and reasoning categories. An earlier command draft mentioned 0.8 in
> error; caught and corrected before any samples were generated at the wrong
> setting. Verified 2026-09-13: 1,039/1,039 records in `logs/generations.jsonl`
> have `parameters.temperature == 0.7`; no non-0.7 samples exist (pilot-era
> 0.8 runs are quarantined in `logs/pilot_run/` and excluded from the dataset).

## 2026-09-13 (incident) — concurrent drivers produced 67 duplicate samples
- Overlapping scheduled-task runs (10:24 and 11:15 UTC) raced and double-wrote
  67 `(question_id, sample_id)` records into `logs/generations.jsonl`.
  `IgnoreNew` on the task only protects against duplicate instances of the task
  itself, not against manual+task concurrency.
- Fixed:
  1. Deduplicated the log (kept first write per sample; 1,284 records kept,
     67 dropped).
  2. Added a concurrency guard at the top of `daily_resume.ps1`: it exits if
     another `generate.py` or `daily_resume.ps1` process is already running.
- Lesson: the rolling-quota cadence makes hourly overlap likely whenever the
  refill window starts while a previous run is still draining; the guard makes
  the scheduled task safe to run hourly.
- Post-dedup verification (2026-09-13): all 67 affected `(question_id,
  sample_id)` pairs exist exactly once; kept-first records are complete
  ok-samples (non-empty, final-answer markers, `finish=stop`). The log only
  ever contains `status=ok` records (failures live in `failures.jsonl`), so a
  kept record can never be a failed/incomplete generation, and the dropped
  copies were equally valid second draws. math_0090-0106 retain complete
  5-sample sets; math_0107's 4/5 and 0108+ gaps are quota-pending state, not
  over-removal.

## 2026-09-13 10:24 UTC - automatic resume run
- 10:24-12:01 UTC: +169 samples (math +169); 1 quota errors, 224 failed, 94 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 11:15 UTC - automatic resume run
- 11:15-12:02 UTC: +71 samples (math +71); 1 quota errors, 220 failed, 81 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 12:15 UTC - automatic resume run
- 12:15-12:17 UTC: +4 samples (math +4); 1 quota errors, 216 failed, 5 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 13:15 UTC - automatic resume run
- 13:15-13:26 UTC: +22 samples (math +22); 1 quota errors, 194 failed, 7 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 14:15 UTC - automatic resume run
- 14:15-14:23 UTC: +21 samples (math +21); 1 quota errors, 173 failed, 0 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 15:15 UTC - automatic resume run
- 15:15-15:23 UTC: +17 samples (math +17); 1 quota errors, 156 failed, 0 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 16:15 UTC - automatic resume run
- 16:15-16:23 UTC: +13 samples (math +13); 1 quota errors, 143 failed, 5 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-14 (reorganization) — project restructured into folders
- Project restructured for clarity: `dataset/` (build/validate/spot-check),
  `generation/` (generate, check_remaining, daily_resume), `scoring/`
  (UQ modules + evaluate), `docs/` (README, research_log, CHANGELOG,
  questions_manifest, fallback_models). `config.py` and `.env` remain at the
  root; `data/`, `logs/`, `results/` unchanged.
- All moved Python modules got a `sys.path` shim pointing at the root;
  `daily_resume.ps1` paths, manifest write paths, README examples, and the
  Task Scheduler action were updated to the new locations.
- Verified before re-enabling automation: validate_dataset.py,
  check_remaining.py, and a manual daily_resume.ps1 run all work from their
  new folders; task re-enabled (state Ready, next run 16:45 IST).

## 2026-09-14 — GENERATION COMPLETE: 2250/2250 samples
- All three categories finished at 22:28 IST (last sample 16:58 UTC):
  factual 750, math 750, reasoning 750.
- Dataset integrity: 2,250 records, 0 duplicates, single model
  `groq/qwen/qwen3.8-27b` everywhere, temperature 0.7 everywhere.
- Totals: 569,238 tokens logged; 53.9 hours wall-clock (2026-09-12 11:04 UTC
  -> 2026-09-14 16:58 UTC); all collection via free-tier quota with
  resumable scheduled harvests.

## 2026-09-14 (Week 1 evaluation) — n-gram + TF-IDF baselines per professor
- Professor's requested methods implemented FIRST as the uncertainty
  baselines: `scoring/score_ngram_tfidf.py` computes per-question bigram
  Jaccard, trigram Jaccard, and TF-IDF cosine (global smoothed IDF over all
  2,250 samples, pure Python) uncertainties. Unigram Jaccard kept from
  `score_lexical.py` (--ngram 1); semantic entropy (NLI) kept as comparison.
- Correctness on the full set (majority vote, 5 samples): factual 85 correct /
  48 incorrect / 17 unresolved (29 questions have needs_review samples from
  conservative alias matching); math 144 / 6; reasoning 108 / 42.
- Full-data AUROC (uncertainty vs. majority-vote error), all categories:
  tfidf_cosine **0.835**, unigram 0.812, bigram 0.804, trigram 0.801,
  semantic_entropy 0.697. Best single category: factual tfidf **0.884**.
  Math AUROCs are noisy (only 6 incorrect questions).
- Report: `results/week1_auroc_report.md` (+ machine-readable
  `results/auroc.json`); per-method tables ordered bigram -> trigram -> tfidf
  first per the professor's preference.
- Pipeline order for reproducibility: score_correctness -> score_lexical
  (--ngram 1) -> score_ngram_tfidf -> score_semantic_entropy ->
  evaluate_methods. Semantic entropy ran with `--batch-size 64 --half` on the
  GTX 1650 (~50 min; the GPU is the bottleneck).
- Open item for discussion with the professor: 29 factual questions carry
  needs_review samples (`results/needs_review.jsonl`) and 17 factual questions
  are "unresolved" and currently excluded from the factual AUROC.
- Figures (2026-09-14, `scoring/make_plots.py` -> `results/figures/`):
  `auroc_bar.png` (AUROC per method, overall + per category, with
  incorrect/correct counts) and `uncertainty_boxplots.png` (tfidf/bigram/
  trigram/semantic distributions for incorrect vs correct questions).

## 2026-09-14 (outlier analysis) — confidently-wrong cases + grader fixes
- Ran `scoring/analyze_low_uncertainty.py` on the full data: questions with
  majority-vote incorrect AND low lexical uncertainty (bigram < 0.4 OR
  trigram < 0.5) -> `results/low_uncertainty_incorrect_cases.md`.
- Initial 4 cases were ALL factual; inspection showed 2 were grader artifacts:
  "George II" vs GT "GEORGE THE SECOND" and "Francois Hollande" vs
  "Francois Hollande" (accent). Fixed `uq_common.normalize_factual`: accent
  folding (NFKD) + Roman-numeral -> ordinal-word mapping ("ii" -> "the second").
  factual majority labels corrected 85->87 correct / 48->46 incorrect.
- Remaining 2 true confident-wrong cases:
  - factual_0081 (Little Red-Haired Girl): model insists "Snoopy" 4/5,
    "Peppermint Patty" 1/5 -- genuine confidently-wrong pattern (near-identical
    wrong answers).
  - factual_0059 (Dick Grayson "better known as who?"): model says "Nightwing"
    4/5 vs GT "Robin" -- ground-truth ambiguity (he is both); flagged for
    manual review rather than treated as model error.
- Takeaway for the professor: after grader fixes, only ~2/450 questions show
  the dangerous "confident wrong answer" pattern, both factual; n-gram and
  TF-IDF AUROCs improved slightly after label corrections (all: tfidf 0.845,
  unigram 0.825, bigram 0.820, trigram 0.817, semantic 0.706).

## 2026-09-14 (hypothesis test) — does NLI semantic entropy merge different numbers on math?
- Tested with `scoring/diagnose_math_semantic.py` ->
  `results/semantic_entropy_math_diagnosis.md`. Bottom quartile of math
  semantic entropy = 37 "confident" questions (entropy = 0).
- Only 2/37 have different extracted final numbers across samples; one of
  those (`math_0032`) is a unit-equivalence artifact of our extractor
  (6.5 hours vs 390 minutes = same value).
- The one genuine case, `math_0009` (12000 vs 7000 vs 2000): 4 of 7
  differing-number pairs were merged by bidirectional entailment with
  p up to 0.995 -- NLI cannot distinguish the different final numbers when
  the reasoning text is nearly identical.
- Verdict: hypothesis CONFIRMED but small incidence (~1/37 confident math
  questions); the failure mode matches prediction (same reasoning shape,
  different final number, high NLI similarity). No fix applied yet, per plan.

## 2026-09-14 (ensemble) — rank-averaged UQ ensembles vs. TF-IDF baseline
- Built `scoring/ensemble_uq.py` -> `results/ensemble_report.md` (+
  `results/ensemble_scores.jsonl`). 433 labeled questions with all 5 scores.
- Polarity verified for all methods (no flips needed). Scores rank-normalized
  per category; ensembles = rank averages. Weighted variants = logistic
  regression on the ranks with 5-fold stratified CV (OOF predictions).
- Results (AUROC all): tfidf 0.845 | unigram 0.825 | bigram 0.820 | trigram
  0.817 | semantic 0.706 | ensemble-unweighted-5 0.747 | ensemble-weighted-5
  0.745 | ensemble-unweighted-3 0.751 | ensemble-weighted-3 0.748.
- Verdict: **no ensemble beats TF-IDF alone**. The rank average dilutes the
  strong method with weaker, correlated ones. Per category the story differs:
  math ensembles win (best 0.814 vs tfidf 0.756) and reasoning too (best 0.679
  vs 0.630), but factual loses (best 0.884 vs tfidf 0.909). Logistic weights
  add nothing (methods highly correlated).
- Implication for the thesis: TF-IDF cosine is the strongest single signal;
  ensembles only help in categories where it is weak. A per-category method
  selector (or TF-IDF + numeric-agreement for math) is the natural next step.

## 2026-09-14 (selector) — cross-validated per-category method selector
- Built `scoring/selector_cv.py` -> `results/selector_cv_report.md` +
  `results/selector_cv_results.json`. Per category, 5-fold stratified CV
  (seed 42): winner chosen on the training split only (from tfidf, unigram,
  bigram, trigram, semantic entropy raw scores), evaluated on the held-out
  fold; averages over folds.
- Bug caught during the run: first version passed scores/labels to
  `uq.roc_auc` in swapped order, which silently produced garbage winners
  (semantic entropy "won" everywhere because its scores can exceed 1.0).
  Fixed; all numbers below are from the corrected run.
- Fold winners (stability): factual tfidf 5/5; math unigram 4/5 (one bigram);
  reasoning bigram 4/5 (one trigram).
- CV selector AUROC per category: factual 0.910, math 0.836, reasoning 0.667.
  Same-protocol TF-IDF CV: factual 0.910, math 0.740, reasoning 0.629.
- Macro-average: selector 0.8046 vs TF-IDF 0.7595 (+0.045). Pooled OOF-rank
  aggregate 0.7597 does not beat the in-sample full-data TF-IDF 0.8449
  (protocol mismatch; per-category ranking removes TF-IDF's cross-category
  scale advantage on factual).
- Verdict: the CV selector beats TF-IDF on math and reasoning, ties on
  factual, and wins the macro-average; math remains noisy (6 incorrect
  questions, fold AUCs 0.69-0.97).

## 2026-09-15 (math expansion) — set B to fix the math noise problem
- Motivation: only 6/150 math majority-vote errors made the math AUROC
  unstable (CV fold AUCs 0.69-0.97). Expanding the incorrect-math pool with
  fresh GSM8K questions.
- Built `dataset/build_math_expansion.py` -> `data/math_expansion.json`:
  **150 fresh GSM8K questions** (ids `mathb_0001..0150`, seed 100), validated
  with the original `check_math` + dedupe against the locked 454 (16 rejected:
  10 length, 6 near-duplicates). NOT merged into the main dataset.
- Tooling: `generate.py`, `check_remaining.py`, `score_correctness.py` gained
  a `--dataset` flag; `daily_resume.ps1` now runs the expansion set B after
  the main categories (same qwen3.8-27b / temp 0.7 / n=5 / sleep 22 flags).
- ETA: 750 samples ~ 420k tokens -> ~2-3 days of rolling free-tier quota
  (evening harvest windows). The 2026-09-15 16:45 scheduled run picked up the
  expansion automatically (13/750 samples in the first minutes) -- the
  automation worked end-to-end without a manual launch.
- Pending: once 750/750, run `score_correctness.py --dataset
  data/math_expansion.json` and report the incorrect count before any full
  AUROC rerun. Per plan, partial generation is not committed.

## 2026-09-16 (mathb complete) — expansion incorrect-count reported
- mathb generation finished 750/750 (single model, temp 0.7, 0 dups).
- Correctness on the 150 expansion questions: majority 147 correct / 3
  incorrect (22 incorrect samples of 750). Combined math pool (main + mathb =
  300 questions): 9 majority-incorrect (was 6), 62 incorrect samples.
- Honest finding: GSM8K is too easy for qwen3.8-27b (98% majority accuracy),
  so doubling the pool only grew the incorrect count 6 -> 9. The math noise
  problem is reduced but NOT solved; per-category math AUROC will still be
  dominated by a small positive set. Decision pending on whether to use the
  combined pool or keep main only.
- Artifacts: `results/mathb_correctness.jsonl`; mathb samples appended to
  `logs/generations.jsonl` (now committed).

## 2026-09-16 (escalation) — confidence-gated escalation pipeline, first pass
- Built `scoring/escalate.py` -> `results/escalation_report.md` +
  `results/escalation_decisions.jsonl`. Gate = the CV selector's per-category
  winner (factual tfidf, math unigram, reasoning bigram); the top-N%
  most-uncertain questions are escalated; threshold configurable via
  `--top-pct`.
- Second-model call is a STUB (tier pending professor sign-off), marked TODO
  in `escalate_to_larger_model`.
- Results (top 15%): escalation rate 15% per category; precision
  factual 1.00 / math 0.13 / reasoning 0.43; recall factual 0.43 / math 0.50
  / reasoning 0.24. Overall: precision 0.50, recall 0.35 vs 0.22 base error
  rate (2.3x error enrichment).
- Honest read: the gate is clearly better than random overall and excellent on
  factual (top-15% uncertainty == 100% errors), but weak on math (13%
  precision — only 3 of 23 escalations are errors) because math has few
  errors and the unigram gate fires on mostly-correct uncertain answers.

## 2026-09-16 (escalation sweep) — math-only threshold diagnostic
- Built `scoring/escalation_sweep_math.py`; computed unigram scores for mathb
  (`results/mathb_lexical.jsonl`) and swept top-pct {5,10,15,20,25} on the
  combined math pool (300 questions, 9 errors, base rate 0.03). Section
  appended to `results/escalation_report.md`.
- Results: precision 0.13 / 0.13 / 0.09 / 0.07 / 0.07; recall 0.22 / 0.44 /
  0.44 / 0.44 / 0.56. Best precision at the smallest thresholds and it only
  degrades from there; half the errors are low-uncertainty for unigram and
  unreachable at any threshold.
- Verdict: the math gate weakness is a DATA-VOLUME problem (9 positives), not
  a threshold-tuning problem. Fixes to consider later: a math-specific
  uncertainty signal (numeric disagreement) or a harder math source.
- Bug caught during the sweep: the first version forgot the category filter
  and pooled all 433 main questions with mathb (583/97); fixed, and the bogus
  report section was removed before re-running.

## 2026-09-16 (meeting prep) — week3 discussion agenda
- Added `docs/week3_meeting_prep.md`: one-page talking-points doc (separate
  from the formal mid_review_draft.md) with a one-paragraph "since last
  meeting" summary and three decisions for the professor — (a) model tier
  (1B/8B/20B plan vs available 27B/70B/120B), (b) math error-pool scarcity
  (9/300; accept small-n vs MATH dataset vs numeric-aware signal), and
  (c) escalation gate sign-off (0.50 precision, 2.3x enrichment, stubbed
  second-model call). Ends with the next step conditional on (a) and (b).
- All numbers pulled from existing results files; nothing recomputed.

## 2026-09-16 (numeric signal + prep rewrite) — math numeric-aware signal
- Built `scoring/math_numeric_signal.py`: extracts the final number from each
  sample (reusing the correctness extractor) and scores
  `numeric_disagreement = 1 - mode_fraction` for all 300 math questions
  (main + mathb). Output `results/math_numeric_signal.jsonl`; section appended
  to `results/escalation_report.md`; also wired into `evaluate_methods.py`
  (math-only row, AUROC 0.6487 on the main 150).
- Combined-pool evaluation (300 q, 9 errors): numeric_disagreement AUROC
  **0.651** vs unigram **0.794**; top-15% escalation precision **0.20** vs
  0.09 (recall 0.33 vs 0.44). The numeric signal is a better precision gate
  when it fires but a weaker standalone ranking signal (many consistent wrong
  answers show zero disagreement).
- Rewrote `docs/week3_meeting_prep.md`: only the model-tier item remains a
  "decision needed"; the math item is now "decided and done" (numeric signal,
  with the numbers above) and the escalation gate is "approved as designed".
- Decision recorded: numeric-aware signal chosen over the harder-dataset
  (MATH) route; combined numeric+unigram gate noted as the follow-up.

## 2026-09-16 (meeting prep) — week3 discussion agenda added
- Wrote `docs/week3_meeting_prep.md` (one-page talking-points doc, separate
  from the formal `mid_review_draft.md`): recap paragraph + three decisions
  (model tiers, math error-pool scarcity, escalation gate approval) each with
  evidence and options+tradeoffs, plus the conditional next step.

## 2026-09-15 (extended methods) — graph-based UQ measures from the base paper
- Implemented the remaining Lin et al. (TMLR 2024) graph measures in
  `scoring/score_graph_methods.py` on the ALREADY PERSISTED NLI pairwise
  matrix (`results/semantic_entropy.jsonl` -- no new GPU/NLI work):
  NumSets (connected components), Degree matrix (trace of Laplacian), EigV
  (sum of Laplacian eigenvalues), Eccentricity (max shortest-path).
- Full-data AUROC (all / factual / math / reasoning): num_sets 0.710 / 0.659 /
  0.515 / 0.633; degree_matrix = eigv 0.265 / 0.272 / 0.264 / 0.362 (INVERTED:
  they measure agreement, not uncertainty; flipped ~0.735 all);
  eccentricity 0.408 (also inverted, flipped 0.592).
- 9-method CV selector rerun (`results/selector_cv_report_9methods.md`):
  winners unchanged (tfidf/unigram/bigram), none of the 4 new methods won a
  single training fold, macro-AUROC unchanged at 0.8046. The new methods add
  no selector value on this model/dataset.
- Extended report: `results/extended_methods_report.md`; evaluate_methods now
  takes --graph-methods and honors --output; selector_cv takes --output.

## 2026-09-15 (write-up) — mid_review_draft TODOs filled
- Base-paper citation finalized: Zhen Lin, Shubhendu Trivedi, Jimeng Sun,
  "Generating with Confidence: Uncertainty Quantification for Black-box Large
  Language Models", TMLR, May 2024, arXiv:2305.19187 (verified against
  arXiv/OpenReview).
- Review pass over docs/mid_review_draft.md: all numbers re-checked against
  auroc.json (94/339 errors; 46/87 factual, 6/144 math, 42/108 reasoning),
  ensemble_report.md, selector_cv_report.md, extended_methods_report.md,
  semantic_entropy_math_diagnosis.md — no mismatches found.
- Section 9 updated: 9-method Lin et al. set now complete (with findings),
  and the mathb expansion generation noted as underway (results pending).

## 2026-09-13 (scheduling change) — hourly around-the-clock harvest
- `ThesisDailyResume` task extended from 16:45-21:45 IST only to **hourly,
  24h/day** (daily trigger 00:05 IST, 60-min repetition, 24h duration,
  `WakeToRun`, 12h execution limit). Night runs now harvest the overnight
  trickle of the rolling RPD window. Machine must be on AC power for
  wake-on-timer to work.
- Reverted 2026-09-14: back to the afternoon-to-night window only
  (daily 16:45 IST, hourly x6 = 16:45-21:45 IST); no overnight wake-ups.

## 2026-09-13 17:15 UTC - automatic resume run
- 17:15-17:24 UTC: +20 samples (math +20); 1 quota errors, 123 failed, 0 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 18:35 UTC - automatic resume run
- 18:35-18:47 UTC: +28 samples (math +28); 1 quota errors, 95 failed, 0 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 19:35 UTC - automatic resume run
- 19:35-19:53 UTC: +14 samples (math +14); 1 quota errors, 81 failed, 9 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-13 20:51 UTC - automatic resume run
- 20:51-21:03 UTC: +19 samples (math +19); 1 quota errors, 62 failed, 3 retry attempts; quota exhausted, resume tomorrow.

## 2026-09-14 11:15 UTC - automatic resume run
- 11:15-16:38 UTC: +812 samples (math +62, reasoning +750); 0 quota errors, 0 failed, 14 retry attempts; all incomplete categories attempted.

## 2026-09-14 17:15 UTC - automatic resume run
- All MAIN-dataset samples collected; expansion set B unchecked (driver exited on main-complete — bug, fixed in driver v2).

## 2026-09-15 15:15 UTC - automatic resume run
- All MAIN-dataset samples collected; expansion set B unchecked (driver exited on main-complete — bug, fixed in driver v2).

## 2026-09-15 15:38 UTC - automatic resume run
- All MAIN-dataset samples collected; expansion set B unchecked (driver exited on main-complete — bug, fixed in driver v2).

## 2026-09-15 (driver bugfix) - expansion now checked before early exit
- Fixed daily_resume.ps1: it exited as soon as the MAIN dataset was complete and never ran the mathb expansion block once main hit 2250/2250. The early-exit check now requires both main and expansion to be complete. Previous no-op runs (Sep 14 17:15 and Sep 15 15:15/15:38 UTC) left misleading 'all collected' lines; annotated above.

## 2026-09-15 15:42 UTC - automatic resume run
- 15:42-15:52 UTC: +23 samples (mathB +23); 1 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-15 16:15 UTC - automatic resume run
- 16:15-16:18 UTC: +8 samples (mathB +8); 1 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-15 17:15 UTC - automatic resume run
- 17:15-17:24 UTC: +13 samples (mathB +13); 1 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-15 17:52 UTC - automatic resume run
- 17:52-17:57 UTC: +10 samples (mathB +10); 1 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-15 20:41 UTC - automatic resume run
- 20:41-21:14 UTC: +58 samples (mathB +58); 1 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-16 08:54 UTC - automatic resume run
- 08:54-10:45 UTC: +238 samples (mathB +238); 0 quota errors, 0 failed, 0 retry attempts; all incomplete categories attempted.

## 2026-09-16 11:15 UTC - automatic resume run
- All samples collected (main 2250 + expansion); nothing left to generate.

## 2026-09-16 12:15 UTC - automatic resume run
- All samples collected (main 2250 + expansion); nothing left to generate.
