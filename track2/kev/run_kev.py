"""Run on the laptop while Kev is serving on localhost:8009. Standard library only.
Usage: python run_kev.py   (resumes if interrupted). Writes kev_scores.jsonl next to this file."""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IN, OUT = os.path.join(HERE, "kev_input.jsonl"), os.path.join(HERE, "kev_scores.jsonl")
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["question_id"] for l in open(OUT, encoding="utf-8") if l.strip()}
rows = [json.loads(l) for l in open(IN, encoding="utf-8") if l.strip()]
with open(OUT, "a", encoding="utf-8") as f:
    for i, r in enumerate(rows):
        if r["question_id"] in done:
            continue
        body = {"state": f"Question: {r['question']}\nProposed answer: {r['answer'] or '(no answer)'}",
                "questions": {"correct": {"type": "noul", "instructions": "Is the proposed answer correct?"}}}
        req = urllib.request.Request("http://localhost:8009/v1/systemone", json.dumps(body).encode(),
                                     {"content-type": "application/json"})
        t = time.time()
        res = json.loads(urllib.request.urlopen(req, timeout=300).read())
        f.write(json.dumps({"question_id": r["question_id"], "p_yes": res["answers"]["correct"]["noul"]}) + "\n")
        f.flush()
        print(f"{i+1}/{len(rows)} {r['question_id']} p={res['answers']['correct']['noul']:.3f} ({time.time()-t:.1f}s)")
print("done ->", OUT)
