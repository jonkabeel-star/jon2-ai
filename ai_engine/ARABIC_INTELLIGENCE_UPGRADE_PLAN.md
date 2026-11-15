# Jon2 Arabic intelligence upgrade — rights, data, training, and release plan

Status: implementation plan only. No dataset is approved by this document, no corpus is downloaded, and no training/checkpoint/deployment is started.

## 1. Non-negotiable product definition

Jon2 answers only from the project-owned Jon2 checkpoint. No canned answer bank, cached answer, retrieval-as-answer, or third-party model fallback may be presented as Jon2 output. Retrieval may be used only as clearly identified supporting context if the original model itself writes the answer; this is not enabled by this plan.

If the original model is missing, fails inference, or returns malformed output, the API must fail closed. A successful forward pass or a fluent-looking string is not evidence of understanding.

## 2. Current verified blocker

The latest audited original checkpoint is a very small from-scratch Transformer (roughly 285k parameters, 512-token vocabulary, context 128) trained on a corpus measured at about 305k Arabic characters / 193k tokens. Historical held-out Arabic generations were incoherent. This checkpoint is not a viable general conversational assistant and must not be released.

The repository's private GPU workflow targets the `arabic_30m` profile and currently requires at least 20 approved tokens per parameter. At roughly 30M parameters, this implies a corpus on the order of 600M tokens before training. This is an engineering gate, not a guarantee that 600M tokens alone creates intelligence. Do not lower the gate, duplicate data, or pretend a smaller run is equivalent.

## 3. Dataset sourcing — candidate register, not approvals

Every candidate stays quarantined until its exact version, upstream provenance, license text, intended-use compatibility, privacy, and attribution obligations have been reviewed. A dataset-card license is not proof that every underlying record is owned or sublicensable.

| Candidate | Publicly declared terms / scope | Proposed treatment |
|---|---|---|
| UBC-NLP/Alexandria | Current dataset card declares CC BY-NC 4.0; a separately surfaced historical/revision-specific README declares CC BY-NC-ND 4.0. Multi-turn Arabic dialect conversations including Egyptian; published train/dev/public-test/private-test splits | **Quarantine / license conflict.** Pin an exact immutable revision and obtain written clarification from the publisher before any use. NC blocks commercial use; ND adds a separate adaptation concern. Never merge any test split into training. |
| Almheiri/ArabCulture-Dialogue | CC BY-SA 4.0; human-curated MSA and country dialect multi-turn dialogue; includes Egypt; currently exposes a single `eval` split per country | **Evaluation-only candidate.** Keep entirely outside training. Review share-alike implications and the upstream ArabCulture rights chain before use, even for evaluation. |
| ArSyra Arabic instruction/chatbot collections | Dataset cards declare CC BY-NC-SA 4.0; access/preview and paid full-data terms vary by collection | Quarantine pending exact file access terms and non-commercial/share-alike review. No paid data is assumed licensed. |
| Owner-authored Jon2 dialogues | Must be created by the project owner or contributors under a written assignment/license explicitly covering model training and intended distribution | Preferred source family. Store signed provenance/consent evidence privately; never put private records or signatures in the public repository. |
| Commissioned/native-speaker Egyptian dialogue | Requires contributor contracts covering recording/transcription, model training, derivative weights, commercial use if applicable, privacy, and withdrawal terms | Preferred source family for authentic Egyptian conversation, after written rights and privacy review. |
| LDC JANA Egyptian human-human dialogue corpus | LDC publishes a separate for-profit agreement allowing incorporation of portions into commercial work products for linguistic education/research/technology development; redistribution/display of the source data is restricted and access is licensed | **Commercial licensing lead only.** Obtain the actual license, confirm intended product use with LDC, price, access terms, and derivative-weight scope before considering it. Not downloaded or approved. |

References reviewed during planning:
- Alexandria dataset card: https://huggingface.co/datasets/UBC-NLP/alexandria
- ArabCulture-Dialogue dataset card: https://huggingface.co/datasets/Almheiri/ArabCulture-Dialogue
- ArSyra chatbot dataset card: https://huggingface.co/datasets/ArSyra/arsyra-chatbot
- Alexandria project split description: https://alexandria.dlnlp.ai/
- LDC JANA for-profit license agreement: https://catalog.ldc.upenn.edu/license/jana-a-human-human-dialogues-corpus-for-egyptian-dialect-agreement-for-profit.pdf
- Arabic dataset catalogue (discovery only): https://arbml.github.io/masader/

