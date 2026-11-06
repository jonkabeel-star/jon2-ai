# Jon2 model scaling profiles

This module defines reproducible architecture presets for the **project-owned**
Jon2 Transformer. It does not download third-party weights, create checkpoints,
provision hardware, or start a training job.

## Profiles

Run from `ai_engine`:

```bash
python -c "from model_profiles import list_profiles; import json; print(json.dumps(list_profiles(), indent=2))"
```

- `cpu_small`: small experimental configuration.
- `balanced`: medium research configuration.
- `advanced`: larger research configuration.
- `large_research`: large from-scratch experiment.

The estimate counts trainable parameters for the current tied-embedding
`Jon2Transformer` architecture. FP32 weight size is only a lower bound:
training also needs gradients, optimizer state, activations, temporary buffers,
and checkpoint space.

## Critical limitations

- A larger randomly initialized network is **not automatically smarter**.
- The current original corpus is only about 185,697 training tokens and the
  previous 269,952-parameter run produced incoherent Arabic. It is not enough
  evidence to train a substantially larger general-purpose assistant.
- A rough planning heuristic is to seek many training tokens per parameter;
  10–20 tokens per parameter is a useful *starting target*, not a guarantee.
  The advanced and large profiles therefore need vastly more reviewed text.
- Do not duplicate the existing corpus to satisfy a size threshold.
- Every new source must pass `source_approval.py` with its exact SHA-256,
  rights basis, intended use, and explicit approval. Do not add Wikipedia,
  CC BY-SA, unclear web scrapes, or any source without documented rights.
- The existing checkpoint is preserved. A new profile requires a fresh,
  separately named checkpoint; never overwrite the known-good historical file.
- No profile should be trained on the iPhone. The iPhone is the project-control
  device, not a practical training accelerator.

## Next safe training sequence

1. Review and approve additional original or clearly licensed Arabic dialogue.
2. Collect a large, diverse corpus with separate held-out evaluation blocks.
3. Run a hardware and memory preflight on the actual training machine.
4. Train a new checkpoint under a new filename and keep the old checkpoint.
5. Run held-out Arabic tests and human review. Keep public chat disabled unless
   answers are coherent, useful, and factually acceptable.

A profile is a capacity plan, not a claim that weights have been created.
