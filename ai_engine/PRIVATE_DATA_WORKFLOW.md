# Private training data: storage and approval workflow

## Purpose and current boundary

The public repository is for source code, tests, and generic templates only. Keep training corpora, evaluation prompts, exact-file approval manifests, run logs, and checkpoints in private storage outside every repository checkout. A `.gitignore` rule is only a guard against future accidental additions: it does not remove a file already tracked or erase prior public Git history.

The repository currently contains tracked files under `ai_engine/training_data/`, including Arabic text, JSONL dialogue, and `source_approvals.json`. Those files are publicly exposed in the current repository and may also remain available in Git history. This workflow does not delete, move, or change those files and does not remove historical exposure. Do not copy their contents, approval records, or fingerprints into new public documentation or commits.

No existing corpus is approved by this document. Dataset/rights review and owner approval remain required for every exact file and intended use.

## Private storage layout

Choose one owner-controlled private location, such as an encrypted local volume or a private Google Drive folder with access limited to explicitly authorized reviewers. Configure the Drive desktop sync folder outside the repository checkout; never use a shared/public link. Confirm provider account security, sharing permissions, retention, and backup policy before use.

Suggested layout (names are examples, not repository paths):

```text
<private-root>/jon2/
  data/                 # reviewed candidate files only
  approvals/            # source_approvals.json; private and access-controlled
  evaluation/           # held-out prompts and results, separate from training
  checkpoints/          # model and optimizer state; never in the public checkout
  logs/                  # private run/preflight records
```

Keep the approval manifest in the private approvals directory, not in the repository's `ai_engine/training_data/`. Treat filenames, rights evidence, approval records, fingerprints, logs, evaluation content, and checkpoints as private metadata or assets; do not paste them into issues, pull requests, CI logs, or public reports.

## Exact-file approval and local validation

The existing `ai_engine/source_approval.py` gate validates selected `.txt` files by default and `.jsonl` only when explicitly enabled. It requires a one-to-one exact relative-path approval with a matching SHA-256, character count, approval status, reviewer, review date, rights basis, and intended use. Missing, changed, unmatched, malformed, or unapproved files fail closed. JSONL additionally requires valid user and assistant messages.

For each candidate, the owner/reviewer should:

1. Place it in the private data directory; do not stage it in the public checkout.
2. Review provenance, rights/permission for the intended training use, privacy, quality, and duplicates manually. A fingerprint proves byte identity only; it does not establish rights or consent.
3. Create/update the exact-file approval record locally in the private approvals directory only after review. Do not use the tracked manifest in the public checkout as an approval source.
4. From a clean source-code checkout, run the gate against the external data directory and external manifest. Example (replace the placeholders locally; do not commit a filled-in command or output):

   ```bash
   PYTHONPATH=ai_engine python -c \
     'from pathlib import Path; from source_approval import validate_source_approvals; validate_source_approvals(Path("<PRIVATE_DATA_DIR>"), Path("<PRIVATE_APPROVALS_DIR>/source_approvals.json"))'
   ```

   For explicitly reviewed JSONL, pass `include_jsonl=True` in that local call. Do not enable it as a shortcut around exact-file review.
5. Re-run validation after any file or approval change. A changed file must be reviewed and approved again; never copy fingerprints from a previous manifest.
6. Keep evaluation assets separate. Never include a held-out evaluation file in the training data directory.
7. Store any future checkpoint and logs on private storage separate from both the public checkout and the data directory. Do not start a run until the owner separately authorizes it and all readiness, compute, and evaluation gates pass.

The gate is a training-input check, not a rights/privacy review. Do not run training or download data as part of this foundation task.

## Repository and CI safeguards

- Keep future private data, approval manifests, checkpoints, and evaluation assets outside the checkout. Ignore patterns are defense in depth, not a substitute for this boundary.
- Never use `git add -f` for private assets. Before committing, inspect staged paths and ensure no private text, manifests, hashes, credentials, evaluation prompts, or checkpoints are staged.
- Public CI may run only synthetic fixtures and source-code tests. It must not access the private Drive/local storage or print private inputs or fingerprints.
- Pages and public runtime assets remain in the public repository; no private data is needed to build or deploy them.
- If a private asset is accidentally staged or pushed, stop and notify the owner. Do not attempt cleanup by deleting files or rewriting history under this workflow; historical exposure requires a separate owner decision and response plan.

## Owner decisions before future use

- Select and secure the private storage provider/location and define authorized access, backup, and retention.
- Decide whether any currently tracked corpus or approval material may be used in a future private workflow; this document does not approve it.
- Review exact-source provenance, rights, privacy, quality, and intended use before creating any private approval record.
- Separately authorize any training run and select a safe new output/checkpoint location without altering the original weights.
- Decide whether to pursue a separate incident/retention response for historical public Git exposure. No history cleanup or visibility change is performed here.
