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

This is the data-preparation foundation only. It is not yet a training command.
Before training is enabled, the next implementation stage must add a checkpoint
loader that preserves the exact private checkpoint architecture and tokenizer,
an assistant-only loss loop using shifted labels, a new output checkpoint path,
SHA-256 provenance, and tests proving the source checkpoint is never overwritten.
