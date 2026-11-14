"""Conservative Arabic output diagnostics; never a semantic quality judge."""
import re

# This is a conservative output sanity check, not a proof of factual accuracy.
_ALLOWED_ANSWER = re.compile(
    r"^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»\"'\-]+$"
)
_ARABIC_LETTERS = re.compile(r"[\u0621-\u064A\u066E-\u06D3]")
_MULTI_STEP_OR_EXPLANATORY = re.compile(
    r"(اشرح|وضح|فسر|حلل|قارن|استنتج|اذكر|رتب|بيّن|بيّن|لماذا|ما السبب)"
)


def validate_generated_answer(answer: str) -> bool:
    """Reject empty, trivially short, corrupted, mixed-script, or looping output."""
    if not isinstance(answer, str):
        return False
    answer = answer.strip()
    if len(answer) < 4 or len(answer) > 4000:
        return False
    if not _ALLOWED_ANSWER.fullmatch(answer):
        return False

    visible = [char for char in answer if not char.isspace()]
    arabic_count = len(_ARABIC_LETTERS.findall(answer))
    if arabic_count / max(1, len(visible)) < 0.70:
        return False

    if re.search(r"(.)\1{3,}", answer):
        return False
    if re.search(r"(.{2,8})\1{2,}", answer):
        return False

    words = answer.split()
    if len(words) >= 8:
        for size in (1, 2, 3):
            if any(
                words[index:index + size] == words[index + size:index + 2 * size]
                == words[index + 2 * size:index + 3 * size]
                for index in range(len(words) - 3 * size + 1)
            ):
                return False
    return True


def diagnose_answer(answer: str, prompt: str | None = None) -> dict:
    """Report surface and prompt-length warning signals; semantic review is always required."""
    text = answer.strip() if isinstance(answer, str) else ""
    prompt_text = prompt.strip() if isinstance(prompt, str) else ""
    words = re.findall(r"\S+", text)
    visible = [char for char in text if not char.isspace()]
    arabic = len(_ARABIC_LETTERS.findall(text))
    unique_ratio = len(set(words)) / max(1, len(words))
    repeated_trigram = any(
        words[index:index + 3] == words[index + 3:index + 6]
        for index in range(max(0, len(words) - 5))
    )
    warnings = []
    if len(text) < 20:
        warnings.append("very_short_answer")
    if len(words) < 4:
        warnings.append("very_few_words")
    if arabic / max(1, len(visible)) < 0.70:
        warnings.append("low_arabic_character_ratio")
    if len(words) >= 8 and unique_ratio < 0.45:
        warnings.append("low_unique_word_ratio")
    if repeated_trigram:
        warnings.append("repeated_three_word_sequence")
    if not text:
        warnings.append("empty_answer")

    prompt_requires_explanation = bool(_MULTI_STEP_OR_EXPLANATORY.search(prompt_text))
    if prompt_requires_explanation and len(words) < 6:
        warnings.append("possibly_incomplete_for_explanatory_prompt")

    return {
        "character_count": len(text),
        "word_count": len(words),
        "arabic_character_ratio": round(arabic / max(1, len(visible)), 3),
        "unique_word_ratio": round(unique_ratio, 3),
        "prompt_requires_explanation": prompt_requires_explanation,
        "surface_warnings": warnings,
        "human_semantic_review_required": True,
        "semantic_quality_assessed": False,
    }