No external source above is approved for Jon2 training by this plan.

## 4. Rights gate before any download or training

For each exact dataset revision, record privately:
- source ID, repository and immutable revision/commit;
- source owner and upstream source chain;
- full license text/version and proof the publisher can license the underlying records;
- explicit permission for machine-learning/model training and, separately, intended commercial or non-commercial distribution;
- attribution, notice, share-alike, redistribution, and derivative-work obligations;
- privacy/consent review, personal-data handling, and takedown/withdrawal process;
- exact downloaded file names, byte counts, SHA-256 hashes, and collection date;
- reviewer identity, decision, and decision date.

Unknown, missing, NC, ND, SA, research-only, or otherwise incompatible terms remain excluded unless a qualified reviewer confirms compatibility for the actual intended use. Do not infer permission from public availability. A changing dataset-card badge is not enough: record the exact immutable revision and archive the license text that applied to that revision.

## 5. Data design and split discipline

Create separate private stores for:
1. `candidate_quarantine/`: raw candidate material plus provenance; never read by training.
2. `approved_sources/`: exact files whose rights and content have been explicitly approved.
3. `train/` and `validation/`: generated only from approved sources.
4. `heldout_eval/`: locked prompts and gold review materials; never exposed to the training loader.

Split by source, conversation, speaker/session, and near-duplicate cluster before chunking. All turns from a conversation and paraphrase/near-duplicate family must remain in one partition. Keep test prompts and human reference answers outside all training artifacts. Record hashes for every partition and prove no exact or normalized duplicate crosses train/validation/test. Use a final untouched test set for release decisions.

Coverage should include Egyptian colloquial Arabic, MSA, spelling variation, code-switching, natural multi-turn conversation, question answering, explanation, reasoning, arithmetic, instruction following, summarization, ambiguity, uncertainty, factual grounding, and safe refusal. Do not inflate the corpus with repeated lines or synthetic low-quality paraphrases.

## 6. Training sequence

1. Complete rights and privacy review for a meaningful, diverse source set.
2. Run the existing quarantine import/audit only where permitted; inspect reports before approval.
3. Build a private corpus using the existing rights-checked builder; strengthen it with conversation-aware split and cross-partition near-duplicate checks.
4. Run the existing tokenizer-aware preflight. Stop if approved tokens, quality, hardware, or profile gates fail.
5. Train a new profile-specific Jon2 checkpoint on a private GPU runner; keep all data, checkpoints, logs, and manifests outside the public repo and website.
6. Save best and resumable checkpoints, tokenizer, source hashes, config, training plan, hardware, and reproducible logs.
7. Run held-out MSA and Egyptian evaluations on the exact checkpoint hash. Compare against the previous checkpoint on the same prompts.
8. Require a native Arabic reviewer to score every release-blocking answer with the repository rubric. Record errors and rerun after fixes.

The current private GPU workflow is a guarded manual workflow, not an available GPU machine. Do not dispatch it until a real private GPU runner, private paths, approved corpus, and owner authorization exist.

## 7. Release gates

The public chat stays closed unless all are true:
- exact checkpoint and tokenizer hashes are recorded;
- inference is tested on the production runtime;
- held-out MSA and Egyptian sets pass predeclared semantic thresholds;
- multi-turn context and instruction-following tests pass;
- no critical factual, privacy, or safety failure is found;
- native-speaker human review is complete and signed;
- deployment is separately approved by the owner.

A UI change, health endpoint, low validation loss, or successful model load cannot satisfy semantic review. Never auto-set release environment flags from a training workflow.

## 8. Immediate next actions

- Confirm whether Jon2 is intended for commercial use. This determines whether NC datasets are categorically excluded.
- Resolve Alexandria's surfaced license discrepancy against the exact pinned revision; until then, exclude it.
- Treat ArabCulture-Dialogue as an external eval-only set, not a source for training examples.
- If commercial development is intended, request LDC's current JANA commercial terms and written confirmation of the intended model/weight use.
- Build a rights-reviewed owner-authored Egyptian/MSA conversation set and/or commission contributors with explicit model-training rights.
- Keep public benchmark/eval datasets separate from training.
- Only after the approved corpus and private GPU environment exist, run preflight and training.
