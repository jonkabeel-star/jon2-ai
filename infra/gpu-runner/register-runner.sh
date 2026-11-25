#!/usr/bin/env bash
set -euo pipefail
set +x

# Register a dedicated, non-root self-hosted runner for this private repository.
# RUNNER_TOKEN is short-lived; never pass it as a command-line argument or print it.
: "${GITHUB_REPOSITORY:?Set GITHUB_REPOSITORY=owner/repo}"
: "${RUNNER_TOKEN:?Export the short-lived token from GitHub Settings → Actions → Runners}"
: "${RUNNER_NAME:=jon2-gpu-$(hostname -s)}"
: "${RUNNER_DIR:=$HOME/actions-runner}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERROR: Do not configure the Actions runner as root." >&2; exit 1
fi
if [[ "$GITHUB_REPOSITORY" != "jonkabeel-star/"* ]]; then
  echo "ERROR: Refusing to register outside the Jon2 repository owner." >&2; exit 1
fi
for cmd in curl jq tar sha256sum sudo; do
  command -v "$cmd" >/dev/null || { echo "ERROR: Missing command: $cmd" >&2; exit 1; }
done
mkdir -p "$RUNNER_DIR"
if [[ -f "$RUNNER_DIR/.runner" ]]; then
  echo "ERROR: A runner is already configured in $RUNNER_DIR." >&2; exit 1
fi

release="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest)"
asset="$(printf '%s' "$release" | jq -r '.assets[] | select(.name | test("^actions-runner-linux-x64-[0-9.]+\\.tar\\.gz$")) | .browser_download_url' | head -n1)"
digest="$(printf '%s' "$release" | jq -r '.assets[] | select(.name | test("^actions-runner-linux-x64-[0-9.]+\\.tar\\.gz$")) | .digest' | head -n1)"
if [[ -z "$asset" || "$digest" != sha256:* ]]; then
  echo "ERROR: GitHub release did not provide a runner archive with a SHA-256 digest. Refusing unverified download." >&2
  exit 1
fi

archive="$RUNNER_DIR/runner-linux-x64.tar.gz"
curl -fL "$asset" -o "$archive"
printf '%s  %s\n' "${digest#sha256:}" "$archive" | sha256sum -c -
tar -xzf "$archive" -C "$RUNNER_DIR"
rm -f "$archive"

(
  cd "$RUNNER_DIR"
  ./config.sh \
    --url "https://github.com/$GITHUB_REPOSITORY" \
    --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" \
    --labels "jon2-gpu" \
    --work "_work" \
    --unattended \
    --replace
)
unset RUNNER_TOKEN
sudo "$RUNNER_DIR/svc.sh" install "$USER"
sudo "$RUNNER_DIR/svc.sh" start
echo "Runner configured. Verify it appears Idle/Online with labels self-hosted, linux, x64, jon2-gpu."
