"""Arabic-first answer cleanup and conservative output-quality checks.

These checks measure observable text quality only. They do not claim to prove
semantic correctness, factuality, or grammatical perfection.
"""
from __future__ import annotations

import re
import unicodedata


_ARABIC_LETTERS = re.compile(r"[\u0621-\u064A\u066E-\u06D3]")
_ALLOWED = re.compile(
    r"^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»\"'\-–—:]+$"
)
_ROLE_PREFIX = re.compile(r"^(?:Jon2|المساعد|المستخدم)\s*[:：]\s*", re.IGNORECASE)
_ROLE_LINE = re.compile(r"(?m)^\s*(?:المستخدم|Jon2|المساعد)\s*[:：].*$")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([،؛؟.!…])")
_MULTI_PUNCTUATION = re.compile(r"([،؛؟.!]){2,}")
_SPACES = re.compile(r"[ \t]{2,}")
_WORD = re.compile(r"[\u0621-\u064A\u066E-\u06D3]+|[0-9٠-٩]+")


def clean_generated_answer(answer: str) -> str:
    """Normalize harmless formatting noise without rewriting Arabic words."""
    if not isinstance(answer, str):
        return ""
    text = unicodedata.normalize("NFC", answer)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("\ufffd", "")
    text = _ROLE_LINE.sub("", text)
    text = text.strip()
    text = _ROLE_PREFIX.sub("", text).strip()
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    text = _MULTI_PUNCTUATION.sub(r"\1", text)
    text = _SPACES.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(" \n\t")


def diagnose_arabic_answer(answer: str, question: str | None = None) -> dict:
    """Return transparent surface metrics; semantic review remains mandatory."""
    text = clean_generated_answer(answer)
    visible = [char for char in text if not char.isspace()]
    arabic_count = len(_ARABIC_LETTERS.findall(text))
    words = _WORD.findall(text)
    normalized_words = [word.casefold() for word in words]
    unique_ratio = len(set(normalized_words)) / max(1, len(normalized_words))
    sentences = [
        part.strip()
        for part in re.split(r"[.!؟!\n]+", text)
        if part.strip()
    ]

    warnings: list[str] = []
    if len(text) < 12:
        warnings.append("answer_too_short")
    if len(normalized_words) < 3:
        warnings.append("too_few_words")
    if arabic_count / max(1, len(visible)) < 0.70:
        warnings.append("low_arabic_ratio")
    if len(normalized_words) >= 12 and unique_ratio < 0.35:
        warnings.append("low_vocabulary_variety")
    if re.search(r"(.)\1{3,}", text):
        warnings.append("repeated_character_run")

    # Detect repeated complete sentences, ignoring punctuation and whitespace.
    sentence_keys = [
        re.sub(r"[^\u0621-\u064A\u066E-\u06D3\w]", "", item).casefold()
        for item in sentences
    ]
    nonempty_keys = [item for item in sentence_keys if item]
    if len(nonempty_keys) != len(set(nonempty_keys)):
        warnings.append("repeated_sentence")

    for size in (2, 3, 4):
        if len(normalized_words) >= size * 3 and any(
            normalized_words[i:i + size]
            == normalized_words[i + size:i + 2 * size]
            == normalized_words[i + 2 * size:i + 3 * size]
            for i in range(len(normalized_words) - size * 3 + 1)
        ):
            warnings.append("repeated_phrase")
            break

    question_words = set(_WORD.findall(clean_generated_answer(question or "")))
    answer_words = set(normalized_words)
    overlap = len(question_words & answer_words) / max(1, len(question_words))
    if question_words and overlap < 0.08:
        warnings.append("low_lexical_overlap_review")

    return {
        "character_count": len(text),
        "word_count": len(normalized_words),
        "sentence_count": len(sentences),
        "arabic_character_ratio": round(arabic_count / max(1, len(visible)), 3),
        "unique_word_ratio": round(unique_ratio, 3),
        "question_word_overlap": round(overlap, 3) if question_words else None,
        "warnings": warnings,
        "semantic_correctness_verified": False,
        "human_semantic_review_required": True,
    }


def validate_arabic_answer(answer: str, question: str | None = None) -> bool:
    """Fail closed on malformed, non-Arabic, or obviously looping output."""
    text = clean_generated_answer(answer)
    if len(text) < 12 or len(text) > 4000:
        return False
    if not _ALLOWED.fullmatch(text):
        return False

    visible = [char for char in text if not char.isspace()]
    arabic_count = len(_ARABIC_LETTERS.findall(text))
    if arabic_count / max(1, len(visible)) < 0.70:
        return False

    report = diagnose_arabic_answer(text, question)
    rejected = {
        "answer_too_short",
        "too_few_words",
        "low_vocabulary_variety",
        "repeated_character_run",
        "repeated_sentence",
        "repeated_phrase",
    }
    return not (rejected & set(report["warnings"]))
