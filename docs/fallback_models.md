# Fallback Models

Backup single-model candidates in case the primary model,
`qwen/qwen3.8-27b` (Groq), is retired or degraded during the thesis.
Not wired into the pipeline; use only after a documented substitution.

## Why this file exists

Precedents during this project:

- Groq retired **all Llama models** (Llama-3.2-1B / Llama-3.1-8B were the
  original plan).
- Gemini retired **gemini-2.0-flash, gemini-2.5-flash, and
  gemini-2.5-flash-lite** for new accounts (HTTP 404).
- Groq's GPT-5 horizon shifted model availability repeatedly.

The primary model may disappear any day; pick the nearest fallback below and
log the substitution.

## Substitutes (ordered)

### 1. `qwen/qwen3.6-27b` — closest sibling
- Same provider limits as the primary (verified on qwen3.8-27b): 200k
  tokens/day TPD, 1000 requests/day RPD, 1000 output tokens/minute (OTPM),
  `reasoning_effort="none"` accepted, maximum output ~1,536 tokens for
  reasoning questions.
- Expected quality/format closest to qwen3.8-27b. Only Groq model tested in
  the same size class with full instruct-mode support.
- Constraints: verbose CoT on math/reasoning (~300-900 tokens/sample),
  TPD-bound throughput ~300-500 samples/day; OTPM-safe pacing required
  (handle 429s with backoff as the wrapper already does).

### 2. `openai/gpt-oss-20b` — lightweight pilot-proven fallback
- Supported reasoning_effort values: `low|medium|high` (Groq API rejects
  `none` for this model family) — instruct with `low`.
- Constraints from pilot testing: ~207 tokens/sample for factual; expect
  roughly 400-700 tokens/sample for math/reasoning; same 200k TPD since it is
  any-model on Groq. Cleanest short answers of all tested models.
- Use when qwen quality degrades or qwen family retires; note that hidden
  reasoning tokens (`low`) are unavoidable here.

### 3. `openai/gpt-oss-120b` — bigger sibling, unverified
- Same OpenAI reasoning-model family; expect more tokens/sample than
  gpt-oss-20b and slightly better quality. Not yet tested; treat as backup's
  backup.
- Constraints: same as #2 plus higher token usage; probably slower per call.
- Recorded here so that a future re-run validates it before use (run a
  15-call feasibility test first like the qwen one).

## Substitution protocol (also noted in research_log.md)

If `qwen/qwen3.8-27b` becomes unavailable:

1. Stop the current generation run (it resumes cleanly).
2. Pick the first viable model from this list; validate it with a short
   feasibility probe (e.g., `python generation/generate.py --list-models` to confirm the
   model is still listed; then 5-15 test calls).
3. Re-run only the affected samples with the replacement model, using
   `--skip-started` so already-started questions keep a single model.
4. Record the substitution explicitly in the methodology section (model
   string per question/sample is the reproducibility guarantee; see
   `logs/generations.jsonl`).
5. Do not silently mix models within a question's sample set.

## What was ruled out (context, not fallbacks)

- Multi-provider pooling (Gemini + Groq + OpenRouter free): evaluated and
  rejected in favour of the professor's single-model requirement and zero
  compute-budget constraint. A paid top-up to Zen/OpenRouter was likewise
  rejected.
- OpenAI/OpenCode Zen trial as "free trial": not usable (workspace has no
  payment method; free tier locked to OpenCode app sessions).