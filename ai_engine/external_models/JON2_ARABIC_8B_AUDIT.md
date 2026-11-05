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
- The Hugging Face repository currently requires a logged-in user to review and accept access conditions before downloading files; this is a model-access gate, not evidence that the underlying training corpus rights are cleared.
- The model card reports 8B parameters in BF16 and an 8,192-token context window. BF16 weights alone require roughly 16 GB before runtime memory, KV cache, and operating-system overhead; an actual deployment needs additional memory.
- The model card publishes its own benchmark results, including Arabic instruction-following and AraGen results. Treat these as publisher-reported results, not an independent guarantee of Egyptian-dialect quality; Jon2 must run its own held-out Egyptian Arabic evaluation.
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

A separate local-only adapter has been added at `ai_engine/external_models/jais2_runtime.py`. It loads from a local directory only (`local_files_only=True`), disables remote custom code, uses the model's chat template, and does not call an inference provider. It is intentionally not connected to the public `/api/chat` route and cannot load anything until a local path is configured. This is preparation code, not a model download or a successful inference test.

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


## Additional official-source review (2026-11-05)

- Inception's current multilingual-models page explicitly lists Jais-2 8B and Jais-2 8B Chat, and describes Jais pre-trained models as trained from scratch. It also provides an official "Get in touch" route: https://www.inception42.ai/contact.
- The official Cerebras Jais 2 technical overview states that Jais 2 pretraining used 2.6 trillion curated Arabic, English, and code tokens, and that supervised fine-tuning used more than twenty million instruction-response pairs. The overview describes the training pipeline but the public page reviewed here still does not give a source-by-source dataset manifest with license/permission evidence.
- The official Inception contact page provides a company contact form/page, but the reviewed page does not publish a direct email address. Jon2 has therefore prepared a written inquiry at `ai_engine/external_models/Jais2_RIGHTS_INQUIRY.md`; send it through the official contact page rather than guessing an email.
- This additional review does not resolve source-level rights. **Jais 2 remains on HOLD.** No checkpoint download, fine-tuning, production inference, or public chat activation is authorized by this audit.


## New Arabic-model candidate review (2026-11-05)

### Jais 3 / K2 Horizon — promising transparency, but not approved for Jon2

Official sources published in September–October 2026 describe K2 Horizon as a much more transparent release than a weights-only model: IFM says it releases training data or detailed construction recipes, mixture composition, code, configurations, logs, evaluations, and weights. The Jais 3 technical blog then discloses more of the Arabic adaptation pipeline.

However, this does **not** make Jais 3 eligible under Jon2's current data policy:

- Jais 3 sizes include 7B and 32B, not the owner's selected 8B size.
- The official Jais 3 technical blog explicitly says its cool-down stage includes **Arabic Wikipedia**. Jon2's owner has not approved Wikipedia-derived training material.
- Jais 3 continues pretraining from K2 Horizon and replays K2 Horizon training data. The K2 Horizon mixture includes diverse web sources and synthetic data; where redistribution is restricted, IFM says it publishes source descriptions, filtering/construction methods, and mixture composition. This still requires source-by-source rights review against Jon2's stricter policy.
- The Jais 3 announcement reports strong Arabic results, but publisher-reported aggregate benchmark scores do not establish Egyptian-dialect suitability for Jon2.

Official references:
- K2 Horizon transparency and dataset release description: https://ifm.ai/blog/k2/
- Jais 3 technical training disclosure: https://ifm.ai/blog/jais3/
- Jais 3 launch announcement: https://www.inception42.ai/news/Jais3-Launch

**Decision: NOT APPROVED for Jon2 at this time.** This is not a quality judgment. It is excluded because it is 7B rather than 8B and its disclosed pipeline includes Arabic Wikipedia, which the owner has not authorized. Do not silently switch the project from Jais 2 8B to Jais 3 7B.

### Jais 2 remains the exact-size candidate

The official Jais 2 technical article confirms the 8B release and summarizes the training stages and aggregate data scale, but it does not provide the source-level dataset manifest needed for Jon2's rights review. Keep Jais 2 on HOLD pending a written response from the publisher.

## Adapter verification automation

Added an offline-only contract test suite at `test_jais2_runtime.py` and a GitHub Actions workflow at `.github/workflows/jais2-adapter-check.yml`. These checks verify fail-closed local-path behavior and enforce `local_files_only=True` plus `trust_remote_code=False` in the loader. They do not download weights, install the model, or prove inference quality. Confirm the GitHub Actions run result before treating these checks as passed.


## New candidate review — Karnak 40B (Egyptian-focused)

Official sources reviewed on 2026-11-05:

- AIC project page: https://www.aic.gov.eg/projects/38/
- AIC launch announcement for Karnak Chat (2026-08-23): https://www.aic.gov.eg/news/43/
- Official Hugging Face model card: https://huggingface.co/Applied-Innovation-Center/Karnak-40B-v1.0

What the publisher states:

