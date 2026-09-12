# M.Tech Thesis — Ensemble Uncertainty Quantification for LLMs

Pipeline for building a MECE question dataset (150 factual / 150 math /
150 reasoning) and collecting N=5 samples per question at temperature 0.8 from
Groq (primary) and Gemini (fallback), resumably on free-tier quotas.

## Layout
- `config.py` — paths, model names, token caps; API keys loaded from `.env`
- `build_dataset.py` — samples and filters TriviaQA / GSM8K / StrategyQA
- `validate_dataset.py` — structural, duplicate and balance checks
- `apply_spot_check.py` — applies manual spot-check results and replacements
- `generate.py` — resumable multi-sample generation wrapper
- `check_remaining.py` — per-category progress report (`--json`, `--list-gaps`)
- `daily_resume.ps1` — quota-aware daily collection driver
- `data/dataset.json`, `logs/generations.jsonl`, `questions_manifest.md`,
  `research_log.md`, `CHANGELOG.md`

## Daily collection

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\daily_resume.ps1"
```

`daily_resume.ps1` checks progress, runs only the incomplete categories
(factual → math → reasoning), appends a summary to `research_log.md`, and stops
early with "quota exhausted, resume tomorrow" instead of retrying.

## Scheduling with Windows Task Scheduler (once daily)

GUI: **Task Scheduler → Create Task**
- **Triggers**: Daily, e.g. 00:30
- **Actions → Start a program**:
  - Program: `powershell.exe`
  - Arguments: `-NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\daily_resume.ps1"`
  - Start in: `D:\M.Tech Thesis Phase I`
- **Settings**: tick "Run task as soon as possible after a scheduled start is
  missed"; use "Run whether user is logged on or not" if the PC stays on.

PowerShell alternative:

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "D:\M.Tech Thesis Phase I\daily_resume.ps1"' `
  -WorkingDirectory "D:\M.Tech Thesis Phase I"
$trigger = New-ScheduledTaskTrigger -Daily -At 00:30
Register-ScheduledTask -TaskName "ThesisDailyResume" -Action $action -Trigger $trigger `
  -Description "Daily free-tier sample collection; auto-resumes missing samples"
```

Check or run it manually:

```powershell
Start-ScheduledTask -TaskName "ThesisDailyResume"
Get-ScheduledTask -TaskName "ThesisDailyResume" | Get-ScheduledTaskInfo
```

## Notes
- Task Scheduler needs `python` on PATH; `daily_resume.ps1` resolves it and
  fails with a clear message if missing.
- Free-tier budgets: Groq `openai/gpt-oss-20b` 200k tokens/day. Gemini free
  tier is paced at ~15 requests/minute; `gemini-2.5-flash` is retired for new
  accounts, so the fallback is `gemini-3.5-flash-lite` (the previous
  `gemini-3.6-flash` had an unusually restrictive 20 requests/day cap).
- The wrapper auto-paces Gemini calls (`GEMINI_PRIMARY_SLEEP`), so fallback
  bursts do not burn retries on per-minute 429s.
- Per-run logs go to `logs/resume_<timestamp>.log`; successful/failed samples
  go to `logs/generations.jsonl` / `logs/failures.jsonl`.
