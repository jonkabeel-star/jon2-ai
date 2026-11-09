# Jon2 local autonomous engineer

This branch adds real-model Arabic benchmarking, an optional local semantic judge, an open-weight coding model, Docker-isolated patch tests, and a fail-closed training gate.

## Local model runtime

Install Ollama on a computer or GPU host, then pull the open-weight models:

```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5-coder:1.5b
```

Start Ollama at `http://127.0.0.1:11434`. Set optional `OLLAMA_HOST`, `JON2_JUDGE_MODEL`, `JON2_CODER_MODEL`, and `JON2_MODEL_NAME`. These are local model calls; no paid inference API is used. The host needs storage and RAM/compute to load models.

## Run the real Jon2 benchmark

Install project requirements in a suitable Python environment:

```bash
python ai_engine/run_model_benchmark.py --semantic
```

The runner loads the real language engine, generates actual answers for each reviewed Egyptian Arabic/MSA case, saves answer JSONL, and asks the local semantic judge to compare against reviewed reference answers. A judge pass is not proof of truth; human review remains mandatory.

## Generate and test a code proposal

Install Docker and ensure its daemon is running:

```bash
python ai_engine/coding_agent.py --task "Improve error handling in Jon2 language engine without changing its public API"
```

The coding model has no Git credentials. It may propose only Python files under `ai_engine/`; rights gates, training, checkpoints, datasets, CI, deployment, dependencies, and credentials are protected. The patch is applied only to a disposable copy and tests run in a no-network, read-only-root Docker container. The patch is saved for human review. No commit, branch, PR, merge, or deployment is performed automatically.

## Training gate

Dry-run is the default:

```bash
python ai_engine/training_gate.py --profile arabic_30m
```

Training can start only when exact-file source rights approvals pass, fresh token preflight meets the hard minimum of 10 tokens per parameter, train/validation splits are adequate, CUDA is available, and the checkpoint destination is new. Only then may the owner explicitly add `--execute`. The prior measured corpus was far below the token/parameter requirement, so the current expected result is BLOCKED. Do not duplicate data or lower the threshold.

## Important limits

- This cannot run Ollama or Docker on an iPhone alone; it needs a computer or suitably provisioned host.
- GitHub hosted CPU runners do not provide a persistent local Ollama model or a training GPU. GitHub Actions remains a test/report workflow, while real inference and sandbox execution run on a configured host.
- Nothing automatically merges code, deploys, approves rights, or releases a model.
