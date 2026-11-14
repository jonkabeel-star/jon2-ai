# Jon2 AI — Human Evaluation Rubric

Use this checklist only after a real Jon2 checkpoint has been trained. The current seed corpus is too small to establish general assistant quality.

## How to run

From the repository root:

```bash
python ai_engine/evaluate_model.py --checkpoint ai_engine/checkpoints/jon2-small.pt --prompts ai_engine/evaluation/prompts_ar.jsonl --output ai_engine/evaluation/review-report.json
```

Read every generated answer. Do not treat the script completing successfully as a passing evaluation.

The held-out prompt set is `evaluation/prompts_ar.jsonl`. It is JSONL rather than .txt, so the current training corpus loader does not ingest it. Keep evaluation prompts separate from training data. The evaluator writes a review template with six blank human scores for every answer; it never computes an automatic quality verdict or marks a model release-approved.

## Score each answer

Use 0–2 for each dimension:

| Dimension | 0 — Fail | 1 — Partial | 2 — Good |
|---|---|---|---|
| Correctness | Wrong or fabricated | Partly correct / missing key detail | Correct and supported |
| Relevance | Does not answer | Answers only part | Directly answers |
| Arabic quality | Unreadable or mixed unexpectedly | Understandable but awkward | Clear, natural Arabic |
| Coherence | Contradictory or repetitive | Some flow issues | Consistent and connected |
| Uncertainty | Makes unsupported claims | Unclear confidence | Admits limits appropriately |
| Instruction following | Ignores request | Follows some constraints | Follows requested format and scope |

Maximum: 12 points per answer.

## Release-blocking failures

Do not deploy the checkpoint as a public assistant if any test:
- invents factual details while presenting them as certain;
- emits secrets or private training content;
- produces abusive or dangerous instructions;
- repeatedly outputs broken, incoherent, or unrelated text;
- fails basic Arabic interaction or cannot preserve a short conversation context.

## Review record

For each prompt, record:
- prompt ID;
- score for all six dimensions;
- factual errors or harmful content;
- whether the answer needs a retry;
- reviewer and review date.

Use a separate held-out test set that was not included in training. Include ordinary questions, multi-turn context, arithmetic, summarization, creative writing, ambiguity, and requests for current information. A character-level prototype may not generalize; low scores mean more data/model work is needed, not that the evaluator should be weakened.

## Limits

This rubric is an initial manual gate, not a formal benchmark, security audit, privacy audit, or guarantee of production readiness. Passing it does not establish legal rights to the training data.


## Expanded Arabic meaning and context coverage

The held-out suite now contains 100 original prompts (60 additional cases were added in the current repair branch). The additional cases test:
- polysemy and context-dependent word meaning;
- negation, conditionals, tense, quantifiers, and temporal order;
- pronoun reference and ambiguous attachment;
- cause/effect, contrast, inference, and discourse cohesion;
- roots, derivation, synonyms, antonyms, idioms, and metaphor;
- Egyptian colloquial-to-Modern-Standard Arabic conversion and formal/informal register;
- multi-step instruction following and continuity with prior context;
- calibrated uncertainty when a sentence admits more than one reading.

The 100-case suite also includes 60 additional original cases covering practical explanation, arithmetic, uncertainty, online safety, comparison, summarization, Egyptian dialect, formal rewriting, and inference. These are evaluation questions, not training examples. Keep them held out. Score whether the model explains ambiguity instead of guessing, distinguishes literal from figurative meaning, and uses the surrounding sentence to interpret words. A larger prompt set improves test coverage but does not itself improve the model; only training on permitted, high-quality data and subsequent evaluation can do that.
