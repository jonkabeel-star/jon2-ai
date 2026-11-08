"""Auditable capacity presets for training the original Jon2 model.

These are architecture configurations, not pretrained weights. Selecting a
profile never allocates hardware, downloads a model, or starts training.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    width: int
    heads: int
    layers: int
    context: int
    tokenizer_vocab_size: int
    batch_size: int
    description: str


PROFILES = {
    "cpu_small": ModelProfile(
        name="cpu_small", width=128, heads=4, layers=4, context=256,
        tokenizer_vocab_size=1024, batch_size=4,
        description="Small experimental model for limited CPU memory.",
    ),
    "balanced": ModelProfile(
        name="balanced", width=192, heads=6, layers=6, context=512,
        tokenizer_vocab_size=2048, batch_size=4,
        description="Medium research model; needs a much larger corpus and long CPU training.",
    ),
    "advanced": ModelProfile(
        name="advanced", width=256, heads=8, layers=8, context=1024,
        tokenizer_vocab_size=4096, batch_size=2,
        description="Larger research model; not suitable for an iPhone or a short free CPU session.",
    ),
    "arabic_30m": ModelProfile(
        name="arabic_30m", width=512, heads=8, layers=8, context=1024,
        tokenizer_vocab_size=8192, batch_size=1,
        description="Approximately 30M-parameter Arabic-focused from-scratch research architecture; requires a high-memory GPU and a very large approved corpus. Configuration only.",
    ),
    "large_research": ModelProfile(
        name="large_research", width=384, heads=8, layers=10, context=2048,
        tokenizer_vocab_size=8192, batch_size=1,
        description="Large from-scratch experiment; requires substantial compute and a very large approved corpus.",
    ),
}


def estimate_parameters(*, width: int, layers: int, context: int, vocab_size: int) -> int:
    """Exact parameter count for Jon2Transformer with tied token/output embeddings."""
    values = (width, layers, context, vocab_size)
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError("Model dimensions must be positive integers.")
    # Token + position embeddings, TransformerEncoderLayer blocks (MHA + 4x FFN
    # + two LayerNorms), and final LayerNorm. Output projection is weight-tied.
    return (
        vocab_size * width
        + context * width
        + layers * (12 * width * width + 13 * width)
        + 2 * width
    )


def describe_profile(name: str) -> dict:
    try:
        profile = PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown Jon2 model profile: {name}") from exc
    result = asdict(profile)
    result["estimated_parameters"] = estimate_parameters(
        width=profile.width,
        layers=profile.layers,
        context=profile.context,
        vocab_size=profile.tokenizer_vocab_size,
    )
    result["estimated_fp32_weights_gib"] = round(
        result["estimated_parameters"] * 4 / (1024 ** 3), 4
    )
    result["training_status"] = "configuration_only_no_weights_created"
    return result


def list_profiles() -> list[dict]:
    return [describe_profile(name) for name in PROFILES]
