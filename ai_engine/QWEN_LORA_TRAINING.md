# Jon2 Arabic LoRA training (separate research path)

## What this does

This optional pipeline fine-tunes the open-weight `Qwen/Qwen2.5-0.5B-Instruct`
base model with PEFT/LoRA. The official model card identifies Apache-2.0:
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

It produces a **separate adapter**, not a newly trained Jon2 foundation model.
It does not replace `jon2-small.pt`, change the original Jon2 trainer, enable
the production chat gate, deploy anything, or upload weights to GitHub.

The current source approvals authorize private experimental research only.
They do not authorize public redistribution or commercial training. Re-check
all model and data licenses before any wider use.

## Data protections

- Every TXT file in the selected data directory must have an exact approval
  entry matching SHA-256, UTF-8 character count, reviewer, review date,
  rights basis, and `intended_use=research_training`.
- Every TXT file present must be approved; an unapproved or changed file stops
  the run rather than being silently ignored.
- Only approved `original_dialogue_ar*.txt` files become supervised pairs.
  The approved narrative seed is hash-checked but not treated as dialogue.
- Candidate JSONL files remain excluded.
- Exact duplicate conversations are removed.
- Likely email addresses, Egyptian mobile numbers, and credential-like strings
  are rejected before tokenization.
- A deterministic conversation-level split creates separate train,
  validation, and final test sets. The final test set is not used for
  checkpoint selection.
- Loss is applied to assistant response tokens; user prompt tokens are masked.
- Training is dry-run by default. `--dry-run` is explicit and read-only.
- Real optimizer steps require `--execute` and a CUDA GPU by default.
- Output is a separate adapter plus metadata; no automatic merge, upload, or release.

## Google Colab setup

1. Open a new Google Colab notebook and select a GPU runtime under
   **Runtime > Change runtime type > T4 GPU** (availability depends on the account).
2. Clone `https://github.com/jonkabeel-star/jon2-ai` and change into the repo root.
3. Mount Google Drive:

   ```python
   from google.colab import drive
   drive.mount("/content/drive")
   ```

4. Install the optional dependencies and run the explicit dry-run:

   ```bash
   pip install -r ai_engine/requirements-lora.txt
   python ai_engine/finetune_qwen_lora.py --dry-run
   ```

The dry-run validates approved-source hashes and character counts, dialogue
format, privacy screening, and train/validation/test counts. It does not
download Qwen, load a model, create an optimizer, or change weights.

5. Review the dry-run report. Only then start actual fine-tuning and save the
   adapter directly to private Google Drive storage:

   ```bash
   python ai_engine/finetune_qwen_lora.py --execute --output /content/drive/MyDrive/Jon2_AI/jon2-qwen25-05b-lora
   ```

The output directory is created by the trainer. Do not commit training data,
model weights, adapters, tokens, or private reports to the public repository.
If GPU memory is insufficient, stop and reassess rather than silently
switching to CPU or removing safeguards.

## After training

1. Confirm metadata reports a non-zero `optimizer_steps_completed`.
2. Confirm the adapter directory contains PEFT adapter weights and config.
3. Inspect `final_held_out_test_evaluation`; it is separate from train and validation.
4. Run a held-out prompt benchmark not included in any training split.
5. Review Egyptian Arabic and Modern Standard Arabic answers manually for
   relevance, factual errors, unsupported claims, repetition, and dialect.
6. Compare the base model and base+adapter on the same prompts.
7. Keep public chat disabled until a human approves the exact adapter and the
   deployment runtime can load both the base model and adapter correctly.

A falling training loss alone is not evidence of better Arabic conversation.
The current project-authored corpus may overfit; treat the first run as a
controlled pilot and inspect validation loss and actual outputs before
extending training.
