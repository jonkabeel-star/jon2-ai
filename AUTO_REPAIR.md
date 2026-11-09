# Jon2 Auto Repair

Jon2 Auto Repair is a conservative maintenance workflow for the repository.

## What it does

1. Runs on pushes to `main` that affect Python source, every day at 03:23 UTC, or when manually started from GitHub Actions.
2. Removes only trailing spaces/tabs and ensures a final newline in Python files under `ai_engine/` and `tests/`.
3. Runs Python compilation, the repository's three unittest discovery suites, training-data audits, the dataset inventory, and the non-training 30M readiness preflight.
4. Writes a JSON diagnostic report and uploads it as a 14-day workflow artifact.
5. Opens or updates a pull request only if every configured check passes and there are safe source changes to propose.

## Safety boundaries

- The workflow checks out trusted `main`; it does not run with write permissions on pull requests from forks.
- It uses a fixed command allowlist. It never executes code or shell commands copied from error logs.
- It does not rewrite application logic, alter model weights, delete checkpoints, change training data, change secrets, or deploy.
- It never pushes directly to `main`. Any proposed source change is isolated in a bot pull request and requires human review before merge.
- A failed test blocks the pull request. The report remains available as a workflow artifact for diagnosis.
- A clean run does not prove that Jon2's language quality is good; model quality still requires held-out evaluation and human review.

## Run it manually

1. Open the repository's **Actions** tab.
2. Select **Jon2 Auto Repair**.
3. Choose **Run workflow** on the `main` branch.
4. Open the run and inspect its **jon2-auto-repair-report** artifact.
5. Review any generated pull request before merging.

This is the first safe automation layer. It can automatically correct formatting-only defects and diagnose failures through the existing tests. It does not claim to repair arbitrary semantic bugs. More powerful AI-generated code changes must be isolated, tested, and reviewed before they are trusted.
