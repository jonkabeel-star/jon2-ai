# Jon2 Arabic Qwen3.5-2B LoRA training

## Model selection

The practical GPU-training target is `Qwen/Qwen3.5-2B` (Apache-2.0). It is
multilingual and small enough for a controlled 16-bit LoRA experiment on a
suitable single GPU. Qwen3.8-27B is newer and more capable, but its 27B scale
and hardware requirements make it unsuitable as the first free-Colab run.

Official references:
- https://huggingface.co/Qwen/Qwen3.5-2B
- https://qwen.ai/blog?id=qwen3.5
- https://unsloth.ai/docs/models/qwen3.5/fine-tune

Qwen3.5 uses a hybrid Gated-DeltaNet / full-attention architecture. This path
uses Unsloth's Qwen3.5-aware loader and Transformers v5, not the older generic
Qwen2.5 AutoModelForCausalLM recipe. Use 16-bit LoRA; 4-bit QLoRA is not
recommended for this model family by the current Unsloth guide.

## What the pipeline does

- Checks every TXT file against the explicit rights manifest, exact SHA-256,
  UTF-8 character count, reviewer, review date, and research-training scope.
- Rejects unapproved/changed files, malformed alternating Arabic turns,
  duplicates, likely emails, Egyptian mobile numbers, and credential strings.
- Splits at the conversation level into train, validation, and held-out test.
- Masks user prompt tokens so training loss is applied to assistant responses.
- Defaults to a read-only dry run. Real optimizer steps require `--execute`
  and CUDA.
- Saves a separate LoRA adapter and metadata. It never overwrites the original
  Jon2 checkpoint and never enables public chat.
- Can export a Q4_K_M GGUF for the local llama.cpp CPU runtime.

The currently approved source rights authorize private experimental research
only. They do not authorize commercial use or public redistribution.

## Google Colab GPU steps

1. Open a new Google Colab notebook and choose a CUDA GPU runtime. A T4 is a
   reasonable first attempt; GPU availability depends on Colab.
2. Clone the repository and enter its root:

   ```bash
   !git clone https://github.com/jonkabeel-star/jon2-ai.git
   %cd jon2-ai
   ```

3. Mount Google Drive so the adapter and GGUF survive the notebook session:

   ```python
   from google.colab import drive
   drive.mount("/content/drive")
   ```

4. Install the Qwen3.5 training dependencies:

   ```bash
   !pip install -r ai_engine/requirements-lora.txt
   ```

5. Run the safe dry-run first. It validates rights, parsing, privacy, and split
   counts without downloading the model or changing weights:

   ```bash
   !python ai_engine/finetune_qwen_lora.py --dry-run
   ```

6. Only after reviewing the dry-run report, start real training and export a
   Q4_K_M GGUF directly into private Google Drive storage:

   ```bash
   !python ai_engine/finetune_qwen_lora.py --execute --export-gguf --output /content/drive/MyDrive/Jon2_AI/jon2-qwen35-2b-lora
   ```

If the GPU runs out of memory, stop and reassess. Do not silently switch to CPU
or remove the rights checks. The script uses 16-bit LoRA and gradient
checkpointing; the exact run still depends on available VRAM and Colab limits.

## After training

Verify all of the following in the metadata:
- `training_completed` is true.
- `optimizer_steps_completed` is greater than zero.
- Adapter weights and config exist.
- `validation_evaluation` and `final_held_out_test_evaluation` are present.
- GGUF export completed if `--export-gguf` was selected.

The GGUF exporter may produce a filename containing the quantization suffix.
Rename the Q4_K_M file to
`jon2-qwen35-2b-q4_k_m.gguf` before copying it to the Oracle VM's private
`/opt/jon2/models` directory.

Compare base-model and adapter outputs on the same held-out Arabic prompts.
Human-review Egyptian Arabic and Modern Standard Arabic for relevance,
accuracy, repetition, privacy leakage, and unsupported claims. A lower loss
or successful training run is not proof of a useful assistant.

Do not enable public chat until the exact GGUF passes the held-out benchmark,
human review, and a memory/latency test on the actual target server.
