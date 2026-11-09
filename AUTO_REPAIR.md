# Jon2 Auto Repair

Jon2 Auto Repair is a conservative maintenance workflow for the repository.

## What it does

1. Runs on pushes to `main`, every hour (at minute 17 UTC), when an allowlisted trusted `main` workflow fails, or when manually started from GitHub Actions.
2. Reads failed logs only from allowlisted workflows that ran on the trusted `main` branch.
3. Recognizes exact missing-name `NameError` signatures and can insert one import from a small standard-library allowlist into a traceback file under `ai_engine/`; it also normalizes Python trailing whitespace.
4. Runs Python compilation, the repository's three unittest discovery suites, training-data audits, the dataset inventory, and the non-training 30M readiness preflight.
5. Writes a JSON diagnostic report and uploads it as a 14-day workflow artifact. Raw failure logs are not uploaded.
6. Opens or updates a review-only pull request only if every configured check passes and there are safe source changes to propose. It never commits repairs directly to `main` and never merges its own pull request.

## Safety boundaries

- The workflow checks out trusted `main`; it does not run with write permissions on pull requests from forks.
- It uses a fixed command allowlist. It never executes code or shell commands copied from error logs.
- The only code-generation rule currently enabled is a minimal import insertion for an exact missing-name `NameError`, limited to approved standard-library symbols and files under `ai_engine/`.
- It does not rewrite application logic, alter model weights, delete checkpoints, change training data, change secrets, or deploy.
- It never pushes repairs directly to `main`. Any proposed source change is isolated in a bot pull request and requires human review before merge.
- The hourly schedule is periodic monitoring, not a continuously running 24/7 process. Failed trusted workflows trigger an additional run shortly after completion.
- A failed test blocks the pull request. The report remains available as a workflow artifact for diagnosis.
- A clean run does not prove that Jon2's language quality is good; model quality still requires held-out evaluation and human review.

## Run it manually

1. Open the repository's **Actions** tab.
2. Select **Jon2 Auto Repair**.
3. Choose **Run workflow** on the `main` branch.
4. Open the run and inspect its **jon2-auto-repair-report** artifact.
5. Review any generated pull request before merging.

This is a bounded rule-based repair generator, not an unrestricted autonomous programmer. It monitors hourly and reacts to failed trusted workflows; it is not a permanently running server. It can generate and test a narrow code patch when a recognized failure is found. It does not claim to repair arbitrary semantic bugs; broader AI-generated changes must be isolated, tested, and reviewed before they are trusted.
