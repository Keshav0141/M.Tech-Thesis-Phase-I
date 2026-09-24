# Scale Curve Summary — 1.5B / 7B / 27B

Reference document for the exploratory Kaggle scale experiments vs the main pipeline.

## Correctness (majority vote, N=5)

| Model | Params | Factual | Math | Reasoning | Overall |
|---|---|---|---|---|---|
| Qwen2.5-1.5B | 1.5B | 21.5% | 81.3% | 60.7% | 55.7% |
| Qwen2.5-7B | 7B | 50.4% | 95.3% | 70.7% | 72.9% |
| qwen3.8-27B (main) | 27B | 66.7% | 96.0% | 72.0% | 78.2% |

## TF-IDF AUROC (UQ signal quality)

| Model | Params | Factual | Math | Reasoning | Overall |
|---|---|---|---|---|---|
| Qwen2.5-1.5B | 1.5B | 0.839 | 0.629 | 0.512 | 0.668 |
| Qwen2.5-7B | 7B | 0.818 | 0.699 | 0.583 | 0.713 |
| qwen3.8-27B (main) | 27B | 0.911 | 0.756 | 0.630 | 0.847 |

## Key observations

- Math correctness recovers almost fully by 7B (95.3% vs 96.0% at 27B); factual and reasoning still trail meaningfully.
- Factual AUROC drops slightly 1.5B→7B (0.839→0.818) before jumping at 27B (0.911) — likely small error-pool variance, not a real inversion.
- Overall UQ jump is larger at 7B→27B (+0.134) than 1B→7B (+0.045) — suggests a capability threshold effect rather than smooth linear scaling.
- Reasoning AUROC remains the weakest signal at all scales (0.512→0.583→0.630) — self-consistency methods may structurally struggle with multi-hop implicit reasoning regardless of model size.
- 1.5B and 7B experiments are exploratory only (Kaggle/ngrok setup, fp16, isolated in experiments/); main pipeline (27B) is the thesis baseline.
