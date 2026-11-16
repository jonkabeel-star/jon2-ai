# Jon2 Arabic language data pipeline

This document defines the safe path from public discovery to an approved private
training corpus. A dataset being free to download does **not** mean its text is
licensed for model training, redistribution, or commercial use.

## Target language coverage

Build separate, measurable coverage for:
- Egyptian colloquial Arabic (primary conversational target)
- Modern Standard Arabic (MSA / الفصحى)
- Mixed Egyptian/MSA, spelling variation, Arabizi only if explicitly in scope
- Multi-turn conversations, explanations, summaries, instructions, reasoning,
  uncertainty, writing, and safety behavior

Do not mix dialect labels or assume that generic Arabic text teaches Egyptian
conversation. Preserve source and dialect metadata at record level.

## Candidate discovery (not automatic approval)

Use Masader to discover resources and inspect each dataset's own licence,
provider terms, paper, collection method, and redistribution restrictions:
https://arbml.github.io/masader/

Candidate notes:
- UBC-NLP/Alexandria includes Egyptian Arabic dialogue/parallel material, but
  its Hugging Face card declares CC BY-NC 4.0. Treat it as **non-commercial
  research only** unless the owner grants separate written permission. It is
  not approved for a public/commercial Jon2 release:
  https://huggingface.co/datasets/UBC-NLP/alexandria
- MADAR is useful for dialect coverage, but the resources index reports custom
  terms of use. Do not ingest until those terms are read and the intended model
  use is confirmed:
  https://github.com/NNLP-IL/Arabic-Resources
- NADI, DART, AOC, social-media crawls, and web-scraped corpora require
  source-level review. A catalogue entry or public download is not proof that
  the underlying authors granted model-training rights.

## Approval checklist for every exact file

1. Record dataset name, provider, canonical URL, version/revision, download date,
   exact file path, SHA-256, language/dialect, size, and collection method.
2. Save the full licence text or a stable licence URL and record allowed uses:
   research, redistribution, public model, and commercial model separately.
3. Reject unknown, custom, non-commercial, or incompatible terms for any use
   they do not explicitly permit. Ask the rights holder when ambiguous.
4. Check personal data, private conversations, scraped usernames, sensitive
   content, and takedown obligations. Remove or reject material that should not
   be retained.
5. Deduplicate exact and near-duplicate records before splitting.
6. Split by source/conversation group into train, validation, and a sealed test
   set. Never split adjacent turns from one conversation across partitions.
7. Human-review samples for Egyptian naturalness, factual quality, and noise.
8. Add only approved exact files and hashes to the private source approval
   manifest. The trainer must remain fail-closed if any file is unapproved.

## Dataset quality and training format

Prefer complete, coherent user/assistant conversations written or reviewed by
native Egyptian Arabic speakers. Include realistic spelling variation while
avoiding artificial slang stuffing. Store JSONL as one conversation per line:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}

Do not copy held-out evaluation prompts into training. Keep source groups intact.
Keep a balanced MSA subset so the model can switch register when asked.

## Training and model sizing

Do not select the 30M profile until the approved corpus and measured token count
support it. Current trainer policy requires 20 approved tokens per parameter;
that means roughly 600M approved tokens for 30M parameters. This is a project
quality gate, not a universal scientific law. Use a smaller capacity-matched
profile until the corpus grows, and report actual token counts, validation loss,
and overfit indicators. Do not duplicate data to satisfy thresholds.

Train the original Jon2 architecture from scratch; do not download pretrained
weights or call hosted inference APIs. Keep checkpoints, manifests, and raw
licensed data private. Record checkpoint SHA-256 and training configuration.

## Free compute and limits

Kaggle documents free GPU notebook access, with quotas and availability limits.
Use it only for reproducible training runs with checkpoints saved frequently:
https://www.kaggle.com/docs/efficient-gpu-usage

A free GPU session is temporary compute, not permanent hosting. It does not
remove the need for a sufficiently large approved corpus. iPhone-only local
inference is a separate export/runtime project and must pass device memory,
latency, and thermal tests before release.

## Release gates

A checkpoint is eligible only after:
- clean train/validation/test separation and source audit
- successful deterministic load and generation tests
- held-out Egyptian and MSA benchmark review by humans
- multi-turn context, instruction-following, and safety review
- no critical failures and documented minimum score agreed by the owner
- real iPhone runtime tests if local Safari is the release target

Never change release approval flags to make the interface appear functional.
