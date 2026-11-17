# Jon2 phase 4: checkpoint quality comparison

This phase establishes a human-reviewed comparison process before any proposed
checkpoint change is considered.

## What is measured

Each held-out prompt is reviewed for five dimensions on a 1–5 scale:

- correctness
- coherence
- Arabic quality (including dialect appropriateness)
- instruction following
- factuality

Every record identifies whether the prompt is MSA, Egyptian Arabic, or mixed,
the baseline/candidate checkpoint SHA-256, reviewer, and review date. The
comparison requires the same prompt, reviewer, and language variant to be
scored for both checkpoints. It reports candidate-minus-baseline deltas and
keeps MSA and Egyptian results separate.

## Safety

- Records must use the heldout_evaluation_only split. This tool rejects
  training-split records.
- Held-out prompts and model outputs must never be added to pretraining or SFT.
- The tool checks hash format and equality, not checkpoint authenticity.
- Human ratings are evidence for review, not proof of understanding.
- No checkpoint is loaded or executed by this tool.
- No weights are changed, no fine-tuning is run, and no candidate is promoted.
- A candidate should not be considered better based on one aggregate number;
  inspect per-dimension and per-dialect deltas and review disagreements.

The existing private original checkpoint and a candidate checkpoint must be
evaluated in the user's private environment. Their bytes and generated outputs
must not be committed to this repository.
