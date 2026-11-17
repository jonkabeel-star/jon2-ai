from __future__ import annotations

import pytest

from ai_engine.sft_training import (
    MIN_SFT_ASSISTANT_TOKENS,
    MIN_SFT_CONVERSATIONS,
    _validate_new_output_path,
)


def test_sft_readiness_gate_is_not_a_pretraining_token_parameter_gate():
    assert MIN_SFT_CONVERSATIONS == 50
    assert MIN_SFT_ASSISTANT_TOKENS == 10_000


def test_sft_refuses_to_overwrite_original_checkpoint(tmp_path):
    source = tmp_path / "jon2-last.pt"
    source.write_bytes(b"private checkpoint fixture")
    with pytest.raises(ValueError, match="source checkpoint is protected"):
        _validate_new_output_path(source, source)
    assert source.read_bytes() == b"private checkpoint fixture"


def test_sft_refuses_existing_output_file(tmp_path):
    source = tmp_path / "jon2-last.pt"
    output = tmp_path / "jon2-sft.pt"
    source.write_bytes(b"source")
    output.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError, match="already exists"):
        _validate_new_output_path(source, output)
    assert source.read_bytes() == b"source"
    assert output.read_bytes() == b"do not overwrite"
