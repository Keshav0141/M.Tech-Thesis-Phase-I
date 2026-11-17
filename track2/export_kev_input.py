"""Track 2, component (e): build Kev input = question + qwen's sample-0 extracted answer. No labels exported."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
qtext = {}
for l in (ROOT / "track2/kaggle/questions.jsonl").open(encoding="utf-8"):
    q = json.loads(l)
    qtext[q["question_id"]] = q["question_text"]
out = []
for l in (ROOT / "results/correctness.jsonl").open(encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        s = next(s for s in r["per_sample"] if int(s["sample_id"]) == 0)
        out.append({"question_id": r["question_id"], "category": r["category"],
                    "question": qtext[r["question_id"]], "answer": str(s["extracted"] if s["extracted"] is not None else "").strip()})
(ROOT / "track2/kev/kev_input.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
print(len(out), "rows;", sum(not x["answer"] for x in out), "empty answers")
