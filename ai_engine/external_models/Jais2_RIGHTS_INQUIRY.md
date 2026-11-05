# Jais 2 8B — Training Data Rights and Provenance Inquiry

**Project:** Jon2 AI (independent Arabic AI platform)  
**Checkpoint under review:** `inception42/Jais-2-8B-Chat`  
**Purpose:** Determine whether Jon2 can lawfully download, locally run, fine-tune, and commercially deploy this checkpoint and derivatives while honoring source-level rights.

## Why we are asking

The public Jais 2 announcement describes pretraining on 2.6 trillion curated Arabic, English, and code tokens, and more than twenty million instruction-response pairs for supervised fine-tuning. The public material reviewed for this audit does not provide a source-by-source dataset manifest with licenses or permission basis. The model-weight license alone does not answer every underlying data-rights question.

## Questions requiring written answers

Please answer specifically for **Jais 2 8B Chat**, distinguishing pretraining, supervised fine-tuning, preference/alignment, and synthetic data:

1. What are the exact datasets, dataset versions, corpus snapshots, and collection dates used in each training stage?
2. For each dataset/source, who is the original publisher or custodian? Please provide source URLs or dataset documentation and the applicable license or other permission basis.
3. Did any stage include Wikipedia or Wikimedia-derived content, Common Crawl or other web crawls, books, news, forums, blogs, social-media posts, code repositories, or other user-generated content? Please identify each source family and its rights basis.
4. Were any sources used under licenses with attribution, share-alike, non-commercial, research-only, field-of-use, or other downstream restrictions? If yes, what obligations apply to a commercial derivative model?
5. What filtering, deduplication, opt-out, takedown, and rights-review processes were applied? Can you provide a data card, manifest, or audit summary?
6. For synthetic and translated data, what source materials and teacher models were used, and what rights/terms govern the generated outputs?
7. Does the Apache-2.0 model release grant permission to use, fine-tune, and commercially deploy the weights, subject to any separately applicable data-source obligations? Please identify all notices, attribution, share-alike, or other obligations that a downstream deployer must satisfy.
8. Are there any excluded or restricted uses, territories, or deployment conditions beyond the published model license and access terms?

## Jon2's intended use

- Download the published checkpoint after reviewing and accepting the official access terms.
- Run inference on Jon2-controlled infrastructure; do not send user prompts or conversation histories to an external inference provider.
- Potentially fine-tune a derivative using separately rights-reviewed, owner-approved data.
- Potentially offer the resulting Jon2 service commercially.
- Preserve a separate original Jon2 model and its independently created corpus.

We will not treat a general statement that data was "publicly available" or "curated" as sufficient evidence of source-level rights.

## Draft message to send

**Subject:** Jais 2 8B Chat — request for training-data provenance and downstream rights clarification

Hello Inception AI / Jais team,

I am developing Jon2 AI, an independent Arabic AI platform. We are evaluating `inception42/Jais-2-8B-Chat` as a locally hosted foundation model, with Egyptian Arabic as our first priority and Modern Standard Arabic support.

Before downloading, fine-tuning, or deploying the checkpoint, we need to understand the provenance and rights status of the training data. The public release materials describe the model and its permissive weights license, but we have not found a sufficiently detailed source-level dataset manifest.

Could you please provide the dataset names and versions for pretraining and post-training, their original sources and applicable licenses/permissions, and clarify whether Wikipedia/Wikimedia content, web crawls, books, news, forums, social-media or other user-generated content were included? We would also appreciate written guidance on downstream commercial fine-tuning/deployment and any attribution, share-alike, opt-out, or other obligations.

Our goal is to respect copyright and dataset licenses. We will keep the model local and will not forward Jon2 users' prompts or conversations to an external inference provider.

If a full public manifest is not available, could you direct us to the appropriate legal, research, or model-governance contact and provide a written summary of the relevant sources and permissions?

Thank you for your time.

Best regards,  
Jon2 AI project

## Official contact route

Use Inception's official contact page: https://www.inception42.ai/contact

Do not invent or guess an email address. Submit this request through the official contact route or an official contact supplied by the company.

## Decision rule

Keep Jais 2 in **HOLD** until the answers are specific enough to assess the source-level rights. A permissive model-weight license is not, by itself, proof that every training source is cleared for the intended downstream use.
