"""Experimental decoder-only MoE architecture for Jon2's 20B-class target.

This module defines architecture only. Constructing the default 20B model requires
large distributed memory and is intentionally not part of import-time behavior.
No pretrained weights, datasets, or external model files are loaded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn
import torch.nn.functional as F


@dataclass(frozen=True)
class MoE20BConfig:
    vocab_size: int = 65_536
    hidden_size: int = 4_096
    num_layers: int = 24
    num_attention_heads: int = 32
    num_key_value_heads: int = 8
    num_experts: int = 32
    experts_per_token: int = 4
    expert_intermediate_size: int = 2_048
    max_position_embeddings: int = 8_192
    rms_norm_eps: float = 1e-6
    rope_theta: float = 10_000.0
    tie_word_embeddings: bool = True

    def validate(self) -> None:
        positive = (
            self.vocab_size, self.hidden_size, self.num_layers,
            self.num_attention_heads, self.num_key_value_heads,
            self.num_experts, self.experts_per_token,
            self.expert_intermediate_size, self.max_position_embeddings,
        )
        if any(type(value) is not int or value <= 0 for value in positive):
            raise ValueError("All model dimensions must be positive integers.")
        if self.hidden_size % self.num_attention_heads:
            raise ValueError("hidden_size must divide evenly across attention heads.")
        if self.num_attention_heads % self.num_key_value_heads:
            raise ValueError("attention heads must be divisible by key/value heads.")
        if self.experts_per_token > self.num_experts:
            raise ValueError("experts_per_token cannot exceed num_experts.")
        if (self.hidden_size // self.num_attention_heads) % 2:
            raise ValueError("RoPE head dimension must be even.")
        if self.rms_norm_eps <= 0 or self.rope_theta <= 0:
            raise ValueError("Normalization epsilon and RoPE theta must be positive.")


def estimate_moe_parameters(config: MoE20BConfig) -> int:
    """Exact trainable parameter count for this bias-free, tied-embedding model."""
    config.validate()
    h = config.hidden_size
    head_dim = h // config.num_attention_heads
    kv_dim = config.num_key_value_heads * head_dim
    attention = 2 * h * h + 2 * h * kv_dim
    experts = config.num_experts * 3 * h * config.expert_intermediate_size
    router = h * config.num_experts
    norms = 2 * h
    embeddings = config.vocab_size * h
    final_norm = h
    output = 0 if config.tie_word_embeddings else config.vocab_size * h
    return (
        embeddings + final_norm + output
        + config.num_layers * (attention + experts + router + norms)
    )


def estimate_active_parameters(config: MoE20BConfig) -> int:
    """Approximate active parameters/token, including attention and selected experts."""
    total = estimate_moe_parameters(config)
    h = config.hidden_size
    head_dim = h // config.num_attention_heads
    kv_dim = config.num_key_value_heads * head_dim
    attention = 2 * h * h + 2 * h * kv_dim
    active_experts = config.experts_per_token * 3 * h * config.expert_intermediate_size
    router = h * config.num_experts
    norms = 2 * h
    return (
        config.vocab_size * h + h
        + config.num_layers * (attention + active_experts + router + norms)
    )


def default_20b_config() -> MoE20BConfig:
    """Return the proposed ~20B total-parameter configuration without allocating it."""
    return MoE20BConfig()


def default_20b_report() -> dict:
    """Describe the 20B target and storage requirements without creating tensors."""
    config = default_20b_config()
    parameters = estimate_moe_parameters(config)
    active = estimate_active_parameters(config)
    gib = 1024 ** 3
    return {
        "model": "Jon2 Arabic MoE 20B target",
        "total_parameters": parameters,
        "active_parameters_per_token_estimate": active,
        "weights_only_gib": {
            "bf16_fp16": round(parameters * 2 / gib, 2),
            "fp32": round(parameters * 4 / gib, 2),
            "int8_raw_lower_bound": round(parameters / gib, 2),
            "int4_raw_lower_bound": round(parameters * 0.5 / gib, 2),
        },
        "mixed_precision_adam_state_gib_estimate": round(parameters * 18 / gib, 2),
        "configuration": asdict(config),
        "weights_created": False,
        "weights_trained": False,
    }


class RMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        variance = x.float().pow(2).mean(dim=-1, keepdim=True)
        x = x * torch.rsqrt(variance + self.eps).to(dtype=x.dtype)
        return x * self.weight


def _apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    # x: [batch, heads, sequence, head_dim]
    first, second = x.chunk(2, dim=-1)
    rotated = torch.cat((-second, first), dim=-1)
    return x * cos + rotated * sin


class GroupedQueryAttention(nn.Module):
    def __init__(self, config: MoE20BConfig):
        super().__init__()
        h = config.hidden_size
        self.heads = config.num_attention_heads
        self.kv_heads = config.num_key_value_heads
        self.head_dim = h // self.heads
        kv_dim = self.kv_heads * self.head_dim
        self.q_proj = nn.Linear(h, h, bias=False)
        self.k_proj = nn.Linear(h, kv_dim, bias=False)
        self.v_proj = nn.Linear(h, kv_dim, bias=False)
        self.o_proj = nn.Linear(h, h, bias=False)
        inv_freq = 1.0 / (
            config.rope_theta ** (
                torch.arange(0, self.head_dim, 2, dtype=torch.float32) / self.head_dim
            )
        )
        self.register_buffer("inv_freq", inv_freq, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, sequence, hidden = x.shape
        q = self.q_proj(x).view(batch, sequence, self.heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch, sequence, self.kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch, sequence, self.kv_heads, self.head_dim).transpose(1, 2)

        positions = torch.arange(sequence, device=x.device, dtype=self.inv_freq.dtype)
        frequencies = torch.outer(positions, self.inv_freq)
        embedding = torch.cat((frequencies, frequencies), dim=-1)
        cos = embedding.cos().to(dtype=q.dtype)[None, None, :, :]
        sin = embedding.sin().to(dtype=q.dtype)[None, None, :, :]
        q = _apply_rope(q, cos, sin)
        k = _apply_rope(k, cos, sin)

        repeat = self.heads // self.kv_heads
        k = k.repeat_interleave(repeat, dim=1)
        v = v.repeat_interleave(repeat, dim=1)
        attended = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        attended = attended.transpose(1, 2).contiguous().view(batch, sequence, hidden)
        return self.o_proj(attended)


class SwiGLUExpert(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class SparseMoE(nn.Module):
    def __init__(self, config: MoE20BConfig):
        super().__init__()
        self.num_experts = config.num_experts
        self.top_k = config.experts_per_token
        self.router = nn.Linear(config.hidden_size, config.num_experts, bias=False)
        self.experts = nn.ModuleList([
            SwiGLUExpert(config.hidden_size, config.expert_intermediate_size)
            for _ in range(config.num_experts)
        ])
        self.last_aux_loss = torch.tensor(0.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, sequence, hidden = x.shape
        flat = x.reshape(-1, hidden)
        routing = self.router(flat).float()
        router_probabilities = F.softmax(routing, dim=-1)
        weights, indices = torch.topk(routing, self.top_k, dim=-1)
        weights = F.softmax(weights, dim=-1).to(dtype=x.dtype)
        # Switch-style load-balancing auxiliary loss discourages expert collapse.
        assignment_fraction = F.one_hot(indices, num_classes=self.num_experts).float()
        assignment_fraction = assignment_fraction.sum(dim=(0, 1)) / max(
            1, flat.shape[0] * self.top_k
        )
        mean_probability = router_probabilities.mean(dim=0)
        self.last_aux_loss = self.num_experts * torch.sum(
            assignment_fraction * mean_probability
        )
        output = torch.zeros_like(flat)

        # Dispatch only tokens selected for each expert. No unselected expert runs.
        for expert_id, expert in enumerate(self.experts):
            token_rows, slots = torch.where(indices == expert_id)
            if token_rows.numel() == 0:
                continue
            expert_input = flat.index_select(0, token_rows)
            expert_output = expert(expert_input)
            contribution = expert_output * weights[token_rows, slots].unsqueeze(-1)
            output.index_add_(0, token_rows, contribution)

        return output.view(batch, sequence, hidden)


class Jon2MoEBlock(nn.Module):
    def __init__(self, config: MoE20BConfig):
        super().__init__()
        self.attention_norm = RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.attention = GroupedQueryAttention(config)
        self.moe_norm = RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.moe = SparseMoE(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attention(self.attention_norm(x))
        return x + self.moe(self.moe_norm(x))


class Jon2MoEForCausalLM(nn.Module):
    """Decoder-only sparse MoE language model. Do not instantiate default 20B on a phone."""

    def __init__(self, config: MoE20BConfig):
        super().__init__()
        config.validate()
        self.config = config
        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
        self.layers = nn.ModuleList([Jon2MoEBlock(config) for _ in range(config.num_layers)])
        self.norm = RMSNorm(config.hidden_size, config.rms_norm_eps)
        self.lm_head = None if config.tie_word_embeddings else nn.Linear(
            config.hidden_size, config.vocab_size, bias=False
        )

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence].")
        if input_ids.shape[1] > self.config.max_position_embeddings:
            raise ValueError("Input sequence exceeds configured context length.")
        hidden = self.embed_tokens(input_ids)
        for layer in self.layers:
            hidden = layer(hidden)
        hidden = self.norm(hidden)
        if self.lm_head is None:
            return F.linear(hidden, self.embed_tokens.weight)
        return self.lm_head(hidden)

    @property
    def router_aux_loss(self) -> torch.Tensor:
        losses = [layer.moe.last_aux_loss for layer in self.layers]
        if not losses:
            return torch.zeros((), device=self.embed_tokens.weight.device)
        return torch.stack(losses).mean()

    def architecture_report(self) -> dict:
        return {
            "config": asdict(self.config),
            "estimated_total_parameters": estimate_moe_parameters(self.config),
            "estimated_active_parameters_per_token": estimate_active_parameters(self.config),
            "weights_created": True,
            "weights_trained": False,
            "warning": "A newly initialized model has random weights and cannot chat usefully until trained.",
        }


if __name__ == "__main__":
    import json
    print(json.dumps(default_20b_report(), indent=2))
