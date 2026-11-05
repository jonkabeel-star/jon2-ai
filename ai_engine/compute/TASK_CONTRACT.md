# Jon2 Compute Task Contract — v0.1 (not dispatched)

## Purpose
Defines a narrow, testable contract for a future scheduler. This is metadata
validation and state-machine logic only. There is no queue endpoint, no worker
assignment, no task execution, and no remote command channel.

## Allowed task types
- `resource_probe`
- `health_check`
- `model_evaluation`

Arbitrary shell commands, scripts, executable paths, and externally-directed
URLs are rejected. Parameters must be finite JSON and remain under 16 KiB.

## Lifecycle
`queued -> assigned -> running -> succeeded|failed`
Cancellation is permitted before terminal completion. An assigned task may
return to queued when an assignment is safely released. Terminal states cannot
be reopened.

## Safety gates before dispatch can be considered
1. Worker identity and revocation tests pass.
2. HTTPS and token handling are independently reviewed.
3. Worker process isolation, resource quotas, and filesystem/network boundaries
   are implemented and tested.
4. Job payloads are signed and replay-protected.
5. Output storage, retention, and cleanup are defined.
6. Per-owner quotas, rate limits, audit records, and kill switch exist.
7. A real worker is enrolled and verified with a harmless health task.
8. CI passes on the exact release commit.

Until all gates are satisfied, `dispatch_enabled` must remain false.
