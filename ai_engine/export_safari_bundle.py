"""Export a private, original Jon2 PyTorch checkpoint for the Safari CPU runtime.

This exports weights only; it does not train, improve, or certify the model.
Run from the repository root:
  python ai_engine/export_safari_bundle.py --checkpoint /private/jon2-small.pt --output-dir /private/jon2-safari
The output directory contains manifest.json and weights.bin. Keep both private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from jon2_core import Jon2Transformer
from tokenizer import ByteBPETokenizer


FORMAT = "jon2-safari-f32-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_bundle(checkpoint_path: Path, output_dir: Path) -> dict:
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise TypeError("Jon2 checkpoint must be a dictionary.")
    required = {"config", "model_state", "tokenizer"}
    missing = required.difference(checkpoint)
    if missing:
        raise ValueError(
            "Safari export requires a native byte-BPE Jon2 checkpoint; missing: "
            + ", ".join(sorted(missing))
        )

    tokenizer = ByteBPETokenizer.from_dict(checkpoint["tokenizer"])
    config = dict(checkpoint["config"])
    if "vocab_size" in config:
        raise ValueError("Checkpoint config must not override tokenizer vocabulary size.")
    config["vocab_size"] = tokenizer.vocab_size

    model = Jon2Transformer(vocab_size=tokenizer.vocab_size, **{
        key: value for key, value in config.items() if key != "vocab_size"
    })
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.eval()

    state = model.state_dict()
    tied = state.get("output.weight")
    embedding = state.get("token_embedding.weight")
    if tied is None or embedding is None or not torch.equal(tied, embedding):
        raise ValueError("Jon2 output projection is not tied to token_embedding.weight.")

    tensor_order = [name for name in state.keys() if name != "output.weight"]
    chunks: list[bytes] = []
    tensors: dict[str, dict] = {}
    offset = 0
    for name in tensor_order:
        tensor = state[name].detach().cpu().to(dtype=torch.float32).contiguous()
        if not torch.isfinite(tensor).all().item():
            raise ValueError(f"Non-finite values in Jon2 tensor: {name}")
        # Explicit little-endian IEEE-754 float32, matching DataView.getFloat32(..., true).
        raw = tensor.numpy().astype("<f4", copy=False).tobytes(order="C")
        elements = tensor.numel()
        if len(raw) != elements * 4:
            raise ValueError(f"Unexpected float32 byte length for tensor: {name}")
        tensors[name] = {
            "shape": list(tensor.shape),
            "offset": offset,
            "elements": elements,
        }
        chunks.append(raw)
        offset += len(raw)

    weights = b"".join(chunks)
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / "weights.bin"
    manifest_path = output_dir / "manifest.json"
    weights_path.write_bytes(weights)

    manifest = {
        "format": FORMAT,
        "checkpoint": {
            "sha256": sha256_file(checkpoint_path),
            "filename": checkpoint_path.name,
        },
        "weights_sha256": hashlib.sha256(weights).hexdigest(),
        "byte_length": len(weights),
        "config": config,
        "tokenizer": tokenizer.to_dict(),
        "tensor_order": tensor_order,
        "tensors": tensors,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "weights": str(weights_path),
        "checkpoint_sha256": manifest["checkpoint"]["sha256"],
        "weights_sha256": manifest["weights_sha256"],
        "byte_length": len(weights),
        "tensor_count": len(tensor_order),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a native Jon2 byte-BPE checkpoint for the Safari CPU runtime."
    )
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = export_bundle(args.checkpoint.expanduser(), args.output_dir.expanduser())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Export only: this does not certify answer quality or iPhone performance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
