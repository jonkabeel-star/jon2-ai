"""Report Arabic character and vocabulary coverage without rewriting source text."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ARABIC_LETTERS = list("ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي")
DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")
WORD_RE = re.compile(r"[\u0600-\u06FF]+", re.UNICODE)


def normalize_word(word: str) -> str:
    """Normalize only for aggregate counting; never modify the training corpus."""
    word = unicodedata.normalize("NFC", word)
    word = DIACRITICS.sub("", word)
    return word.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def analyze_text(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    char_counts = Counter(ch for ch in text if "ARABIC" in unicodedata.name(ch, ""))
    letter_counts = Counter(
        ch for ch in text
        if "ARABIC" in unicodedata.name(ch, "") and unicodedata.category(ch).startswith("L")
    )
    words = [normalize_word(w) for w in WORD_RE.findall(text)]
    words = [w for w in words if w]
    word_counts = Counter(words)
    total_letters = sum(letter_counts.values())
    total_arabic_chars = sum(char_counts.values())

    frequencies = []
    for letter in ARABIC_LETTERS:
        count = letter_counts[letter]
        frequencies.append({
            "letter": letter,
            "count": count,
            "percentage_of_arabic_letters": round(100 * count / total_letters, 4) if total_letters else 0.0,
        })

    return {
        "total_characters": len(text),
        "arabic_characters_including_marks": total_arabic_chars,
        "arabic_letters": total_letters,
        "unique_arabic_letters_seen": sum(1 for ch in ARABIC_LETTERS if letter_counts[ch]),
        "arabic_alphabet_size": len(ARABIC_LETTERS),
        "missing_arabic_letters": [ch for ch in ARABIC_LETTERS if not letter_counts[ch]],
        "letter_frequencies": frequencies,
        "arabic_word_tokens": len(words),
        "unique_normalized_words": len(word_counts),
        "lexical_diversity": round(len(word_counts) / len(words), 4) if words else 0.0,
        "most_common_words": [
            {"word": word, "count": count}
            for word, count in word_counts.most_common(30)
        ],
        "normalization_note": "Word normalization is used only for aggregate counts; source text is unchanged.",
        "interpretation_note": (
            "Observed frequencies describe this corpus only. They are not target quotas or "
            "proof of semantic understanding. Do not artificially equalize letter counts."
        ),
    }


def analyze_directory(data_dir: Path) -> dict:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")
    files = sorted(p for p in data_dir.rglob("*.txt") if p.is_file())
    if not files:
        raise ValueError(f"No .txt training files found in {data_dir}")
    combined = []
    file_reports = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        combined.append(text)
        file_reports.append({
            "file": path.relative_to(data_dir).as_posix(),
            **analyze_text(text),
        })
    return {
        "report_version": 1,
        "files": file_reports,
        "combined": analyze_text("\n".join(combined)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Arabic character and vocabulary coverage.")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = analyze_directory(Path(args.data))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
