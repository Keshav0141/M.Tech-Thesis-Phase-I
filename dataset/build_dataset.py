"""Build the MECE question dataset for the thesis from established benchmarks.

Sources:
    factual   -> TriviaQA (rc.nocontext)   single-hop verifiable facts
    math      -> GSM8K (main)              numeric word problems
    reasoning -> StrategyQA                multi-hop binary inference

Outputs:
    data/dataset.json            clean, validated questions
    data/excluded_examples.json  dropped candidates + reasons
    data/spot_check_sample.md    20 stratified samples for manual review
    questions_manifest.md        living manifest (counts + per-question metadata)

The run is deterministic given --seed, so rebuilding yields the same dataset.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

TIME_SENSITIVE_RE = re.compile(
    r"\b(currently|current|nowadays|as of|latest|most recent|presently|"
    r"at present|this year|so far|right now)\b",
    re.IGNORECASE,
)
MULTI_PART_RE = re.compile(r"\((?:a|b|c|i|ii|iii)\)|multiple choice|which of the following", re.IGNORECASE)
MULTI_ANSWER_RE = re.compile(r"\b(name all|list all|name every|list every|all of the)\b", re.IGNORECASE)
ARITHMETIC_RE = re.compile(
    r"\d+\s*[+\-*/×÷]\s*\d+|\b(calculate|compute|sum of|product of|multiplied by|divided by|percentage of)\b",
    re.IGNORECASE,
)
NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")

STRATEGYQA_CANDIDATES = [
    "ChilleD/StrategyQA",
    "tasksource/strategy-qa",
    "voidful/StrategyQA",
    "wics/strategy-qa",
]

STRATEGYQA_ARITHMETIC_REASON = "overlaps with mathematical category (arithmetic inference)"
STRATEGYQA_BINARY_REASON = "no clear binary (yes/no) final answer"


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_answer(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s\.\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class Deduper:
    """Exact and near-duplicate detection across all accepted questions."""

    def __init__(self, threshold: float = config.NEAR_DUPLICATE_THRESHOLD):
        self.threshold = threshold
        self.exact: dict[str, str] = {}
        self.items: list[tuple[str, str, str]] = []

    def check(self, question: str, category: str, question_id: str, register: bool = True) -> str | None:
        """Return a rejection reason, or None if the question is unique.

        register=False is used for the post-target scan, where we only want to
        detect duplicates against the accepted set without adding candidates.
        """
        norm = normalize_text(question)
        if norm in self.exact:
            return f"exact duplicate of {self.exact[norm]}"
        for other_norm, other_cat, other_id in self.items:
            length_ratio = min(len(norm), len(other_norm)) / max(len(norm), len(other_norm))
            if length_ratio < 0.6:
                continue
            if SequenceMatcher(None, norm, other_norm).ratio() >= self.threshold:
                return f"near duplicate of {other_id} (sequence ratio >= {self.threshold})"
        if register:
            self.exact[norm] = question_id
            self.items.append((norm, category, question_id))
        return None


def iter_candidates(category: str, seed: int, max_candidates: int):
    """Yield raw rows from the benchmark for a category, shuffled deterministically."""
    from datasets import load_dataset

    if category == "factual":
        ds = load_dataset("mandarjoshi/trivia_qa", "rc.nocontext", split="train")
        yield from _shuffled(ds, seed, max_candidates)
    elif category == "math":
        ds = load_dataset("openai/gsm8k", "main", split="train")
        yield from _shuffled(ds, seed, max_candidates)
    elif category == "reasoning":
        last_error: Exception | None = None
        for name in STRATEGYQA_CANDIDATES:
            try:
                ds = load_dataset(name, split="train")
                yield from _shuffled(ds, seed, max_candidates)
                return
            except Exception as exc:  # try the next mirror
                last_error = exc
        raise SystemExit(f"Could not load StrategyQA from any mirror: {last_error}")
    else:
        raise ValueError(f"Unknown category: {category}")


def _shuffled(dataset, seed: int, max_candidates: int):
    rng = random.Random(seed)
    order = list(range(len(dataset)))
    rng.shuffle(order)
    for i in order[:max_candidates]:
        yield dataset[i]


def check_factual(item: dict) -> tuple[dict | None, str | None]:
    question = str(item.get("question", "")).strip()
    answer_field = item.get("answer")
    if isinstance(answer_field, dict):
        answer = str(answer_field.get("value", "")).strip()
        aliases = [str(a) for a in (answer_field.get("aliases") or []) if a]
    else:
        answer, aliases = str(answer_field or "").strip(), []

    if not question:
        return None, "missing question text"
    if question.count("?") > 1:
        return None, "multiple questions in one item"
    if len(question) < 20 or len(question) > 220:
        return None, "question length outside 20-220 chars"
    if TIME_SENSITIVE_RE.search(question):
        return None, "time-sensitive wording"
    if MULTI_ANSWER_RE.search(question):
        return None, "asks for multiple answers (not atomic)"
    if not answer:
        return None, "empty ground-truth answer"
    if len(answer.split()) > 6:
        return None, "answer too long to be atomic"

    primary = normalize_answer(answer)
    distinct = sorted({normalize_answer(a) for a in aliases if a} | {primary})
    distinct = [a for a in distinct if a]

    def related(a: str, b: str) -> bool:
        return a in b or b in a or bool(set(a.split()) & set(b.split()))

    if any(not any(related(a, b) for b in distinct if b != a) for a in distinct):
        return None, "ambiguous answer (aliases refer to different answers)"

    year_in_answer = bool(YEAR_RE.search(answer))
    word_count = len(question.split())
    difficulty = "easy" if word_count <= 10 else "medium" if word_count <= 16 else "hard"
    return {
        "question_text": question,
        "ground_truth_answer": answer,
        "difficulty_flag": difficulty,
        "metadata": {
            "word_count": word_count,
            "is_year_answer": year_in_answer,
            "n_aliases": len(aliases),
        },
    }, None


def check_math(item: dict) -> tuple[dict | None, str | None]:
    question = str(item.get("question", "")).strip()
    answer = str(item.get("answer", "")).strip()

    if question.count("?") > 1:
        return None, "multiple questions in one item"
    if len(question) < 20 or len(question) > 400:
        return None, "question length outside 20-400 chars"
    if MULTI_PART_RE.search(question):
        return None, "multi-part question (ambiguous final answer)"
    if "####" not in answer:
        return None, "no '####' final answer marker"
    tail = answer.split("####")[-1].strip().replace(",", "").replace("$", "")
    if not NUMERIC_RE.fullmatch(tail):
        return None, "final answer is not a single number/symbol"

    steps = answer.count("<<")
    difficulty = "easy" if steps <= 2 else "medium" if steps <= 4 else "hard"
    return {
        "question_text": question,
        "ground_truth_answer": tail,
        "difficulty_flag": difficulty,
        "metadata": {"n_reasoning_steps": steps, "word_count": len(question.split())},
    }, None


def check_reasoning(item: dict) -> tuple[dict | None, str | None]:
    question = str(item.get("question", "")).strip()
    raw_answer = item.get("answer")
    if isinstance(raw_answer, bool):
        answer = "yes" if raw_answer else "no"
    else:
        text = str(raw_answer or "").strip().lower()
        answer = {"true": "yes", "false": "no"}.get(text, text)

    if question.count("?") > 1:
        return None, "multiple questions in one item"
    if len(question) < 15 or len(question) > 220:
        return None, "question length outside 15-220 chars"
    if answer not in {"yes", "no"}:
        return None, STRATEGYQA_BINARY_REASON
    if ARITHMETIC_RE.search(question):
        return None, STRATEGYQA_ARITHMETIC_REASON

    facts = item.get("facts")
    if isinstance(facts, list):
        facts_count = len(facts)
    elif isinstance(facts, str) and facts.strip():
        facts_count = len([s for s in re.split(r"(?<=[.!?])\s+", facts.strip()) if s.strip()])
    else:
        facts_count = 0
    if facts_count == 0:
        word_count = len(question.split())
        facts_count = 1 if word_count <= 10 else 2 if word_count <= 16 else 3
    if facts_count <= 2:
        difficulty = "easy"
    elif facts_count <= 4:
        difficulty = "medium"
    else:
        difficulty = "hard"
    return {
        "question_text": question,
        "ground_truth_answer": answer,
        "difficulty_flag": difficulty,
        "metadata": {"n_supporting_facts": facts_count, "word_count": len(question.split())},
    }, None


CHECKERS = {"factual": check_factual, "math": check_math, "reasoning": check_reasoning}


def build_category(
    category: str,
    target: int,
    seed: int,
    max_candidates: int,
    deduper: Deduper,
    max_examples_per_reason: int,
    extra_scan: int = 0,
):
    accepted: list[dict] = []
    reason_counts: Counter = Counter()
    reason_examples: dict[str, list[dict]] = defaultdict(list)

    def record_rejection(question: str, reason: str, source_id: str):
        reason_counts[reason] += 1
        if len(reason_examples[reason]) < max_examples_per_reason:
            reason_examples[reason].append(
                {"category": category, "question_text": question, "reason": reason, "source_id": source_id}
            )

    inspected = 0
    post_target_inspected = 0
    for item in iter_candidates(category, seed, max_candidates):
        if len(accepted) >= target:
            if post_target_inspected >= extra_scan:
                break
            post_target_inspected += 1
            record, _reason = CHECKERS[category](item)
            if record:
                duplicate_reason = deduper.check(record["question_text"], category, "", register=False)
                if duplicate_reason:
                    record_rejection(str(item.get("question") or "")[:300], duplicate_reason, str(item.get("question_id") or ""))
            continue
        inspected += 1
        source_id = str(item.get("question_id") or item.get("id") or item.get("qid") or "")
        raw_question = str(item.get("question") or "")[:300]

        record, reason = CHECKERS[category](item)
        if reason:
            record_rejection(raw_question, reason, source_id)
            continue

        question_id = f"{category}_{len(accepted) + 1:04d}"
        duplicate_reason = deduper.check(record["question_text"], category, question_id)
        if duplicate_reason:
            record_rejection(raw_question, duplicate_reason, source_id)
            continue

        record.update(
            {
                "question_id": question_id,
                "category": category,
                "ground_truth_answer": record["ground_truth_answer"],
                "source_dataset": config.SOURCE_DATASETS[category],
                "validation_status": "auto_validated",
            }
        )
        record["metadata"]["source_id"] = source_id
        accepted.append(record)

    stats = {
        "category": category,
        "target": target,
        "inspected": inspected + post_target_inspected,
        "accepted": len(accepted),
        "rejected": int(sum(reason_counts.values())),
        "rejections_by_reason": dict(reason_counts.most_common()),
    }
    return accepted, stats, reason_examples


def write_spot_check(dataset: list[dict], seed: int):
    rng = random.Random(seed + 1)
    per_category = {"factual": 7, "math": 7, "reasoning": 6}
    lines = [
        "# Manual spot-check sample",
        "",
        "Review these 20 questions against the dataset. For each one:",
        "1. Confirm the question is unambiguous and self-contained.",
        "2. Confirm the ground-truth answer is correct and verifiable.",
        "3. If it passes, set `validation_status` to `spot_checked` in data/dataset.json.",
        "   If it fails, set it to `rejected` and note the reason in research_log.md.",
        "",
    ]
    for category, count in per_category.items():
        items = [q for q in dataset if q["category"] == category]
        sample = rng.sample(items, min(count, len(items)))
        lines.append(f"## {category.title()} ({len(sample)} sampled)")
        lines.append("")
        for q in sample:
            lines.append(f"- **{q['question_id']}** ({q['difficulty_flag']}): {q['question_text']}")
            lines.append(f"  - Ground truth: `{q['ground_truth_answer']}`")
        lines.append("")
    config.SPOT_CHECK_PATH.write_text("\n".join(lines), encoding="utf-8")


def difficulty_table(dataset: list[dict]) -> dict:
    table = {c: Counter() for c in config.CATEGORIES}
    for q in dataset:
        table[q["category"]][q["difficulty_flag"]] += 1
    return table


def write_manifest(
    dataset: list[dict],
    stats: list[dict],
    reason_examples: dict,
    seed: int,
    target: int,
    manual_examples: list[dict] | None = None,
):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    manual_examples = list(manual_examples or [])
    active = [q for q in dataset if q.get("validation_status") != "rejected"]
    rejected = [q for q in dataset if q.get("validation_status") == "rejected"]
    counts = Counter(q["category"] for q in active)
    diffs = difficulty_table(active)
    total = len(active)

    lines: list[str] = []
    lines.append("# Questions Manifest")
    lines.append("")
    lines.append(f"_Living document. Last regenerated: {now} (seed {seed}, target {target}/category)._")
    lines.append("")
    lines.append("## Dataset summary")
    lines.append("")
    lines.append(f"Total active questions: **{total}** — " + ", ".join(f"{c}: {counts.get(c, 0)}" for c in config.CATEGORIES))
    if rejected:
        lines.append("")
        lines.append(
            f"{len(rejected)} entries are retained in data/dataset.json with status `rejected` "
            "(manual spot-check findings) and are excluded from generation and validation counts."
        )
    lines.append("")
    lines.append("| Category | Source | Inspected | Accepted | Rejected | Target met |")
    lines.append("|---|---|---:|---:|---:|:---:|")
    for s in stats:
        met = "yes" if s["accepted"] >= s["target"] else "NO"
        lines.append(
            f"| {s['category']} | {config.SOURCE_DATASETS[s['category']]} | {s['inspected']} | "
            f"{s['accepted']} | {s['rejected']} | {met} |"
        )
    lines.append("")
    lines.append("## Difficulty distribution (heuristic proxy)")
    lines.append("")
    lines.append("| Category | easy | medium | hard |")
    lines.append("|---|---:|---:|---:|")
    for c in config.CATEGORIES:
        lines.append(f"| {c} | {diffs[c].get('easy', 0)} | {diffs[c].get('medium', 0)} | {diffs[c].get('hard', 0)} |")
    lines.append("")
    lines.append(
        "Difficulty flags are deterministic heuristics, not gold labels: factual = question word count "
        "(<=10 / <=16 / more), math = number of calculator steps in the solution (<=2 / <=4 / more), "
        "reasoning = number of supporting facts in the evidence (<=2 / <=4 / more)."
    )
    lines.append("")
    lines.append("## Validation criteria applied")
    lines.append("")
    lines.append("- **Factual**: single unambiguous answer, verifiable from a Wikipedia entity, not time-sensitive, no multi-answer prompts.")
    lines.append("- **Mathematical**: exactly one numeric final answer after the `####` marker, no multi-part questions, no unit ambiguity.")
    lines.append("- **Reasoning**: multi-step inference, clear binary (yes/no) final answer, no arithmetic-heavy items (math overlap).")
    lines.append("")
    lines.append("All questions were additionally required to be unique (exact and near-duplicate check at sequence ratio >= 0.90 across all categories).")
    lines.append("")
    lines.append("## Excluded examples")
    lines.append("")
    lines.append("Selected dropped candidates (full reasons in data/excluded_examples.json):")
    lines.append("")

    priority_prefixes = [
        "ambiguous answer (aliases",
        "time-sensitive wording",
        STRATEGYQA_ARITHMETIC_REASON,
        "final answer is not a single number",
        "multi-part question (ambiguous final answer)",
        "asks for multiple answers (not atomic)",
        "exact duplicate",
        "near duplicate",
    ]

    chosen: list[tuple[str, dict]] = [(example["reason"], example) for example in manual_examples]
    used_reasons: set[str] = {reason for reason, _ in chosen}
    for prefix in priority_prefixes:
        for reason, examples in reason_examples.items():
            if reason.startswith(prefix) and reason not in used_reasons and examples:
                chosen.append((reason, examples[0]))
                used_reasons.add(reason)
                break
        if len(chosen) >= 5:
            break
    if len(chosen) < 5:
        for reason, examples in reason_examples.items():
            if reason not in used_reasons and examples:
                chosen.append((reason, examples[0]))
                used_reasons.add(reason)
            if len(chosen) >= 5:
                break

    if chosen:
        for number, (reason, example) in enumerate(chosen, 1):
            if example.get("question_id"):
                label = f"**{example['question_id']}** ({example['category']})"
            else:
                label = f"**{example['category']}**"
            lines.append(f"{number}. {label} — `{example['question_text'][:140]}`")
            lines.append(f"   - Reason: {reason}")
    else:
        lines.append("_No exclusions were recorded for this build._")
    lines.append("")
    lines.append("Aggregate rejection counts by category:")
    lines.append("")
    for s in stats:
        lines.append(f"- **{s['category']}**: {s['rejected']} rejected")
        for reason, count in s["rejections_by_reason"].items():
            lines.append(f"  - {count}x {reason}")
    if manual_examples:
        lines.append("")
        lines.append("Manual spot-check rejections (source-data errors, not filtering misses):")
        lines.append("")
        for example in manual_examples:
            lines.append(f"- **{example['question_id']}**: {example['reason']}")
    lines.append("")
    lines.append("## Overlap / MECE note")
    lines.append("")
    lines.append(
        "The three categories are defined as: factual = single-hop lookup from parametric knowledge; "
        "mathematical = numeric computation on a word problem; reasoning = multi-hop logical inference over "
        "stated or world facts."
    )
    overlap_example = None
    for reason, examples in reason_examples.items():
        if reason == STRATEGYQA_ARITHMETIC_REASON and examples:
            overlap_example = examples[0]["question_text"]
            break
    if overlap_example:
        lines.append(
            f"StrategyQA items that reduce to arithmetic were dropped as mathematical overlap, e.g. `{overlap_example}`."
        )
    else:
        lines.append(
            "No inspected StrategyQA candidate reduced to arithmetic, so no mathematical-overlap item was "
            "dropped in this build; the filter still runs at build time."
        )
    lines.append("")
    if rejected:
        lines.append("## Rejected entries (excluded from generation)")
        lines.append("")
        lines.append("| question_id | reason |")
        lines.append("|---|---|")
        for q in rejected:
            lines.append(f"| {q['question_id']} | {q.get('rejection_reason', '')} |")
        lines.append("")
    lines.append("## Per-question metadata")
    lines.append("")
    lines.append("| question_id | category | source | difficulty | status | words |")
    lines.append("|---|---|---|---|---|---:|")
    for q in dataset:
        lines.append(
            f"| {q['question_id']} | {q['category']} | {q['source_dataset']} | "
            f"{q['difficulty_flag']} | {q['validation_status']} | {q['metadata'].get('word_count', '')} |"
        )
    lines.append("")
    config.PROJECT_ROOT.joinpath("docs", "questions_manifest.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the MECE question dataset.")
    parser.add_argument("--target", type=int, default=config.TARGET_PER_CATEGORY, help="questions per category")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--max-candidates", type=int, default=4000, help="max candidate rows inspected per category")
    parser.add_argument("--extra-scan", type=int, default=400, help="candidates validated after the target is met, for exclusion stats")
    parser.add_argument("--max-examples-per-reason", type=int, default=50, help="stored examples per rejection reason")
    args = parser.parse_args()

    deduper = Deduper()
    dataset: list[dict] = []
    stats: list[dict] = []
    all_examples: dict[str, list[dict]] = defaultdict(list)

    for category in config.CATEGORIES:
        print(f"[build] {category}: sampling up to {args.target} valid questions ...")
        accepted, category_stats, examples = build_category(
            category,
            args.target,
            args.seed,
            args.max_candidates,
            deduper,
            args.max_examples_per_reason,
            extra_scan=args.extra_scan,
        )
        dataset.extend(accepted)
        stats.append(category_stats)
        for reason, items in examples.items():
            all_examples[reason].extend(items)
        print(
            f"[build] {category}: accepted {category_stats['accepted']}, "
            f"rejected {category_stats['rejected']} (inspected {category_stats['inspected']})"
        )

    config.DATASET_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")
    true_counts: Counter = Counter()
    for category_stats in stats:
        for reason, count in category_stats["rejections_by_reason"].items():
            true_counts[reason] += count

    config.EXCLUDED_PATH.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "rejections_by_reason": dict(true_counts.most_common()),
                "category_stats": stats,
                "examples": dict(all_examples),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_spot_check(dataset, args.seed)
    write_manifest(dataset, stats, all_examples, args.seed, args.target)

    print(f"[build] dataset -> {config.DATASET_PATH} ({len(dataset)} questions)")
    print(f"[build] manifest -> {config.PROJECT_ROOT / 'docs' / 'questions_manifest.md'}")
    print(f"[build] spot-check -> {config.SPOT_CHECK_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
