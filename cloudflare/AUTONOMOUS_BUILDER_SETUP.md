# Jon2 continuous brain-builder dispatcher

## What this adds

The Cloudflare Worker receives a Cron Trigger every 30 minutes and asks GitHub Actions to run the existing read-only Jon2 Autonomous Brain Builder workflow. The workflow uses a concurrency group so repeated triggers do not start an unbounded queue of overlapping assessments.

This is an always-repeating control-plane check, not a permanently running model process. Each invocation ends after dispatching the bounded GitHub Actions job. It does not host an LLM, train weights, download models, approve data rights, merge code, or deploy the public chat model.

## Required one-time Cloudflare secret

After this change is merged and deployed, create a fine-grained GitHub Personal Access Token limited to this repository with **Actions: Read and write** permission (Metadata read is automatic). Do not grant Contents write, Administration, or workflow file write permissions.

In Cloudflare Dashboard:
1. Open Workers & Pages and select the `jon2-ai` Worker.
2. Open Settings > Variables and Secrets.
3. Add a secret named `JON2_GITHUB_TOKEN` and paste the token value.
4. Save. Never put the token in GitHub files, chat messages, or browser JavaScript.

The Worker only uses this secret to call the GitHub workflow-dispatch endpoint. It never returns or logs the token. Revoke the token if it is exposed.

## Free-tier limits and real model training

Cloudflare Cron Triggers are periodic invocations, not a continuously running machine. The current free Workers plan has a 10 ms CPU limit per Cron invocation and a 128 MB memory limit, so it cannot run PyTorch or host/train Jon2's language model. The GitHub Actions workflow is a bounded, read-only assessment. Genuine training still requires sufficient rights-cleared data, an approved training plan, and suitable compute; no training is started by this dispatcher.

The 30-minute cadence is intentionally conservative to avoid excessive GitHub Actions runs and free-tier quota exhaustion. A successful dispatch only confirms that GitHub accepted the workflow request; check the Actions run for the actual assessment result.
