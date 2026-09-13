# Changelog

Dated entries tied to git commits.

## 2026-09-14
- Reorganized project into `dataset/`, `generation/`, `scoring/`, `docs/`
  folders; `config.py` and `.env` remain at root. All references (Python
  imports via sys.path shims, `daily_resume.ps1` paths, Task Scheduler
  action, README) updated and verified working before re-enabling automation.

## 2026-09-12 (commit 180ebc6)
- Project scaffold: `config.py`, `data/`, `logs/`, `requirements.txt`, `.gitignore`.
- `build_dataset.py`: 450-question MECE dataset (150 factual TriviaQA,
  150 math GSM8K, 150 reasoning StrategyQA) with per-category validation,
  exact/near-duplicate checks, rejection logging, and post-target scan.
- `questions_manifest.md` generated: counts before/after filtering, exclusion
  examples, MECE note, per-question metadata.
- `data/spot_check_sample.md`: 20 stratified questions for manual review.
- `generate.py`: Groq primary + Gemini fallback, exponential backoff, resumable
  JSONL logging, reasoning-model support, run summaries.
- `validate_dataset.py`: structural checks, duplicates, balance, difficulty and
  status spread, optional generation coverage report.
- Smoke-tested both providers (6 samples logged, 1 forced-fallback sample).

## 2026-09-12 (later, commit 207696c)
- Manual spot-check applied via `apply_spot_check.py`: `factual_0037` and
  `factual_0025` rejected (source-data errors, reasons logged in manifest),
  18 reviewed questions set to `spot_checked`, replacements pulled from
  TriviaQA with a stricter time-sensitivity guard (`factual_0151`, `factual_0153`;
  guard also rejected the time-relative auto-replacement `factual_0152`).
- `validate_dataset.py` re-passed: 450 active (150/150/150), 0 duplicates,
  0 structural errors; rejected entries retained in the dataset file.
- `generate.py` hardened: empty-response retry path, `ProviderExhausted`
  short-circuit on daily quota errors, retry counter in run summary.
- Generation run 1 (gpt-oss-20b, n=5, temp 0.8): factual 735/750 samples
  (725 Groq + 20 Gemini fallback, ~156k tokens, 316 retries); math/reasoning
  blocked by free-tier daily caps, to resume after reset.
- Curation pass 2: `reasoning_0106` rejected (time-sensitive wording),
  replacement `reasoning_0151` added; dataset re-validated 150/150/150 with
  4 rejected entries retained.
- Added `check_remaining.py` (per-category resume checker with exit codes).

## 2026-09-12 (decision: single model qwen3.8-27b)
- Chose `qwen/qwen3.8-27b` (Groq, instruct mode) as the sole dataset model;
  accepted a 5-6 day timeline with no multi-provider fallback or paid tier.
- `MAX_TOKENS_BY_CATEGORY` = 1024 for all categories; `--reasoning-effort none`
  is now sent (not omitted); default `--sleep 22` with dynamic OTPM pacing
  (completion_tokens/900 x 60 s floor increase).
- Archived all pilot/test artifacts to `logs/pilot_run/`.
- Started the factual run (750 calls) in the background; math/reasoning follow.
- `daily_resume.ps1` and `check_remaining.py` updated to the canonical flags.

## 2026-09-12 (reasoning prompt fix)
- Reasoning prompt shortened to "yes/no + one-sentence justification";
  retest on 5 questions: 5/5 parseable, 0 truncations, avg 174 completion
  tokens (was 369-1024+ with 40%/25% truncation).
- `MAX_TOKENS_BY_CATEGORY["reasoning"] = 1536`; per-category config caps now
  drive daily_resume and check_remaining (global override removed).
- Revised capacity: ~265 tokens/sample, ~754 samples/day under 200k TPD,
  ~3 days of budget instead of 5-6.
