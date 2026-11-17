from __future__ import annotations

import json

import pytest
import torch

from ai_engine.sft_data import (
    IGNORE_INDEX,
    collate_sft_batch,
    encode_conversation,
    load_approved_sft_splits,
)
from ai_engine.tokenizer import ByteBPETokenizer


@pytest.fixture
def tokenizer():
    return ByteBPETokenizer()


def conversation():
    return [
        {"role": "user", "content": "عامل ايه؟"},
        {"role": "assistant", "content": "أنا بخير، شكرًا."},
        {"role": "user", "content": "قولها بالفصحى."},
        {"role": "assistant", "content": "أنا بخير، شكرًا لك."},
    ]


def test_only_assistant_content_and_end_marker_are_supervised(tokenizer):
    encoded = encode_conversation(conversation(), tokenizer, max_length=512)
    labels = encoded["labels"]
    supervised = [token for token in labels if token != IGNORE_INDEX]
    expected = (
        tokenizer.encode("أنا بخير، شكرًا.")
        + tokenizer.encode("\n")
        + tokenizer.encode("أنا بخير، شكرًا لك.")
        + tokenizer.encode("\n")
    )
    assert supervised == expected
    assert len(labels) == len(encoded["input_ids"])
    assert labels.count(IGNORE_INDEX) > len(supervised)


def test_user_prompt_is_context_but_never_a_target(tokenizer):
    encoded = encode_conversation(conversation(), tokenizer, max_length=512)
    decoded_targets = tokenizer.decode(
        [token for token in encoded["labels"] if token != IGNORE_INDEX]
    )
    assert "عامل ايه؟" not in decoded_targets
    assert "قولها بالفصحى" not in decoded_targets
    assert "أنا بخير" in decoded_targets


@pytest.mark.parametrize(
    "messages",
    [
        [{"role": "assistant", "content": "رد"}],
        [
            {"role": "user", "content": "سؤال"},
            {"role": "user", "content": "سؤال آخر"},
        ],
        [
            {"role": "user", "content": "سؤال"},
            {"role": "assistant", "content": "   "},
        ],
    ],
)
def test_rejects_incomplete_or_invalid_turns(tokenizer, messages):
    with pytest.raises(ValueError):
        encode_conversation(messages, tokenizer, max_length=512)


def test_rejects_oversized_conversation_instead_of_truncating(tokenizer):
    messages = [
        {"role": "user", "content": "س" * 100},
        {"role": "assistant", "content": "ج" * 100},
    ]
    with pytest.raises(ValueError, match="exceeding"):
        encode_conversation(messages, tokenizer, max_length=20)


def test_collator_masks_padding_and_keeps_targets():
    batch = collate_sft_batch(
        [
            {"input_ids": [1, 2, 3], "labels": [IGNORE_INDEX, 2, 3]},
            {"input_ids": [4, 5], "labels": [IGNORE_INDEX, 5]},
        ]
    )
    assert batch["input_ids"].shape == (2, 3)
    assert batch["labels"].tolist() == [
        [IGNORE_INDEX, 2, 3],
        [IGNORE_INDEX, 5, IGNORE_INDEX],
    ]
    assert batch["input_ids"].dtype == torch.long


def test_splits_by_conversation_and_requires_private_exact_file_approval(tmp_path, tokenizer):
    data_dir = tmp_path / "sft"
    data_dir.mkdir()
    source = data_dir / "approved.jsonl"
    records = [ {"messages": conversation()} for _ in range(10) ]
    raw = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    source.write_text(raw, encoding="utf-8")
    manifest = tmp_path / "source_approvals.json"
    import hashlib
    manifest.write_text(json.dumps({
        "approved_sources": [{
            "file": "approved.jsonl",
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "character_count": len(raw),
            "status": "APPROVED",
            "reviewer": "test reviewer",
            "review_date": "2026-11-13",
            "rights_basis": "test-only fixture",
            "intended_use": "research_training",
        }]
    }), encoding="utf-8")

    train, validation = load_approved_sft_splits(
        data_dir, manifest, tokenizer, max_length=512, seed=7
    )
    assert len(train) == 9
    assert len(validation) == 1
    assert {id(item) for item in train}.isdisjoint({id(item) for item in validation})


def test_rejects_unapproved_or_changed_jsonl(tmp_path, tokenizer):
    data_dir = tmp_path / "sft"
    data_dir.mkdir()
    source = data_dir / "dialogue.jsonl"
    source.write_text(json.dumps({"messages": conversation()}) + "\n", encoding="utf-8")
    manifest = tmp_path / "source_approvals.json"
    manifest.write_text('{"approved_sources": []}', encoding="utf-8")
    with pytest.raises(PermissionError):
        load_approved_sft_splits(data_dir, manifest, tokenizer, max_length=512)
