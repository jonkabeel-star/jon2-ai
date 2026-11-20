#!/bin/sh
set -eu

CHECKPOINT_PATH="${JON2_CHECKPOINT:-/app/model-weights/jon2-last.pt}"
EXPECTED_SHA256="${JON2_CHECKPOINT_SHA256:-edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2}"
export JON2_CHECKPOINT="$CHECKPOINT_PATH"
export JON2_CHECKPOINT_SHA256="$EXPECTED_SHA256"

if [ ! -s "$CHECKPOINT_PATH" ]; then
  echo "Jon2: private checkpoint is not mounted at $CHECKPOINT_PATH."
  echo "Jon2: API will start in health-only mode; chat release remains closed."
else
  ACTUAL_SHA256="$(python -c 'import hashlib,sys; h=hashlib.sha256(); f=open(sys.argv[1],"rb"); [h.update(b) for b in iter(lambda:f.read(1048576),b"")]; print(h.hexdigest())' "$CHECKPOINT_PATH")"
  if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "Jon2 ERROR: private checkpoint SHA256 mismatch."
    echo "Expected: $EXPECTED_SHA256"
    echo "Actual:   $ACTUAL_SHA256"
    exit 1
  fi
  echo "Jon2: private checkpoint SHA256 verified."
fi

exec "$@"
