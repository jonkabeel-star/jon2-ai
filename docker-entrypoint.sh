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
  TEMP_DIR="$(mktemp -d)"
  mkdir -p "$CHECKPOINT_DIR"

  if command -v kaggle >/dev/null 2>&1; then
    echo "Jon2: Kaggle CLI executable found."
    kaggle --version > "$TEMP_DIR/version.log" 2>&1
    VERSION_STATUS=$?
    echo "Jon2: Kaggle CLI version command exit code: $VERSION_STATUS"
    sed -E 's/(KGAT_[A-Za-z0-9._-]+)/[REDACTED]/g; s/(Bearer )[A-Za-z0-9._-]+/\1[REDACTED]/g' "$TEMP_DIR/version.log"
  else
    echo "Jon2 ERROR: Kaggle CLI executable is missing from the container PATH."
  fi

  echo "Jon2: checking access and downloading the private checkpoint."
  kaggle datasets download jon2kabeel/jon2-private-model-checkpoint \
    -f jon2-small.pt -p "$TEMP_DIR" --unzip --force > "$TEMP_DIR/download.log" 2>&1
  DOWNLOAD_STATUS=$?
  echo "Jon2: Kaggle download command exit code: $DOWNLOAD_STATUS"
  echo "Jon2: Kaggle download diagnostic output (credentials redacted):"
  sed -E 's/(KGAT_[A-Za-z0-9._-]+)/[REDACTED]/g; s/(Bearer )[A-Za-z0-9._-]+/\1[REDACTED]/g' "$TEMP_DIR/download.log"

  if [ "$DOWNLOAD_STATUS" -eq 0 ]; then
    DOWNLOADED_FILE="$(find "$TEMP_DIR" -type f -name 'jon2-small.pt' -print -quit)"
    if [ -n "$DOWNLOADED_FILE" ] && [ -s "$DOWNLOADED_FILE" ]; then
      SOURCE_SIZE="$(wc -c < "$DOWNLOADED_FILE" | tr -d ' ')"
      echo "Jon2 diagnostic: downloaded checkpoint size is ${SOURCE_SIZE} bytes."
      if cp "$DOWNLOADED_FILE" "$CHECKPOINT_PATH" 2> "$TEMP_DIR/copy-error.log"; then
        if [ -s "$CHECKPOINT_PATH" ]; then
          TARGET_SIZE="$(wc -c < "$CHECKPOINT_PATH" | tr -d ' ')"
          echo "Jon2: private checkpoint downloaded and verified (${TARGET_SIZE} bytes)."
        else
          echo "Jon2 ERROR: copy command succeeded but target file is empty or missing."
        fi
      else
        COPY_STATUS=$?
        echo "Jon2 ERROR: checkpoint copy command failed with exit code $COPY_STATUS."
        sed -E 's/(KGAT_[A-Za-z0-9._-]+)/[REDACTED]/g; s/(Bearer )[A-Za-z0-9._-]+/\\1[REDACTED]/g' "$TEMP_DIR/copy-error.log"
      fi
    else
      echo "Jon2 ERROR: Kaggle command succeeded, but jon2-small.pt was not found in the extracted files."
      find "$TEMP_DIR" -maxdepth 4 -type f -printf '%P (%s bytes)\n' 2>/dev/null || true
    fi
  else
    echo "Jon2 ERROR: private checkpoint download failed; API will start without chat."
  fi

  rm -rf "$TEMP_DIR"
fi

exec "$@"
