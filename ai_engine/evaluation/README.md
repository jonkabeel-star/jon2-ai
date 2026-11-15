# Jon2 Arabic 100-question held-out evaluation

**Evaluation only. Never include this file in pretraining, instruction tuning, augmentation, or model-selection training data.**

- 100 prompts: 10 categories × 10 prompts.
- Coverage: MSA, Egyptian Arabic, instruction following, reasoning, uncertainty, safety/privacy, grammar, translation, multi-turn context, and planning.
- Each item has a rubric and empty score fields. Human reviewers must inspect actual raw model answers. Automatic fluency or repetition checks do not replace human review.
- Score each dimension from 1–5; leave null until reviewed. 1 = unusable/materially wrong; 2 = major errors; 3 = partly useful; 4 = good with minor issues; 5 = correct, clear, fully compliant.
- For each run, record checkpoint SHA-256, tokenizer SHA-256, runtime, decoding parameters, and raw outputs in a separate private report.
- Do not tune on these 100 prompts. If used to guide model changes, retire the set and create a fresh held-out benchmark.

## Release rule

Passing syntax or heuristic checks is not model approval. Require category-level human review, factuality checks, and a separate fresh challenge set before public chat release. Preserve raw generations, including failures.
