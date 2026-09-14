# M.Tech Thesis — Ensemble Uncertainty Quantification for LLMs

Pipeline for building a MECE question dataset (150 factual / 150 math /
150 reasoning) and collecting N=5 samples per question at temperature 0.7 from
Groq `qwen/qwen3.8-27b`, resumably on free-tier quotas.

## Layout

- `config.py` — paths, model names, token caps; API keys loaded from `.env`
  (must stay at project root)
- `dataset/` — `build_dataset.py`, `validate_dataset.py`, `apply_spot_check.py`
- `generation/` — `generate.py`, `check_remaining.py`, `daily_resume.ps1`
- `scoring/` — `uq_common.py`, `score_correctness.py`, `score_lexical.py`,
  `score_semantic_entropy.py`, `evaluate_methods.py`
- `docs/` — `README.md`, `research_log.md`, `CHANGELOG.md`,
  `questions_manifest.md`, `fallback_models.md`
- `data/dataset.json`, `logs/generations.jsonl`, `results/`

## Daily collection

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\generation\daily_resume.ps1"
```

`daily_resume.ps1` checks progress, runs only the incomplete categories
(factual → math → reasoning), appends a summary to `docs/research_log.md`, and
stops early with "quota exhausted, resume tomorrow" instead of retrying.

## Scheduling with Windows Task Scheduler

GUI: **Task Scheduler → Create Task**
- **Triggers**: Daily, e.g. 16:45
- **Actions → Start a program**:
  - Program: `powershell.exe`
  - Arguments: `-NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\generation\daily_resume.ps1"`
  - Start in: `D:\M.Tech Thesis Phase I`
- **Settings**: tick "Run task as soon as possible after a scheduled start is
  missed"; use "Run whether user is logged on or not" if the PC stays on.

PowerShell alternative:

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\generation\daily_resume.ps1"' `
  -WorkingDirectory "D:\M.Tech Thesis Phase I"
$trigger = New-ScheduledTaskTrigger -Daily -At 16:45
Register-ScheduledTask -TaskName "ThesisDailyResume" -Action $action -Trigger $trigger `
  -Description "Daily free-tier sample collection; auto-resumes missing samples"
```

Check or run it manually:

```powershell
Start-ScheduledTask -TaskName "ThesisDailyResume"
Get-ScheduledTask -TaskName "ThesisDailyResume" | Get-ScheduledTaskInfo
```

## Scoring pipeline (Week 1 evaluation)

```powershell
python scoring/score_correctness.py        # per-sample labels + majority vote
python scoring/score_lexical.py --ngram 1  # unigram Jaccard uncertainty
python scoring/score_ngram_tfidf.py        # bigram / trigram / TF-IDF uncertainty
python scoring/score_semantic_entropy.py   # NLI clustering entropy (GPU; --half for speed)
python scoring/evaluate_methods.py         # AUROC report -> results/week1_auroc_report.md
```

## Notes
- Task Scheduler needs `python` on PATH; `daily_resume.ps1` resolves it and
  fails with a clear message if missing.
- **Single-model plan (decided 2026-09-12):** the dataset uses Groq
  `qwen/qwen3.8-27b` with `reasoning-effort none` (per-category caps 1024/1024/1536,
  temperature 0.7, `--sleep 22`) for all 450 questions. No multi-provider
  fallback and no paid tier; Groq's free tier allows 200k tokens/day, ~1,000
  requests/day (rolling 24h), and 1,000 output tokens/minute (OTPM).
- Pacing: `--sleep 22` is the floor; the wrapper additionally waits
  `completion_tokens / 900 * 60` seconds after each call so the rolling OTPM
  stays under Groq's cap even for long math/reasoning completions. A full
  category run (~750 calls) takes roughly 4.5-6 hours, so the machine must stay
  awake; the run is resumable if interrupted.
- Per-run logs go to `logs/resume_<timestamp>.log`; successful/failed samples
  go to `logs/generations.jsonl` / `logs/failures.jsonl`. Earlier pilot data is
  archived under `logs/pilot_run/` and is not part of the final dataset.
