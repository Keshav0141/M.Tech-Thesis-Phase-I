# Kaggle 1B Experiment — Isolated Notes

## Purpose

Exploratory only: host a 1B-class model on Kaggle and generate answers
against it using the same high-level protocol as the main thesis pipeline
(N=5 samples per question, temperature 0.7).

This experiment is fully isolated:

- Reads `data/dataset.json` read-only.
- Never writes to `dataset/`, `generation/`, `scoring/`, `docs/`, `results/`,
  `logs/`, `data/`, `config.py`, or `.env`.
- All outputs stay under `experiments/kaggle_1b/`.

## Current target

- Model: `Qwen2.5-1.5B-Instruct`
- Host: Kaggle notebook
- Access: ngrok tunnel URL, pasted fresh each session as `KAGGLE_URL`
- Status: scaffolding complete; awaiting user review before any full run.

## Feasibility findings so far

- Factual: good out of the box.
- Math: good out of the box.
- Reasoning: needed a forced Yes/No response format.

## Running log

- Scaffolded `client.py` with resume-by-`(question_id, sample_id)`,
  retry/backoff, and `--limit N` for small smoke tests.
- 2026-09-23 smoke test (`--limit 10`, 50 requests) against
  `https://lard-barstool-contact.ngrok-free.dev/generate`: **50/50 ok,
  0 failed, ~120 s total (~2.4 s/request incl. 1 s pacing)**.
- Server schema discovered via `/openapi.json`: payload must be
  `{"question", "temperature", "max_new_tokens"}` (initial `prompt` /
  `max_tokens` guess returned HTTP 422); responses arrive as
  `{"response": ...}`. `client.py` updated accordingly.
- Resume verified twice: full re-run → `sent=0 skipped=50 failed=0`;
  simulated mid-run kill (log truncated to 30 lines) → `sent=20
  skipped=30 failed=0`, then log restored to 50 lines.
- Retry/backoff verified against a dead endpoint: 3 attempts → clean
  FAILED, no crash, nothing logged.
- Full-dataset estimate: 2,250 requests × ~2.4 s ≈ **~90 min**, plus any
  tunnel-drop retries.
- Full run completed: 2,250 requests deduped to 2,250 clean unique
  `(question_id, sample_id)` records in `logs/generations_1b.jsonl`.

## Summary: 1B vs 27B findings (exploratory, isolated)

- **Setup:** Qwen2.5-1.5B-Instruct hosted on Kaggle T4x2, ngrok tunnel
  (`https://lard-barstool-contact.ngrok-free.dev/generate`), full 450-question
  dataset, N=5 samples, temperature 0.7 — same protocol as main pipeline.
  All generation and scoring stayed inside `experiments/kaggle_1b/` (custom
  `score_correctness_1b.py` / `score_uncertainty_1b.py` / `evaluate_1b.py`
  copies).

- **Correctness (majority vote, labeled questions only):**
  factual **21.5%** (29/135), math **81.3%** (122/150), reasoning **60.7%**
  (91/150), overall **55.7%** (242/435) — vs 27B
  **66.7% / 96.0% / 72.0% / 78.2%** (`qwen/qwen3.8-27b` post-manual-review).

- **AUROC (uncertainty vs. incorrect):** TF-IDF overall **0.668** vs 27B
  **0.847**; factual UQ holds up relatively well (**0.839 vs 0.911**) despite
  correctness collapse; math (**0.629 vs 0.756**) and especially reasoning
  (**0.512 vs 0.630**, near random) degrade sharply. Unigram shows the same
  pattern. See `results/auroc_1b.json` / `results/correctness_1b.jsonl`.

- **Key takeaway:** UQ signal reliability appears model-scale-dependent,
  particularly for reasoning — smaller models don't just answer worse, their
  uncertainty becomes less measurable via self-consistency methods.

- **Scope note:** This is exploratory and isolated in `experiments/kaggle_1b/`;
  no files in `results/`, `docs/mid_review_draft.md`, or the main pipeline
  were modified or merged.
