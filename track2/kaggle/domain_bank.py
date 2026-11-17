"""Domain bank for Step 1 (domain check) and Step 2 (difficulty thresholds).

Builds a reference "universe" of factual, math and reasoning questions that are NOT in the
450 test questions (or the 150 extra math questions), from the TRAIN splits of the same
benchmarks: TriviaQA (rc.nocontext), GSM8K (main) and StrategyQA.

For every bank question it stores:
  - a MiniLM sentence embedding (for similarity / nearest neighbours)
  - the question NLL under Qwen2.5-1.5B (for per-domain difficulty thresholds)

No answers and no correctness labels are used. Outputs (next to this script):
  bank_questions.jsonl, bank_emb.npz, bank_nll.csv
"""
import json
import math
import os
import random
import re

import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
PER_DOMAIN = 1000
SEED = 2026
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32
print("device:", DEVICE, torch.cuda.get_device_name(0) if DEVICE == "cuda" else "")


def norm(t):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t.lower()).split())


test = [json.loads(l) for l in open(os.path.join(HERE, "questions.jsonl"), encoding="utf-8") if l.strip()]
test_norm = {norm(q["question_text"]) for q in test}
print("excluding", len(test_norm), "test questions")


def pick(rows, lo, hi, domain):
    rng = random.Random(SEED)
    rows = [r.strip() for r in rows if r and lo <= len(r.strip()) <= hi]
    rng.shuffle(rows)
    out, seen = [], set()
    for r in rows:
        n = norm(r)
        if n in test_norm or n in seen:
            continue
        seen.add(n); out.append(r)
        if len(out) == PER_DOMAIN:
            break
    print(domain, len(out))
    return [{"bank_id": f"bank_{domain}_{i:04d}", "domain": domain, "question_text": t} for i, t in enumerate(out)]


bank = []
tq = load_dataset("mandarjoshi/trivia_qa", "rc.nocontext", split="train")
bank += pick(tq["question"], 20, 220, "factual")
gs = load_dataset("openai/gsm8k", "main", split="train")
bank += pick(gs["question"], 20, 400, "math")
for name in ["ChilleD/StrategyQA", "tasksource/strategy-qa", "voidful/StrategyQA", "wics/strategy-qa"]:
    try:
        sq = load_dataset(name, split="train"); print("StrategyQA from", name); break
    except Exception as e:
        print("skip", name, e)
bank += pick(sq["question"], 10, 300, "reasoning")
with open(os.path.join(HERE, "bank_questions.jsonl"), "w", encoding="utf-8") as f:
    for b in bank:
        f.write(json.dumps(b) + "\n")

# ---- embeddings (MiniLM, mean pooling, unit length) ----
name = "sentence-transformers/all-MiniLM-L6-v2"
tok = AutoTokenizer.from_pretrained(name); enc = AutoModel.from_pretrained(name).to(DEVICE).eval()


@torch.no_grad()
def embed(texts, bs=64):
    out = []
    for i in range(0, len(texts), bs):
        b = tok(list(texts[i:i + bs]), padding=True, truncation=True, max_length=256, return_tensors="pt").to(DEVICE)
        h = enc(**b).last_hidden_state; m = b["attention_mask"].unsqueeze(-1).float()
        v = torch.nn.functional.normalize((h * m).sum(1) / m.sum(1), dim=-1)
        out.append(v.cpu().numpy())
    return np.concatenate(out)


emb = embed([b["question_text"] for b in bank])
np.savez(os.path.join(HERE, "bank_emb.npz"), ids=np.array([b["bank_id"] for b in bank]),
         domain=np.array([b["domain"] for b in bank]), emb=emb)
print("embeddings", emb.shape)
del enc; torch.cuda.empty_cache()

# ---- question NLL (same scoring as question_nll_embed.py) ----
PREFIX = "Question:"
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B")
lm = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B", torch_dtype=DTYPE).to(DEVICE).eval()


@torch.no_grad()
def nll(text):
    p = tok(PREFIX, add_special_tokens=False)["input_ids"]
    q = tok(" " + text.strip(), add_special_tokens=False)["input_ids"]
    if tok.bos_token_id is not None:
        p = [tok.bos_token_id] + p
    ids = torch.tensor([p + q], device=DEVICE)
    logp = torch.log_softmax(lm(ids).logits.float()[0, :-1], dim=-1)
    t = -logp.gather(1, ids[0, 1:][:, None])[:, 0][len(p) - 1:].cpu().numpy()
    return float(t.mean()), len(t)


rows = []
for i, b in enumerate(bank):
    m, n = nll(b["question_text"])
    rows.append({"bank_id": b["bank_id"], "domain": b["domain"], "mean_nll": m, "n_tokens": n})
    if i % 250 == 0:
        print("nll", i, flush=True)
pd.DataFrame(rows).to_csv(os.path.join(HERE, "bank_nll.csv"), index=False)
print("done")
