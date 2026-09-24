"""Isolated Kaggle 7B generation client (exploratory only).

Reads questions from data/dataset.json READ-ONLY and sends them to a
Kaggle-hosted model over HTTP. All outputs stay inside
experiments/kaggle_7b/; this script never touches the main pipeline's
logs/, results/, scoring/, generation/, docs/, data/, config.py, or .env,
and never touches experiments/kaggle_1b/.

The Kaggle server URL changes every session (ngrok), so pass it explicitly:

    python client.py --kaggle-url https://xxxx.ngrok-free.app --limit 2

Resume behaviour: (question_id, sample_id) pairs already present in the
local JSONL log are skipped, so interrupted runs can be restarted safely.

Default model label: Qwen2.5-7B-Instruct
Default KAGGLE_URL: https://lard-barstool-contact.ngrok-free.dev/generate
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "dataset.json"
LOG_PATH = HERE / "logs" / "generations_7b.jsonl"
DEFAULT_KAGGLE_URL = "https://lard-barstool-contact.ngrok-free.dev/generate"

CATEGORY_INSTRUCTIONS = {
    "factual": "Answer the factual question. Respond with a short, single, unambiguous answer and no explanation.",
    "math": "Solve the math problem step by step. End your response with one line exactly in the form: 'Final answer: <number>'.",
    "reasoning": "Answer the reasoning question with Yes or No. End your response with one line exactly in the form: 'Final answer: <Yes/No>'.",
}


def load_questions(limit: int | None) -> list[dict]:
    """Read-only load of the shared dataset; never writes back to it."""
    with DATASET_PATH.open("r", encoding="utf-8") as handle:
        dataset = json.load(handle)
    questions = [q for q in dataset if q.get("validation_status") != "rejected"]
    if limit is not None:
        questions = questions[:limit]
    return questions


def load_done() -> set[tuple[str, int]]:
    """(question_id, sample_id) pairs already recorded in the local log."""
    done: set[tuple[str, int]] = set()
    if not LOG_PATH.exists():
        return done
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") == "ok":
                done.add((record.get("question_id"), int(record.get("sample_id", -1))))
    return done


def post_prompt(url: str, prompt: str, temperature: float, max_tokens: int,
                timeout_s: int, retries: int) -> str:
    """POST one prompt with retry/backoff. Raises on persistent failure.

    Payload matches the Kaggle FastAPI server's Req schema:
    {"question": str, "temperature": float, "max_new_tokens": int}.
    """
    payload = json.dumps({
        "question": prompt,
        "temperature": temperature,
        "max_new_tokens": max_tokens,
    }).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
            if isinstance(body, dict):
                for key in ("response", "response_text", "text", "answer", "output"):
                    if body.get(key):
                        return str(body[key])
                return json.dumps(body, ensure_ascii=False)
            return str(body)
        except Exception as error:  # noqa: BLE001 - tunnel drops are varied
            last_error = error
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"request failed after {retries + 1} attempts: {last_error}")


def append_record(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolated Kaggle 7B generation client.")
    parser.add_argument("--kaggle-url", default=DEFAULT_KAGGLE_URL, help="ngrok URL of the Kaggle server")
    parser.add_argument("--model", default="Qwen2.5-7B-Instruct")
    parser.add_argument("--limit", type=int, default=None, help="max questions (smoke test)")
    parser.add_argument("--n-samples", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds between calls")
    args = parser.parse_args()

    questions = load_questions(args.limit)
    done = load_done()
    print(f"questions: {len(questions)} | already done samples: {len(done)}", flush=True)
    print(f"logging to: {LOG_PATH}", flush=True)

    sent = skipped = failed = 0
    for question in questions:
        system = CATEGORY_INSTRUCTIONS.get(question.get("category", ""), "")
        prompt = f"{system}\n\nQuestion: {question['question_text']}".strip()
        for sample_id in range(args.n_samples):
            if (question["question_id"], sample_id) in done:
                skipped += 1
                continue
            try:
                text = post_prompt(args.kaggle_url, prompt, args.temperature,
                                   args.max_tokens, args.timeout, args.retries)
                append_record({
                    "status": "ok",
                    "question_id": question["question_id"],
                    "category": question.get("category"),
                    "model_name": args.model,
                    "sample_id": sample_id,
                    "response_text": text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "parameters": {"temperature": args.temperature,
                                   "max_tokens": args.max_tokens},
                })
                done.add((question["question_id"], sample_id))
                sent += 1
            except Exception as error:  # noqa: BLE001 - record and continue
                print(f"FAILED {question['question_id']} sample {sample_id}: {error}", flush=True)
                failed += 1
            time.sleep(args.sleep)
    print(f"sent={sent} skipped={skipped} failed={failed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
