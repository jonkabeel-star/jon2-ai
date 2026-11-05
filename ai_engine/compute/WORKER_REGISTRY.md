# Jon2 Compute Worker Registry — v0.2

## Implemented
- Owner-authenticated worker enrollment (minimum 32-character owner token).
- Random per-worker bearer credential returned once at enrollment.
- Only SHA-256 credential hashes are stored in SQLite.
- Authenticated heartbeats update measured worker capacity.
- Owner-only worker listing and revocation.
- Workers become stale after 120 seconds without a heartbeat.
- SQLite WAL mode and a configurable database path.

## API
- `POST /api/compute/workers/enroll` — owner bearer token required.
- `POST /api/compute/workers/{node_id}/heartbeat` — worker bearer token required.
- `GET /api/compute/workers` — owner bearer token required.
- `DELETE /api/compute/workers/{node_id}` — owner bearer token required.

Set these environment variables on the API host:
- `JON2_COMPUTE_OWNER_TOKEN`: random secret with at least 32 characters.
- `JON2_COMPUTE_DB_PATH`: persistent writable path, e.g.
  `/var/lib/jon2/compute/workers.sqlite3`.

## Security and operational limits
- Always serve this API over HTTPS. Never put owner or worker tokens in Git,
  frontend JavaScript, browser storage, issue text, or logs.
- A worker token is shown only once. Re-enroll a node to rotate its token.
- SQLite data survives process restarts only if the host path is on persistent
  storage. Ephemeral container disks are not durable.
- Worker capacity is self-reported by the authenticated worker; it is not
  independently benchmarked or attested.
- Worker registration does not enable task dispatch. `dispatch_enabled`
  remains false until a separately tested scheduler and execution sandbox exist.
- No remote workers, GPU instances, cloud credits, or paid services are created
  by this code.
