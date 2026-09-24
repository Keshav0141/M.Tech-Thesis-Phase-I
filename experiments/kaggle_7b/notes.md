# Kaggle 7B Experiment — Isolated Notes

## Purpose

Exploratory only: host a 7B-class model on Kaggle and generate answers
against it using the same high-level protocol as the main thesis pipeline
(N=5 samples per question, temperature 0.7).

This experiment is fully isolated:

- Reads `data/dataset.json` read-only.
- Never writes to `dataset/`, `generation/`, `scoring/`, `docs/`, `results/`,
  `logs/`, `data/`, `config.py`, or `.env`, and never touches
  `experiments/kaggle_1b/`.
- All outputs stay under `experiments/kaggle_7b/`.

## Current target

- Model: `Qwen2.5-7B-Instruct`
- Host: Kaggle notebook (T4x2)
- Access: ngrok tunnel URL `https://lard-barstool-contact.ngrok-free.dev/generate`
- Status: scaffolding complete; awaiting smoke test.

## Running log

- Scaffolded `client.py` from `experiments/kaggle_1b/client.py` with
  `LOG_PATH=logs/generations_7b.jsonl`, default `model=Qwen2.5-7B-Instruct`,
  and identical resumability/retry logic.
- 2026-09-24 smoke test (`--limit 10`, 50 requests) against
  `https://lard-barstool-contact.ngrok-free.dev/generate`: **50/50 ok,
  0 failed, 102.8 s total (~2.06 s/request incl. 1 s pacing)**.
- Resume verified: truncated log to 30 lines → re-run sent 20, skipped 30,
  restored to 50 lines.
- Retry/backoff verified against dead endpoint `http://127.0.0.1:9/generate`:
  5 attempts on new samples → all `FAILED ... after 3 attempts` with
  exponential backoff, no crash, nothing logged for those pairs.
- Full run (450 questions ×5 = 2,250 requests): **2,250/2,250 ok, 0 failed,
  267.4 min wall-clock (261.7 min active), ~7.0 s/request incl. 1 s pacing**,
  all via `https://lard-barstool-contact.ngrok-free.dev/generate`
  (dedup-clean, 450 questions ×5/5).

## Summary: 7B vs 1B vs 27B findings (exploratory, isolated)

- **Setup:** Qwen2.5-7B-Instruct hosted on Kaggle T4x2, fp16, ngrok tunnel,
  4h27m, 2,250 samples, 0 failures — same protocol as main pipeline
  (N=5, temperature 0.7). All generation and scoring stayed inside
  `experiments/kaggle_7b/` (custom `score_correctness_7b.py` /
  `score_uncertainty_7b.py` / `evaluate_7b.py` copies).

- **Correctness (majority vote, labeled only):** factual **50.4%**
  (68/135; 45.3% raw over 150), math **95.3%** (143/150), reasoning
  **70.7%** (106/150), overall **72.9%** (317/435; 70.4% raw over 450) —
  vs 1B 21.5%/81.3%/60.7%/55.7% and 27B 66.7%/96.0%/72.0%/78.2%.

- **AUROC (uncertainty vs incorrect):** TF-IDF overall **0.713** (factual
  **0.818**, math **0.699**, reasoning **0.583**) — vs 1B 0.668 and 27B
  0.847. Unigram 0.695 overall shows the same ordering. See
  `results/auroc_7b.json` / `results/correctness_7b.jsonl`.

- **Key takeaway:** 7B sits squarely between 1B and 27B on both correctness
  and UQ signal; math recovers nearly fully by 7B; the largest UQ jump is
  7B→27B not 1B→7B, suggesting a capability threshold effect.

- **Scope note:** This is exploratory and isolated in `experiments/kaggle_7b/`;
  no files in `results/`, `docs/mid_review_draft.md`, or the main pipeline
  were modified or merged.
