# Qwen3 Egyptian Arabic Trial (isolated)

This is an evaluation-only experiment. It does **not** make Qwen3 the production
brain of Jon2, does not fine-tune Qwen3, and does not modify Jon2 checkpoints.

## Model

- Model ID: `Qwen/Qwen3-0.6B`
- Official model card: https://huggingface.co/Qwen/Qwen3-0.6B
- Listed license: Apache-2.0 (review the model card and license file again before redistribution).
- The model card lists 0.6B parameters, a 32,768-token context window, and support for 100+ languages/dialects.
- We make no claim that the model will run acceptably on an iPhone. Run this trial in a temporary Python runtime with enough RAM/accelerator memory first.

## Run

From the repository root, install the existing AI-engine requirements and run:

```bash
python -m pip install -r ai_engine/requirements.txt
python ai_engine/evaluate_qwen3.py
```

The first run downloads the model weights from Hugging Face. This is local inference
inside the selected runtime, not a hosted Qwen API call. It requires network access
for the initial download and sufficient runtime memory/storage.

For a quick smoke test:

```bash
python ai_engine/evaluate_qwen3.py --limit 2 --output /tmp/qwen3-smoke.jsonl
```

The full run writes `qwen3_egyptian_trial.jsonl` in the current working directory.
Keep the output private until it has been reviewed.

## Review rules

1. Compare Qwen outputs with Jon2 outputs using the same held-out questions.
2. Have a human reviewer score correctness, Egyptian-naturalness, instruction following,
   context retention, safety, and hallucination separately.
3. Do not score an answer as good merely because it is fluent.
4. The benchmark is held out: do not add its prompts or outputs to any training corpus.
5. Do not use model-generated outputs as Jon2 training data without separate rights,
   provenance, and quality review.
6. Do not change production routing, release flags, or the original Jon2 checkpoint
   based on this experiment.

## Scope and limitations

This runner records raw outputs and execution errors. It does not provide an automatic
semantic-quality pass, does not prove Arabic dialect competence, and does not certify
production readiness. A successful run is only an inference smoke test.
