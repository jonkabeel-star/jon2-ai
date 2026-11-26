#!/bin/sh
set -eu
# Model weights are not downloaded from third-party services at startup.
# Mount a verified project-owned checkpoint explicitly before enabling inference.
exec "$@"
