"""Track 2 Kaggle job: question NLL (component a) + question embeddings (component b).

Run on a free Kaggle notebook (GPU T4, Internet ON). Upload questions.jsonl as a dataset,
or put it next to this script. Outputs go to /kaggle/working:
  question_nll.csv      one row per (question, reference model)
  question_emb.npz      MiniLM embeddings for our 600 questions (+ Banking77 if it loads)

Only the QUESTION text is scored. No answers or ground truth are used.
"""
import glob
import json
import math
import os

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

OUT_DIR = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.path.dirname(os.path.abspath(__file__))
cands = glob.glob("/kaggle/input/**/questions.jsonl", recursive=True) + [os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.jsonl")]
QPATH = next(p for p in cands if os.path.exists(p))
questions = [json.loads(l) for l in open(QPATH, encoding="utf-8") if l.strip()]
print(len(questions), "questions from", QPATH)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32
PREFIX = "Question:"  # fixed neutral context so the first question token is also scored
REF_MODELS = ["Qwen/Qwen2.5-1.5B", "gpt2"]  # base LMs, two families


@torch.no_grad()
def score(model, tok, text):
    prefix_ids = tok(PREFIX, add_special_tokens=False)["input_ids"]
    q_ids = tok(" " + text.strip(), add_special_tokens=False)["input_ids"]
    if tok.bos_token_id is not None and "gpt2" not in tok.name_or_path:
        prefix_ids = [tok.bos_token_id] + prefix_ids
    ids = torch.tensor([prefix_ids + q_ids], device=DEVICE)
    logits = model(ids).logits.float()
    logp = torch.log_softmax(logits[0, :-1], dim=-1)
    target = ids[0, 1:]
    tok_nll = -logp.gather(1, target[:, None])[:, 0]
    q_nll = tok_nll[len(prefix_ids) - 1:].cpu().numpy()  # question tokens only
    return {
        "n_tokens": len(q_nll),
        "sum_nll": float(q_nll.sum()),
        "mean_nll": float(q_nll.mean()),
        "max_nll": float(q_nll.max()),
        "frac_tokens_nll_gt10": float((q_nll > 10).mean()),
        "perplexity": float(math.exp(q_nll.mean())),
    }


rows = []
for name in REF_MODELS:
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=DTYPE).to(DEVICE).eval()
    for i, q in enumerate(questions):
        rows.append({"question_id": q["question_id"], "category": q["category"], "split": q["split"],
                     "ref_model": name, **score(model, tok, q["question_text"])})
        if i % 100 == 0:
            print(name, i)
    del model
    torch.cuda.empty_cache()
pd.DataFrame(rows).to_csv(f"{OUT_DIR}/question_nll.csv", index=False)
print("wrote question_nll.csv", len(rows))

# ---- embeddings for the out-of-domain detector (deterministic: embeddings + cosine) ----
from transformers import AutoModel  # MiniLM via plain transformers (mean pooling = sentence-transformers default)


class Enc:
    def __init__(self, name):
        self.tok = AutoTokenizer.from_pretrained(name)
        self.m = AutoModel.from_pretrained(name).to(DEVICE).eval()

    @torch.no_grad()
    def encode(self, texts, normalize_embeddings=True, batch_size=64):
        out = []
        for i in range(0, len(texts), batch_size):
            b = self.tok(list(texts[i:i + batch_size]), padding=True, truncation=True, max_length=256, return_tensors="pt").to(DEVICE)
            h = self.m(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            v = (h * m).sum(1) / m.sum(1)
            if normalize_embeddings:
                v = torch.nn.functional.normalize(v, dim=-1)
            out.append(v.cpu().numpy())
        return np.concatenate(out)


enc = Enc("sentence-transformers/all-MiniLM-L6-v2")
emb = enc.encode([q["question_text"] for q in questions], normalize_embeddings=True, batch_size=64)
save = {"ids": np.array([q["question_id"] for q in questions]), "emb": emb}

try:  # optional business-domain set: Banking77 customer queries
    from datasets import load_dataset
    try:
        ds = load_dataset("PolyAI/banking77", revision="refs/convert/parquet")
    except Exception:
        ds = load_dataset("legacy-datasets/banking77")
    for split in ("train", "test"):
        texts = list(ds[split]["text"])
        save[f"banking_{split}_text"] = np.array(texts)
        save[f"banking_{split}_label"] = np.array(ds[split]["label"])
        save[f"banking_{split}_emb"] = enc.encode(texts, normalize_embeddings=True, batch_size=128)
    print("banking77 ok", {k: v.shape for k, v in save.items() if k.endswith("_emb")})
except Exception as exc:
    print("banking77 skipped:", exc)

np.savez_compressed(f"{OUT_DIR}/question_emb.npz", **save)
print("done")
