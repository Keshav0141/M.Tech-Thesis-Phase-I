"""Resumable multi-sample generation wrapper for the thesis dataset.

Primary provider: Groq. Fallback: Gemini (used only when Groq keeps failing
after retries, unless --no-fallback is set).

Every raw response is appended to logs/generations.jsonl. Runs are resumable:
a (question_id, provider, model_name, sample_id) tuple that already exists in
the log is skipped, so interrupted free-tier runs can simply be restarted.

Examples:
    python generate.py --list-models
    python generate.py --category factual --limit 5 --n 2 --dry-run
    python generate.py --model llama-3.1-8b-instant --n 5 --temperature 0.8
    python generate.py --provider gemini --model gemini-2.0-flash --n 5
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import config


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dataset(limit: int | None, categories: list[str]) -> list[dict]:
    if not config.DATASET_PATH.exists():
        raise SystemExit(f"{config.DATASET_PATH} not found. Run build_dataset.py first.")
    dataset = json.loads(config.DATASET_PATH.read_text(encoding="utf-8"))
    selected = [
        q
        for q in dataset
        if q["category"] in categories and q.get("validation_status") != "rejected"
    ]
    if limit is not None:
        selected = selected[:limit]
    return selected


def load_completed() -> set[tuple[str, str, str, int]]:
    completed: set[tuple[str, str, str, int]] = set()
    if not config.GENERATIONS_PATH.exists():
        return completed
    with config.GENERATIONS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") == "ok":
                completed.add(
                    (
                        record["question_id"],
                        record.get("provider", ""),
                        record.get("model_name", ""),
                        int(record.get("sample_id", -1)),
                    )
                )
    return completed


def append_jsonl(path, record: dict):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def status_code_of(error: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(error, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def is_auth_error(error: Exception) -> bool:
    return status_code_of(error) in (401, 403)


class ProviderExhausted(Exception):
    """Daily quota gone; retrying today is pointless."""


def is_daily_quota(error: Exception) -> bool:
    text = str(error).lower()
    return (
        "tokens per day" in text
        or "requests per day" in text
        or "per-day" in text
        or " tpd" in text
        or "tpd)" in text
    )


def is_rate_limit(error: Exception) -> bool:
    if status_code_of(error) == 429:
        return True
    text = str(error).lower()
    return any(marker in text for marker in ("rate limit", "resource_exhausted", "quota", "429"))


class GroqProvider:
    name = "groq"

    def __init__(self, model: str, reasoning_effort: str | None = None):
        from groq import Groq

        self.model = model
        self.reasoning_effort = reasoning_effort
        self.client = Groq(api_key=config.get_groq_api_key(), max_retries=0)

    def generate(self, prompt: str, system: str, temperature: float, max_tokens: int):
        kwargs = {}
        if self.reasoning_effort and self.model.startswith(config.REASONING_EFFORT_MODELS):
            kwargs["reasoning_effort"] = self.reasoning_effort
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError(
                "empty response content (reasoning model likely exhausted max_tokens; "
                "raise --max-tokens or lower --reasoning-effort)"
            )
        usage = response.usage
        details = getattr(usage, "completion_tokens_details", None)
        token_usage = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "reasoning_tokens": getattr(details, "reasoning_tokens", None),
        }
        return text, token_usage

    @staticmethod
    def list_models() -> list[str]:
        from groq import Groq

        client = Groq(api_key=config.get_groq_api_key(), max_retries=0)
        return sorted(model.id for model in client.models.list().data)


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str):
        from google import genai

        self.model = model
        self.client = genai.Client(api_key=config.get_gemini_api_key())

    def generate(self, prompt: str, system: str, temperature: float, max_tokens: int):
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        text = (response.text or "").strip()
        usage = getattr(response, "usage_metadata", None)
        token_usage = {
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "completion_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
            "reasoning_tokens": getattr(usage, "thoughts_token_count", None),
        }
        return text, token_usage

    @staticmethod
    def list_models() -> list[str]:
        from google import genai

        client = genai.Client(api_key=config.get_gemini_api_key())
        names = []
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if not actions or "generateContent" in actions:
                names.append(model.name.replace("models/", ""))
        return sorted(set(names))


def call_with_retries(provider, prompt, system, temperature, max_tokens, max_retries, base_delay, run_id, question_id, sample_id):
    """Call a provider with exponential backoff. Returns (text, usage, attempts) or raises."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            text, usage = provider.generate(prompt, system, temperature, max_tokens)
            return text, usage, attempt
        except Exception as error:  # provider SDKs raise varied exception types
            last_error = error
            if is_auth_error(error):
                raise SystemExit(
                    f"[{provider.name}] authentication failed ({error}). Check the API key in .env."
                ) from error
            if is_daily_quota(error):
                raise ProviderExhausted(str(error)) from error
            rate_limited = is_rate_limit(error)
            if attempt == max_retries:
                break
            if "empty response content" in str(error):
                delay = 1.0 * attempt + random.uniform(0, 0.5)
            else:
                delay = min(base_delay * (2 ** (attempt - 1)), 60.0) + random.uniform(0, 1.0)
            reason = "rate limit" if rate_limited else type(error).__name__
            print(f"    retry {attempt}/{max_retries - 1} for {question_id} sample {sample_id} ({reason}) in {delay:.1f}s")
            time.sleep(delay)
    raise last_error if last_error else RuntimeError("provider call failed")


