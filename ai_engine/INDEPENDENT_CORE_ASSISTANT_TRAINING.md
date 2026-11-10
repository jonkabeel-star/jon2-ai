# Jon2 Original Core — Assistant-only training v1

This optional training path continues the **project-owned, from-scratch Jon2 Transformer**. It does not use Qwen, a hosted inference API, or downloaded pretrained weights.

## Why this exists

The first 269,952-parameter Jon2 checkpoint completed genuine training, but its held-out Arabic answers were incoherent. The old next-token objective learned from both user and assistant text. This path keeps user turns as context while applying the training loss only to assistant response tokens, which is a more appropriate starting point for dialogue instruction-following.

This is a training-method improvement, not a claim that the model is now intelligent or production-ready.

## Critical gates

- Every TXT and JSONL source under the selected data directory must pass the exact SHA-256 and rights approval manifest.
- The current JSONL dialogue files are not approved in the main-branch manifest. This command is expected to stop until the owner reviews and approves the exact files for the permitted private research purpose.
- The default data floor is 10 assistant-target tokens per model parameter. This is a conservative planning gate, not a guarantee of quality. The existing corpus is far below the volume needed for a 270k-parameter model, so training is expected to remain blocked.
- Do not duplicate dialogue, lower the guard, or move held-out prompts into training.
- This script creates a separate checkpoint named jon2-dialogue-v1.pt; it never overwrites jon2-small.pt or jon2-last.pt.
- The generated checkpoint always has release_approved=false. Human review of held-out answers is mandatory.

## How it works

1. Validates the exact-file source-approval manifest.
2. Loads complete user/assistant conversations from approved JSONL.
3. Splits whole conversations into train and held-out validation groups.
4. Fits the byte-BPE tokenizer on training conversations only.
5. Includes user text as context, but calculates cross-entropy only on assistant response tokens.
6. Saves a separate checkpoint and SHA-256 manifest.

## Manual command (do not run until source approvals and data preflight pass)

    PYTHONPATH=ai_engine python ai_engine/train_jon2_dialogue.py       --data ai_engine/training_data       --approval-manifest ai_engine/training_data/source_approvals.json       --output ai_engine/checkpoints/jon2-dialogue-v1.pt

This script is not scheduled and is not called by the public website. No training is started by adding this code. GitHub Actions CPU time is not a permanent inference server, and a checkpoint file alone does not make the Pages website capable of running PyTorch.
