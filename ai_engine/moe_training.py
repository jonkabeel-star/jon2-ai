"""Training primitives and hard admission gates for Jon2 MoE."""
from __future__ import annotations
import hashlib, math, os, random, tempfile
from pathlib import Path
import torch
import torch.nn.functional as F

def validate_corpus_scale(token_count: int, parameter_count: int, minimum_ratio: float = 10.0) -> float:
    if type(token_count) is not int or token_count <= 0 or type(parameter_count) is not int or parameter_count <= 0:
        raise ValueError("Token and parameter counts must be positive integers.")
    if isinstance(minimum_ratio, bool) or not isinstance(minimum_ratio, (int, float)) or not math.isfinite(minimum_ratio) or minimum_ratio <= 0:
        raise ValueError("minimum_ratio must be positive.")
    ratio = token_count / parameter_count
    if ratio < minimum_ratio:
        raise ValueError(f"Insufficient approved corpus scale: {ratio:.6g} tokens/parameter; minimum is {minimum_ratio:g}. Add rights-approved data; never duplicate text.")
    return ratio

def validate_20b_training_hardware(min_gpu_count: int = 8, min_gpu_memory_gib: float = 80.0) -> dict:
    """Inventory only; never allocates tensors or provisions hardware."""
    if type(min_gpu_count) is not int or min_gpu_count < 1 or not isinstance(min_gpu_memory_gib, (int, float)) or isinstance(min_gpu_memory_gib, bool) or not math.isfinite(min_gpu_memory_gib) or min_gpu_memory_gib <= 0:
        raise ValueError("GPU count and memory requirements must be positive finite values.")
    if not torch.cuda.is_available():
        raise RuntimeError("20B training blocked: no CUDA GPUs are visible.")
    count = torch.cuda.device_count()
    if count < min_gpu_count:
        raise RuntimeError(f"20B training blocked: {count} CUDA GPU(s) visible; at least {min_gpu_count} are required.")
    devices = []
    for index in range(count):
        props = torch.cuda.get_device_properties(index)
        memory_gib = props.total_memory / (1024 ** 3)
        devices.append({"index": index, "name": props.name, "memory_gib": round(memory_gib, 2)})
        if memory_gib < min_gpu_memory_gib:
            raise RuntimeError(f"20B training blocked: GPU {index} has {memory_gib:.2f} GiB; minimum is {min_gpu_memory_gib:.2f} GiB.")
    return {"cuda_device_count": count, "devices": devices, "admitted": True}

def wrap_model_fsdp2(model: torch.nn.Module, device: torch.device) -> torch.nn.Module:
    """Apply composable FSDP2 bottom-up to experts, blocks, then root."""
    if not torch.distributed.is_available() or not torch.distributed.is_initialized():
        raise RuntimeError("FSDP2 requires an initialized torch.distributed process group.")
    if device.type != "cuda":
        raise RuntimeError("FSDP2 Jon2 training currently requires CUDA devices.")
    try:
        from torch.distributed._composable.fsdp import fully_shard, MixedPrecisionPolicy
    except ImportError as exc:
        raise RuntimeError("This PyTorch build does not expose the required composable FSDP2 API.") from exc
    policy = MixedPrecisionPolicy(param_dtype=torch.bfloat16, reduce_dtype=torch.float32, output_dtype=torch.bfloat16)
    for block in reversed(model.layers):
        for expert in block.moe.experts:
            fully_shard(expert, mp_policy=policy)
        fully_shard(block, mp_policy=policy)
    fully_shard(model, mp_policy=policy)
    return model

def causal_lm_objective(model, input_ids: torch.Tensor, router_aux_weight: float = 0.01):
    if input_ids.ndim != 2 or input_ids.shape[1] < 2:
        raise ValueError("input_ids must be [batch, sequence] with sequence >= 2.")
    if router_aux_weight < 0:
        raise ValueError("router_aux_weight cannot be negative.")
    logits = model(input_ids[:, :-1])
    targets = input_ids[:, 1:]
    language_loss = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), targets.reshape(-1))
    auxiliary = model.router_aux_loss.float()
    total = language_loss + router_aux_weight * auxiliary
    return total, {"language_model_loss": float(language_loss.detach().cpu()), "router_aux_loss": float(auxiliary.detach().cpu()), "total_loss": float(total.detach().cpu())}

