#!/bin/sh
set -u

CHECKPOINT_PATH="${JON2_CHECKPOINT:-/app/model-weights/jon2-small.pt}"
CHECKPOINT_DIR="$(dirname "$CHECKPOINT_PATH")"

# Some hosting runtimes mount /app as read-only or override image directory
# permissions. If the configured directory cannot actually accept a file,
# fall back to the writable temporary filesystem and export the effective path
# so the API loads the exact file downloaded by this entrypoint.
if [ ! -s "$CHECKPOINT_PATH" ]; then
  mkdir -p "$CHECKPOINT_DIR" 2>/dev/null || true
  WRITE_TEST=""
  if [ -d "$CHECKPOINT_DIR" ] && [ -w "$CHECKPOINT_DIR" ]; then
    WRITE_TEST="$(mktemp "$CHECKPOINT_DIR/.jon2-write-test.XXXXXX" 2>/dev/null || true)"
  fi
  if [ -z "$WRITE_TEST" ]; then
    FALLBACK_DIR="${TMPDIR:-/tmp}/jon2-model-weights"
    mkdir -p "$FALLBACK_DIR" 2>/dev/null || true
    WRITE_TEST="$(mktemp "$FALLBACK_DIR/.jon2-write-test.XXXXXX" 2>/dev/null || true)"
    if [ -n "$WRITE_TEST" ]; then
      rm -f "$WRITE_TEST"
      CHECKPOINT_PATH="$FALLBACK_DIR/jon2-small.pt"
      CHECKPOINT_DIR="$FALLBACK_DIR"
      export JON2_CHECKPOINT="$CHECKPOINT_PATH"
      echo "Jon2 warning: configured checkpoint directory is not writable; using temporary path: $CHECKPOINT_PATH"
    else
      echo "Jon2 ERROR: neither configured checkpoint directory nor temporary fallback is writable."
    fi
  else
    rm -f "$WRITE_TEST"
  fi
fi

log_safe_file() {
  # Print diagnostics while masking common Kaggle/Bearer credential formats.
  sed -E \
    -e 's/(KGAT_[A-Za-z0-9._-]+)/[REDACTED]/g' \
    -e 's/(Bearer )[A-Za-z0-9._-]+/\1[REDACTED]/g' \
    -e 's/("?(token|key|password)"?[[:space:]]*:[[:space:]]*")[^"]+(")/\1[REDACTED]\3/Ig' \
    "$1"
}

if [ -s "$CHECKPOINT_PATH" ]; then
  echo "Jon2: checkpoint already exists; skipping Kaggle download."
elif [ -z "${KAGGLE_API_TOKEN:-}" ]; then
  echo "Jon2 ERROR: KAGGLE_API_TOKEN is missing; starting in health-only mode."