def build_providers(args) -> list:
    providers = []
    if args.provider in ("auto", "groq"):
        effort = None if args.reasoning_effort == "none" else args.reasoning_effort
        providers.append(GroqProvider(args.model or config.GROQ_DEFAULT_MODEL, reasoning_effort=effort))
    if args.provider in ("auto", "gemini"):
        model = args.model if args.provider == "gemini" else args.fallback_model
        providers.append(GeminiProvider(model or config.GEMINI_DEFAULT_MODEL))
    if args.no_fallback and len(providers) > 1:
        providers = providers[:1]
    return providers


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate N samples per question, resumably.")
    parser.add_argument("--category", choices=config.CATEGORIES, help="restrict to one category")
    parser.add_argument("--limit", type=int, help="max questions to process this run")
    parser.add_argument("--n", type=int, default=config.N_SAMPLES_DEFAULT, help="samples per question")
    parser.add_argument("--temperature", type=float, default=config.TEMPERATURE_DEFAULT)
    parser.add_argument("--model", help=f"model id (default groq: {config.GROQ_DEFAULT_MODEL})")
    parser.add_argument("--fallback-model", default=config.GEMINI_DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high"],
        default=config.GROQ_REASONING_EFFORT,
        help="for Groq reasoning models (gpt-oss, qwen3); 'none' omits the parameter",
    )
    parser.add_argument("--provider", choices=["auto", "groq", "gemini"], default="auto")
    parser.add_argument("--no-fallback", action="store_true", help="never fall back to the secondary provider")
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--backoff-base", type=float, default=5.0, help="seconds, doubled per retry")
    parser.add_argument("--sleep", type=float, default=0.0, help="seconds between successful calls")
    parser.add_argument("--max-tokens", type=int, help="override per-category cap")
    parser.add_argument("--force", action="store_true", help="regenerate samples already logged")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    args = parser.parse_args()

    if args.list_models:
        for provider_cls in (GroqProvider, GeminiProvider):
            try:
                print(f"[{provider_cls.name}] " + ", ".join(provider_cls.list_models()))
            except Exception as error:
                print(f"[{provider_cls.name}] could not list models: {error}")
        return 0

    categories = [args.category] if args.category else list(config.CATEGORIES)
    questions = load_dataset(args.limit, categories)
    providers = build_providers(args)
    completed = set() if args.force else load_completed()
    run_id = uuid.uuid4().hex[:12]

    planned = 0
    for question in questions:
        for sample_id in range(args.n):
            if (question["question_id"], providers[0].name, providers[0].model, sample_id) in completed:
                continue
            planned += 1

    print(f"[generate] run {run_id}: {len(questions)} questions, n={args.n}, "
          f"temperature={args.temperature}, primary={providers[0].name}/{providers[0].model}")
    if len(providers) > 1:
        print(f"[generate] fallback: {providers[1].name}/{providers[1].model}")
    print(f"[generate] calls planned this run: {planned} (already logged samples are skipped)")
    if args.dry_run:
        return 0

    calls_made = skipped = failures = 0
    tokens_total = 0
    fallback_calls = 0
    retries_total = 0
    exhausted_providers: set[str] = set()
    start = time.time()

    for index, question in enumerate(questions, start=1):
        qid = question["question_id"]
        category = question["category"]
        system = config.CATEGORY_INSTRUCTIONS[category]
        max_tokens = args.max_tokens or config.MAX_TOKENS_BY_CATEGORY[category]
        label = f"[{index}/{len(questions)}] {qid}"

        for sample_id in range(args.n):
            if not args.force and (qid, providers[0].name, providers[0].model, sample_id) in completed:
                skipped += 1
                continue

            last_error: Exception | None = None
            for provider_index, provider in enumerate(providers):
                if provider.name in exhausted_providers:
                    continue
                sample_start = time.time()
                try:
                    text, usage, attempts = call_with_retries(
                        provider,
                        question["question_text"],
                        system,
                        args.temperature,
                        max_tokens,
                        args.max_retries,
                        args.backoff_base,
                        run_id,
                        qid,
                        sample_id,
                    )
                except ProviderExhausted as error:
                    exhausted_providers.add(provider.name)
                    print(f"  {provider.name} daily quota exhausted for today; switching to fallback for the rest of this run")
                    last_error = error
                    continue
                except Exception as error:
                    last_error = error
                    print(f"  {label} sample {sample_id}: {provider.name} failed ({error})")
                    continue

                record = {
                    "run_id": run_id,
                    "status": "ok",
                    "question_id": qid,
                    "category": category,
                    "provider": provider.name,
                    "model_name": provider.model,
                    "sample_id": sample_id,
                    "response_text": text,
                    "timestamp": utc_now(),
                    "token_usage": usage,
                    "parameters": {
                        "temperature": args.temperature,
                        "max_tokens": max_tokens,
                        "instruction": system,
                    },
                    "latency_s": round(time.time() - sample_start, 3),
                    "attempts": attempts,
                }
                append_jsonl(config.GENERATIONS_PATH, record)
                calls_made += 1
                retries_total += attempts - 1
                tokens_total += usage.get("total_tokens") or 0
                if provider_index > 0:
                    fallback_calls += 1
                    print(f"  {label} sample {sample_id}: served by fallback {provider.name}/{provider.model}")
                sleep_seconds = args.sleep
                if sleep_seconds == 0 and provider.name == "gemini":
                    sleep_seconds = config.GEMINI_PRIMARY_SLEEP
                if sleep_seconds:
                    time.sleep(sleep_seconds)
                break
            else:
                failures += 1
                append_jsonl(
                    config.FAILURES_PATH,
                    {
                        "run_id": run_id,
                        "status": "failed",
                        "question_id": qid,
                        "category": category,
                        "sample_id": sample_id,
                        "timestamp": utc_now(),
                        "error": str(last_error),
                        "attempted_providers": [f"{p.name}/{p.model}" for p in providers],
                    },
                )
                print(f"  {label} sample {sample_id}: FAILED after all providers")

        print(f"{label} done")

    elapsed = time.time() - start
    print("[generate] run summary")
    print(f"  run_id          : {run_id}")
    print(f"  calls completed : {calls_made}")
    print(f"  samples skipped : {skipped}")
    print(f"  fallback calls  : {fallback_calls}")
    print(f"  retry attempts  : {retries_total}")
    print(f"  failed samples  : {failures}")
    print(f"  total tokens    : {tokens_total}")
    print(f"  elapsed         : {elapsed:.1f}s")
    print(f"  log             : {config.GENERATIONS_PATH}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
