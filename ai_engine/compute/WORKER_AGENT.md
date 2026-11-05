# Jon2 Compute Worker Agent — v0.1

## Purpose
A small Python client for a real Linux, Windows, macOS, or hosted notebook worker.
It measures resources visible to the process and sends authenticated heartbeats
to the Jon2 API. It is **heartbeat-only**: it does not enroll, receive jobs,
download models, execute remote code, or provision hardware.

## Owner setup
1. Configure `JON2_COMPUTE_OWNER_TOKEN` (32+ random characters) on the Jon2 API host.
2. Serve the API over HTTPS and configure a persistent `JON2_COMPUTE_DB_PATH`.
3. The owner calls `POST /api/compute/workers/enroll` with an Authorization Bearer
   owner token and the node's measured metadata.
4. Save the returned per-worker token securely. It is shown once. Never put it in Git,
   a web page, browser storage, or logs.

## Worker setup
Install the Jon2 repository package/dependencies on a supported Python machine,
then set these environment variables in that machine's private environment:
- `JON2_COMPUTE_API_URL`: HTTPS API base URL (HTTP is allowed only for localhost).
- `JON2_WORKER_ID`: the node ID enrolled by the owner.
- `JON2_WORKER_TOKEN`: the one-time worker token.
- Optional `JON2_HEARTBEAT_INTERVAL_SECONDS`: defaults to 30; minimum 10.

Run from the repository root:
```bash
python -m compute.worker_agent
```
When running from a checkout where `ai_engine` is the package root:
```bash
PYTHONPATH=ai_engine python -m compute.worker_agent
```

## Security and limits
- Remote connections require HTTPS; only localhost may use HTTP.
- The worker token is sent only as an Authorization header.
- The client never logs the token and never embeds it in the URL.
- The API owner must enroll/revoke workers; this client cannot self-enroll.
- Reported capacity is measured locally but remains self-reported, not attested.
- No task dispatch or remote execution is implemented. The registry continues to
  return `dispatch_enabled: false`.
- The user's iPhone is not treated as a worker. iOS background execution and
  package/runtime restrictions make this agent unsuitable as an always-on iPhone node.
