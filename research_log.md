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
