# Jon2 Arabic LoRA training (separate research path)

## What this does

This optional pipeline fine-tunes the open-weight \`Qwen/Qwen2.5-0.5B-Instruct\`
base model with PEFT/LoRA. The model card lists Apache-2.0 for this 0.5B
Instruct checkpoint: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

It produces a **separate adapter**, not a newly trained Jon2 foundation model.
It does not replace \`jon2-small.pt\`, change the original Jon2 trainer, enable
the production chat gate, deploy anything, or upload weights to GitHub.

The pipeline is deliberately limited to private experimental research, matching
the intended use recorded in the current source-approval manifest. Re-check the
model and data licenses before any distribution or commercial use.

## Data protections

- Every TXT file in the selected data directory must have an exact approval
  entry matching SHA-256, UTF-8 character count, reviewer, rights basis, and
  \`intended_use=research_training\`.
- Only approved \`original_dialogue_ar*.txt\` files are used as supervised
  user/assistant examples. Narrative seed prose is not silently converted into
  conversations.
- Candidate JSONL files remain excluded; this path does not read them.
- Exact duplicate conversations are removed.
- Likely email addresses, Egyptian mobile numbers, and credential-like strings are rejected before tokenization.
- A deterministic conversation-level split creates separate train, validation, and final test sets; the final test set is not used for checkpoint selection.
- Loss is applied to assistant response tokens; user prompt tokens are masked.
- Training is dry-run by default. No model is loaded until \`--execute\` is set.
- A CUDA GPU is required by default. CPU mode needs an explicit opt-in.
- Output is a local adapter plus metadata; no automatic merge, upload, or release.

## Google Colab setup

Use a fresh GPU runtime. From the repository root, run:

\`\`\`bash
pip install -r ai_engine/requirements-lora.txt
python ai_engine/finetune_qwen_lora.py
\`\`\`

The second command is a read-only dry-run. It prints approved source hashes,
conversation counts, train/validation/test counts, source hashes, and the model/license identity.

Only after checking that report, start real fine-tuning:

\`\`\`bash
python ai_engine/finetune_qwen_lora.py --execute
\`\`\`

The default adapter output is \`artifacts/jon2-qwen25-05b-lora/\`. Keep it in
private storage such as the user's Google Drive. Do not commit training data,
model weights, adapters, tokens, or private reports to the public repository.

For a small GPU, reduce \`--batch-size\` to 1 and keep gradient accumulation
enabled. If CUDA memory is insufficient, stop rather than silently switching
to CPU or reducing data safeguards. A 0.5B model may fit on a modest GPU, but
memory use depends on the runtime, sequence length, and optimizer state.

## After training

1. Confirm the metadata reports a non-zero \`optimizer_steps_completed\`.
2. Confirm the adapter directory contains PEFT adapter weights and config.
3. Run a held-out benchmark that was not included in the training split.
4. Review Egyptian Arabic and Modern Standard Arabic answers manually for
   relevance, factual errors, unsupported claims, repetition, and dialect.
5. Compare the base model and base+adapter on the same prompts.
6. Keep public chat disabled until a human approves the exact adapter and the
   deployment runtime can load both the base model and adapter correctly.

A falling training loss alone is not evidence of better Arabic conversation.
The current small project-authored corpus may overfit; use the first run as a
controlled pilot and inspect validation loss and actual outputs before extending
training.
