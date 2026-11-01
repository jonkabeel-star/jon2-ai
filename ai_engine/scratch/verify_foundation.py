"""Verify the original Jon2 model foundation without loading a pretrained model.

Run from the repository root:
    python ai_engine/scratch/verify_foundation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import torch

from jon2_core import Jon2Transformer
from tokenizer import ByteBPETokenizer


def main() -> None:
    torch.manual_seed(2026)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))

    # The tokenizer is trained only on this tiny, in-memory project test phrase.
    sample = "مرحبًا بك في Jon2 AI. هذا اختبار عربي."
    tokenizer = ByteBPETokenizer.train(sample, vocab_size=280, min_frequency=1)
    encoded = tokenizer.encode(sample)
    decoded = tokenizer.decode(encoded)
    assert decoded == sample, "Arabic tokenizer round-trip failed."

    # Two separately initialized models must not share identical random weights.
    first = Jon2Transformer(
        vocab_size=tokenizer.vocab_size,
        width=32,
        heads=4,
        layers=2,
        context=16,
        dropout=0.0,
    ).eval()
    second = Jon2Transformer(
        vocab_size=tokenizer.vocab_size,
        width=32,
        heads=4,
        layers=2,
        context=16,
        dropout=0.0,
    ).eval()

    first_parameters = list(first.parameters())
    second_parameters = list(second.parameters())
    assert any(
        not torch.equal(left, right)
        for left, right in zip(first_parameters, second_parameters)
    ), "Independent models unexpectedly have identical initialization."

    # Forward pass: each input position predicts a distribution over vocabulary.
    token_ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    with torch.inference_mode():
        logits = first(token_ids)
    assert logits.shape == (1, 4, tokenizer.vocab_size), (
        f"Unexpected output shape: {tuple(logits.shape)}"
    )

    # Causal check: changing a future token must not alter earlier-position logits.
    changed = token_ids.clone()
    changed[0, 3] = 5
    with torch.inference_mode():
        original_logits = first(token_ids)
        changed_logits = first(changed)
    assert torch.allclose(
        original_logits[:, :3, :],
        changed_logits[:, :3, :],
        atol=1e-6,
        rtol=1e-6,
    ), "Causal mask failed: future token affected earlier predictions."

    # Confirm that this verification path did not import a pretrained-model stack.
    assert "transformers" not in sys.modules, (
        "Unexpected transformers import in the from-scratch verification."
    )

    print("PASS: Arabic byte-BPE round-trip")
    print("PASS: random model initialization")
    print("PASS: Transformer forward pass and output dimensions")
    print("PASS: causal attention mask")
    print("PASS: no Transformers/pretrained model was loaded")
    print("NOTE: this verifies architecture only; the model is not trained yet.")


if __name__ == "__main__":
    main()
