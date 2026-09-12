"""Apply manual spot-check results and curation findings to the locked dataset.

Curation step, run after a human has reviewed data/spot_check_sample.md:
    1. Marks known source-data errors and curation-guard findings as `rejected`
       (reasons attached).
    2. Marks every other reviewed question as `spot_checked`.
    3. Pulls replacement questions from the source candidate pools, applying
       the existing per-category validators plus a time-sensitivity guard.
    4. Rewrites data/dataset.json and refreshes data/excluded_examples.json and
       questions_manifest.md.

Safe to re-run: it only adds replacements while an active category count is
below target.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone

import build_dataset
import config

MANUAL_REJECTIONS = {
    "factual_0037": (
        "manual spot-check: source question contains a factual error — Keiko the orca "
        "died in Taknes Bay, Halsa (Norway), not off the coast of Finland"
    ),
    "factual_0025": (
        "manual spot-check: source question conflates two films — Kasper Gutman is a "
        "character from The Maltese Falcon (1941), not Casablanca (1942)"
    ),
}

# Caught during curation review (not part of the spot-check sample). Both are
# time-relative: the intended answer can change with time.
CURATION_REJECTIONS = {
    "factual_0152": (
        "curation guard: time-sensitive wording ('recent London summer Olympics'); "
        "auto-replacement rejected during curation"
    ),
    "reasoning_0106": (
        "curation guard: time-sensitive wording ('most recent Democrat President' — "
        "the referent changes over time); rejected during curation review"
    ),
}

# Stricter guard applied to replacements only, so the locked original questions
# are not shifted. build_dataset.TIME_SENSITIVE_RE covers the rest.
REPLACEMENT_GUARD_RE = re.compile(r"\b(recent|recently|lately)\b", re.IGNORECASE)


def parse_reviewed_ids(text: str) -> list[str]:
    return [f"{category}_{number}" for category, number in re.findall(r"- \*\*(factual|math|reasoning)_(\d{4})\*\*", text)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dataset: list[dict] = json.loads(config.DATASET_PATH.read_text(encoding="utf-8"))
    by_id = {entry["question_id"]: entry for entry in dataset}

    reviewed = parse_reviewed_ids(config.SPOT_CHECK_PATH.read_text(encoding="utf-8"))
    missing = [qid for qid in reviewed if qid not in by_id]
    if missing:
        raise SystemExit(f"Spot-check file references unknown ids: {missing}")

    for question_id, reason in {**MANUAL_REJECTIONS, **CURATION_REJECTIONS}.items():
        entry = by_id[question_id]
        entry["validation_status"] = "rejected"
        entry["rejection_reason"] = reason
        print(f"[curate] rejected {question_id}: {reason}")

    spot_checked = 0
    for question_id in reviewed:
        if question_id not in MANUAL_REJECTIONS and question_id not in CURATION_REJECTIONS:
            by_id[question_id]["validation_status"] = "spot_checked"
            spot_checked += 1
    print(f"[curate] marked {spot_checked} reviewed questions as spot_checked")

    def active_count(category: str) -> int:
        return sum(
            1
            for entry in dataset
            if entry["category"] == category and entry.get("validation_status") != "rejected"
        )

    categories_needing = [
        category for category in config.CATEGORIES if active_count(category) < config.TARGET_PER_CATEGORY
    ]

    if categories_needing:
        deduper = build_dataset.Deduper()
        for entry in dataset:
            if entry.get("validation_status") != "rejected":
                deduper.check(entry["question_text"], entry["category"], entry["question_id"])
        used_source_ids = {entry.get("metadata", {}).get("source_id") for entry in dataset}

        for category in categories_needing:
            needed = config.TARGET_PER_CATEGORY - active_count(category)
            next_index = 1 + max(
                int(entry["question_id"].split("_")[1])
                for entry in dataset
                if entry["category"] == category
            )
            replacements: list[dict] = []

            for item in build_dataset.iter_candidates(category, config.RANDOM_SEED, 4000):
                if len(replacements) >= needed:
                    break
                text = str(item.get("question") or "")
                if REPLACEMENT_GUARD_RE.search(text) or build_dataset.TIME_SENSITIVE_RE.search(text):
                    continue
                source_id = str(item.get("question_id") or item.get("qid") or "")
                if source_id and source_id in used_source_ids:
                    continue
                record, reason = build_dataset.CHECKERS[category](item)
                if reason or record is None:
                    continue
                question_id = f"{category}_{next_index:04d}"
                if deduper.check(record["question_text"], category, question_id):
                    continue
                record.update(
                    {
                        "question_id": question_id,
                        "category": category,
                        "source_dataset": config.SOURCE_DATASETS[category],
                        "validation_status": "auto_validated",
                    }
                )
                record["metadata"]["source_id"] = source_id
                replacements.append(record)
                used_source_ids.add(source_id)
                next_index += 1
                print(f"[curate] replacement {question_id}: {record['question_text'][:100]}")

            if len(replacements) < needed:
                raise SystemExit(
                    f"Only found {len(replacements)} of {needed} {category} replacements in the candidate pool."
                )

            insert_at = max(i for i, entry in enumerate(dataset) if entry["category"] == category) + 1
            dataset[insert_at:insert_at] = replacements

    config.DATASET_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")

    excluded = json.loads(config.EXCLUDED_PATH.read_text(encoding="utf-8"))
    existing_examples = {
        (example.get("question_id"), example.get("reason"))
        for examples in excluded.get("examples", {}).values()
        for example in examples
    }
    manual_examples = []
    for question_id, reason in {**MANUAL_REJECTIONS, **CURATION_REJECTIONS}.items():
        entry = by_id[question_id]
        example = {
            "category": entry["category"],
            "question_id": question_id,
            "question_text": entry["question_text"],
            "reason": reason,
        }
        if question_id in MANUAL_REJECTIONS:
            manual_examples.append(example)
        if (question_id, reason) not in existing_examples:
            excluded.setdefault("examples", {}).setdefault(reason, []).append(example)
            excluded["rejections_by_reason"][reason] = excluded["rejections_by_reason"].get(reason, 0) + 1
    excluded["curated_utc"] = datetime.now(timezone.utc).isoformat()
    config.EXCLUDED_PATH.write_text(json.dumps(excluded, indent=2, ensure_ascii=False), encoding="utf-8")

    stats = excluded["category_stats"]
    build_dataset.write_manifest(
        dataset,
        stats,
        excluded["examples"],
        config.RANDOM_SEED,
        config.TARGET_PER_CATEGORY,
        manual_examples=manual_examples,
    )
    print(f"[curate] dataset updated -> {config.DATASET_PATH}")
    print(f"[curate] manifest refreshed -> {config.PROJECT_ROOT / 'questions_manifest.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
