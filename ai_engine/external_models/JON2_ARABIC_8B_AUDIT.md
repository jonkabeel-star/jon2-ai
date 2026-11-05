# Jon2 Arabic 8B — Model and Rights Audit

**Owner-approved target:** 8B parameters, Egyptian Arabic first, with strong Modern Standard Arabic.
**Runtime goal:** self-hosted Python inference inside Jon2 infrastructure; no paid inference API and no forwarding user conversations to an external AI provider.
**Decision status:** BLOCKED pending training-data provenance review. No third-party checkpoint is approved for download, fine-tuning, or deployment yet.

## Candidate A — Jais 2 8B Chat

- Model repository: https://huggingface.co/inception42/Jais-2-8B-Chat
- Model identifier: `inception42/Jais-2-8B-Chat`
- Published parameter count: 8B.
- Model card declares Apache-2.0 for the model release.
- Model card describes Arabic and English training from scratch, an Arabic-centric vocabulary, MSA and regional dialect support.
- The public model card inspected for this audit does not provide a sufficiently detailed, auditable inventory of underlying pretraining and post-training datasets, source URLs, per-source licenses, or rights/permission basis for every text source.
- Related historical disclosure: the older Jais-family model card (not the Jais 2 card) explicitly lists public web pages, Wikipedia articles, news, social-network content, books, arXiv papers, and synthetic translations as training sources. This does **not** prove Jais 2 used the same sources; it does make a written clarification about Jais 2's own corpus especially important for this project. See https://huggingface.co/inception42/jais-family-590m-chat/blob/refs/pr/2/README.md.
- Therefore Apache-2.0 on the model repository is not treated as proof that every underlying training text is independently cleared for Jon2's intended use.
- **Status: HOLD — do not download, fine-tune, or deploy until the model authors provide adequate written provenance and rights clarification.**

## Candidate B — Falcon-H1-Arabic

- Official model family announcement: https://huggingface.co/blog/tiiuae/falcon-h1-arabic
- Official product page: https://falconllm.tii.ae/falcon-h1-arabic.html
- Publicly announced sizes: 3B, 7B, and 34B; there is no announced 8B variant.
- The official description reports Arabic, English, and multilingual training content, with dialect coverage including Egyptian Arabic. It describes approximately 300 billion total tokens but does not provide a complete source-by-source rights manifest in the material reviewed here.
- **Status: NOT SELECTED** because no 8B checkpoint matches the owner's selected size, and the reviewed public materials do not settle the project's source-level rights requirements.

## Rights rules for Jon2

1. Do not use Wikipedia-derived text, CC BY-SA material, HPLT web-crawl text, or sources with unclear rights unless the owner separately approves after a documented rights review.
2. Do not infer dataset rights from a model-weight license alone.
3. Require the model publisher to identify dataset names, source provenance, applicable licenses/permissions, exclusions, and any attribution/share-alike obligations.
4. Preserve the existing Jon2 original checkpoint and training corpus separately. Do not overwrite them.
5. Never place model weights, access tokens, private datasets, or credentials in the public GitHub repository.
6. Do not set `JON2_CHAT_RELEASE_APPROVED=true` until the selected checkpoint passes held-out Egyptian Arabic and MSA evaluation plus human review.

## Implementation preparation

The integration must be isolated from the original Jon2 model:

- Keep the original Jon2 Transformer and checkpoint loader unchanged.
- Add a separate external-open-weights adapter only after a specific model and its license/provenance are approved.
- Keep model identifier, revision/commit, tokenizer revision, quantization, and runtime settings in a private deployment configuration.
- Load weights from private runtime storage or a trusted model registry; never commit them to Git.
- Expose the selected model only through Jon2's own authenticated Python API.
- Disable outbound inference-provider calls. Network access needed to fetch approved model files during deployment must not be used to forward prompts or conversation history.
- Evaluate Egyptian colloquial fluency, MSA fluency, instruction following, factuality, multi-turn coherence, refusals, and prompt-injection resistance.

## Next evidence required

Before approving Jais 2 8B, obtain a written answer from the publisher covering:
- Exact pretraining and post-training dataset names and versions.
- Original source URLs or dataset custodians and the source-level license/permission basis.
- Whether Wikipedia, web crawls, books, forums, or user-generated content are included.
- Whether training and commercial deployment of a derived model are permitted under those source rights.
- Required attribution, notice, opt-out, or share-alike obligations.

**Current operational decision:** prepare the integration design, but do not download or train on an unverified third-party checkpoint. This is a rights-and-provenance hold, not a technical failure.
