# Qwen3.5-9B: free Kaggle GPU evaluation (isolated)

## Goal

Evaluate the official open-weight Qwen/Qwen3.5-9B model locally inside a temporary Kaggle GPU notebook, against Jon2's held-out Arabic/Egyptian benchmark. This is not an API call and does not make Qwen the production model automatically.

Official model card: https://huggingface.co/Qwen/Qwen3.5-9B  
License shown on the official model card: Apache-2.0. Re-check the model card and license before redistribution.

## Free-only runtime

- Use Kaggle Notebooks' free GPU allocation when available. Kaggle documents a weekly GPU quota (commonly 30 hours) and queue/availability limits.
- Select a GPU accelerator in Notebook Settings. The session must report CUDA available before loading the model.
- Install current Transformers and bitsandbytes in that Kaggle session. Qwen3.5 requires a recent Transformers build; use the current official model-card instructions if the preinstalled Kaggle version is too old.
- Load in 4-bit NF4 to reduce VRAM use. This is a best-effort configuration, not a guarantee that every free GPU type has enough memory or supports the installed bitsandbytes build.
- If CUDA is missing, the script stops. It never silently runs on CPU.
- Do not use paid Kaggle add-ons, paid Hugging Face hardware, paid inference providers, or external model APIs.

## Run in Kaggle

Upload or attach the repository's approved benchmark and this script to the notebook, then run:

    !pip install -U transformers bitsandbytes accelerate
    !python ai_engine/evaluate_qwen35.py --limit 2 --output /kaggle/working/qwen35_smoke.jsonl

After the smoke test succeeds, run the full benchmark:

    !python ai_engine/evaluate_qwen35.py --output /kaggle/working/qwen35_egyptian_trial.jsonl

Keep the notebook private. Download the output for private human review; do not publish raw prompts or user data.

## Review

Score each held-out answer for:
- factual correctness and relevance;
- natural Egyptian Arabic and clear MSA;
- instruction following;
- multi-turn context retention;
- reasoning quality and consistency;
- hallucinations, unsafe content, and repetitive output.

A successful model load or fluent answer is not a quality pass. Do not place benchmark questions or outputs into training data. Do not change Jon2 production routing or public-chat release flags based on this trial.

## Resource limits and honest expectations

Kaggle's free GPU is quota-limited and may be queued; sessions are temporary. This can support evaluation and experiments, not a guaranteed always-on public chat service. A permanently hosted GPU inference service cannot be promised at zero cost. The GitHub Pages site remains static and cannot run the model.

No training is performed by this evaluation script. No Jon2 checkpoint is read, overwritten, or promoted.