- Karnak is an Egyptian Arabic-English model family, with explicit focus on Egyptian colloquial Arabic and local cultural context.
- The published open-weight checkpoint is Karnak 40B, approximately 40B parameters, not 8B.
- Its model card identifies Qwen/Qwen3-30B-A3B-Instruct-2507 as the base model and describes depth extension, continued pretraining, and supervised fine-tuning.
- The Hugging Face model card declares Apache-2.0 for the Karnak release.
- AIC describes the training material as curated, cleaned, and locally sourced Arabic data, but the public materials reviewed here do not provide a source-by-source dataset inventory, source URLs, licenses, or permission evidence.
- The AIC launch announcement says the model draws on documents published in Egypt and the Arab world; this description alone does not establish the license or reuse permission for every source.

Jon2 decision:

- **NOT SELECTED for the current 8B target:** the published checkpoint is 40B.
- **RIGHTS HOLD:** Apache-2.0 on the model card does not replace the missing source-level training-data rights manifest.
- **POTENTIALLY RELEVANT TO EGYPTIAN DIALECT RESEARCH:** its stated focus is aligned with Jon2's Egyptian-first goal, so retain it as a research lead only.
- Do not download, fine-tune, deploy, or switch the project to Karnak without a separate owner decision, compatible compute, and written source-level rights review.

This review does not change the selected Jais 2 8B candidate or authorize any third-party checkpoint.


## New candidate review — Apertus 1.5 8B (2026-11-05)

Official sources reviewed:
- Project Apertus transparency page: https://apertus-ai.org/pages/about/
- Official Hugging Face model card: https://huggingface.co/swiss-ai/Apertus-v1.5-8B
- Official model collection: https://huggingface.co/collections/swiss-ai/apertus-v15

What is promising:
- The publisher describes Apertus as fully open and publishes architecture, weights, training data, and methods. Apertus 1.0 is described as using public, versioned sources under open licenses, respecting web-data opt-outs, and being released under Apache-2.0.
- Apertus 1.5 offers an 8B-class checkpoint (the model card identifies it as Apertus-v1.5-8B; the repository UI reports approximately 9B total parameters), Apache-2.0, and multilingual text/image/audio input.
- The v1.5 card describes fully open training data and says the full training details will be published in its technical report.

Important unresolved points:
- Apertus 1.5 is a continuation of Apertus 1.0 with an additional multimodal mix of 4 trillion tokens for the 8B model. The model card says the detailed technical report and training pipelines will be provided in the coming weeks; the full source-level inventory and rights mapping for this v1.5 addition therefore still need to be checked before Jon2 can approve it.
- The Hugging Face repository requires the account owner to review and accept Apache-2.0 plus the Apertus Acceptable Use Policy. The page also says the owner's email and username will be shared with the repository authors on acceptance. Do not accept this on the owner's behalf.
- The official page describes multilingual coverage but does not establish strong Egyptian-colloquial performance. Jon2 must run its own Egyptian Arabic and MSA evaluation.
- The model card says its Transformers integration is not yet in a released upstream Transformers version and currently points to a Swiss-AI fork. Runtime compatibility and pinned dependencies must be tested before deployment.
- Its 8B BF16 class is not suitable for the user's iPhone 12 Pro Max as a local inference host. A separate compatible GPU host is still required.

Jon2 decision:
- **PROMISING RIGHTS-TRANSPARENCY CANDIDATE, NOT APPROVED YET.**
- This is a stronger transparency lead than a weights-only model, and it preserves the project's approximate 8B target.
- Keep Jais 2 on HOLD and do not replace it automatically. Apertus 1.5 may become the preferred candidate only after the v1.5 4T-token data supplement is documented at source/license level, the owner personally reviews the AUP and contact-information disclosure, and Arabic evaluation confirms acceptable quality.
- Do not download, accept access conditions, fine-tune, or deploy this checkpoint yet.



## Apertus 1.5 source-level rights review — 2026-11-05

The official Apertus dataset transparency catalogue was inspected directly (including its `used_in` field, license labels, and notes). The catalogue explicitly lists `HuggingFaceFW/clean-wikipedia` with `cc-by-sa-4.0` under `used_in: v1`. The official Apertus 1.5 release notes state that v1.5 is continued pretraining from Apertus 1.0. Therefore the v1.5 model inherits a base-model lineage whose v1 training catalogue includes Wikipedia / CC BY-SA, which the owner explicitly prohibited.

The v1.5 catalogue also includes additional records with Unknown/Other/Mixed/Openrail license labels and at least one v1.5 dataset row marked CC-BY-NC-4.0. The publisher describes filters and source-level exclusions for some mixed datasets, but this does not satisfy Jon2's stricter requirement to avoid prohibited or unclear source material across the entire inherited lineage.

Official evidence:
- Release notes: https://huggingface.co/blog/swiss-ai/apertus-v15-release-notes
- Dataset catalogue: https://github.com/swiss-ai/apertus-data-transparency
- Raw catalogue: https://raw.githubusercontent.com/swiss-ai/apertus-data-transparency/main/Apertus%20dataset%20repository.tsv

**Decision: Apertus 1.5 8B is REJECTED for Jon2 under the current data policy.** Do not download, fine-tune, or deploy it. The Apache-2.0 model-weight license does not override the owner's explicit data-source restrictions. See `APERTUS_1_5_RIGHTS_REVIEW.md` for details. This does not alter the Jais 2 HOLD decision or authorize a substitute.
