# Jon2 Arabic 20B — multi-GPU cluster plan

**Status: DESIGN ONLY. No GPUs have been provisioned and no training job has started.**

## Isolation of model lineages

- Original Jon2 checkpoint lineage remains the existing small-model path and is never used as an output path for the MoE model.
- New model artifacts belong under a separate private directory such as `/srv/jon2-20b/checkpoints/`.
- Original checkpoint paths must be mounted read-only in any future training container.
- Never copy, rename, overwrite, or convert the original checkpoint as part of a 20B run.
- Every run records a unique run ID, model config hash, tokenizer hash, corpus hash, and parent checkpoint (null for from-scratch).

## Candidate cluster profile (planning estimate, not a guarantee)

A serious first cluster candidate for this 20.61B-total / 3.69B-active MoE design is:

- 2 compute nodes, each with 8 NVIDIA GPUs.
- 80 GiB or more VRAM per GPU as an initial screening target.
- High-bandwidth node-local GPU interconnect and low-latency RDMA-capable networking between nodes.
- At least 512 GiB system RAM per node as an initial planning target.
- Local NVMe scratch capacity of 2 TiB or more per node, plus separate durable checkpoint/object storage.
- Compatible Linux, NVIDIA driver, CUDA, NCCL, and a pinned PyTorch build with tested composable FSDP2 and distributed checkpoint APIs.

This is not a promise that the model will fit or train efficiently. The current 18-byte/parameter Adam planning estimate is about 345 GiB for model/optimizer state before activations, communication buffers, fragmentation, checkpoint staging, and runtime overhead. Actual fit must be measured with a small-scale distributed smoke test on the exact cluster and software stack. Eight 80-GiB GPUs are only the existing code's admission floor, not proof of sufficiency.

## Required provisioning checks

1. Record cloud/provider, region, GPU SKU/count, VRAM, CPU, RAM, local NVMe, network fabric, driver, CUDA, NCCL, and PyTorch versions.
2. Confirm all ranks see the expected devices and identical model/tokenizer/corpus hashes.
3. Run NCCL collective tests across every node and measure bandwidth/latency.
4. Run a tiny MoE FSDP2 forward/backward/update test.
5. Implement and test distributed checkpoint save, restore, and interrupted-run recovery. The current single-rank checkpoint helper deliberately rejects world size greater than one.
6. Measure peak allocated/reserved memory and sustained tokens/second; increase cluster size if headroom is inadequate.
7. Enforce job quotas, private storage, encrypted transport, least-privilege credentials, and automatic shutdown.

## Launch policy

No provider resources are created by repository code. No cloud account, billing method, or paid instance is selected or changed by this plan. Provisioning requires the owner's explicit provider/account action and cost approval.

The current `moe_training.py` is not a complete distributed training launcher. Do not run `torchrun` for the 20B model until distributed checkpoint coordination, data pipeline, scheduler, gradient accumulation, held-out evaluation, and multi-node smoke tests are complete.
