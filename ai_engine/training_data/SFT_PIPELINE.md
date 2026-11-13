# Jon2 assistant-only SFT data pipeline

This module prepares supervised conversation examples for the original Jon2
Byte-BPE Transformer. It does not download data, start training, or modify a
checkpoint.

## Loss behavior

- User text and role markers remain in `input_ids` as conditioning context.
- Their corresponding labels are `-100` (`IGNORE_INDEX`), so they contribute
  no cross-entropy loss.
- Only assistant response tokens and the assistant turn-ending newline are
  supervised.
- Conversations must alternate user/assistant and end on a complete assistant
  turn. Oversized conversations are rejected rather than silently truncated.
- Train/validation splitting happens by whole conversation, never by token
  windows, to prevent the same dialogue leaking across both splits.

## Required safeguards

Use a dedicated private directory containing only JSONL conversation files.
The exact-file approval manifest must be private and must contain each file's
SHA-256, character count, reviewer, review date, rights basis, APPROVED status,
and intended use. This module calls the existing fail-closed source approval
validator before reading any conversation.

The current project dialogue JSONL files are not automatically approved.
Do not add the 100-question held-out evaluation file to SFT data. It is
evaluation-only and must remain separate.

## Status

## Optional training command

`ai_engine/sft_training.py` adds an explicit, opt-in trainer. It strictly loads the
private checkpoint's original Byte-BPE tokenizer and model configuration, then
computes shifted causal loss only where assistant labels are not `-100`.
It refuses to run below 50 approved training conversations or 10,000 assistant
target tokens, and it refuses to overwrite either the source checkpoint or an
existing output file. The new checkpoint records the source-checkpoint SHA-256,
approval-manifest SHA-256, approved file hashes, train/validation counts, and
validation loss.

Example command (only after the private dataset and manifest are approved):

```bash
python ai_engine/sft_training.py \\
  --checkpoint /private/jon2-last.pt \\
  --data /private/jon2-sft-jsonl \\
  --approval-manifest /private/source_approvals.json \\
  --output /private/jon2-sft-v1.pt
```

The command has not been run. CI tests validate data masking and overwrite
protection; they do not train the user's private model. Passing code checks is
not a claim that the model's Arabic quality has improved.
