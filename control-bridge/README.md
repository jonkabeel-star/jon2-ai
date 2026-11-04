# Jon2 AI Control Bridge

This folder documents the first safe bridge stage. It does not contain account credentials.

## Current scope

- GitHub is the code source of truth.
- The Kaggle workflow validates a notebook folder and submits it with the official Kaggle CLI.
- The workflow runs only when manually dispatched; it does not run continuously.
- ChatGPT can prepare and commit code to this branch through the connected GitHub integration. The available integration does not currently expose a GitHub Actions "dispatch workflow" action, so a person must start the workflow in GitHub unless that capability is added later.
- Google Colab is not yet connected for remote notebook execution. Colab's API for managing runtimes is not, by itself, a general-purpose API for editing and executing arbitrary notebook cells. Do not treat Colab as connected until an end-to-end test proves it.

## Kaggle setup (one-time, by repository owner)

1. Create a recommended Kaggle API token from the Kaggle account settings. Keep it private.
2. In the GitHub repository settings, open **Secrets and variables → Actions**.
3. Add one repository secret:
   - `KAGGLE_API_TOKEN`: paste the complete API token value from Kaggle.
4. Do not add the token to chat, source files, commits, notebook output, or screenshots. The token is not the Kaggle username and is not a legacy `kaggle.json` key.

## Notebook folder contract

Each runnable Kaggle notebook folder must contain:

- `kernel-metadata.json`
- The notebook file named by the metadata's `code_file` field (normally an `.ipynb` file).

The metadata `id` must be the Kaggle kernel identifier in `username/kernel-slug` form. The repository workflow validates the folder before uploading it.

## Run

After the secret is configured, open **Actions → Jon2 AI Kaggle Bridge → Run workflow**, choose the branch `jon2-ai-free-rebuild`, and enter the notebook folder path. Kaggle GPU availability and quotas remain controlled by Kaggle.

## Security and limits

- No secret values are stored in this repository.
- The workflow has read-only repository permissions.
- The workflow is manually started and does not provide unattended 24/7 compute.
- Kaggle execution, GPU quotas, and account eligibility remain subject to Kaggle's current policies.
- A successful upload is not proof that the notebook completed successfully; check the Kaggle notebook status and logs separately.
