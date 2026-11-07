#!/bin/sh
set -u

CHECKPOINT_PATH="${JON2_CHECKPOINT:-/app/ai_engine/checkpoints/jon2-small.pt}"
if [ ! -s "$CHECKPOINT_PATH" ] && [ -n "${KAGGLE_API_TOKEN:-}" ]; then
  echo "Jon2: retrieving the private original checkpoint from Kaggle."
  CHECKPOINT_DIR="$(dirname "$CHECKPOINT_PATH")"
  TEMP_DIR="$(mktemp -d)"
  mkdir -p "$CHECKPOINT_DIR"
  if kaggle datasets download jon2kabeel/jon2-private-model-checkpoint \
      -f jon2-small.pt -p "$TEMP_DIR" --unzip; then
    if [ -s "$TEMP_DIR/jon2-small.pt" ]; then
      cp "$TEMP_DIR/jon2-small.pt" "$CHECKPOINT_PATH"
      echo "Jon2: private checkpoint downloaded and verified."
    else
      echo "Jon2 warning: Kaggle download completed but checkpoint file is missing."
    fi
  else
    echo "Jon2 warning: private checkpoint download failed; API will start without chat."
  fi
  rm -rf "$TEMP_DIR"
elif [ ! -s "$CHECKPOINT_PATH" ]; then
  echo "Jon2 warning: no checkpoint file and no Kaggle token; API will start health-only."
fi

exec "$@"
