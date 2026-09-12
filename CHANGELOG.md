# Changelog

Dated entries tied to git commits.

## 2026-09-12
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
