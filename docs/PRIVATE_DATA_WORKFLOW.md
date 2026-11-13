# Jon2 private-data workflow (owner-safe)

## Purpose

This document defines the operating boundary for future Jon2 experiments. It does not remove previously committed files, approve any dataset, authorize training, or change model weights.

**Default rule: the public repository contains code and non-sensitive documentation only.** Private corpora, approval manifests, checkpoints, exported model bundles, and training reports containing private text must live outside the repository checkout.

## Important historical limitation

The repository has previously contained corpus and approval-related files in public Git history. Adding ignore rules, deleting a file in a later commit, or moving a file out of the current working tree does not erase earlier public commits, forks, caches, or copies. This workflow prevents new exposure; it does not claim to remediate historical exposure.

Do not rewrite Git history, change repository visibility, delete old corpus files, or attempt a cleanup migration as part of routine training setup. Any historical remediation requires a separate owner decision and impact review.

## Suggested private storage layout

Create this structure in a private Google Drive folder or encrypted local storage. Do not create it inside the cloned repository.

```text
Jon2Private/
  data/
    approved/
    pending-review/
    quarantine/
  approvals/
    source_approvals.json
  checkpoints/
    baseline-readonly/
    experiments/
  reports/
```

Keep the folder private and restrict sharing to people who are authorized to access the material. Do not place credentials, access tokens, or private data in notebooks committed to GitHub.

## Google Colab operating pattern

1. Mount the owner's Google Drive in Colab using the normal Google authorization flow.
2. Clone the public Jon2 repository into a separate runtime directory such as `/content/jon2-ai`.
3. Set the private root to a Drive path outside that checkout, for example:

   ```python
   from pathlib import Path
   import os

   REPO_ROOT = Path("/content/jon2-ai").resolve()
   PRIVATE_ROOT = Path("/content/drive/MyDrive/Jon2Private").resolve()

   if PRIVATE_ROOT == REPO_ROOT or REPO_ROOT in PRIVATE_ROOT.parents:
       raise RuntimeError("Private data must not be stored inside the repository")
   if PRIVATE_ROOT in REPO_ROOT.parents:
       raise RuntimeError("Keep the private root separate from the repository")

   os.environ["JON2_PRIVATE_ROOT"] = str(PRIVATE_ROOT)
   ```

4. Confirm that the private root is outside the repository before running any inventory, validation, or training command.
5. Do not copy private files into the checkout for convenience. If an existing tool only accepts an in-repository path, stop and adapt the tool in a separately reviewed code change rather than copying the data.
6. Store checkpoints and reports under the private root. Never upload them to a public branch, issue, pull request, release, or workflow artifact.

The example only establishes path separation. It is not a training command and does not validate dataset rights.

## Approval manifest contract

Maintain the authoritative approval manifest only in private storage. Each approved file must have a record bound to its exact bytes, including:

- normalized relative path within the private data root;
- SHA-256 digest;
- byte length and, where relevant, decoded character count;
- explicit review status;
- reviewer identity and review date;
- source/provenance and documented rights basis;
- intended use and any limitations.

Approval is file-specific and use-specific. A changed file, renamed file, new file, missing field, ambiguous rights basis, or mismatch must fail closed and require a new human review. A hash proves file identity, not ownership, permission, accuracy, or suitability.

Do not infer rights from a filename, a previous approval, public availability, or a dataset's wrapper package. Do not automatically approve the existing repository corpus or dialogue drafts. Keep held-out evaluation prompts separate from training data.

## Before any future training run

Training remains blocked until all of the following are true:

- the owner has explicitly approved the particular source and intended use;
- provenance and license/permission evidence has been reviewed;
- the private manifest validates exact file hashes and counts;
- the training process reads only from the private root;
- held-out evaluation data is isolated from training;
- the run writes checkpoints and reports only to private storage;
- the baseline checkpoint is preserved read-only and any experiment writes to a new, uniquely named location;
- the owner has explicitly authorized that specific training run.

A passing software test or manifest check is not legal clearance and is not evidence that model quality improved.

## Safe GitHub contribution policy

Before opening a PR, inspect its complete diff and verify that it contains no:

- corpus text, dialogue examples, or private evaluation prompts;
- private approval manifest or per-file hashes;
- checkpoints, model weights, exported bundles, or training outputs;
- credentials, tokens, or private Drive paths that reveal sensitive information.

A generic schema or synthetic test fixture may be committed only if it contains no copied private content and cannot be mistaken for a real approval. Keep tests deterministic and offline.

## Current status

- Historical public exposure: documented; not removed by this workflow.
- Existing data approvals: not revalidated by this document.
- Training: not authorized or started.
- Original checkpoints and weights: must remain unchanged.
- Private Drive workflow: proposed operating procedure; the owner must create and secure the private folder before using it.
