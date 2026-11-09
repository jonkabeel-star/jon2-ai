# Jon2 AI — Training Readiness and Model Quality Status

Last verified: 2026-11-09

## Latest read-only preflight — 2026-11-09

The latest successful Python Checks run is [42539702586](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42539702586). Its \`arabic_30m\` preflight was read-only and did not create weights or start training.

- Six exact text files passed the private source-approval manifest gate.
- Dataset inventory: 307,091 raw Unicode characters and 195,059 inventory tokens using the 512-token audit vocabulary.
- The preflight's deterministic corpus reader produced 305,406 characters; its 10% held-out split yielded 174,050 training tokens and 19,353 validation tokens.
- The \`arabic_30m\` profile estimates 29,938,688 parameters from its architecture configuration. This is an estimate, not a count of trained model weights; no 30M checkpoint exists as a result of this preflight.
- The 512-vocabulary probe produced 193,403 tokens total. Even this optimistic upper bound is only 0.00646 tokens per estimated parameter, below the configured minimum of 10.
- Readiness result: **NOT READY**, blocker \`insufficient_tokens_per_parameter\`.
- Script counts do not distinguish Modern Standard Arabic from Egyptian dialect. Human annotation is still required.
- The full 8,192-token tokenizer build was skipped because the optimistic upper bound already fails.

Do not start \`arabic_30m\` training based on this report. It is a capacity/readiness estimate only.

## Previously verified experimental checkpoint — 2026-11-05

- Five UTF-8 Arabic dialogue files were explicitly approved for this experimental training run through the private source-approval manifest.
- The approved corpus contained 289,120 Unicode characters at the time of training. It is a small corpus for a general-purpose conversational model.
- Real training run [42027297208](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42027297208) completed on a GitHub-hosted CPU runner using the project-owned Transformer and PyTorch.
- The run completed 1,200 optimizer steps. The best validation checkpoint was selected at step 900 with validation loss 3.6355; the final resumable checkpoint was saved at step 1,200.
- The model contains 269,952 parameters. These are real trained weights, not a pretrained third-party model.
- The checkpoint loaded on CPU and generation executed successfully.
- The private Kaggle dataset contains \`jon2-small.pt\` (3,285,607 bytes) and \`jon2-last.pt\` (3,285,488 bytes), as confirmed by verification run [42028045019](https://github.com/jonkabeel-star/jon2-ai). The training artifact records SHA-256 for \`jon2-small.pt\`: \`acbae28e4acc4dc060194df466f65a72410792f5b0fec7ff9bdd939244b9c43f\`. The last-checkpoint SHA-256 was not captured in the available evidence.
- Held-out evaluation of 40 Arabic prompts completed in run [42028581017](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42028581017). The generated answers were visibly malformed and incoherent Arabic. The report marks every human review as not reviewed and contains no human scores.
- Public chat remains disabled. Do not set \`JON2_CHAT_RELEASE_APPROVED=true\` for this checkpoint.

## Interpretation

The project has completed one genuine end-to-end training and private checkpoint-storage cycle. This proves that the training code can update model weights, save a checkpoint, reload it, execute inference, and preserve the weights in private storage.

It does **not** prove that the model understands Arabic, answers accurately, follows instructions, remembers context, or is safe for public use. The current checkpoint fails the practical conversation-quality gate.

## Next gates

1. Expand the corpus substantially with original, high-quality Arabic examples and documented ownership/permission for every source.
2. Keep held-out evaluation prompts separate from training data.
3. Audit every new source for exact duplicates, malformed UTF-8, privacy signals, and content quality before approval.
4. Increase model/tokenizer capacity only alongside a materially larger and more diverse corpus; scaling the model alone will not create knowledge.
5. Before any further training, make checkpoint outputs run-versioned so a new run cannot overwrite prior checkpoints.
6. Train a new checkpoint only after explicit approval and a fresh compatibility check; compare validation curves and generate the same held-out report.
7. Have a human review all held-out answers using \`EVALUATION_RUBRIC.md\`.
8. Keep the public chat release gate closed until the exact checkpoint passes human review and is deployed to a real backend.

## Data and rights boundary

The six exact text files currently listed in the private source-approval manifest are approved only for private experimental research training. Any new or modified source requires its own explicit approval record bound to the exact SHA-256 fingerprint and UTF-8 character count before another training run. Do not add Wikipedia-derived, scraped, private, personal, or third-party text without separately verifying the required approval.

The training text files are currently present in the public GitHub repository. The repository documentation says training corpora should remain private; do not add more private corpus material to the public repository. Moving already tracked files out of public Git history requires a separate, owner-approved migration and history-cleanup plan.

## Hardware boundary

The RTL design and its Icarus Verilog simulations are a separate engineering track. No physical FPGA board, ASIC, GPU, or local AI compute hardware has been created or programmed by these training runs. GitHub-hosted CPU runners supplied the compute for the training cycle.
