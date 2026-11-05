# Jon2 Compute Control Plane — v0.3

Jon2 Compute now has read-only hardware discovery, an authenticated worker
registry, and a heartbeat-only worker client. It still has **no task execution
or dispatch capability**.

## API

- `GET /api/compute/health` — compute service status and capacity class.
- `GET /api/compute/resources` — hardware snapshot.
- `GET /api/compute/admission?min_memory_gib=2&require_gpu=false` — admission
  assessment only; it never starts or reserves a workload.
- `POST /api/compute/workers/enroll` — owner-authenticated enrollment.
- `POST /api/compute/workers/{node_id}/heartbeat` — worker-authenticated heartbeat.
- `GET /api/compute/workers` — owner-only registry listing.
- `DELETE /api/compute/workers/{node_id}` — owner-only revocation.

## Worker client

See [WORKER_AGENT.md](WORKER_AGENT.md). It reports resources measured by the
local process over HTTPS. It cannot enroll itself, receive jobs, or execute
remote code. Owner enrollment returns a worker token once; only its hash is
stored by the registry.

## Task contract

See [TASK_CONTRACT.md](TASK_CONTRACT.md). The allowlist and lifecycle state
machine are validation-only foundations. There is no queue endpoint, scheduler,
worker assignment, artifact transport, or executor. `dispatch_enabled`
remains false.

## Tests

The container CI runs:
- `compute.test_resource_probe`
- `compute.test_worker_registry`
- `compute.test_worker_agent`
- `compute.test_worker_routes`
- `compute.test_task_contract`

## Security and honest limits

- Serve remote API traffic over HTTPS. Never place owner/worker tokens in Git,
  frontend code, browser storage, issue text, or logs.
- Configure `JON2_COMPUTE_OWNER_TOKEN` (32+ random characters) and a persistent
  `JON2_COMPUTE_DB_PATH` on the API host.
- Registry metadata is self-reported by an authenticated worker; it is not
  independently attested or benchmarked.
- Add reverse-proxy rate limits before exposing enrollment/heartbeat publicly.
- No hardware is provisioned, no cloud credits are created, and no worker is
  currently claimed as online merely because this code exists.
- This control plane does not alter Jon2 model weights, training data, or the
  separate chat release approval gate.

## Before dispatch can be enabled

Implement and independently test process/container isolation, resource quotas,
signed and replay-protected task envelopes, durable queue semantics, artifact
retention/cleanup, per-owner quotas, audit records, and a kill switch. Then
verify an end-to-end harmless task on a real enrolled worker. Until then,
remote execution stays disabled.
