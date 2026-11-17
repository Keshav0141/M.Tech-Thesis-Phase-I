"""Export the 450 main + 150 held-out math questions (text only, no answers) for the Kaggle scoring run."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
keep = {json.loads(l)["question_id"] for f in ("results/correctness.jsonl", "results/mathb_correctness.jsonl")
        for l in (ROOT / f).open(encoding="utf-8") if l.strip()}
rows = []
for f, split in (("data/dataset.json", "main"), ("data/math_expansion.json", "mathb_heldout")):
    for q in json.loads((ROOT / f).read_text(encoding="utf-8")):
        if q["question_id"] in keep:
            rows.append({"question_id": q["question_id"], "category": q["category"], "split": split,
                         "question_text": q["question_text"]})
out = ROOT / "track2/kaggle/questions.jsonl"
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
print(len(rows), "questions ->", out)
