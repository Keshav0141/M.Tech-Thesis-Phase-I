"""Central configuration for the M.Tech thesis dataset pipeline.

Secrets are read from .env and never hardcoded. Paths are absolute so the
scripts can be run from any working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DATASET_PATH = DATA_DIR / "dataset.json"
EXCLUDED_PATH = DATA_DIR / "excluded_examples.json"
SPOT_CHECK_PATH = DATA_DIR / "spot_check_sample.md"
GENERATIONS_PATH = LOGS_DIR / "generations.jsonl"
FAILURES_PATH = LOGS_DIR / "failures.jsonl"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

CATEGORIES = ("factual", "math", "reasoning")

SOURCE_DATASETS = {
    "factual": "TriviaQA (rc.nocontext)",
    "math": "GSM8K (main)",
    "reasoning": "StrategyQA",
}

TARGET_PER_CATEGORY = 150
RANDOM_SEED = 42
NEAR_DUPLICATE_THRESHOLD = 0.90

N_SAMPLES_DEFAULT = 5
TEMPERATURE_DEFAULT = 0.8
MAX_TOKENS_BY_CATEGORY = {
    "factual": 1024,
    "math": 1024,
    "reasoning": 1536,
}

# Single-model plan (decided 2026-09-12): qwen/qwen3.8-27b in instruct mode as
# the sole dataset model. Groq free tier for it: 1,000 requests/day, 200k
# tokens/day, and 1,000 output tokens/minute (OTPM) -- the throughput binding
# limit. ~22s between calls keeps OTPM under the cap for typical outputs.
# reasoning_effort="none" must be SENT (not omitted) to disable Qwen thinking.
GROQ_DEFAULT_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "none")
DEFAULT_SLEEP_SECONDS = 22.0
# Dynamic pacing target: after each call the wrapper waits at least
# completion_tokens / GROQ_OTPM_TARGET * 60 seconds, so the rolling output
# tokens/minute stays under Groq's 1,000 OTPM limit even for 1,000-token
# completions. The --sleep value acts as the floor.
GROQ_OTPM_TARGET = 900

# Groq reasoning models accept reasoning_effort; values differ by family
# (gpt-oss: low/medium/high; qwen3: none disables thinking).
REASONING_EFFORT_MODELS = ("openai/gpt-oss", "qwen/qwen3")

# Model availability drifts fast. Verified against the live APIs on 2026-09-12:
# Groq serves openai/gpt-oss-20b|120b and qwen/qwen3.x (no Llama models anymore).
# Gemini: gemini-2.0-flash, gemini-2.5-flash and gemini-2.5-flash-lite are all
# retired for new accounts (404); gemini-3.6-flash has only 20 requests/day.
# The dataset uses qwen/qwen3.8-27b on Groq as the sole model; Gemini remains
# available only for ad-hoc runs, not for the dataset.
# Re-check with: python generate.py --list-models
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Free-tier pacing when Gemini is the primary provider (requests/minute cap).
GEMINI_PRIMARY_SLEEP = 4.5

CATEGORY_INSTRUCTIONS = {
    "factual": (
        "Answer the factual question. Respond with a short, single, unambiguous "
        "answer and no explanation. End your response with one line exactly in "
        "the form: 'Final answer: <answer>'."
    ),
    "math": (
        "Solve the math word problem step by step. End your response with one "
        "line exactly in the form: 'Final answer: <number>'."
    ),
    "reasoning": (
        "Answer with just yes/no followed by a one-sentence justification. "
        "End your response with one line exactly in the form: "
        "'Final answer: yes' or 'Final answer: no'."
    ),
}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name} in {PROJECT_ROOT / '.env'}. "
            "Add it there (never commit that file)."
        )
    return value


def get_groq_api_key() -> str:
    return _require_env("GROQ_API_KEY")


def get_gemini_api_key() -> str:
    return _require_env("GEMINI_API_KEY")
