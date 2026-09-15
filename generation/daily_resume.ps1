<#
daily_resume.ps1 - quota-aware daily driver for the thesis generation pipeline.

1. Runs `python check_remaining.py --json`. If nothing is missing, prints
   "All samples collected" and stops.
2. Otherwise runs generate.py for each incomplete category, in order
   factual -> math -> reasoning, with `--n 5 --temperature 0.8`.
3. Appends start/end time and a one-line summary (samples collected, quota
   errors) to research_log.md.
4. If a daily quota is hit and a category is still incomplete, logs
   "quota exhausted, resume tomorrow" and stops (no retry loops).

Full generator output is written to logs/resume_<timestamp>.log.
Schedule with Windows Task Scheduler; see README.md.
#>

$ErrorActionPreference = "Continue"
# generation/ folder -> project root is the parent directory
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $ProjectRoot

# Concurrency guard: refuse to run if another generation driver is active
# (manual run vs scheduled task overlap once produced 67 duplicate samples).
$otherDrivers = Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='powershell.exe'" |
    Where-Object { $_.ProcessId -ne $PID -and ($_.CommandLine -match "generate\.py|daily_resume\.ps1") }
if ($otherDrivers) {
    Write-Host "another generation driver is already running (PID $($otherDrivers.ProcessId -join ', ')); exiting."
    exit 0
}

$startUtc = (Get-Date).ToUniversalTime()
$stamp = $startUtc.ToString("yyyyMMdd_HHmmss")
$logsDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$runLog = Join-Path $logsDir ("resume_{0}.log" -f $stamp)
$researchLog = Join-Path $ProjectRoot "docs\research_log.md"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -LiteralPath $runLog -Value $line
}

function Append-ResearchLog {
    param([string]$Summary)
    Add-Content -LiteralPath $researchLog -Value ""
    Add-Content -LiteralPath $researchLog -Value ("## {0} UTC - automatic resume run" -f $startUtc.ToString("yyyy-MM-dd HH:mm"))
    Add-Content -LiteralPath $researchLog -Value $Summary
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { $pythonCommand = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCommand) { throw "python was not found on PATH. Fix PATH or edit daily_resume.ps1." }
$python = $pythonCommand.Source

Write-RunLog "daily resume started"

# --- 1. check remaining ------------------------------------------------------
$statusText = & $python (Join-Path $ProjectRoot "generation\check_remaining.py") --json | Out-String
if ($LASTEXITCODE -eq 0) {
    Write-RunLog "All samples collected. Nothing to do."
    Append-ResearchLog "- All 2250 samples collected; nothing left to generate."
    exit 0
}

try {
    $remaining = $statusText | ConvertFrom-Json
} catch {
    throw "Could not parse check_remaining.py output: $_"
}

$order = @("factual", "math", "reasoning")
$incomplete = @()
foreach ($category in $order) {
    if ($remaining.$category -and [int]$remaining.$category.samples_missing -gt 0) {
        $incomplete += $category
    }
}
if ($incomplete.Count -eq 0) {
    Write-RunLog "check_remaining.py reported work, but no category is incomplete; stopping."
    exit 0
}
Write-RunLog ("incomplete categories: {0}" -f ($incomplete -join ", "))

# --- 2. generate per incomplete category ------------------------------------
$totalCollected = 0
$totalRetries = 0
$totalFailed = 0
$quotaEvents = 0
$perCategory = @()
$stoppedReason = "all incomplete categories attempted"

try {
    foreach ($category in $incomplete) {
        Write-RunLog ("starting generate.py --category {0} --n 5 --temperature 0.7 --provider groq --model qwen/qwen3.8-27b --reasoning-effort none --sleep 22 (per-category caps from config)" -f $category)
        $output = & $python (Join-Path $ProjectRoot "generation\generate.py") --category $category --n 5 --temperature 0.7 `
            --provider groq --model qwen/qwen3.8-27b --reasoning-effort none `
            --sleep 22 2>&1 |
            Tee-Object -FilePath $runLog -Append | Out-String

        $collected = 0
        $failed = 0
        if ($output -match "calls completed\s*:\s*(\d+)") { $collected = [int]$Matches[1] }
        if ($output -match "failed samples\s*:\s*(\d+)") { $failed = [int]$Matches[1] }
        if ($output -match "retry attempts\s*:\s*(\d+)") { $totalRetries += [int]$Matches[1] }
        $quotaHere = ([regex]::Matches($output, "daily quota exhausted")).Count

        $totalCollected += $collected
        $totalFailed += $failed
        $quotaEvents += $quotaHere
        $perCategory += ("{0} +{1}" -f $category, $collected)
        Write-RunLog ("{0}: +{1} samples, {2} failed, {3} quota events" -f $category, $collected, $failed, $quotaHere)

        if ($quotaHere -gt 0) {
            $recheckText = & $python (Join-Path $ProjectRoot "generation\check_remaining.py") --json --category $category | Out-String
            $recheck = $recheckText | ConvertFrom-Json
            if ([int]$recheck.$category.samples_missing -gt 0) {
                $stoppedReason = "quota exhausted, resume tomorrow"
                Write-RunLog $stoppedReason
                break
            }
        }
    }

    # --- math expansion set B (data/math_expansion.json) ---
    $expansionPath = Join-Path $ProjectRoot "data\math_expansion.json"
    if (Test-Path -LiteralPath $expansionPath) {
        $expText = & $python (Join-Path $ProjectRoot "generation\check_remaining.py") --json --dataset $expansionPath | Out-String
        try { $exp = $expText | ConvertFrom-Json } catch { $exp = $null }
        $expMissing = 0
        if ($exp -and $exp.math -and [int]$exp.math.samples_missing -gt 0) {
            $expMissing = [int]$exp.math.samples_missing
        }
        if ($expMissing -gt 0) {
            Write-RunLog "starting generate.py --category math (expansion set B) ..."
            $outputExp = & $python (Join-Path $ProjectRoot "generation\generate.py") --category math --n 5 --temperature 0.7 `
                --provider groq --model qwen/qwen3.8-27b --reasoning-effort none `
                --sleep 22 --dataset $expansionPath 2>&1 |
                Tee-Object -FilePath $runLog -Append | Out-String
            $collectedExp = 0
            if ($outputExp -match "calls completed\s*:\s*(\d+)") { $collectedExp = [int]$Matches[1] }
            $quotaExp = ([regex]::Matches($outputExp, "daily quota exhausted")).Count
            $totalCollected += $collectedExp
            $quotaEvents += $quotaExp
            $perCategory += ("mathB +{0}" -f $collectedExp)
            Write-RunLog ("mathB: +{0} samples, {1} quota events" -f $collectedExp, $quotaExp)
        }
    }
} finally {
    # --- 3. write the one-line summary to research_log.md -------------------
    $endUtc = (Get-Date).ToUniversalTime()
    $summary = "- {0}-{1} UTC: +{2} samples ({3}); {4} quota errors, {5} failed, {6} retry attempts; {7}." -f `
        $startUtc.ToString("HH:mm"), $endUtc.ToString("HH:mm"), $totalCollected, ($perCategory -join ", "), `
        $quotaEvents, $totalFailed, $totalRetries, $stoppedReason
    Append-ResearchLog $summary
    Write-RunLog ("summary: {0}" -f $summary)
}

& $python (Join-Path $ProjectRoot "generation\check_remaining.py")
exit 0
