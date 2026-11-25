#!/usr/bin/env bash
set -euo pipefail

# Jon2 private GPU host preflight. Run as the dedicated, non-root Actions runner user.
# This script does not install drivers, register a runner, fetch data, or train.

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: Linux is required." >&2; exit 1
fi
arch="$(uname -m)"
if [[ "$arch" != "x86_64" ]]; then
  echo "ERROR: x86_64 is required; found $arch." >&2; exit 1
fi
if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERROR: Run as the dedicated non-root runner account, not root." >&2; exit 1
fi

: "${JON2_VOLUME_MOUNT:=/workspace}"
if [[ ! -d "$JON2_VOLUME_MOUNT" ]] || ! mountpoint -q "$JON2_VOLUME_MOUNT"; then
  echo "ERROR: $JON2_VOLUME_MOUNT is not a mounted persistent volume." >&2
  echo "Attach your provider's persistent volume and mount it there first." >&2
  exit 1
fi

command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi missing; use an NVIDIA CUDA image." >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 missing." >&2; exit 1; }
command -v df >/dev/null

nvidia-smi
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required.")
try:
    import torch
except Exception as exc:
    raise SystemExit(f"PyTorch is missing: {exc}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to PyTorch; install a matching CUDA wheel/driver.")
print("Python:", sys.version.split()[0])
print("PyTorch:", torch.__version__)
print("PyTorch CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM GiB:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))
PY

available_kb="$(df -Pk "$JON2_VOLUME_MOUNT" | awk 'NR==2 {print $4}')"
minimum_kb=$((80 * 1024 * 1024))
if [[ -z "$available_kb" || "$available_kb" -lt "$minimum_kb" ]]; then
  echo "ERROR: Need at least 80 GiB free on the persistent volume." >&2
  df -h "$JON2_VOLUME_MOUNT"
  exit 1
fi

data_dir="$JON2_VOLUME_MOUNT/jon2/data"
checkpoint_dir="$JON2_VOLUME_MOUNT/jon2/checkpoints"
mkdir -p "$data_dir" "$checkpoint_dir/candidates"
chmod 700 "$JON2_VOLUME_MOUNT/jon2" "$data_dir" "$checkpoint_dir" "$checkpoint_dir/candidates"

cat <<EOF
JON2 GPU HOST PREFLIGHT: PASS

Set these GitHub repository variables:
JON2_PRIVATE_DATA_DIR=$data_dir
JON2_PRIVATE_CHECKPOINT_DIR=$checkpoint_dir

Keep raw datasets, source_approvals.json, split files, logs, and checkpoints on this private volume.
No dataset was downloaded and no training was started.
EOF
