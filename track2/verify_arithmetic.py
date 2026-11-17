"""Track 2, component (c): real-time verifiability for math.

Deterministic check of the arithmetic inside ONE response, no LLM and no ground truth.
Every "expr = number" step the model writes (e.g. "4 \\times 20 = 80") is re-computed in
Python. A response with a step that does not compute is flagged.

Uses logs/generations.jsonl (read-only) and results/*correctness.jsonl for evaluation only.
Writes track2/outputs/arith_verify.jsonl and prints how well the flag catches wrong answers.
"""
import json
import re
import warnings
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scoring"))
from uq_common import roc_auc  # noqa: E402

warnings.filterwarnings("ignore", category=SyntaxWarning)
NUMERIC = re.compile(r"^[\d\.\s\+\-\*/\(\)]+$")


def clean(part: str) -> str:
    s = part
    s = re.sub(r"\\text\{[^}]*\}", " WORD ", s)
    s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))", s)
    for a, b in ((r"\times", "*"), ("×", "*"), (r"\cdot", "*"), ("·", "*"), (r"\div", "/"), ("÷", "/"),
                 (r"\left", ""), (r"\right", ""), (r"\$", ""), ("$", ""), (r"\,", ""), ("**", ""),
                 ("{", "("), ("}", ")"), ("−", "-")):
        s = s.replace(a, b)
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)          # 1,200 -> 1200
    s = re.sub(r"(\d+(?:\.\d+)?)\s*\\?%", r"(\1*0.01)", s)  # 20% -> (20*0.01)
    s = s.strip().rstrip(".:,;")
    return s


def evaluate(expr: str):
    if not expr or not NUMERIC.match(expr) or not re.search(r"\d", expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # charset already restricted to digits/operators
    except Exception:
        return None


def check_response(text: str):
    steps, wrong = 0, []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line)  # drop bullet / list markers
        if "=" not in line or "\\approx" in line or "≈" in line:
            continue
        parts = [clean(p) for p in re.split(r"(?<![<>!])=(?!=)", line)]
        for left, right in zip(parts, parts[1:]):
            if not re.search(r"[\+\-\*/]", left):
                continue  # nothing to compute, e.g. "x = 5"
            lv, rv = evaluate(left), evaluate(right)
            if lv is None or rv is None:
                continue
            steps += 1
            pct = "*0.01)" in right  # "0.8 * 100 = 80%" style: compare against 80
            ok = any(abs(lv - t) <= max(0.011, 0.005 * abs(t)) for t in ([rv, rv * 100] if pct else [rv]))
            if not ok:  # allow 2-decimal rounding
                wrong.append(f"{left} = {right} (computes to {lv:g})")
    return steps, wrong


labels = {}
for f in ("results/correctness.jsonl", "results/mathb_correctness.jsonl"):
    for line in (ROOT / f).open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            for s in r["per_sample"]:
                labels[(r["question_id"], int(s["sample_id"]))] = int(s["label"] == "correct")

rows = []
for f in ("logs/generations.jsonl",):
    for line in (ROOT / f).open(encoding="utf-8"):
        r = json.loads(line)
        if r.get("status") != "ok" or r["category"] != "math":
            continue
        key = (r["question_id"], int(r["sample_id"]))
        if key not in labels:
            continue
        steps, wrong = check_response(r["response_text"] or "")
        rows.append({"question_id": key[0], "sample_id": key[1],
                     "split": "mathb_heldout" if key[0].startswith("mathb") else "main",
                     "n_steps_checked": steps, "n_steps_wrong": len(wrong), "wrong_steps": wrong[:3],
                     "flag": int(len(wrong) > 0), "correct": labels[key]})

(ROOT / "track2/outputs").mkdir(parents=True, exist_ok=True)
(ROOT / "track2/outputs/arith_verify.jsonl").write_text(
    "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")

groups = defaultdict(list)
for x in rows:
    groups[x["split"]].append(x)
groups["all"] = rows
for name, xs in groups.items():
    n, wrong = len(xs), [x for x in xs if not x["correct"]]
    covered = sum(x["n_steps_checked"] > 0 for x in xs)
    flagged = [x for x in xs if x["flag"]]
    tp = sum(not x["correct"] for x in flagged)
    auc, _, _ = roc_auc([1 - x["correct"] for x in xs], [x["n_steps_wrong"] for x in xs])
    print(f"{name:14s} responses={n} wrong={len(wrong)} with>=1 checkable step={covered} "
          f"steps={sum(x['n_steps_checked'] for x in xs)} flagged={len(flagged)} "
          f"flagged&wrong={tp} wrong-caught={tp}/{len(wrong)} flagged&right(magic)={len(flagged)-tp} "
          f"AUROC={auc if auc is None else round(auc, 3)}")
