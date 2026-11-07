#!/bin/sh
set -u

CHECKPOINT_PATH="${JON2_CHECKPOINT:-/app/model-weights/jon2-small.pt}"
CHECKPOINT_DIR="$(dirname "$CHECKPOINT_PATH")"

if [ -s "$CHECKPOINT_PATH" ]; then
  echo "Jon2: checkpoint already exists; skipping Kaggle download."
elif [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  echo "Jon2 ERROR: KAGGLE_API_TOKEN is not present in the production runtime environment."
  echo "Jon2: API will start in health-only mode; no credential values are printed."
else
  echo "Jon2: Kaggle token variable is present (value hidden)."
  echo "Jon2: Kaggle CLI version:"
  kaggle --version || true

  TEMP_DIR="$(mktemp -d)"
  mkdir -p "$CHECKPOINT_DIR"

  echo "Jon2: checking access and downloading the private checkpoint."
  if kaggle datasets download jon2kabeel/jon2-private-model-checkpoint \
      -f jon2-small.pt -p "$TEMP_DIR" --unzip --force; then
    DOWNLOADED_FILE="$(find "$TEMP_DIR" -type f -name 'jon2-small.pt' -print -quit)"
    if [ -n "$DOWNLOADED_FILE" ] && [ -s "$DOWNLOADED_FILE" ]; then
      cp "$DOWNLOADED_FILE" "$CHECKPOINT_PATH"
      if [ -s "$CHECKPOINT_PATH" ]; then
        echo "Jon2: private checkpoint downloaded and verified."
      else
        echo "Jon2 ERROR: checkpoint copy failed."
      fi
    else
      echo "Jon2 ERROR: Kaggle command succeeded, but jon2-small.pt was not found in the extracted files."
      echo "Jon2: extracted file listing:"
      find "$TEMP_DIR" -maxdepth 4 -type f -printf '%P (%s bytes)\n' 2>/dev/null || true
    fi
  else
    echo "Jon2 ERROR: Kaggle download failed. Review the Kaggle CLI error immediately above this line."
    echo "Jon2: common causes are an invalid/revoked token or missing access to the private dataset."
  fi

  rm -rf "$TEMP_DIR"
fi

exec "$@"
