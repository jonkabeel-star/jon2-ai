# Jon2 AI — Training Readiness and Model Quality Status

Last verified: 2026-11-05

## Current verified state

- Five UTF-8 Arabic dialogue files were explicitly approved for this experimental training run through the private source-approval manifest.
- The approved corpus contained 289,120 Unicode characters at the time of training. It is a small corpus for a general-purpose conversational model.
- Real training run [42027297208](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42027297208) completed on a GitHub-hosted CPU runner using the project-owned Transformer and PyTorch.
- The run completed 1,200 optimizer steps. The best validation checkpoint was selected at step 900 with validation loss 3.6355; the final resumable checkpoint was saved at step 1,200.
- The model contains 269,952 parameters. These are real trained weights, not a pretrained third-party model.
- The checkpoint loaded on CPU and generation executed successfully.
- Both `jon2-small.pt` and `jon2-last.pt` were uploaded to the private Kaggle dataset `jon2kabeel/jon2-private-model-checkpoint`. Independent verification run [42028045019](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42028045019) confirmed that both files were present.
- Held-out evaluation of 40 Arabic prompts completed in run [42028581017](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42028581017). The generated answers were visibly malformed and incoherent Arabic. The run created a human-review artifact; it did not grant a quality pass.
- Public chat remains disabled. Do not set `JON2_CHAT_RELEASE_APPROVED=true` for this checkpoint.

## Interpretation

The project has now completed its first genuine end-to-end training and private checkpoint-storage cycle. This proves that the training code can update model weights, save a checkpoint, reload it, execute inference, and preserve the weights in private storage.

It does **not** prove that the model understands Arabic, answers accurately, follows instructions, remembers context, or is safe for public use. The current checkpoint fails the practical conversation-quality gate.

## Next gates

1. Expand the corpus substantially with original, high-quality Arabic examples and documented ownership/permission for every source.
2. Keep held-out evaluation prompts separate from training data.
3. Audit every new source for exact duplicates, malformed UTF-8, privacy signals, and content quality before approval.
4. Increase model/tokenizer capacity only alongside a materially larger and more diverse corpus; scaling the model alone will not create knowledge.
5. Train a new checkpoint, compare validation curves, and generate the same held-out report.
6. Have a human review all held-out answers using `EVALUATION_RUBRIC.md`.
7. Keep the public chat release gate closed until the exact checkpoint passes human review and is deployed to a real backend.

## Data and rights boundary

The five approved files are the only sources covered by the current training approval. Any new or modified `.txt` file must receive its own explicit approval record bound to the exact SHA-256 fingerprint and UTF-8 character count before another training run. Do not add Wikipedia-derived, scraped, private, personal, or third-party text without separately verifying the rights and obtaining the required approval.

## Hardware boundary

The RTL design and its Icarus Verilog simulations are a separate engineering track. No physical FPGA board, ASIC, GPU, or local AI compute hardware has been created or programmed by these training runs. GitHub-hosted CPU runners supplied the compute for the training cycle.


## Verified readiness update — 2026-11-09

### 30M profile preflight

The latest successful Python Checks workflow on draft branch `work/egyptian-arabic-foundation-v2` is [42542396281](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42542396281), commit `00da8afc90da770259e2750af969f7ac6d3a6043`. It ran the `arabic_30m` preflight only; it did not instantiate or train a 30M model.

- Measured corpus inventory from the read-only preflight: 305,406 characters.
- 512-vocabulary probe: 193,403 tokens total (an optimistic upper bound for the larger target tokenizer).
- `arabic_30m` configuration estimate: 29,938,688 parameters. This is a configuration-derived estimate, not trained weights.
- At the configured minimum of 10 tokens per estimated parameter, the rough gate would require 299,386,880 approved tokens. The current probe is about 0.00646 tokens per estimated parameter and fails by a very large margin.
- Readiness: **NOT READY**. The exact 8,192-token tokenizer fit was skipped because even the optimistic probe bound could not meet the corpus-scale gate.
- The 80-turn Egyptian draft and 30 held-out Egyptian prompts are separate and are not counted as approved training tokens.

Do not launch 30M training. Do not lower the token/parameter gate or duplicate text to pass it. The 30M profile still needs a suitable high-memory GPU environment and a verified, resumable, profile-specific checkpoint workflow.

### Checkpoint evidence and limitations

The historical original model checkpoint contains 269,952 actual parameters and completed 1,200 optimizer steps. The private Kaggle dataset previously verified the two legacy checkpoint files; the recorded sizes were 3,285,607 bytes (`jon2-small.pt`) and 3,285,488 bytes (`jon2-last.pt`). The captured SHA-256 is available for the best checkpoint only: `acbae28e4acc4dc060194df466f65a72410792f5b0fec7ff9bdd939244b9c43f`. A matching recorded SHA-256 for the resumable checkpoint was not present in the available evidence.

No 30M checkpoint exists. Do not confuse the legacy 269,952-parameter checkpoint with the 30M profile.

### Automation safety

The legacy CPU training workflow on `main` currently has schedule and push triggers and writes fixed latest checkpoint filenames. This is not a 30M training workflow. A proposed safety PR changes it to manual-only with an exact confirmation input and adds run-specific checkpoint copies plus SHA-256 manifests. Until that PR is reviewed and merged, the existing main-branch workflow definition remains unchanged.

A previously observed legacy workflow run `42538599326` remained in `pending` with no job records at the time of inspection. No active job was visible in the connector snapshot; this is not proof that the queue has been cancelled. The connector does not expose a cancel action here. Do not dispatch another training run.

### Human review

No human review or release approval is recorded for the current checkpoint. The 40-prompt historical evaluation was explicitly marked for human review and showed incoherent Arabic. The release flag must remain false.

## Verified Vercel preview runtime and model-quality check — 2026-11-25

- The Vercel Preview FastAPI service started successfully and loaded the approved `jon2-last.pt` checkpoint from the private Vercel Blob store. The runtime verified the checkpoint SHA-256 before loading it; the health endpoint reported 3,471,600 bytes, a readable checkpoint path under `/tmp`, and `model_loaded=true`.
- A preview-only four-prompt diagnostic exercised MSA explanation, Egyptian instruction following, simple arithmetic, and conversation context. The raw model output was malformed/incoherent Arabic on the MSA, Egyptian, and arithmetic prompts; the conversation-context output failed the text-integrity validator. This is a technical inference failure, not a semantic-quality pass.
- The preview health state correctly remained `inference_tested=false`, `quality_review_passed=false`, `release_approved=false`, and `chat_ready=false`. Public chat must remain closed.
- The latest read-only `arabic_30m` preflight (GitHub Actions run 1121) measured 305,406 corpus characters, 129,768 training tokens, 63,751 validation tokens, and 193,519 total probe tokens. The target profile estimates 29,938,688 parameters and requires at least 20 approved tokens per parameter (about 598.8 million tokens). The measured ratio is only 0.006464 tokens per parameter.
- The preflight correctly reported `ready=false` with blockers `corpus_below_minimum_characters` and `insufficient_tokens_per_parameter`. The 8,192-token tokenizer fit was skipped. No 30M model was instantiated or trained, and no candidate dataset was downloaded or approved.
- Conclusion: the current checkpoint is genuinely loaded and executable on Preview, but it is not a usable Arabic conversational model. Do not enable public chat, lower the data gate, or pad the corpus with duplicates or synthetic low-quality text. Next work requires a materially larger rights-cleared Arabic corpus, conversation-aware held-out splits, a private GPU runner, and human review of the next checkpoint.
