---
title: Jon2 Arabic ZeroGPU Proof of Concept
emoji: 🧠
colorFrom: blue
colorTo: cyan
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
---

# Jon2 Arabic — ZeroGPU proof of concept

**Locked by default. Not deployed. No model weights are stored in this repository.**

This is a temporary, interactive inference experiment—not the production Jon2 API and not a permanent hosting solution.

## Mandatory gates

The app does not download or load the model unless all four conditions are met:

1. `JON2_MODEL_RIGHTS_APPROVED=YES` — only after written training-data provenance/licensing review.
2. `JON2_HF_ACCESS_ACCEPTED=YES` — set only after the owner personally reviews and accepts the model-host terms.
3. `JON2_MODEL_REVISION` — an exact immutable 40-character commit SHA, not `main`.
4. `HF_TOKEN` — a Hugging Face token stored only as a private Space secret, never in code, GitHub, browser JavaScript, or chat.

All gates are intentionally absent by default. Do not set them just to make the demo run.

## Space configuration after separate owner approval

- Create a Gradio Space in the owner's Hugging Face account.
- Select ZeroGPU hardware in Space settings. Confirm the actual hardware assignment before testing.
- Keep the Space private for the first test.
- Add the four values above through the Space's Secrets/Variables settings; `HF_TOKEN` must be a Secret.
- Never commit model weights or tokens.
- Run one short test, record actual load success, GPU memory, latency, and output quality, then pause the Space.

The Space may require access to the gated model to be granted by its publisher. The owner must personally complete that access flow.

## Limitations

- ZeroGPU is quota-limited, queued, and not guaranteed to be continuously available.
- This app handles one message at a time and is only an initial inference smoke test.
- It does not connect to GitHub Pages, expose the private Jon2 API token, or provide production user accounts.
- A successful demo does not approve model release. The Arabic evaluation suite and human review remain mandatory.
- The model is loaded only when all gates are explicitly satisfied. The default locked mode does not load Transformers or fetch model files.
