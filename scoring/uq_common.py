"""Shared helpers for the UQ scoring pipeline.

Used by score_correctness.py, score_lexical.py, score_semantic_entropy.py and
evaluate_methods.py. Kept dependency-light on purpose; only config and stdlib.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

RESULTS_DIR = config.PROJECT_ROOT / "results"

ARTICLE_RE = re.compile(r"\b(a|an|the)\b")
PAREN_RE = re.compile(r"\([^)]*\)")
TITLE_RE = re.compile(r"\b(king|queen|sir|dame|dr|president|pope|saint|st|mr|mrs|ms|prime minister)\b")
PUNCT_RE = re.compile(r"[^\w\s]")
IGNORED_EXTRA_TOKENS = {
    "of", "the", "a", "an", "in", "at", "on", "for", "and", "to", "by", "from",
    "with", "year", "years", "series", "film", "movie", "novel", "book",
}

ROMAN_TO_ORDINAL = {
    "ii": "the second", "iii": "the third", "iv": "the fourth", "v": "the fifth",
    "vi": "the sixth", "vii": "the seventh", "viii": "the eighth", "ix": "the ninth",
    "x": "the tenth", "xi": "the eleventh", "xii": "the twelfth",
    "xiii": "the thirteenth", "xiv": "the fourteenth", "xv": "the fifteenth",
    "xvi": "the sixteenth", "xvii": "the seventeenth", "xviii": "the eighteenth",
    "xix": "the nineteenth", "xx": "the twentieth",
}
ROMAN_RE = re.compile(r"\b(ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi|xvii|xviii|xix|xx)\b", re.IGNORECASE)


def fold_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
FINAL_RE = re.compile(r"final answer\s*[:\-]?\s*(.+)", re.IGNORECASE | re.DOTALL)
FINAL_YESNO_RE = re.compile(r"final answer\s*[:\-]?\s*\**\s*(yes|no)\b", re.IGNORECASE)


def ensure_results_dir() -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    return RESULTS_DIR


def load_questions(path=None) -> list[dict]:
    dataset_path = Path(path) if path else config.DATASET_PATH
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [q for q in dataset if q.get("validation_status") != "rejected"]


def load_samples(model: str | None = None, provider: str | None = None):
    """Return (samples_by_question, provider_model_counts)."""
    samples: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()
    if not config.GENERATIONS_PATH.exists():
        return samples, counts
    with config.GENERATIONS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") != "ok":
                continue
            key = (record.get("provider", "?"), record.get("model_name", "?"))
            counts[key] += 1
            if model and record.get("model_name") != model:
                continue
            if provider and record.get("provider") != provider:
                continue
            samples[record["question_id"]].append(record)
    for question_id in samples:
        samples[question_id].sort(key=lambda r: int(r.get("sample_id", -1)))
    return samples, counts


def resolve_filters(args, counts: Counter):
    """Warn and pick the most frequent model if the log mixes several."""
    if args.model or args.provider or len(counts) <= 1:
        return args.model, args.provider
    (provider, model), _count = counts.most_common(1)[0]
    print(
        f"[warn] generation log contains {len(counts)} provider/model combos; "
        f"evaluating the most frequent: {provider}/{model}"
    )
    return model, provider


def extract_final(text: str) -> str | None:
    """Text following the last 'Final answer:' marker, first line only."""
    if not text:
        return None
    matches = FINAL_RE.findall(text)
    if not matches:
        return None
    tail = matches[-1].strip()
    if not tail:
        return None
    return tail.splitlines()[0].strip() or None


def extract_number(text: str) -> float | None:
    """Final numeric answer, preferring the text after 'Final answer:'."""
    if not text:
        return None
    final = extract_final(text)
    scope = final or text
    numbers = NUMBER_RE.findall(scope)
    if not numbers and final:
        numbers = NUMBER_RE.findall(text)
    if not numbers:
        return None
    try:
        return float(numbers[-1].replace(",", ""))
    except ValueError:
        return None


def extract_yes_no(text: str) -> str | None:
    if not text:
        return None
    matches = FINAL_YESNO_RE.findall(text)
    if matches:
        return matches[-1].lower()
    words = re.findall(r"\b(yes|no)\b", text, re.IGNORECASE)
    return words[-1].lower() if words else None


def normalize_factual(text: str | None) -> str:
    if text is None:
        return ""
    text = fold_accents(text.lower())
    text = ROMAN_RE.sub(lambda match: ROMAN_TO_ORDINAL[match.group(1).lower()], text)
    text = PAREN_RE.sub(" ", text)
    text = TITLE_RE.sub(" ", text)
    text = PUNCT_RE.sub(" ", text)
    text = ARTICLE_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def classify_factual(prediction: str | None, ground_truth: str) -> str:
    """correct / needs_review / incorrect / no_extraction for factual answers."""
    normalized_pred = normalize_factual(prediction)
    normalized_gt = normalize_factual(ground_truth)
    if not normalized_pred:
        return "no_extraction"
    if normalized_pred == normalized_gt:
        return "correct"
    pred_numbers = set(re.findall(r"\d+(?:\.\d+)?", normalized_pred))
    gt_numbers = set(re.findall(r"\d+(?:\.\d+)?", normalized_gt))
    if pred_numbers and pred_numbers == gt_numbers:
        return "correct"
    pred_tokens = set(normalized_pred.split())
    gt_tokens = set(normalized_gt.split())
    if pred_tokens and gt_tokens and (pred_tokens <= gt_tokens or gt_tokens <= pred_tokens):
        extra = pred_tokens ^ gt_tokens
        if extra <= IGNORED_EXTRA_TOKENS or all(
            token in IGNORED_EXTRA_TOKENS or re.fullmatch(r"\d+(?:\.\d+)?", token) for token in extra
        ):
            return "correct"
    if normalized_gt in normalized_pred or normalized_pred in normalized_gt:
        return "needs_review"
    if pred_tokens and gt_tokens:
        jaccard = len(pred_tokens & gt_tokens) / len(pred_tokens | gt_tokens)
        if jaccard >= 0.5:
            return "needs_review"
    return "incorrect"


def classify_math(prediction: str | None, ground_truth: str):
    """Return (label, extracted_number)."""
    predicted = extract_number(prediction or "")
    if predicted is None:
        return "no_extraction", None
    try:
        expected = float(str(ground_truth).replace(",", ""))
    except ValueError:
        return "incorrect", predicted
    if abs(predicted - expected) <= max(1e-6, abs(expected) * 1e-6):
        return "correct", predicted
    return "incorrect", predicted


def classify_reasoning(prediction: str | None, ground_truth: str):
    """Return (label, extracted_yes_no)."""
    predicted = extract_yes_no(prediction or "")
    if predicted is None:
        return "no_extraction", None
    expected = str(ground_truth).strip().lower()
    return ("correct" if predicted == expected else "incorrect"), predicted


def write_jsonl(path, rows: list[dict]) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def roc_auc(labels: list[int], scores: list[float]):
    """Tie-aware ROC-AUC (Mann-Whitney U). Returns (auc, n_pos, n_neg)."""
    pairs = [
        (float(score), int(label))
        for score, label in zip(scores, labels)
        if score is not None and label is not None
    ]
    if not pairs:
        return None, 0, 0
    positives = sum(label for _, label in pairs)
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return None, positives, negatives
    order = sorted(range(len(pairs)), key=lambda i: pairs[i][0])
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and pairs[order[end + 1]][0] == pairs[order[index]][0]:
            end += 1
        average_rank = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            ranks[order[position]] = average_rank
        index = end + 1
    rank_sum_positives = sum(ranks[i] for i in range(len(pairs)) if pairs[i][1] == 1)
    auc = (rank_sum_positives - positives * (positives + 1) / 2.0) / (positives * negatives)
    return auc, positives, negatives


def tokenize(text: str) -> list[str]:
    return normalize_factual(text).split()


def ngram_set(tokens: list[str], n: int) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def enable_utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
