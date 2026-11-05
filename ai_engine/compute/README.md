# Jon2 Compute Control Plane — v0.1

This is the first real, read-only hardware discovery layer for Jon2. It reports
CPU affinity, measurable memory, and CUDA/Apple MPS devices visible to the
running Python process.

## API

- `GET /api/compute/health` — compute service status and capacity class.
- `GET /api/compute/resources` — hardware snapshot.
- `GET /api/compute/admission?min_memory_gib=2&require_gpu=false` — checks
  whether the current process appears to meet a minimum resource requirement.

Admission is an assessment only: it does not start, queue, reserve, or execute
a workload. A missing CUDA GPU is not silently treated as GPU capacity.

## Run tests

From the repository root:

```bash
python -m unittest ai_engine.compute.test_resource_probe -v
```

## Honest limits

- No hardware is provisioned by this code.
- No remote workers or paid cloud resources are created.
- Container memory limits may differ from host memory.
- CUDA is reported only when PyTorch can see it; Apple MPS is reported
  separately and is not classified as CUDA.
- This layer does not change Jon2's model weights, training corpus, or release
  approval gate.

## Next engineering stage

Add an authenticated worker registry, signed worker heartbeats, durable job
queue, artifact storage, and per-worker capacity reservations. Those features
must not be exposed as operational until backed by real worker processes and
end-to-end tests.
