# Jon2 Developer Agent

The Developer Agent is a bounded, scheduled coding assistant for the Jon2 AI repository. It uses Cloudflare Workers AI to propose at most one small engineering improvement per run.

## One-time setup

In the private GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `JON2_CF_ACCOUNT_ID`: the Cloudflare account ID that owns the Workers AI service.
- `JON2_CF_API_TOKEN`: a Cloudflare API token restricted to this account with **Workers AI: Read** permission. Do not use the global API key. Never paste the token into source files, issues, or chat.

The token is read only by the GitHub Actions runner and is not printed in logs. GitHub Actions also needs the repository's normal `GITHUB_TOKEN` permissions to create a branch and pull request; the workflow declares only Contents and Pull Requests write access.

## Run

1. Open the repository's **Actions** tab.
2. Select **Jon2 Developer Agent**.
3. Select **Run workflow** on `main`.
4. Inspect the run and its `jon2-developer-agent-report` artifact.
5. Review the generated pull request and its verification results. Merge only after human review.

The workflow also runs once daily at 02:23 UTC.

## Safety and current limits

- Reads a bounded selection of tracked Python/JavaScript/TypeScript source files from `ai_engine/` and read-only test context in `tests/`.
- May replace at most two existing Python source files under `ai_engine/` per run; test files are read-only context. No file creation, deletion, rename, or arbitrary shell execution.
- Cannot edit CI workflows, Cloudflare deployment code, CORS, authentication, secrets, model weights, checkpoints, training data, evaluation data, or licensing approvals.
- Runs the repository's existing fixed verification suite before opening a pull request.
- Never pushes to `main`, merges a pull request, deploys a release, or changes Cloudflare settings.
- If the model proposes no safe change, no pull request is opened.
- A daily run is scheduled automation, not a continuously running autonomous service. Workers AI quota and availability apply; a failed or quota-limited run does not change the repository.
- Model-generated code can still be wrong. Passing tests is necessary but not proof of correctness; a human must review every pull request.

This is version 1: a constrained code-improvement agent, not an unrestricted self-modifying system.
