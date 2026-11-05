# Jon2 Compute Core

Jon2 Compute Core is a Python software CPU simulator and local storage layer for the Jon2 AI project.

## Important boundary
This is a **virtual CPU**, not a physical processor. It executes a small, documented instruction set using the host machine's real CPU and RAM. It does not create additional hardware resources or free cloud capacity.

## First milestone
- 8 general-purpose 32-bit registers
- 64 KiB bounded virtual RAM
- Fetch/decode/execute loop
- Arithmetic, memory, conditional jump, output, and halt instructions
- SQLite persistent key/value storage
- No external dependencies

## Safety
- Programs are Python data structures, not arbitrary Python code.
- Memory addresses and instruction operands are validated.
- Execution has a configurable instruction limit.
- Storage stays in the configured local SQLite database.
- No network access, external model download, training, or data-source approval is performed.

## Run tests
From the repository root:

```bash
python -m unittest discover -s compute_core/tests -v
```

## Status
Prototype milestone 1. Not connected to the public Jon2 chat API and does not change its release approval setting.