else
  echo "Jon2: Kaggle token variable is present (value hidden)."
  TEMP_DIR="$(mktemp -d 2>/dev/null)"
  if [ -z "$TEMP_DIR" ] || [ ! -d "$TEMP_DIR" ]; then
    echo "Jon2 ERROR: unable to create a temporary directory for the checkpoint download."
  elif ! mkdir -p "$CHECKPOINT_DIR"; then
    echo "Jon2 ERROR: cannot create checkpoint directory: $CHECKPOINT_DIR"
  elif [ ! -w "$CHECKPOINT_DIR" ]; then
    echo "Jon2 ERROR: checkpoint directory is not writable: $CHECKPOINT_DIR"
  elif ! command -v kaggle >/dev/null 2>&1; then
    echo "Jon2 ERROR: Kaggle CLI executable is missing from PATH."
  else
    echo "Jon2: Kaggle CLI version:"
    kaggle --version 2>&1 || true

    DATASET_ID="jon2kabeel/jon2-private-model-checkpoint"
    echo "Jon2: checking private dataset access and file listing."
    kaggle datasets files "$DATASET_ID" --page-size 200 > "$TEMP_DIR/files.log" 2>&1
    FILES_STATUS=$?
    echo "Jon2: Kaggle dataset file-list exit code: $FILES_STATUS"
    if [ -s "$TEMP_DIR/files.log" ]; then
      echo "Jon2: Kaggle dataset file-list output (credentials redacted):"
      log_safe_file "$TEMP_DIR/files.log"
    fi
    if [ "$FILES_STATUS" -eq 0 ] && ! grep -Fq "jon2-small.pt" "$TEMP_DIR/files.log"; then
      echo "Jon2 ERROR: Kaggle account can access the dataset, but the exact file jon2-small.pt was not listed."
      echo "Jon2 diagnosis: check the exact filename shown in the dataset file listing above."
      DOWNLOAD_STATUS=2
    else
      echo "Jon2: requesting jon2-small.pt from private dataset."
      # Pass the dataset handle positionally for compatibility with Kaggle CLI
      # releases that differ in how the hidden -d alias is exposed.
      kaggle datasets download "$DATASET_ID" -f jon2-small.pt \
        -p "$TEMP_DIR" --unzip --force > "$TEMP_DIR/download.log" 2>&1
      DOWNLOAD_STATUS=$?
    fi
    echo "Jon2: Kaggle download exit code: $DOWNLOAD_STATUS"
    if [ -s "$TEMP_DIR/download.log" ]; then
      echo "Jon2: Kaggle diagnostic output (credentials redacted):"
      log_safe_file "$TEMP_DIR/download.log"
    fi

    if [ "$DOWNLOAD_STATUS" -eq 0 ]; then
      DOWNLOADED_FILE="$(find "$TEMP_DIR" -type f -name 'jon2-small.pt' -print -quit 2>/dev/null)"
      if [ -z "$DOWNLOADED_FILE" ] || [ ! -s "$DOWNLOADED_FILE" ]; then
        echo "Jon2 ERROR: Kaggle returned success, but jon2-small.pt is absent or empty after extraction."
        echo "Jon2 diagnostic: extracted files:"
        find "$TEMP_DIR" -maxdepth 5 -type f -print 2>/dev/null || true
      else
        SOURCE_SIZE="$(wc -c < "$DOWNLOADED_FILE" | tr -d ' ')"
        echo "Jon2: downloaded checkpoint size: $SOURCE_SIZE bytes."
        # Copy atomically on the same filesystem as the final checkpoint. The
        # Python helper reports permission, disk-space, and I/O failures.
        JON2_SOURCE_FILE="$DOWNLOADED_FILE" JON2_TARGET_FILE="$CHECKPOINT_PATH" python - <<'PY'
import os
import shutil
import sys
import tempfile

source = os.environ["JON2_SOURCE_FILE"]
target = os.environ["JON2_TARGET_FILE"]
try:
    if not os.path.isfile(source) or os.path.getsize(source) <= 0:
        raise RuntimeError("downloaded source file is missing or empty")
    target_dir = os.path.dirname(os.path.abspath(target))
    os.makedirs(target_dir, exist_ok=True)
    needed = os.path.getsize(source)
    free = shutil.disk_usage(target_dir).free
    if free < needed:
        raise OSError("insufficient disk space: need %d bytes, have %d bytes free" % (needed, free))
    fd, temporary = tempfile.mkstemp(prefix=".jon2-checkpoint-", suffix=".tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as out, open(source, "rb") as inp:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if os.path.getsize(temporary) != needed:
            raise OSError("copied file size does not match downloaded file size")
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("Jon2: checkpoint copy and size verification succeeded (%d bytes)." % os.path.getsize(target))
except Exception as exc:
    print("Jon2 ERROR: checkpoint installation failed: %s: %s" % (type(exc).__name__, exc))
    sys.exit(1)
PY
        COPY_STATUS=$?
        if [ "$COPY_STATUS" -ne 0 ]; then
          echo "Jon2 ERROR: checkpoint installation failed with exit code $COPY_STATUS."
        fi
      fi
    else
      echo "Jon2 ERROR: Kaggle download failed (exit code $DOWNLOAD_STATUS)."
      if grep -Eqi '401|unauthori[sz]ed|authentication|invalid.*token|api token' "$TEMP_DIR/download.log"; then
        echo "Jon2 diagnosis: Kaggle rejected the configured credential. Check that the token belongs to the dataset owner account and is active."
      elif grep -Eqi '403|forbidden|permission|access denied' "$TEMP_DIR/download.log"; then
        echo "Jon2 diagnosis: the Kaggle account is authenticated but does not have permission to download this private dataset."
      elif grep -Eqi '404|not found|does not exist' "$TEMP_DIR/download.log"; then
        echo "Jon2 diagnosis: the dataset id or requested filename was not found."
      elif grep -Eqi 'no space|disk quota|out of space' "$TEMP_DIR/download.log"; then
        echo "Jon2 diagnosis: the container ran out of temporary storage during download."
      else
        echo "Jon2 diagnosis: inspect the redacted Kaggle diagnostic output above for the exact cause."
      fi
    fi
  fi
  if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
  fi
fi

exec "$@"