def train_microbatch(model, optimizer, input_ids: torch.Tensor, *, router_aux_weight: float = 0.01, max_grad_norm: float = 1.0, use_bf16: bool = True) -> dict:
    """Perform one optimizer update; caller controls data sampling and checkpoint cadence."""
    if max_grad_norm <= 0:
        raise ValueError("max_grad_norm must be positive.")
    device = next(model.parameters()).device
    optimizer.zero_grad(set_to_none=True)
    amp_enabled = device.type == "cuda" and use_bf16 and torch.cuda.is_bf16_supported()
    with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=amp_enabled):
        loss, metrics = causal_lm_objective(model, input_ids, router_aux_weight)
    if not torch.isfinite(loss):
        raise FloatingPointError("Non-finite training loss; optimizer update aborted.")
    loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
    if not torch.isfinite(torch.as_tensor(grad_norm)):
        optimizer.zero_grad(set_to_none=True)
        raise FloatingPointError("Non-finite gradient norm; optimizer update aborted.")
    optimizer.step()
    metrics["gradient_norm"] = float(torch.as_tensor(grad_norm).detach().cpu())
    metrics["bf16_autocast"] = bool(amp_enabled)
    return metrics

def save_training_checkpoint(path: str | Path, *, model, optimizer, step: int, config: dict, corpus_sha256: str, tokenizer_sha256: str, tokens_seen: int) -> str:
    """Write a trusted local checkpoint atomically; caller stores it privately."""
    if type(step) is not int or step < 0 or type(tokens_seen) is not int or tokens_seen < 0:
        raise ValueError("step and tokens_seen must be non-negative integers.")
    for label, digest in (("corpus_sha256", corpus_sha256), ("tokenizer_sha256", tokenizer_sha256)):
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"{label} must be a lowercase SHA-256 hex digest.")
    if torch.distributed.is_available() and torch.distributed.is_initialized() and torch.distributed.get_world_size() > 1:
        raise RuntimeError("Multi-rank checkpoint coordination is not implemented yet; refusing an unsafe partial checkpoint.")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    state = {"format": "jon2_moe_training_checkpoint_v1", "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(), "step": step, "tokens_seen": tokens_seen, "config": config, "corpus_sha256": corpus_sha256, "tokenizer_sha256": tokenizer_sha256, "python_rng_state": random.getstate(), "torch_rng_state": torch.get_rng_state(), "cuda_rng_state_all": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None}
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        torch.save(state, temp)
        with temp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()
    return hashlib.sha256(destination.read_bytes()).hexdigest()

def load_training_checkpoint(path: str | Path, *, model, optimizer, expected_config: dict, corpus_sha256: str, tokenizer_sha256: str) -> dict:
    """Restore only a trusted checkpoint produced by Jon2."""
    if torch.distributed.is_available() and torch.distributed.is_initialized() and torch.distributed.get_world_size() > 1:
        raise RuntimeError("Multi-rank checkpoint restore is not implemented yet.")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    if checkpoint.get("format") != "jon2_moe_training_checkpoint_v1":
        raise ValueError("Unsupported checkpoint format.")
    for key, expected in (("config", expected_config), ("corpus_sha256", corpus_sha256), ("tokenizer_sha256", tokenizer_sha256)):
        if checkpoint.get(key) != expected:
            raise ValueError(f"Checkpoint {key} does not match this training run.")
    model.load_state_dict(checkpoint["model_state"], strict=True)
    optimizer.load_state_dict(checkpoint["optimizer_state"])
    random.setstate(checkpoint["python_rng_state"])
    torch.set_rng_state(checkpoint["torch_rng_state"])
    if torch.cuda.is_available() and checkpoint.get("cuda_rng_state_all") is not None:
        torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state_all"])
    return {"step": int(checkpoint["step"]), "tokens_seen": int(checkpoint["tokens_seen"])}
